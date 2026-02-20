import json
import math
from hard_feasibility_checks import FixedWingHardGate, RotaryWingHardGate
from hard_feasibility_checks import haversine_nm

with open("aircraft_parameters.json") as f:
    aircraft_data = json.load(f)

with open("location_params.json") as f:
    location_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)

with open("alternate_airports.json") as f:
    alternate_data = json.load(f)


def build_aircraft(ac_name, ac_type):

    cat = next(c for c in aircraft_data if c.lower() == ac_type.lower())
    model = next(m for m in aircraft_data[cat] if m.lower() == ac_name.lower())
    params = aircraft_data[cat][model]

    def get_val(key, default=0):
        return params.get(key, {}).get("value", default)

    def parse_power(val):
        if isinstance(val, str) and "x" in val.lower():
            a, b = val.lower().split("x")
            return float(a) * float(b)
        try:
            return float(val)
        except:
            return 0

    return {
        "type": "fixed" if "fixed" in ac_type.lower() else "rotary",
        "empty": get_val("Empty Weight (OEW)") or get_val("Empty Weight"),
        "mtow": get_val("Max Takeoff Weight (MTOW)") or get_val("MTOW"),
        "mlw": get_val("Max Landing Weight") or get_val("MTOW"),
        "takeoff_base": get_val("Takeoff Distance"),
        "landing_base": get_val("Landing Distance"),
        "roc": get_val("Rate of Climb") or get_val("ROC"),
        "roc_loss": get_val("ROC loss per 1000 ft") / 100,
        "cruise": get_val("Cruise Speed") or get_val("Cruised Speed"),
        "fuel_flow": get_val("Cruise") or get_val("Phase Cruise"),
        "climb_fuel_rate": get_val("Phase Climb") or get_val("Cruise"),
        "reserve_min": get_val("Reserve Policy") or get_val("Phase Reserve") or 30,
        "engine_power": parse_power(get_val("Max Continuous Power")),
        "hover_ceiling_oge": get_val("Hover Ceiling OGE"),
        "to_da_sensitivity": get_val("Takeoff Increase per 1000 ft DA") / 100,
        "min_climb_margin": 0.01,
        "min_power_margin": 0.05,
        "min_visibility": 5,
        "max_crosswind": get_val("Max Crosswind") or 20,
        "cg_min": 20,
        "cg_max": 30,
        "cg_current": 25
    }

def compute_leg_fuel(ac, origin, dest, distance_nm):

    cruise_speed = ac["cruise"]
    cruise_rate = ac["fuel_flow"]
    climb_rate = ac["climb_fuel_rate"]

    delta_alt = dest["elevation_ft"] - origin["elevation_ft"]
    roc = ac["roc"]

    # ---- Climb ----
    if delta_alt > 0 and roc > 0:
        climb_time_hr = (delta_alt / roc) / 60
        fuel_climb = climb_rate * climb_time_hr
    else:
        fuel_climb = 0

    # ---- Cruise ----
    cruise_time_hr = distance_nm / cruise_speed if cruise_speed > 0 else 0
    fuel_cruise = cruise_rate * cruise_time_hr

    # ---- Descent ----
    descent_time_hr = abs(delta_alt / roc) / 60 if roc > 0 else 0
    fuel_descent = cruise_rate * 0.5 * descent_time_hr

    total = fuel_climb + fuel_cruise + fuel_descent

    return total, fuel_climb, fuel_cruise, fuel_descent


def find_best_alternate(ac, evaluator, current_origin_key, current_origin,
                        fuel_remaining, reserve_fuel):

    best_option = None
    best_distance = float("inf")

    for key, alt in alternate_data["alternates"].items():

        distance_nm = haversine_nm(
            current_origin["coords"][0],
            current_origin["coords"][1],
            alt["coords"][0],
            alt["coords"][1]
        )

        fuel_needed, _, _, _ = compute_leg_fuel(ac, current_origin, alt, distance_nm)

        usable_fuel = fuel_remaining - reserve_fuel

        if fuel_needed > usable_fuel:
            continue

            alt = find_best_alternate(
                ac,
                evaluator,
                current_origin_key,
                current_origin,
                fuel_remaining,
                reserve_fuel
            )

            if alt is not None:
                mission_status = "DIVERTED"
                leg_results.append({
                    "diverted_to": alt["alternate"],
                    "distance_nm": alt["distance_nm"],
                    "fuel_used": alt["fuel_required"]
                })
                fuel_remaining -= alt["fuel_required"]
                break
            else:
                mission_status = "FAIL_NO_ALTERNATE"
                leg_results.append({
                    "mission_abort": True,
                    "reason": "No reachable alternate"
                })
                break


        # Build leg for hard gate landing check
        leg = {
            "origin": current_origin,
            "destination": alt,
            "distance_nm": distance_nm,
            "payload_kg": 0,  # assume delivery complete
            "fuel_onboard_kg": fuel_remaining - fuel_needed
        }

        hard_result = evaluator.evaluate(ac, leg)

        if hard_result["hard_gate_overall_status"] == "FAIL":
            continue

        if distance_nm < best_distance:
            best_distance = distance_nm
            best_option = {
                "alternate": key,
                "distance_nm": round(distance_nm, 2),
                "fuel_required": round(fuel_needed, 2)
            }

    return best_option


final_output = {
    "mission_id": mission_data["mission_id"],
    "dynamic_mission_result": {}
}

origin_key = mission_data["origin"].lower()
origin = location_data["locations"][origin_key]

deliveries = mission_data["deliveries"]

for aircraft in mission_data["assigned_fleet"]:

    ac_name = aircraft["aircraft_name"]
    ac_type = aircraft["type"]
    ac = build_aircraft(ac_name, ac_type)

    evaluator = FixedWingHardGate() if ac["type"] == "fixed" else RotaryWingHardGate()

    payload_remaining = mission_data["total_payload_kg"]
    fuel_remaining = aircraft["fuel_kg"]
    reserve_fuel = ac["fuel_flow"] * (ac["reserve_min"] / 60)

    current_origin_key = origin_key
    current_origin = origin

    leg_results = []
    mission_status = "PASS"

    total_fuel_used = 0
    total_time_hr = 0
    total_distance_nm = 0
    payload_delivered_kg = 0

    for delivery in deliveries:

        dest_key = delivery["destination"].lower()
        dest = location_data["locations"][dest_key]

        distance_nm = haversine_nm(
            current_origin["coords"][0],
            current_origin["coords"][1],
            dest["coords"][0],
            dest["coords"][1]
        )

        # Time Calc
        delta_alt = dest["elevation_ft"] - current_origin["elevation_ft"]
        climb_time = (delta_alt / ac["roc"]) / 60 if delta_alt > 0 and ac["roc"] > 0 else 0
        cruise_time = distance_nm / ac["cruise"] if ac["cruise"] > 0 else 0
        descent_time = abs(delta_alt / ac["roc"]) / 60 if ac["roc"] > 0 else 0
        leg_time = climb_time + cruise_time + descent_time

        fuel_needed, fc, fru, fd = compute_leg_fuel(ac, current_origin, dest, distance_nm)

        usable_fuel = fuel_remaining - reserve_fuel

        # Hard stop
        if fuel_needed > usable_fuel:
            mission_status = "FAIL_FUEL_BEFORE_DEST"

            # Try alternate
            # Try alternate
            alt_option = find_best_alternate(
                ac,
                evaluator,
                current_origin_key,
                current_origin,
                fuel_remaining,
                reserve_fuel
            )

            if alt_option:
                leg_results.append({
                    "diverted_to": alt_option["alternate"],
                    "reason": "Insufficient fuel for planned leg"
                })
                fuel_remaining -= alt_option["fuel_required"]
                total_fuel_used += alt_option["fuel_required"] # Add alt fuel
                break
            else:
                leg_results.append({
                    "mission_abort": True,
                    "reason": "Insufficient fuel even for alternate"
                })
                break

        # Normal leg execution
        fuel_remaining -= fuel_needed
        payload_remaining -= delivery["weight_kg"]

        total_fuel_used += fuel_needed
        total_distance_nm += distance_nm
        total_time_hr += leg_time
        payload_delivered_kg += delivery["weight_kg"]

        leg = {
            "origin": current_origin,
            "destination": dest,
            "distance_nm": distance_nm,
            "payload_kg": payload_remaining,
            "fuel_onboard_kg": fuel_remaining
        }

        hard_result = evaluator.evaluate(ac, leg)

        if hard_result["hard_gate_overall_status"] == "FAIL":
            mission_status = "FAIL_HARD_GATE"

        # Tactical Info (Simulated)
        threat_level = dest.get("security_threat", "Low")
        is_hotspot = dest.get("is_hotspot", False)

        leg_results.append({
            "from": current_origin_key,
            "to": dest_key,
            "fuel_used": round(fuel_needed, 2),
            "fuel_remaining": round(fuel_remaining, 2),
            "hard_gate_status": hard_result["hard_gate_overall_status"],
            "tactical": {
                "threat_level": threat_level,
                "hotspot_active": is_hotspot
            }
        })

        current_origin = dest
        current_origin_key = dest_key
        
        # REFUELING AT ELEMENT (Universal Refueling Assumption)
        # Refuel back to initial dispatch load
        fuel_remaining = aircraft["fuel_kg"] 

    # Return to base
    distance_nm = haversine_nm(
        current_origin["coords"][0],
        current_origin["coords"][1],
        origin["coords"][0],
        origin["coords"][1]
    )
    
    # We create a virtual leg output for Refueling if needed? 
    # For now, just implicit.

    fuel_rtb, _, _, _ = compute_leg_fuel(ac, current_origin, origin, distance_nm)

    if fuel_rtb > (fuel_remaining - reserve_fuel):
        mission_status = "FAIL_RETURN_BASE"

    else:
        fuel_remaining -= fuel_rtb
        
        # Add stats for RTB
        total_fuel_used += fuel_rtb
        total_distance_nm += distance_nm
        
        delta_alt = origin["elevation_ft"] - current_origin["elevation_ft"]
        climb_time = (delta_alt / ac["roc"]) / 60 if delta_alt > 0 and ac["roc"] > 0 else 0
        cruise_time = distance_nm / ac["cruise"] if ac["cruise"] > 0 else 0
        descent_time = abs(delta_alt / ac["roc"]) / 60 if ac["roc"] > 0 else 0
        total_time_hr += (climb_time + cruise_time + descent_time)

    final_output["dynamic_mission_result"][ac_name] = {
        "mission_status": mission_status,
        "final_fuel_remaining": round(fuel_remaining, 2),
        "total_fuel_used_kg": round(total_fuel_used, 2),
        "total_time_hr": round(total_time_hr, 2),
        "total_distance_nm": round(total_distance_nm, 2),
        "total_payload_delivered_kg": payload_delivered_kg,
        "legs": leg_results
    }


with open("dynamic_mission_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Dynamic Mission Gate (REALISTIC) completed.")

import json
import math
from hard_feasibility_checks import FixedWingHardGate, RotaryWingHardGate
from hard_feasibility_checks import haversine_nm

# ============================================================
# LOAD DATA
# ============================================================

with open("aircraft_parameters.json") as f:
    aircraft_data = json.load(f)

with open("location_params.json") as f:
    location_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)

with open("alternate_airports.json") as f:
    alternate_data = json.load(f)


# ============================================================
# BUILD AIRCRAFT
# ============================================================

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


# ============================================================
# FUEL CALCULATION
# ============================================================

def compute_leg_fuel(ac, origin, dest, distance_nm):

    cruise_speed = ac["cruise"]
    cruise_rate = ac["fuel_flow"]
    climb_rate = ac["climb_fuel_rate"]
    roc = ac["roc"]

    delta_alt = dest["elevation_ft"] - origin["elevation_ft"]

    # Climb
    if delta_alt > 0 and roc > 0:
        climb_time_hr = (delta_alt / roc) / 60
        fuel_climb = climb_rate * climb_time_hr
    else:
        fuel_climb = 0

    # Cruise
    cruise_time_hr = distance_nm / cruise_speed if cruise_speed > 0 else 0
    fuel_cruise = cruise_rate * cruise_time_hr

    # Descent
    descent_time_hr = abs(delta_alt / roc) / 60 if roc > 0 else 0
    fuel_descent = cruise_rate * 0.5 * descent_time_hr

    total = fuel_climb + fuel_cruise + fuel_descent

    return total, fuel_climb, fuel_cruise, fuel_descent


# ============================================================
# ALTERNATE SELECTION
# ============================================================

def find_best_alternate(ac, evaluator, current_origin_key,
                        current_origin, fuel_remaining, reserve_fuel):

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

        leg = {
            "origin": current_origin,
            "destination": alt,
            "distance_nm": distance_nm,
            "payload_kg": 0,
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


# ============================================================
# MAIN SIMULATION
# ============================================================

final_output = {
    "mission_id": mission_data["mission_id"],
    "aircraft_simulation": {}
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

    mission_status = "PASS"
    legs_output = []

    for delivery in deliveries:

        dest_key = delivery["destination"].lower()
        dest = location_data["locations"][dest_key]

        distance_nm = haversine_nm(
            current_origin["coords"][0],
            current_origin["coords"][1],
            dest["coords"][0],
            dest["coords"][1]
        )

        fuel_needed, fc, fru, fd = compute_leg_fuel(ac, current_origin, dest, distance_nm)
        usable_fuel = fuel_remaining - reserve_fuel

        if fuel_needed > usable_fuel:

            alt = find_best_alternate(
                ac, evaluator,
                current_origin_key,
                current_origin,
                fuel_remaining,
                reserve_fuel
            )

            if alt:
                mission_status = "DIVERTED"
                fuel_remaining -= alt["fuel_required"]
                legs_output.append({
                    "diverted_to": alt["alternate"],
                    "fuel_used": alt["fuel_required"]
                })
                break
            else:
                mission_status = "FAIL_NO_ALTERNATE"
                break

        # Update fuel
        fuel_remaining -= fuel_needed

        # Evaluate hard gate after landing
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

        legs_output.append({
            "from": current_origin_key,
            "to": dest_key,
            "fuel_used": round(fuel_needed, 2),
            "fuel_remaining": round(fuel_remaining, 2),
            "hard_gate_status": hard_result["hard_gate_overall_status"]
        })

        payload_remaining -= delivery["weight_kg"]
        current_origin = dest
        current_origin_key = dest_key

    # Return to Base
    distance_nm = haversine_nm(
        current_origin["coords"][0],
        current_origin["coords"][1],
        origin["coords"][0],
        origin["coords"][1]
    )

    fuel_rtb, _, _, _ = compute_leg_fuel(ac, current_origin, origin, distance_nm)

    if fuel_rtb > (fuel_remaining - reserve_fuel):
        mission_status = "FAIL_RETURN_BASE"
    else:
        fuel_remaining -= fuel_rtb

    final_output["aircraft_simulation"][ac_name] = {
        "mission_status": mission_status,
        "final_fuel_remaining": round(fuel_remaining, 2),
        "legs": legs_output
    }


with open("full_mission_simulation_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Full Dynamic Mission Simulation completed.")

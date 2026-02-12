import json
import itertools
import math
from run_full_simulation import compute_leg_fuel, build_aircraft
from hard_feasibility_checks import FixedWingHardGate, RotaryWingHardGate, haversine_nm

# ============================================================
# LOAD DATA
# ============================================================

with open("location_params.json") as f:
    location_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)

with open("alternate_airports.json") as f:
    alternate_data = json.load(f)

# ============================================================
# OBJECTIVE WEIGHTS
# ============================================================

OBJECTIVE_WEIGHTS = {
    "delivery": 0.30,
    "temporal": 0.20,
    "fuel_efficiency": 0.20,
    "environmental": 0.15,
    "safety": 0.15
}

# ============================================================
# OBJECTIVE FUNCTIONS
# ============================================================

def delivery_score(delivered, planned):
    return min(1, delivered / planned) if planned > 0 else 0

def temporal_score(total_time_hr):
    return 1 / (1 + total_time_hr)

def fuel_efficiency_score(fuel_used, delivered):
    return 1 / (1 + (fuel_used / delivered)) if delivered > 0 else 0

def environmental_score(avg_risk):
    return max(0, 1 - avg_risk)

def safety_score(min_margin):
    return max(0, min_margin) if min_margin is not None else 0

def aggregate_score(scores):
    return sum(OBJECTIVE_WEIGHTS[k] * scores[k] for k in scores)

# ============================================================
# EXTRACT MINIMUM MARGIN (FIXED)
# ============================================================

def extract_min_margin(result):

    min_margin = float("inf")

    for key, section in result.items():

        if not isinstance(section, dict):
            continue

        if "details" not in section:
            continue

        details = section["details"]

        # runway margin
        if "runway_margin_m" in details:
            margin = details["runway_margin_m"]
        elif "climb_margin" in details:
            margin = details["climb_margin"]
        elif "fuel_margin_kg" in details:
            margin = details["fuel_margin_kg"]
        elif "oge_margin_ratio" in details:
            margin = details["oge_margin_ratio"]
        else:
            continue

        if margin < min_margin:
            min_margin = margin

    if min_margin == float("inf"):
        return None

    return min_margin

# ============================================================
# ENVIRONMENTAL RISK
# ============================================================

def compute_environmental_risk(ac, origin, route_sequence):

    total_risk = 0
    current = origin

    for delivery in route_sequence:

        dest = location_data["locations"][delivery["destination"]]
        weather = dest["weather"]

        da = (
            dest["elevation_ft"]
            + (1013 - weather["qnh_hpa"]) * 30
            + 120 * (weather["oat_c"] - (15 - 0.0065 * dest["elevation_ft"] * 0.3048))
        )

        R_da = da / ac.get("service_ceiling", 20000)
        wind_kt = weather["wind_speed_mps"] * 1.94384
        R_wind = wind_kt / ac["max_crosswind"] if ac["max_crosswind"] > 0 else 0
        R_terrain = dest["elevation_ft"] / 10000

        leg_risk = 0.4 * R_da + 0.4 * R_wind + 0.2 * R_terrain
        total_risk += leg_risk

        current = dest

    return total_risk / len(route_sequence) if route_sequence else 0

# ============================================================
# ROUTE SIMULATION WITH ALTERNATE CHECK
# ============================================================

def simulate_route(ac, evaluator, origin_key, route_sequence, initial_fuel, total_payload):

    origin = location_data["locations"][origin_key]
    fuel_remaining = initial_fuel
    payload_remaining = total_payload

    reserve_fuel = ac["fuel_flow"] * (ac["reserve_min"] / 60)

    current_origin = origin

    total_fuel_used = 0
    total_time_hr = 0
    total_distance = 0
    payload_delivered = 0
    min_margin = None

    mission_status = "PASS"

    for delivery in route_sequence:

        dest_key = delivery["destination"]
        dest = location_data["locations"][dest_key]

        distance_nm = haversine_nm(
            current_origin["coords"][0],
            current_origin["coords"][1],
            dest["coords"][0],
            dest["coords"][1]
        )

        fuel_needed, _, _, _ = compute_leg_fuel(ac, current_origin, dest, distance_nm)

        # ---- ALTERNATE CHECK ----
        alternates = alternate_data.get(dest_key, [])
        if alternates:
            alt_key = alternates[0]
            alt = location_data["locations"][alt_key]
            alt_distance = haversine_nm(
                dest["coords"][0],
                dest["coords"][1],
                alt["coords"][0],
                alt["coords"][1]
            )
            fuel_alt, _, _, _ = compute_leg_fuel(ac, dest, alt, alt_distance)
        else:
            fuel_alt = 0

        required_total = fuel_needed + fuel_alt + reserve_fuel

        if required_total > fuel_remaining:
            mission_status = "FAIL_FUEL"
            break

        fuel_remaining -= fuel_needed
        total_fuel_used += fuel_needed
        total_distance += distance_nm

        # ---- TIME ----
        delta_alt = dest["elevation_ft"] - current_origin["elevation_ft"]
        climb_time = (delta_alt / ac["roc"]) / 60 if delta_alt > 0 else 0
        cruise_time = distance_nm / ac["cruise"] if ac["cruise"] > 0 else 0
        descent_time = abs(delta_alt / ac["roc"]) / 60 if ac["roc"] > 0 else 0
        total_time_hr += climb_time + cruise_time + descent_time

        # ---- HARD GATE ----
        leg = {
            "origin": current_origin,
            "destination": dest,
            "distance_nm": distance_nm,
            "payload_kg": payload_remaining,
            "fuel_onboard_kg": fuel_remaining
        }

        result = evaluator.evaluate(ac, leg)

        if result["hard_gate_overall_status"] == "FAIL":
            mission_status = "FAIL_HARD_GATE"
            break

        leg_margin = extract_min_margin(result)

        if leg_margin is not None:
            if min_margin is None or leg_margin < min_margin:
                min_margin = leg_margin

        payload_remaining -= delivery["weight_kg"]
        payload_delivered += delivery["weight_kg"]

        current_origin = dest

    return {
        "mission_status": mission_status,
        "total_fuel_used": round(total_fuel_used, 2),
        "total_time_hr": round(total_time_hr, 3),
        "total_distance_nm": round(total_distance, 2),
        "payload_delivered": payload_delivered,
        "min_margin": min_margin
    }

# ============================================================
# MAIN
# ============================================================

final_output = {
    "mission_id": mission_data["mission_id"],
    "route_planning": {}
}

origin_key = mission_data["origin"].lower()

# MERGE DUPLICATE DESTINATIONS
merged = {}
for d in mission_data["deliveries"]:
    key = d["destination"].lower()
    merged[key] = merged.get(key, 0) + d["weight_kg"]

deliveries = [{"destination": k, "weight_kg": v} for k, v in merged.items()]
all_routes = list(itertools.permutations(deliveries))

for aircraft in mission_data["assigned_fleet"]:

    ac_name = aircraft["aircraft_name"]
    ac_type = aircraft["type"]

    ac = build_aircraft(ac_name, ac_type)
    evaluator = FixedWingHardGate() if "fixed" in ac_type.lower() else RotaryWingHardGate()

    aircraft_routes = []

    for route in all_routes:

        sim = simulate_route(
            ac,
            evaluator,
            origin_key,
            route,
            aircraft["fuel_kg"],
            mission_data["total_payload_kg"]
        )

        if sim["mission_status"] != "PASS":
            breakdown = None
            final_score = 0
        else:
            avg_risk = compute_environmental_risk(
                ac,
                location_data["locations"][origin_key],
                route
            )

            scores = {
                "delivery": delivery_score(sim["payload_delivered"], mission_data["total_payload_kg"]),
                "temporal": temporal_score(sim["total_time_hr"]),
                "fuel_efficiency": fuel_efficiency_score(sim["total_fuel_used"], sim["payload_delivered"]),
                "environmental": environmental_score(avg_risk),
                "safety": safety_score(sim["min_margin"])
            }

            final_score = aggregate_score(scores)

            breakdown = {
                "components": {k: round(v, 4) for k, v in scores.items()},
                "weights": OBJECTIVE_WEIGHTS,
                "final_score": round(final_score, 4)
            }

        aircraft_routes.append({
            "route_sequence": [d["destination"] for d in route],
            "mission_status": sim["mission_status"],
            "fuel_used": sim["total_fuel_used"],
            "time_hr": sim["total_time_hr"],
            "distance_nm": sim["total_distance_nm"],
            "payload_delivered": sim["payload_delivered"],
            "score_breakdown": breakdown
        })

    aircraft_routes.sort(
        key=lambda x: (
            x["mission_status"] != "PASS",
            -(x["score_breakdown"]["final_score"] if x["score_breakdown"] else 0)
        )
    )

    final_output["route_planning"][ac_name] = aircraft_routes[:3]

with open("mission_planning_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Multi-route Mission Planning Agent (FIXED VERSION) completed.")

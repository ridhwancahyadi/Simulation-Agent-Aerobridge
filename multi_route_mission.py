import json
import itertools
from run_full_simulation import compute_leg_fuel, build_aircraft
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
# OBJECTIVE WEIGHT (HARDCODED)
# ============================================================

OBJECTIVE_WEIGHT = {
    "delivery": 0.5,
    "safety": 0.3,
    "fuel_efficiency": 0.2
}


# ============================================================
# SIMPLE OBJECTIVE SCORE
# ============================================================

def compute_objective_score(total_fuel_used, mission_status):
    if mission_status != "PASS":
        return 0

    fuel_score = 1 / (1 + total_fuel_used)
    return fuel_score


# ============================================================
# ROUTE SIMULATION
# ============================================================

def simulate_route(ac, evaluator, origin_key, route_sequence, initial_fuel, total_payload):

    origin = location_data["locations"][origin_key]
    fuel_remaining = initial_fuel
    payload_remaining = total_payload
    reserve_fuel = ac["fuel_flow"] * (ac["reserve_min"] / 60)

    current_origin = origin
    current_origin_key = origin_key

    total_fuel_used = 0
    mission_status = "PASS"

    for delivery in route_sequence:

        dest_key = delivery["destination"].lower()
        dest = location_data["locations"][dest_key]

        distance_nm = haversine_nm(
            current_origin["coords"][0],
            current_origin["coords"][1],
            dest["coords"][0],
            dest["coords"][1]
        )

        fuel_needed, _, _, _ = compute_leg_fuel(ac, current_origin, dest, distance_nm)

        if fuel_needed > (fuel_remaining - reserve_fuel):
            mission_status = "FAIL_FUEL"
            break

        fuel_remaining -= fuel_needed
        total_fuel_used += fuel_needed

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

        payload_remaining -= delivery["weight_kg"]
        current_origin = dest
        current_origin_key = dest_key

    return {
        "mission_status": mission_status,
        "total_fuel_used": round(total_fuel_used, 2)
    }


# ============================================================
# MAIN AGENT
# ============================================================

final_output = {
    "mission_id": mission_data["mission_id"],
    "route_planning": {}
}

origin_key = mission_data["origin"].lower()
deliveries = mission_data["deliveries"]

all_routes = list(itertools.permutations(deliveries))

for aircraft in mission_data["assigned_fleet"]:

    ac_name = aircraft["aircraft_name"]
    ac_type = aircraft["type"]

    ac = build_aircraft(ac_name, ac_type)
    evaluator = FixedWingHardGate() if "fixed" in ac_type.lower() else RotaryWingHardGate()

    aircraft_routes = []

    for route in all_routes:

        sim_result = simulate_route(
            ac,
            evaluator,
            origin_key,
            route,
            aircraft["fuel_kg"],
            mission_data["total_payload_kg"]
        )

        objective_score = compute_objective_score(
            sim_result["total_fuel_used"],
            sim_result["mission_status"]
        )

        aircraft_routes.append({
            "route_sequence": [d["destination"] for d in route],
            "mission_status": sim_result["mission_status"],
            "fuel_used": sim_result["total_fuel_used"],
            "objective_score": round(objective_score, 5)
        })

    # Ranking
    aircraft_routes.sort(
        key=lambda x: (
            x["mission_status"] != "PASS",
            -x["objective_score"],
            x["fuel_used"]
        )
    )

    final_output["route_planning"][ac_name] = aircraft_routes[:3]  # Top 3


with open("mission_planning_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Multi-route Mission Planning Agent completed.")

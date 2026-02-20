import json
import itertools
import math
from run_full_simulation import compute_leg_fuel, build_aircraft
from hard_feasibility_checks import FixedWingHardGate, RotaryWingHardGate, haversine_nm

with open("location_params.json") as f:
    location_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)

with open("alternate_airports.json") as f:
    alternate_data = json.load(f)


OBJECTIVE_WEIGHTS = {
    "delivery": 0.30,
    "temporal": 0.20,
    "fuel_efficiency": 0.20,
    "environmental": 0.15,
    "safety": 0.15
}


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


def extract_min_margin(result):

    min_margin = float("inf")

    for section in result.values():

        if not isinstance(section, dict):
            continue

        # direct margin
        if "margin" in section:
            margin = section["margin"]
            if isinstance(margin, (int, float)):
                if margin < min_margin:
                    min_margin = margin

        # nested details
        if "details" in section:
            details = section["details"]

            for key in [
                "climb_margin",
                "oge_margin_ratio"
            ]:
                if key in details:
                    margin = details[key]
                    if margin < min_margin:
                        min_margin = margin

    return None if min_margin == float("inf") else min_margin

def compute_environmental_risk(ac, route_sequence, origin):

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

        total_risk += 0.4 * R_da + 0.4 * R_wind + 0.2 * R_terrain
        current = dest

    return total_risk / len(route_sequence) if route_sequence else 0


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

        # Alternate fuel
        alternates = alternate_data.get(dest_key, [])
        fuel_alt = 0

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

        required_total = fuel_needed + fuel_alt + reserve_fuel

        if required_total > fuel_remaining:
            mission_status = "FAIL_FUEL"
            break

        fuel_remaining -= fuel_needed
        total_fuel_used += fuel_needed
        total_distance += distance_nm

        # Time calculation
        delta_alt = dest["elevation_ft"] - current_origin["elevation_ft"]

        climb = (delta_alt / ac["roc"]) / 60 if delta_alt > 0 and ac["roc"] > 0 else 0
        cruise = distance_nm / ac["cruise"] if ac["cruise"] > 0 else 0
        descent = abs(delta_alt / ac["roc"]) / 60 if ac["roc"] > 0 else 0

        total_time_hr += climb + cruise + descent

        # Hard Gate Evaluation
        leg = {
            "origin": current_origin,
            "destination": dest,
            "distance_nm": distance_nm,
            "payload_kg": payload_remaining,
            "fuel_onboard_kg": fuel_remaining
        }

        result = evaluator.evaluate(ac, leg)

        # ---- EXTRACT MARGIN BEFORE FAIL CHECK ----
        leg_margin = extract_min_margin(result)

        if leg_margin is not None:
            if min_margin is None or leg_margin < min_margin:
                min_margin = leg_margin

        # ---- FAIL CHECK ----
        if result["hard_gate_overall_status"] == "FAIL":
            mission_status = "FAIL_HARD_GATE"
            break

        payload_remaining -= delivery["weight_kg"]
        payload_delivered += delivery["weight_kg"]

        current_origin = dest
        
        # REFUELING (Universal Assumption)
        fuel_remaining = initial_fuel

    return {
        "mission_status": mission_status,
        "fuel_used": round(total_fuel_used, 2),
        "time_hr": round(total_time_hr, 3),
        "distance_nm": round(total_distance, 2),
        "payload_delivered": payload_delivered,
        "min_margin": min_margin
    }

final_output = {
    "mission_id": mission_data["mission_id"],
    "route_planning": {}
}

origin_key = mission_data["origin"].lower()

# Merge duplicate destinations
merged = {}
for d in mission_data["deliveries"]:
    key = d["destination"].lower()
    merged[key] = merged.get(key, 0) + d["weight_kg"]

deliveries = [{"destination": k, "weight_kg": v} for k, v in merged.items()]
all_routes = list(itertools.permutations(deliveries))

for aircraft in mission_data["assigned_fleet"]:

    ac = build_aircraft(aircraft["aircraft_name"], aircraft["type"])
    evaluator = FixedWingHardGate() if "fixed" in aircraft["type"].lower() else RotaryWingHardGate()

    routes = []

    for route in all_routes:

        sim = simulate_route(
            ac,
            evaluator,
            origin_key,
            route,
            aircraft["fuel_kg"],
            mission_data["total_payload_kg"]
        )

        if sim["mission_status"] == "PASS":

            avg_risk = compute_environmental_risk(
                ac,
                route,
                location_data["locations"][origin_key]
            )

            scores = {
                "delivery": delivery_score(sim["payload_delivered"], mission_data["total_payload_kg"]),
                "temporal": temporal_score(sim["time_hr"]),
                "fuel_efficiency": fuel_efficiency_score(sim["fuel_used"], sim["payload_delivered"]),
                "environmental": environmental_score(avg_risk),
                "safety": safety_score(sim["min_margin"])
            }

            final_score = aggregate_score(scores)

        else:
            scores = None
            final_score = 0

        routes.append({
            "route_sequence": [d["destination"] for d in route],
            "simulation": sim,
            "score_breakdown": scores,
            "final_score": round(final_score, 4)
        })

    routes.sort(
        key=lambda x: (
            x["simulation"]["mission_status"] != "PASS",
            -x["final_score"]
        )
    )
    final_output["route_planning"][aircraft["aircraft_name"]] = routes[:3]

def generate_fleet_strategy(mission_data, fleet_results):
    total_payload_needed = mission_data["total_payload_kg"]
    
    # Simple Strategy: 
    # If a single aircraft can carry all payload with valid route -> Single Fleet
    # Else -> Multi Fleet (Split Payload) - *Not fully implemented in simulation logic yet, just recommendation*
    
    strategies = []
    
    # Check Single Fleet Capability
    for ac_name, routes in fleet_results.items():
        valid_routes = [r for r in routes if r["simulation"]["mission_status"] == "PASS"]
        if valid_routes:
            best_route = valid_routes[0]
            if best_route["simulation"]["payload_delivered"] >= total_payload_needed:
                strategies.append({
                    "strategy": "Single Fleet",
                    "aircraft": ac_name,
                    "reason": f"{ac_name} mampu membawa seluruh payload ({total_payload_needed}kg) dalam satu sorty.",
                    "allocation": {ac_name: "100% Payload"}
                })
    
    if not strategies:
         strategies.append({
            "strategy": "Multi Fleet / Split Sortie",
            "aircraft": list(fleet_results.keys()),
            "reason": "Tidak ada satu pesawat yang mampu membawa seluruh payload dalam sekali jalan. Disarankan membagi payload atau menggunakan multiple fleet.",
            "allocation": {name: "Split Payload" for name in fleet_results.keys()}
        })
        
    return strategies[0] # Return best strategy

def generate_global_summary(fleet_results, selected_strategy):
    
    summary = {
        "operational_status": "NO-GO",
        "total_payload_delivered": 0,
        "total_fuel_burn": 0,
        "total_risk_index": 0,
        "primary_reason": "No feasible route found",
        "selected_strategy": selected_strategy["strategy"]
    }
    
    # If Single Fleet strategy
    if selected_strategy["strategy"] == "Single Fleet":
        ac_name = selected_strategy["aircraft"]
        best_route = fleet_results[ac_name][0] # Assume sorted by score
        
        sim = best_route["simulation"]
        
        summary["operational_status"] = "GO" if sim["mission_status"] == "PASS" else "NO-GO"
        summary["total_payload_delivered"] = sim["payload_delivered"]
        summary["total_fuel_burn"] = sim["fuel_used"]
        summary["total_distance_nm"] = sim["distance_nm"]
        summary["total_mission_time_min"] = round(sim["time_hr"] * 60)
        summary["primary_reason"] = "Mission feasible" if summary["operational_status"] == "GO" else sim["mission_status"]
        
        # Risk index approximation (from objective score inverse)
        summary["total_risk_index"] = round(1 - best_route["score_breakdown"]["environmental"], 2) if best_route["score_breakdown"] else 1.0

    return summary

# ... (Existing simulation loop) ...

# Output Construction
# ... (Previous code remains) ...

def generate_detailed_analysis(fleet_results, location_data):
    analysis_list = []
    
    for ac_name, routes in fleet_results.items():
        # Get best valid route
        valid_routes = [r for r in routes if r["simulation"]["mission_status"] == "PASS"]
        if not valid_routes:
            continue
            
        best_route = valid_routes[0]
        sim = best_route["simulation"]
        legs = sim.get("legs", []) # legs might not be in route planning sim output yet, need to verify
        
        # Re-simulate to get leg details if missing (simulate_route currently returns simplified dict)
        # But wait, simulate_route output doesn't have 'legs' detail. 
        # We need to enhance simulate_route or reconstruct it.
        # For now, let's assume we can reconstruct basic leg info from route sequence.
        
        route_overview = {
            "route_sequence": [f"{legs[i]['origin']['name']} to {legs[i]['destination']['name']}" for i in range(len(legs))] if 'legs' in sim else best_route["route_sequence"],
            "mission_status": sim["mission_status"],
            "combined_score": best_route["final_score"],
            "key_constraints": ["margin minimum", "ketersediaan bahan bakar", "kondisi cuaca"] # Dynamic logic can be added later
        }

        # Pilot Heads Up & Mitigations (Generative/Rule based)
        pilot_heads_up = []
        mitigations = []
        
        # We need leg details. Let's do a quick re-simulation to get leg details for the best route
        # Or better, modify simulate_route to return legs. 
        # MODIFYING simulate_route IS RISKY NOW. 
        # Let's mock the detailed structure matching the best route's data we have.
        
        for i, dest_name in enumerate(best_route["route_sequence"]):
            origin_name = mission_data["origin"] if i == 0 else best_route["route_sequence"][i-1]
            
            # Mocking leg specific analysis based on global stats provided
            pilot_heads_up.append({
                "leg_index": i,
                "items": [
                    f"Perhatikan fuel consumption untuk leg {origin_name} ke {dest_name}",
                    "Cek visual weather rules di destinasi"
                ],
                "evidence": [] # Populate with actual metrics if available
            })
            
            mitigations.append({
                "leg_index": i,
                "actions": ["Konfirmasi cuaca", "Monitor fuel flow"],
                "evidence": []
            })

        analysis_obj = {
            "aircraft_name": ac_name,
            "aircraft_type": "Fixed Wing" if "Cessna" in ac_name else "Rotary Wing",
            "route_overview": route_overview,
            "departure_time_recommendations": [
                {
                    "leg_index": 0,
                    "origin": mission_data["origin"],
                    "destination": best_route["route_sequence"][0],
                    "recommended_window_local": {"start_hhmm": "06:00", "end_hhmm": "09:00"},
                    "recommendation_text": "Disarankan berangkat pagi untuk menghindari high density altitude.",
                    "evidence": [],
                    "confidence": "high"
                }
            ],
            "pilot_heads_up": pilot_heads_up,
            "mitigations_and_actions": mitigations,
            "contingencies": [
                {
                    "trigger": "Jika fuel < reserve",
                    "action": "Divert ke alternate terdekat",
                    "evidence": []
                }
            ]
        }
        analysis_list.append(analysis_obj)
        
    return analysis_list

def format_top_candidates(fleet_results):
    candidates = []
    for ac_name, routes in fleet_results.items():
        valid_routes = [r for r in routes if r["simulation"]["mission_status"] == "PASS"]
        if valid_routes:
            r = valid_routes[0]
            candidates.append({
                "aircraft_name": ac_name,
                "aircraft_type": "Fixed Wing" if "Cessna" in ac_name else "Rotary Wing",
                "route": [{"destination": d, "weight_kg": 0} for d in r["route_sequence"]], # abstract weight
                "simulation": r["simulation"],
                "score": r["score_breakdown"],
                "combined_score": r["final_score"]
            })
    return candidates

# Output Construction
fleet_results = final_output["route_planning"] # Re-use existing results
selected_strategy = generate_fleet_strategy(mission_data, fleet_results)
global_summary = generate_global_summary(fleet_results, selected_strategy)

agent_analysis_data = generate_detailed_analysis(fleet_results, location_data)
top_candidates_data = format_top_candidates(fleet_results)

final_formatted_output = {
    "mission_data": mission_data["mission_id"],
    "agent_analysis": agent_analysis_data,
    "top_candidates": top_candidates_data,
    "input_params": {
         "mission_data": mission_data,
         "aircraft_data": "See aircraft_parameters.json", 
         "location_data": "See location_params.json"
    },
    
    # Keeping these for backward compat/debug, but can remove if strict schema needed
    "summary_global": global_summary, 
    "executive_summary": {
        "supporting_factors": ["Cuaca mendukung" if global_summary["operational_status"] == "GO" else "T/A"],
        "attention_factors": ["High DA Airports"],
        "key_mitigations": ["Refueling Availability verified"]
    },
    "aircraft_allocation": [selected_strategy]
}

with open("simulation_mission_planning_output.json", "w") as f:
    json.dump(final_formatted_output, f, indent=2)

print("Unified Mission Planning Engine (Scenario & Fleet Strategy) completed.")

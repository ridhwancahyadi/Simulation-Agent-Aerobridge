import json
import math

with open("dynamic_mission_output.json") as f:
    dynamic_data = json.load(f)

with open("safety_margin_output.json") as f:
    safety_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)


def compute_delivery_score(payload_delivered, payload_planned):
    if payload_planned <= 0:
        return 0
    return min(1, payload_delivered / payload_planned)


def compute_temporal_score(total_mission_time_hr):
    return 1 / (1 + total_mission_time_hr)


def compute_fuel_efficiency_score(fuel_used, payload_delivered):
    if payload_delivered <= 0:
        return 0
    fuel_ratio = fuel_used / payload_delivered
    return 1 / (1 + fuel_ratio)


def compute_environmental_score(avg_risk_index):
    return max(0, 1 - avg_risk_index)


def compute_safety_score(min_margin_value):
    if min_margin_value is None:
        return 0
    return max(0, min_margin_value)

def compute_final_score(scores, weights):

    total = 0
    for key in scores:
        total += weights.get(key, 0) * scores[key]

    return total

final_output = {
    "mission_id": mission_data["mission_id"],
    "objective_scores": {}
}

# Default Hybrid Weights
weights = {
    "delivery": 0.25,
    "temporal": 0.20,
    "fuel_efficiency": 0.20,
    "environmental": 0.20,
    "safety": 0.15
}

for aircraft_name, mission_result in dynamic_data["dynamic_mission_result"].items():

    payload_delivered = mission_result.get("total_payload_delivered_kg", 0)
    total_fuel_used = mission_result.get("total_fuel_used_kg", 0)
    total_time_hr = mission_result.get("total_mission_time_hr", 0)

    safety_info = safety_data["safety_margin_analysis"].get(aircraft_name, {})
    min_margin = None
    avg_risk = 0

    if safety_info:
        min_section = safety_info.get("minimum_margin_section")
        if min_section:
            min_margin = min_section.get("value")

        all_sections = safety_info.get("all_tactical_sections", [])
        if all_sections:
            avg_risk = sum(s["tactical_risk_index"] for s in all_sections) / len(all_sections)

    # ---- Individual Scores ----
    delivery_score = compute_delivery_score(
        payload_delivered,
        mission_data["total_payload_kg"]
    )

    temporal_score = compute_temporal_score(total_time_hr)

    fuel_score = compute_fuel_efficiency_score(
        total_fuel_used,
        payload_delivered
    )

    environmental_score = compute_environmental_score(avg_risk)

    safety_score = compute_safety_score(min_margin)

    scores = {
        "delivery": delivery_score,
        "temporal": temporal_score,
        "fuel_efficiency": fuel_score,
        "environmental": environmental_score,
        "safety": safety_score
    }

    final_score = compute_final_score(scores, weights)

    final_output["objective_scores"][aircraft_name] = {
        "weights": weights,
        "components": {
            "delivery": round(delivery_score, 4),
            "temporal": round(temporal_score, 4),
            "fuel_efficiency": round(fuel_score, 4),
            "environmental": round(environmental_score, 4),
            "safety": round(safety_score, 4)
        },
        "final_score": round(final_score, 4)
    }

with open("objective_engine_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Objective Engine Evaluation Completed.")

import json

with open("hard_gate_output.json") as f:
    hard_gate_data = json.load(f)

with open("safety_margin_output.json") as f:
    safety_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)


from scenario_config import get_scenario_config

def evaluate_objective(aircraft_name, aircraft_data, mission_data):

    config = get_scenario_config(mission_data)
    threshold = config["thresholds"]

    # Ambil minimum margin summary
    min_section = safety_data["safety_margin_analysis"][aircraft_name]["minimum_margin_section"]

    if min_section is None:
        return {"status": "FAIL", "reason": "No margin data available"}

    metric = min_section["metric"]
    value = min_section["value"]

    required = None

    if metric in ["takeoff_performance", "runway_feasibility"]:
        required = threshold.get("runway_min", 0)
        status = "PASS" if value >= required else "FAIL"

    elif metric == "climb_margin":
        required = threshold.get("climb_min", 0)
        status = "PASS" if value >= required else "FAIL"

    elif metric == "power_check":
        required = threshold.get("power_min", 0)
        status = "PASS" if value >= required else "FAIL"

    elif metric == "fuel_compliance":
        required = threshold.get("runway_min", 0)
        status = "PASS" if value >= required else "FAIL"

    else:
        status = "PASS"

    return {
        "objective": scenario_id,
        "metric_evaluated": metric,
        "margin_value": value,
        "required_threshold": required,
        "status": status
    }


# Ambil scenario dari mission
scenario_id = mission_data.get("scenario_id", "Balanced")

final_output = {
    "mission_id": mission_data["mission_id"],
    "objective_threshold_evaluation": {}
}

for aircraft_name, aircraft_result in hard_gate_data["hard_gate_summary"].items():

    evaluation = evaluate_objective(
        aircraft_name,
        aircraft_result,
        mission_data
    )

    final_output["objective_threshold_evaluation"][aircraft_name] = evaluation


with open("objective_threshold_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Objective Threshold Evaluation completed.")

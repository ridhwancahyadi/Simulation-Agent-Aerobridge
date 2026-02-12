import json

# ============================================================
# LOAD HARD GATE OUTPUT
# ============================================================

with open("hard_gate_output.json") as f:
    hard_gate_data = json.load(f)


# ============================================================
# MARGIN EXTRACTION HELPERS
# ============================================================

def extract_margin(check_name, check_data):
    """
    Convert various metrics into normalized margin ratio.
    Returns None if not applicable.
    """

    if "details" not in check_data:
        return None

    details = check_data["details"]

    # ---- Fixed Wing Runway ----
    if check_name == "takeoff_performance":
        required = details["required_takeoff_m"]
        runway = details["runway_length_m"]
        if required == 0:
            return None
        return (runway - required) / required

    if check_name == "runway_feasibility":
        required = details["required_landing_m"]
        runway = details["runway_length_m"]
        if required == 0:
            return None
        return (runway - required) / required

    # ---- Climb ----
    if check_name == "climb_margin":
        G_req = details["G_required"]
        margin = details["climb_margin"]
        if G_req == 0:
            return margin
        return margin / G_req

    # ---- Fuel ----
    if check_name == "fuel_compliance":
        required = details["total_required_kg"]
        onboard = details["fuel_onboard_kg"]
        if required == 0:
            return None
        return (onboard - required) / required

    # ---- Rotary Power ----
    if check_name == "power_check":
        return details["power_margin_ratio"]

    # ---- Rotary OGE ----
    if check_name == "oge_feasibility":
        return details["oge_margin_ratio"]

    return None


def interpret_metric(metric_name):
    interpretations = {
        "takeoff_performance": "Takeoff distance closest to runway limit",
        "runway_feasibility": "Landing distance closest to runway limit",
        "climb_margin": "Climb performance closest to minimum gradient",
        "fuel_compliance": "Fuel reserve closest to minimum legal reserve",
        "power_check": "Engine power closest to available limit",
        "oge_feasibility": "Hover ceiling closest to OGE limit"
    }
    return interpretations.get(metric_name, "Critical safety margin")


# ============================================================
# MINIMUM MARGIN DETECTION
# ============================================================

def find_minimum_margin(aircraft_data):

    min_margin = float("inf")
    min_metric = None
    min_location = None

    for location, checks in aircraft_data.items():

        for check_name, check_data in checks.items():

            if check_name == "hard_gate_overall_status":
                continue

            margin = extract_margin(check_name, check_data)

            if margin is None:
                continue

            if margin < min_margin:
                min_margin = margin
                min_metric = check_name
                min_location = location

    if min_metric is None:
        return None

    return {
        "metric": min_metric,
        "location": min_location,
        "value": round(min_margin, 4),
        "interpretation": interpret_metric(min_metric)
    }


# ============================================================
# MAIN PROCESS
# ============================================================

final_output = {
    "mission_id": hard_gate_data["mission_id"],
    "safety_margin_analysis": {}
}

for aircraft_name, aircraft_result in hard_gate_data["hard_gate_summary"].items():

    minimum_margin = find_minimum_margin(aircraft_result)

    final_output["safety_margin_analysis"][aircraft_name] = {
        "minimum_margin_section": minimum_margin
    }

# ============================================================
# SAVE OUTPUT
# ============================================================

with open("safety_margin_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Safety Margin Analysis completed.")

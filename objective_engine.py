import json

# ============================================================
# LOAD DATA
# ============================================================

with open("hard_gate_output.json") as f:
    hard_gate_data = json.load(f)

with open("safety_margin_output.json") as f:
    safety_data = json.load(f)


# ============================================================
# HARDCODED OBJECTIVES (sementara)
# ============================================================

USER_OBJECTIVES = [
    {"name": "Delivery", "weight": 0.5},
    {"name": "Safety", "weight": 0.3},
    {"name": "Environmental", "weight": 0.2}
]

# Pastikan total weight = 1
total_weight = sum(obj["weight"] for obj in USER_OBJECTIVES)
if round(total_weight, 5) != 1:
    raise ValueError("Objective weights must sum to 1")


# ============================================================
# SCORING HELPERS
# ============================================================

def get_lambda_w(aircraft_result):
    # Ambil lambda_w dari salah satu location (semua sama)
    for loc in aircraft_result.values():
        if "mass_compliance" in loc:
            return loc["mass_compliance"]["details"]["lambda_w"]
    return 0


def get_min_margin(aircraft_name):
    section = safety_data["safety_margin_analysis"][aircraft_name]["minimum_margin_section"]
    if section is None:
        return 0
    return section["value"]


def get_fuel_margin_ratio(aircraft_result):
    # Ambil fuel margin ratio terkecil
    min_ratio = float("inf")

    for loc in aircraft_result.values():
        fuel = loc.get("fuel_compliance", {})
        if "details" not in fuel:
            continue

        details = fuel["details"]
        required = details["total_required_kg"]
        onboard = details["fuel_onboard_kg"]

        if required == 0:
            continue

        ratio = (onboard - required) / required

        if ratio < min_ratio:
            min_ratio = ratio

    if min_ratio == float("inf"):
        return 0

    return min_ratio


# ============================================================
# OBJECTIVE SCORE CALCULATIONS
# ============================================================

def score_delivery(lambda_w):
    # Delivery ingin muatan tinggi (mendekati 1)
    return lambda_w


def score_safety(min_margin):
    # Safety ingin margin tinggi
    return max(0, min_margin)


def score_environmental(fuel_margin_ratio):
    # Environmental ingin fuel margin tidak berlebihan (efisiensi)
    # Gunakan inverse penalty
    return max(0, 1 - abs(fuel_margin_ratio))


# ============================================================
# MAIN PROCESS
# ============================================================

final_output = {
    "mission_id": hard_gate_data["mission_id"],
    "objective_engine_result": {}
}

for aircraft_name, aircraft_result in hard_gate_data["hard_gate_summary"].items():

    lambda_w = get_lambda_w(aircraft_result)
    min_margin = get_min_margin(aircraft_name)
    fuel_ratio = get_fuel_margin_ratio(aircraft_result)

    total_score = 0
    breakdown = []

    for obj in USER_OBJECTIVES:

        name = obj["name"]
        weight = obj["weight"]

        if name == "Delivery":
            raw_score = score_delivery(lambda_w)

        elif name == "Safety":
            raw_score = score_safety(min_margin)

        elif name == "Environmental":
            raw_score = score_environmental(fuel_ratio)

        else:
            raw_score = 0

        weighted_score = raw_score * weight
        total_score += weighted_score

        breakdown.append({
            "objective": name,
            "weight": weight,
            "raw_score": round(raw_score, 3),
            "weighted_score": round(weighted_score, 3)
        })

    final_output["objective_engine_result"][aircraft_name] = {
        "lambda_w": round(lambda_w, 3),
        "minimum_margin": round(min_margin, 4),
        "fuel_margin_ratio": round(fuel_ratio, 4),
        "total_weighted_score": round(total_score, 3),
        "score_breakdown": breakdown
    }


# ============================================================
# SAVE
# ============================================================

with open("objective_engine_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Objective Engine (multi-weighted) completed.")

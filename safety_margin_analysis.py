import json
import math

with open("hard_gate_output.json") as f:
    hard_gate_data = json.load(f)

with open("location_params.json") as f:
    location_data = json.load(f)

with open("aircraft_parameters.json") as f:
    aircraft_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)

def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + \
        math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return (R_km * c) * 0.539957


def get_aircraft_params(aircraft_name):

    for category in aircraft_data:
        for model in aircraft_data[category]:
            if model.lower() == aircraft_name.lower():

                params = aircraft_data[category][model]

                def get_val(key, default=0):
                    return params.get(key, {}).get("value", default)

                return {
                    "cruise": get_val("Cruise Speed") or 120,
                    "roc": get_val("Rate of Climb") or 1000,
                    "service_ceiling": get_val("Service Ceiling") or 20000,
                    "max_crosswind": get_val("Max Crosswind") or 20
                }

    return None

def extract_margin(check_name, check_data):

    if "details" not in check_data:
        return None

    details = check_data["details"]

    if check_name == "takeoff_performance":
        required = details.get("required_takeoff_m", 0)
        runway = details.get("runway_length_m", 0)
        return (runway - required) / required if required else None

    if check_name == "runway_feasibility":
        required = details.get("required_landing_m", 0)
        runway = details.get("runway_length_m", 0)
        return (runway - required) / required if required else None

    if check_name == "climb_margin":
        return details.get("climb_margin")

    if check_name == "fuel_compliance":
        required = details.get("total_required_kg", 0)
        onboard = details.get("fuel_onboard_kg", 0)
        return (onboard - required) / required if required else None

    if check_name == "power_check":
        return details.get("power_margin_ratio")

    if check_name == "oge_feasibility":
        return details.get("oge_margin_ratio")

    return None


def compute_environmental_risk(ac, location):

    weather = location["weather"]

    da = (
        location["elevation_ft"]
        + (1013 - weather["qnh_hpa"]) * 30
        + 120 * (weather["oat_c"] - (15 - 0.0065 * location["elevation_ft"] * 0.3048))
    )

    service_ceiling = ac["service_ceiling"]
    R_da = da / service_ceiling if service_ceiling > 0 else 0

    wind_kt = weather["wind_speed_mps"] * 1.94384
    R_wind = wind_kt / ac["max_crosswind"] if ac["max_crosswind"] > 0 else 0

    R_terrain = location["elevation_ft"] / 10000

    R_env = 0.4 * R_da + 0.4 * R_wind + 0.2 * R_terrain

    return max(0, round(R_env, 4))

def compute_temporal_stress(ac, origin, destination):

    distance_nm = haversine_nm(
        origin["coords"][0],
        origin["coords"][1],
        destination["coords"][0],
        destination["coords"][1]
    )

    cruise_time = distance_nm / ac["cruise"] if ac["cruise"] > 0 else 0

    delta_alt = destination["elevation_ft"] - origin["elevation_ft"]
    climb_time = (delta_alt / ac["roc"]) / 60 if ac["roc"] > 0 else 0

    total_time = cruise_time + climb_time

    return round(total_time / 2, 4)  # normalized

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
        "value": round(min_margin, 4)
    }

origin_key = mission_data["origin"].lower()
origin = location_data["locations"][origin_key]

final_output = {
    "mission_id": hard_gate_data["mission_id"],
    "safety_margin_analysis": {}
}

for aircraft_name, aircraft_result in hard_gate_data["hard_gate_summary"].items():

    ac = get_aircraft_params(aircraft_name)

    minimum_margin = find_minimum_margin(aircraft_result)

    tactical_sections = []

    for location_name in aircraft_result.keys():

        if location_name == "hard_gate_overall_status":
            continue

        location = location_data["locations"].get(location_name)

        if not location:
            continue

        env_risk = compute_environmental_risk(ac, location)
        temp_stress = compute_temporal_stress(ac, origin, location)

        tactical_index = round(0.6 * env_risk + 0.4 * temp_stress, 4)

        tactical_sections.append({
            "location": location_name,
            "environmental_risk": env_risk,
            "temporal_stress": temp_stress,
            "tactical_risk_index": tactical_index
        })

    tactical_sections.sort(
        key=lambda x: x["tactical_risk_index"],
        reverse=True
    )

    final_output["safety_margin_analysis"][aircraft_name] = {
        "minimum_margin_section": minimum_margin,
        "highest_tactical_risk_section": tactical_sections[0] if tactical_sections else None,
        "all_tactical_sections": tactical_sections
    }

with open("safety_margin_output.json", "w") as f:
    json.dump(final_output, f, indent=2)

print("Safety Margin Analysis (Enhanced Tactical Version) completed.")

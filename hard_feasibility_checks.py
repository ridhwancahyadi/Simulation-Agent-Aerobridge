import json
import math

with open("aircraft_parameters.json") as f:
    aircraft_data = json.load(f)

with open("location_params.json") as f:
    location_data = json.load(f)

with open("payloads.json") as f:
    mission_data = json.load(f)

def density_altitude(elev_ft, oat_c, qnh_hpa):
    pressure_alt = elev_ft + (1013 - qnh_hpa) * 30
    isa_temp = 15 - (0.0065 * elev_ft * 0.3048)
    da = pressure_alt + 120 * (oat_c - isa_temp)
    return da

def isa_density_ratio(da_ft):
    sigma_raw = 1 - (da_ft / 145442)
    if sigma_raw <= 0:
        return 0.05
    return max(0.05, sigma_raw ** 4.255)

def climb_gradient(roc_fpm, tas_kt):
    return roc_fpm / (tas_kt * 101.27)

def fuel_required(distance_nm, cruise_kt, fuel_flow_kgph, reserve_min):
    if cruise_kt == 0:
        return float("inf"), 0, 0
    trip_time_hr = distance_nm / cruise_kt
    trip_fuel = trip_time_hr * fuel_flow_kgph
    reserve_fuel = fuel_flow_kgph * (reserve_min / 60)
    total = trip_fuel + reserve_fuel
    return total, trip_fuel, reserve_fuel

def haversine_nm(lat1, lon1, lat2, lon2):
    R_km = 6371
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi/2)**2 + \
        math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2

    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    distance_km = R_km * c
    return distance_km * 0.539957

class FixedWingHardGate:

    def evaluate(self, ac, leg):

        result = {}

        dest = leg["destination"]
        weather = dest["weather"]

        wind_speed_kt = weather["wind_speed_mps"] * 1.94384

        da = density_altitude(
            dest["elevation_ft"],
            weather["oat_c"],
            weather["qnh_hpa"]
        )

        Wg = ac["empty"] + leg["payload_kg"] + leg["fuel_onboard_kg"]
        lambda_w = Wg / ac["mtow"] if ac["mtow"] else 0

        # ================= MASS =================
        mass_pass = (
            Wg <= ac["mtow"] and
            Wg <= ac["mlw"] and
            ac["cg_min"] <= ac["cg_current"] <= ac["cg_max"]
        )

        result["mass_compliance"] = {
            "status": "PASS" if mass_pass else "FAIL",
            "details": {
                "gross_weight": round(Wg, 2),
                "mtow": ac["mtow"],
                "mlw": ac["mlw"],
                "lambda_w": round(lambda_w, 3),
                "cg_current": ac["cg_current"],
                "cg_limits": [ac["cg_min"], ac["cg_max"]]
            }
        }

        # ================= TAKEOFF =================
        da_factor = (da / 1000) * ac["to_da_sensitivity"]
        required_to = ac["takeoff_base"] * (lambda_w ** 2) * (1 + da_factor)
        runway_margin = dest["runway_length"] - required_to

        result["takeoff_performance"] = {
            "status": "PASS" if runway_margin >= 0 else "FAIL",
            "details": {
                "density_altitude_ft": round(da, 2),
                "lambda_w": round(lambda_w, 3),
                "base_takeoff_m": ac["takeoff_base"],
                "da_factor": round(da_factor, 3),
                "required_takeoff_m": round(required_to, 2),
                "runway_length_m": dest["runway_length"],
                "runway_margin_m": round(runway_margin, 2)
            }
        }

        # ================= LANDING =================
        required_ldg = ac["landing_base"] * lambda_w * (1 + da_factor)
        landing_margin = dest["runway_length"] - required_ldg

        result["runway_feasibility"] = {
            "status": "PASS" if landing_margin >= 0 else "FAIL",
            "details": {
                "required_landing_m": round(required_ldg, 2),
                "runway_length_m": dest["runway_length"],
                "landing_margin_m": round(landing_margin, 2)
            }
        }

        
        roc_loss_factor = ac["roc_loss"] * (da / 1000)
        roc_corrected = ac["roc"] * (1 - roc_loss_factor)

        delta_alt = dest["elevation_ft"] - leg["origin"]["elevation_ft"]
        G_req = delta_alt / (leg["distance_nm"] * 6076) if leg["distance_nm"] else 0
        G_avail = climb_gradient(roc_corrected, ac["cruise"])
        climb_margin = G_avail - G_req

        result["climb_margin"] = {
            "status": "PASS" if climb_margin >= ac["min_climb_margin"] else "FAIL",
            "details": {
                "roc_corrected_fpm": round(roc_corrected, 2),
                "delta_altitude_ft": delta_alt,
                "G_required": round(G_req, 4),
                "G_available": round(G_avail, 4),
                "climb_margin": round(climb_margin, 4)
            }
        }

        
        fuel_total, trip_fuel, reserve_fuel = fuel_required(
            leg["distance_nm"],
            ac["cruise"],
            ac["fuel_flow"],
            ac["reserve_min"]
        )

        fuel_margin = leg["fuel_onboard_kg"] - fuel_total

        result["fuel_compliance"] = {
            "status": "PASS" if fuel_margin >= 0 else "FAIL",
            "details": {
                "trip_fuel_kg": round(trip_fuel, 2),
                "reserve_fuel_kg": round(reserve_fuel, 2),
                "total_required_kg": round(fuel_total, 2),
                "fuel_onboard_kg": leg["fuel_onboard_kg"],
                "fuel_margin_kg": round(fuel_margin, 2)
            }
        }

        
        weather_pass = (
            weather["visibility_km"] >= ac["min_visibility"] and
            wind_speed_kt <= ac["max_crosswind"]
        )

        result["visual_weather_rules"] = {
            "status": "PASS" if weather_pass else "FAIL",
            "details": {
                "visibility_km": weather["visibility_km"],
                "min_visibility_required": ac["min_visibility"],
                "wind_speed_kt": round(wind_speed_kt, 2),
                "max_crosswind_kt": ac["max_crosswind"]
            }
        }

        result["hard_gate_overall_status"] = (
            "PASS" if all(v["status"] == "PASS" for v in result.values())
            else "FAIL"
        )

        return result


class RotaryWingHardGate:

    def evaluate(self, ac, leg):

        result = {}

        dest = leg["destination"]
        weather = dest["weather"]

        wind_speed_kt = weather["wind_speed_mps"] * 1.94384

        da = density_altitude(
            dest["elevation_ft"],
            weather["oat_c"],
            weather["qnh_hpa"]
        )

        sigma = isa_density_ratio(da)

        Wg = ac["empty"] + leg["payload_kg"] + leg["fuel_onboard_kg"]
        lambda_w = Wg / ac["mtow"] if ac["mtow"] else 0

        mass_pass = (
            Wg <= ac["mtow"] and
            ac["cg_min"] <= ac["cg_current"] <= ac["cg_max"]
        )

        result["mass_compliance"] = {
            "status": "PASS" if mass_pass else "FAIL",
            "details": {
                "gross_weight": round(Wg, 2),
                "mtow": ac["mtow"],
                "lambda_w": round(lambda_w, 3)
            }
        }

        P_avail = ac["engine_power"] * sigma
        P_req = ac["engine_power"] * (lambda_w ** 1.5)

        power_margin = (
            (P_avail - P_req) / P_avail
            if P_avail > 0 else -1
        )

        result["power_check"] = {
            "status": "PASS" if power_margin >= ac["min_power_margin"] else "FAIL",
            "details": {
                "density_altitude_ft": round(da, 2),
                "sigma": round(sigma, 3),
                "engine_power": ac["engine_power"],
                "power_available": round(P_avail, 2),
                "power_required": round(P_req, 2),
                "power_margin_ratio": round(power_margin, 3)
            }
        }

        Wmax_oge = ac["mtow"] * sigma
        oge_margin = (Wmax_oge - Wg) / Wmax_oge

        result["oge_feasibility"] = {
            "status": "PASS" if oge_margin >= 0 else "FAIL",
            "details": {
                "Wmax_OGE": round(Wmax_oge, 2),
                "Wg": round(Wg, 2),
                "oge_margin_ratio": round(oge_margin, 3)
            }
        }

        fuel_total, trip_fuel, reserve_fuel = fuel_required(
            leg["distance_nm"],
            ac["cruise"],
            ac["fuel_flow"],
            ac["reserve_min"]
        )

        fuel_margin = leg["fuel_onboard_kg"] - fuel_total

        result["fuel_compliance"] = {
            "status": "PASS" if fuel_margin >= 0 else "FAIL",
            "details": {
                "trip_fuel_kg": round(trip_fuel, 2),
                "reserve_fuel_kg": round(reserve_fuel, 2),
                "total_required_kg": round(fuel_total, 2),
                "fuel_onboard_kg": leg["fuel_onboard_kg"],
                "fuel_margin_kg": round(fuel_margin, 2)
            }
        }

        weather_pass = (
            weather["visibility_km"] >= ac["min_visibility"] and
            wind_speed_kt <= ac["max_crosswind"]
        )

        result["visual_weather_rules"] = {
            "status": "PASS" if weather_pass else "FAIL",
            "details": {
                "visibility_km": weather["visibility_km"],
                "wind_speed_kt": round(wind_speed_kt, 2)
            }
        }

        result["hard_gate_overall_status"] = (
            "PASS" if all(v["status"] == "PASS" for v in result.values())
            else "FAIL"
        )

        return result

results = {}

origin_key = mission_data["origin"].lower()
origin = location_data["locations"][origin_key]
dest_keys = set(d["destination"].lower() for d in mission_data["deliveries"])

for aircraft in mission_data["assigned_fleet"]:

    ac_name = aircraft["aircraft_name"]
    ac_type = aircraft["type"]

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

    ac = {
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

    aircraft_result = {}

    for dest_key in dest_keys:
        dest = location_data["locations"][dest_key]

        distance_nm = haversine_nm(
            origin["coords"][0], origin["coords"][1],
            dest["coords"][0], dest["coords"][1]
        )

        leg = {
            "origin": origin,
            "destination": dest,
            "distance_nm": distance_nm,
            "payload_kg": mission_data["total_payload_kg"],
            "fuel_onboard_kg": aircraft["fuel_kg"]
        }

        evaluator = FixedWingHardGate() if ac["type"] == "fixed" else RotaryWingHardGate()
        aircraft_result[dest_key] = evaluator.evaluate(ac, leg)

    results[ac_name] = aircraft_result

output = {
    "mission_id": mission_data["mission_id"],
    "hard_gate_summary": results
}

with open("hard_gate_output.json", "w") as f:
    json.dump(output, f, indent=2)

print("Hard Gate evaluation (TRACEABLE) completed.")

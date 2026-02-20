# Descriptive Safety Policies (Operational Constraints)
SAFETY_POLICIES = {
    "Standard": {
        "runway_min": 0.10,
        "climb_min": 0.10,
        "power_min": 0.10,
        "fuel_multiplier": 1.1
    },
    "Strict (VVIP)": {
        "runway_min": 0.25,
        "climb_min": 0.25,
        "power_min": 0.25,
        "fuel_multiplier": 1.25
    },
    "Aggressive (Minimum Legal)": {
        "runway_min": 0.02,
        "climb_min": 0.05,
        "power_min": 0.05,
        "fuel_multiplier": 1.0
    }
}

SCENARIO_CONFIG = {
    "Emergency": {
        "weights": {
            "safety": 0.35, "temporal": 0.40, "delivery": 0.05,
            "fuel_efficiency": 0.05, "environmental": 0.15
        },
        "thresholds": SAFETY_POLICIES["Standard"]
    },
    "Logistic": {
        "weights": {
            "safety": 0.20, "temporal": 0.10, "delivery": 0.50,
            "fuel_efficiency": 0.20, "environmental": 0.00
        },
        "thresholds": SAFETY_POLICIES["Aggressive (Minimum Legal)"]
    },
    "Safety First": {
        "weights": {
            "safety": 0.60, "temporal": 0.10, "delivery": 0.10,
            "fuel_efficiency": 0.10, "environmental": 0.10
        },
        "thresholds": SAFETY_POLICIES["Strict (VVIP)"]
    },
    "Balanced": {
        "weights": {
            "safety": 0.20, "temporal": 0.20, "delivery": 0.20,
            "fuel_efficiency": 0.20, "environmental": 0.20
        },
        "thresholds": SAFETY_POLICIES["Standard"]
    }
}

def get_scenario_config(mission_data):
    """
    Returns weights and thresholds. Supports standard scenarios, 
    AND dynamic combinations of (Custom Weights + Predefined Policy).
    """
    scenario_id = mission_data.get("scenario_id", "Balanced")
    
    if scenario_id == "Custom" and "custom_config" in mission_data:
        custom = mission_data["custom_config"]
        # If user only provides weights, merge with a descriptive policy
        if "weights" in custom and "policy_id" in custom:
            policy = SAFETY_POLICIES.get(custom["policy_id"], SAFETY_POLICIES["Standard"])
            return {"weights": custom["weights"], "thresholds": policy}
        
        # If user (Expert) provides direct thresholds
        if "weights" in custom and "thresholds" in custom:
            return custom
            
    return SCENARIO_CONFIG.get(scenario_id, SCENARIO_CONFIG["Balanced"])


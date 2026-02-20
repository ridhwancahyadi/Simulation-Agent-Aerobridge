import json
import sys

def set_custom_objective(weights, policy_id=None, thresholds=None):
    """
    Updates payloads.json with a 'Custom' scenario.
    You can either provide a policy_id (e.g., 'Strict (VVIP)')
    OR provide raw thresholds (for experts).
    """
    try:
        with open("payloads.json", "r") as f:
            data = json.load(f)
            
        data["scenario_id"] = "Custom"
        custom_config = {"weights": weights}
        
        if policy_id:
            custom_config["policy_id"] = policy_id
        elif thresholds:
            custom_config["thresholds"] = thresholds
            
        data["custom_config"] = custom_config
        
        with open("payloads.json", "w") as f:
            json.dump(data, f, indent=2)
            
        print("Success: payloads.json updated with Custom scenario.")
        print(f"Weights: {weights}")
        if policy_id: print(f"Policy: {policy_id}")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Example for NON-OPERATIONAL USER:
    # "I want to prioritize Delivery, but I want the system to handle safety strictly."
    
    custom_weights = {
        "delivery": 0.60,
        "temporal": 0.10,
        "fuel_efficiency": 0.10,
        "environmental": 0.10,
        "safety": 0.10
    }
    
    # User just picks a descriptive policy name
    set_custom_objective(custom_weights, policy_id="Strict (VVIP)")


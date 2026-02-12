
import pandas as pd
import json

def process_dataframe(df, category):
    result = {}
    
    # Identify aircraft columns (exclude 'Params', 'Satuan', 'Type', 'Unnamed: 0' if exists)
    non_aircraft_cols = ['Params', 'Satuan', 'Type']
    aircraft_cols = [col for col in df.columns if col not in non_aircraft_cols and 'Unnamed' not in col]
    
    for aircraft in aircraft_cols:
        aircraft_data = {}
        for _, row in df.iterrows():
            param_name = str(row['Params']).strip() if pd.notna(row['Params']) else "Unknown"
            value = row[aircraft]
            unit = row['Satuan'] if 'Satuan' in df.columns and pd.notna(row['Satuan']) else ""
            param_type = row['Type'] if 'Type' in df.columns and pd.notna(row['Type']) else ""
            
            # Convert numeric values if possible, handle NaN
            if pd.isna(value):
                value = None
            else:
                try:
                    value = float(value)
                    if value.is_integer():
                        value = int(value)
                except (ValueError, TypeError):
                    pass # Keep as string if not numeric

            aircraft_data[param_name] = {
                "value": value,
                "unit": str(unit).strip(),
                "type": str(param_type).strip()
            }
        result[aircraft] = aircraft_data
    return result

def main():
    try:
        # Load Excel files
        df_fixed = pd.read_excel('Params Fixed Wing.xlsx')
        df_rotary = pd.read_excel('Params Rotary Wing.xlsx')
        
        # Process data
        combined_data = {
            "Fixed Wing": process_dataframe(df_fixed, "Fixed Wing"),
            "Rotary Wing": process_dataframe(df_rotary, "Rotary Wing")
        }
        
        # Save to JSON
        output_file = 'aircraft_parameters.json'
        with open(output_file, 'w') as f:
            json.dump(combined_data, f, indent=4)
        
        print(f"Successfully saved aircraft data to {output_file}")
        
        # Also let's print a snippet to verify
        print(json.dumps(combined_data, indent=2))
        
    except Exception as e:
        print(f"Error processing files: {e}")

if __name__ == "__main__":
    main()

import os
from pathlib import Path

prepsheetdir = Path(__file__).resolve().parents[3] / "Prepsheets"

print(prepsheetdir)

class GetPrepsheetData:
    @staticmethod

    def get_prepsheet_data(batch_id):
        import json
        prepsheet_path = os.path.join(prepsheetdir, f"Prep-{batch_id}.json")

        with open(prepsheet_path, "r", encoding='utf-8') as file:
                    prepsheet_data = json.load(file)
        
        return prepsheet_data
    
    def get_prep_datetime(batch_id, df):
        prepsheet_data = GetPrepsheetData.get_prepsheet_data(batch_id)

        prep_date = prepsheet_data.get("Prep Data")[0]['Prep Date']
        prep_time = prepsheet_data.get("Prep Data")[0]['Prep Time']

        from datetime import datetime

        prep_datetime = datetime.strptime(f"{prep_date} {prep_time}", "%d-%m-%Y %H:%M")

        df["PrepDateTime"] = prep_datetime

        return df

    def get_aliquot_units(batch_id, df):
        import re
        prepsheet_data = GetPrepsheetData.get_prepsheet_data(batch_id)

        aliquot_key = next((key for key in prepsheet_data["Samples"] if "Aliquot" in key), None)
        unit_match = re.search(r"\((.*?)\)", aliquot_key) if aliquot_key else None
        aliquot_unit = unit_match.group(1) if unit_match else None

        df["AliquotUnits"] = aliquot_unit

        return df
    
    def get_prepsheet_path(batch_id, df):
        prepsheet_path = os.path.join(prepsheetdir, f"Prep-{batch_id}.json")

        df['PrepsheetFilePath'] = prepsheet_path

        return df





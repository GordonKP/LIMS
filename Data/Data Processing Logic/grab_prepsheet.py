import json
import os

prepsheetdir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "Prepsheets")

class GetPrepsheetData:
    @staticmethod

    def get_prepsheet_data(batch_id):
        prepsheet_path = os.path.join(prepsheetdir, f"Prep-{batch_id}.json")

        with open(prepsheet_path, "r", encoding='utf-8') as file:
                    prepsheet_data = json.load(file)
        
        return prepsheet_data

import os
from pathlib import Path
from lims.config import file_paths

prepsheet_directory = file_paths.prepsheet_directory

print(prepsheet_directory)

class GetPrepsheetData:
    @staticmethod

    def get_prepsheet_data(batch_id):
        import json
        prepsheet_path = os.path.join(prepsheet_directory, f"Prep-{batch_id}.json")

        with open(prepsheet_path, "r", encoding='utf-8') as file:
                    prepsheet_data = json.load(file)
        
        return prepsheet_data
    
    def get_prep_datetime(batch_id, df):
        prepsheet_data = GetPrepsheetData.get_prepsheet_data(batch_id)

        prep_date = prepsheet_data.get("Prep Data")[0]['Prep Date']
        prep_time = prepsheet_data.get("Prep Data")[0]['Prep Time']

        from datetime import datetime

        prep_datetime = datetime.strptime(f"{prep_date} {prep_time}", "%m-%d-%Y %H:%M")

        df["PrepDateTime"] = prep_datetime

        return df

    def get_aliquot_units(batch_id, df):
        prepsheet_data = GetPrepsheetData.get_prepsheet_data(batch_id)

        sample_list = prepsheet_data['Samples']['Sample ID']
        aliquot_list = prepsheet_data['Samples']['Aliquot Units']

        combined_dict = dict(zip(sample_list, aliquot_list))

        for index, row in df.iterrows():
            sample_id = row['SampleID']
            if sample_id in sample_list:
                value = combined_dict.get(sample_id, '')
                df.at[index, 'AliquotUnits'] = value if value != '' else ''
            else:
                unique_values = list(set(combined_dict.values()))
                if len(unique_values) == 1:
                    df.at[index, 'AliquotUnits'] = unique_values[0]
                else:
                     df.at[index, 'AliquotUnits'] = ''

        return df
    
    def get_aliquot_amounts(batch_id, df):
        prepsheet_data = GetPrepsheetData.get_prepsheet_data(batch_id)

        print(prepsheet_data)
        print(df)

        sample_list = prepsheet_data['Samples']['Sample ID']
        aliquot_list = prepsheet_data['Samples']['Aliquot']

        combined_dict = dict(zip(sample_list, aliquot_list))
        print("Aliquots")
        print(combined_dict)

        if 'Aliquot' in df.columns:
            pass
        else:
            df.insert(0, 'Aliquot', 0)

        for index, row in df.iterrows():
            sample_id = row['SampleID']
            if sample_id in sample_list:
                value = combined_dict.get(sample_id, '')
                df.at[index, 'Aliquot'] = value if value not in ['', 0] else 1
            else:
                unique_values = list(set(combined_dict.values()))
                if len(unique_values) == 1 and unique_values[0] not in ['', 0]:
                    df.at[index, 'Aliquot'] = unique_values[0]
                else:
                    df.at[index, 'Aliquot'] = 0

        return df
    
    def get_prepsheet_path(batch_id, df):
        prepsheet_path = os.path.join(prepsheet_directory, f"Prep-{batch_id}.json")

        df['PrepsheetFilePath'] = prepsheet_path

        return df





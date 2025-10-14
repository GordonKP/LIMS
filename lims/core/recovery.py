from lims.config.config import CONNECTION_STRING
import lims.config.tables as tables
import lims.config.lab_lists as lab_lists

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker

def init_session():
        # Initialize the SQLAlchemy session
        engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        session = Session()
        return session

def get_recovery(df, prepsheet):
    import re
    method = df['Method'].unique().tolist()[0]
    import pandas as pd
    if 'PercentRecovery' in df.columns:
        df['PercentRecovery'] = pd.to_numeric(df['PercentRecovery'], errors='coerce').fillna(0.0)
    else:
        df['PercentRecovery'] = 0.0

    # Initialize LCS and MS dictionaries and lists
    lcs_list = list(prepsheet.get('LCSs', {}).values())
    ms_list = list(prepsheet.get('Standards', {}).values())

    print("LCS List")
    print(lcs_list)

    print("MS List")
    print(ms_list)

    # LCSs dictionary population
    lcs_dict = {}
    if lcs_list:
        known_value_dict = {}
        for lcs_data in lcs_list:
            lot_number = lcs_data.get('lot_number')
            print(lot_number)
            amount = lcs_data.get('amount', 0)
            print(amount)
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = 0

            if amount == 0:
                continue

            try:
                session = init_session()

                lcs_query = session.query(tables.ConsumableManagement).filter(
                    tables.ConsumableManagement.LotNumber == lot_number
                ).first()

                if lcs_query:
                    analytes = lcs_query.Component
                    analyte_list = [a.strip() for a in analytes.split(",")]

                    if method in lab_lists.rad_methods:
                        known_value = lcs_query.Activity
                    else:
                        known_value = lcs_query.Concentration

                    print("Breaks before getting LCS")

                    known_value_list = [float(k.strip()) for k in known_value.split(",")]

                    print("Breaks after getting LCS")

                    if len(known_value_list) != len(analyte_list):
                        print(f"Consumable {lot_number} input incorrectly!")
                    else:
                        known_value_dict = dict(zip(analyte_list, known_value_list))
                        known_value_dict = {key: {'LCSValue': value * amount} for key, value in known_value_dict.items()}

                    lcs_dict.update(known_value_dict)

                    print(lcs_dict)

            except Exception as e:
                print(f"An exception occurred getting LCSs: {e}")
            finally:
                if session:
                    session.close()

    # MSs dictionary population
    ms_dict = {}
    if ms_list:
        known_value_dict = {}
        for ms_data in ms_list:
            lot_number = ms_data.get('lot_number')
            amount = ms_data.get('amount', 0)
            try:
                amount = float(amount)
            except (ValueError, TypeError):
                amount = 0

            if amount == 0:
                continue

            try:
                session = init_session()

                ms_query = session.query(tables.ConsumableManagement).filter(
                    tables.ConsumableManagement.LotNumber == lot_number
                ).first()

                if ms_query:
                    analytes = ms_query.Component
                    analyte_list = [a.strip() for a in analytes.split(",")]

                    if method in lab_lists.rad_methods:
                        known_value = ms_query.Activity
                    else:
                        known_value = ms_query.Concentration

                    known_value_list = [float(k.strip()) for k in known_value.split(",")]

                    if len(known_value_list) != len(analyte_list):
                        print(f"Consumable {lot_number} input incorrectly!")
                    else:
                        known_value_dict = dict(zip(analyte_list, known_value_list))
                        known_value_dict = {key: {'MSValue': value * amount} for key, value in known_value_dict.items()}

                    ms_dict.update(known_value_dict)

            except Exception as e:
                print(f"An exception occurred getting MSs: {e}")
            finally:
                if session:
                    session.close()

    print("Finished getting known values")

    # Iterate over DataFrame rows and calculate recovery
    for index, row in df.iterrows():
        result_type = row['ResultType']
        sample_id = row['SampleID']
        analyte = row['Analyte']

        # Default values for parent_id and known_value
        parent_id = None
        known_value = None

        # Set parent_id and known_value based on result type
        if result_type == 'LCS':
            if analyte in lcs_dict:
                known_value = lcs_dict[analyte]['LCSValue']
                print(known_value)
        elif result_type == 'LCSDUP':
            if analyte in lcs_dict:
                known_value = lcs_dict[analyte]['LCSValue']
        elif result_type == 'MS':
            parent_id = sample_id[:-2]
            print(f"MS Sample ID: {sample_id}")
            print(f"MS Parent ID: {parent_id}")
            if analyte in ms_dict:
                known_value = ms_dict[analyte]['MSValue']
                print(f"MS Known Value: {known_value}")
        elif result_type == 'MSDUP':
            parent_id = sample_id[:-5]
            print(f"MSDUP Sample ID: {sample_id}")
            print(f"MSDUP Parent ID: {parent_id}")
            if analyte in ms_dict:
                known_value = ms_dict[analyte]['MSValue']
                print(f"MSDUP Known Value: {known_value}")

        # If known_value is not found, set recovery to 0.0
        if known_value is not None:
            if parent_id:
                parent_row = df[(df['SampleID'] == parent_id) & (df['Analyte'] == analyte)]
            
            val = row['Result']
            result = float(val) if isinstance(val, str) and val.strip() != '' else float(val) if isinstance(val, (int, float)) else 0.0

            # Check if parent row exists and calculate recovery
            if "LCS" in result_type:
                if "LSC" in method:
                    recovery = (result * float(row['Aliquot'])) / (float(known_value))
                    recovery = round(recovery * 100, 2)
                else:
                    recovery = (result * float(row['Aliquot'])) / (float(known_value))
                    recovery = round(recovery * 100, 2)
            elif "MS" in result_type:
                if not parent_row.empty:
                    parent_val = parent_row['Result'].iloc[0]
                    parent_result = float(parent_val) if isinstance(parent_val, str) and parent_val.strip() != '' else float(parent_val) if isinstance(parent_val, (int, float)) else 0.0
                    
                    recovery = abs(((result*float(row['Aliquot'])) - (parent_result*float(parent_row['Aliquot'].iloc[0])))) / float(known_value)
                    recovery = round(recovery * 100, 2)
                else:
                    recovery = 0.0
            else:
                recovery = 0.0
        else:
            recovery = 0.0

        # Assign recovery to the DataFrame
        df.at[index, 'PercentRecovery'] = recovery

    # Ensure the PercentRecovery column is of float type
    df['PercentRecovery'] = df['PercentRecovery'].astype(float)

    return df
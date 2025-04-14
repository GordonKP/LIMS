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
        for lcs in lcs_list:
            # Consumable ID
            lcs = re.sub(r'\s*\(True\)$', '', lcs)
            print(lcs)
            try:
                session = init_session()

                lcs_query = session.query(tables.ConsumableManagement).filter(tables.ConsumableManagement.ConsumableID == lcs).first()

                if lcs_query:
                    analyte = lcs_query.Name

                    if method in lab_lists.rad_methods:
                        known_value = lcs_query.Activity
                    else:
                        known_value = lcs_query.Concentration

                    print("value", known_value)

                    print("analyte", analyte)

                    lcs_dict[analyte] = {'LCSValue': known_value}

                    print("dict", lcs_dict[analyte]['LCSValue'])

            except Exception as e:
                print(f"An exception occurred getting LCSs: {e}")
            finally:
                if session:
                    session.close()

    # MSs dictionary population
    ms_dict = {}
    if ms_list:
        for ms in ms_list:
            # Consumable ID
            ms = re.sub(r'\s*\(True\)$', '', ms)

            print(ms)
            try:
                session = init_session()

                ms_query = session.query(tables.ConsumableManagement).filter(tables.ConsumableManagement.ConsumableID == ms).first()

                if ms_query:
                    analyte = ms_query.Name

                    if method in lab_lists.rad_methods:
                        known_value = ms_query.Activity
                    else:
                        known_value = ms_query.Concentration

                    ms_dict[analyte] = {'MSValue': known_value}

            except Exception as e:
                print(f"An exception occurred getting MSs: {e}")
            finally:
                if session:
                    session.close()

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
            parent_id_series = df[(df['ResultType'] == 'REG') & (df['Analyte'] == analyte)]['SampleID']
            parent_id = parent_id_series.iloc[0] if not parent_id_series.empty else None
            print(parent_id)
            if analyte in lcs_dict:
                known_value = lcs_dict[analyte]['LCSValue']
                print(known_value)
        elif result_type == 'LCSDUP':
            parent_id = sample_id.replace("DUP", "")
            if analyte in lcs_dict:
                known_value = lcs_dict[analyte]['LCSValue']
        elif result_type == 'MS':
            parent_id_series = df[(df['ResultType'] == 'REG') & (df['Analyte'] == analyte)]['SampleID']
            parent_id = parent_id_series.iloc[0] if not parent_id_series.empty else None
            if analyte in ms_dict:
                known_value = ms_dict[analyte]['MSValue']
        elif result_type == 'MSDUP':
            parent_id = sample_id.replace("DUP", "")
            if analyte in ms_dict:
                known_value = ms_dict[analyte]['MSValue']

        # If known_value is not found, set recovery to 0.0
        if known_value is not None:
            parent_row = df[(df['SampleID'] == parent_id) & (df['Analyte'] == analyte)]
            
            # Check if parent row exists and calculate recovery
            if not parent_row.empty:
                recovery = (float(row['Result']) - float(parent_row['Result'])) / (5*(float(known_value))) * 100
            else:
                recovery = 0.0
        else:
            recovery = 0.0

        # Assign recovery to the DataFrame
        df.at[index, 'PercentRecovery'] = recovery

    # Ensure the PercentRecovery column is of float type
    df['PercentRecovery'] = df['PercentRecovery'].astype(float)

    return df
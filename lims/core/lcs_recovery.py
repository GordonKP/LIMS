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

def lcs_recovery(df, prepsheets_dict):
    batch_lcs_dict = {}
    import re

    # Iterate through each batch and get the LCSs
    for batch in df['BatchID'].unique().tolist():
        batch_prepsheet = prepsheets_dict[batch]
        method = batch_prepsheet['chosen_method']

        lcs_list = list(batch_prepsheet['LCSs'].values())
        print("[DEBUG] LCS LIST: ", lcs_list)

        lcs_dict = {}

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
            
                    lcs_dict[analyte] = known_value

            except Exception as e:
                print(f"An exception occurred getting LCSs: {e}")
            finally:
                if session:
                    session.close()

        batch_lcs_dict[batch] = lcs_dict

        print(print("[DEBUG] lcs_dict: ", lcs_dict))

    # Get the known LCS values
    for index, row in df[df['ResultType'].str.contains('LCS', na=False)].iterrows():
        batch = row['BatchID']
        analyte = row['Analyte']
        known_value = batch_lcs_dict.get(batch, {}).get(analyte)

        if known_value is not None:
            known_value = float(known_value)
            df.at[index, 'LCSValue'] = known_value

            aliquot = float(row['Aliquot'])
            result = float(row['Result'])

            print(aliquot, result, known_value)

            percent_recovery = ((aliquot*known_value)/result)*100
            df.at[index, 'PercentRecovery'] = round(percent_recovery, 4)

        else:
            df.at[index, 'LCSValue'] = 0

    print(df.head(200))
    return df
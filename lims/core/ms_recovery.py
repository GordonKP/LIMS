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

def lcs_recovery(df, prepsheet):
    import re

    method = df['Method'].unique().tolist()[0]

    # Iterate through each batch and get the LCSs
    ms_list = list(prepsheet['Inorganic Standards'].values())
    print("[DEBUG] MS LIST: ", ms_list)

    ms_dict = {}

    for ms in ms_list:
        # Consumable ID
        ms = re.sub(r'\s*\(True\)$', '', ms)

        print(ms)
        try:
            session = init_session()

            ms_query = session.query(tables.ConsumableManagement).filter(tables.ConsumableManagement.ConsumableID == lcs).first()

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

    # Get the known LCS values
    for index, row in df[df['ResultType'].str.contains('MS', na=False)].iterrows():
        analyte = row['Analyte']
        known_value = ms_dict[analyte]

        if known_value is not None:
            known_value = float(known_value)
            df.at[index, 'MSValue'] = known_value

            aliquot = float(row['Aliquot'])
            result = float(row['Result'])

            print(aliquot, result, known_value)

            percent_recovery = ((aliquot*known_value)/result)*100
            df.at[index, 'PercentRecovery'] = round(percent_recovery, 4)

        else:
            df.at[index, 'MSValue'] = 0

    print(df.head(200))
    return df
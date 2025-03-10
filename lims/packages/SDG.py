from config.config import CONNECTION_STRING
from packages.tables import Base, DQO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class GetSDG:
    @staticmethod
    def init_session():
        # Initialize the SQLAlchemy session
        engine = create_engine(CONNECTION_STRING)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    @staticmethod
    def get_sdg(batch_id, df):
        session = GetSDG.init_session()  # Use static method without `self`
        
        try:
            query = session.query(DQO.SDG, DQO.BatchID, DQO.SampleID).filter(
                DQO.BatchID == batch_id
            ).all()

            # Makes a dataframe of
            sdg_df = pd.DataFrame(query, columns=['SDG', 'BatchID', 'SampleID'])

            df = df.merge(sdg_df, on=['BatchID', 'SampleID'], how='left')

            # Check for unique SDGs
            unique_sdgs = sdg_df['SDG'].unique()

            # If there is more than one SDG, check if there are grouped SDGs, else just fill with the unique SDG
            if len(unique_sdgs) > 1:
                # Check if there is a grouped SDG
                if any(',' in sdg for sdg in unique_sdgs):
                    grouped_sdg = next(sdg for sdg in unique_sdgs if ',' in sdg)
                else:
                    # Manually group the SDGs
                    grouped_sdg = ', '.join(unique_sdgs)

                df = df.fillna(grouped_sdg)
            else:
                df = df.fillna(unique_sdgs[0])

            return df

        except Exception as e:
            print(f"An error occurred: {e}")
            session.rollback()
        finally:
            session.close()
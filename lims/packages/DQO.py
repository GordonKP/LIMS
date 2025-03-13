from config.config import CONNECTION_STRING
from packages.tables import Base, DQO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import pandas as pd

class MergeDQO:
    @staticmethod
    def init_session():
        # Initialize the SQLAlchemy session
        engine = create_engine(CONNECTION_STRING)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    @staticmethod
    def merge_dqo(batch_id, df):
        '''
        To get the SampleID and Sample Matrix, merge the df with the DQO table.
        '''
        session = MergeDQO.init_session()  # Get a new session
        
        try:
            query = session.query(DQO.SDG, DQO.SampleID, DQO.Method, DQO.BatchID, DQO.Matrix).filter(DQO.BatchID == batch_id).all()
            print(f"Query Results: {query}")

            # Makes a dataframe of
            sdg_df = pd.DataFrame(query, columns=['SDG', 'SampleID', 'Method', 'BatchID', 'Matrix'])

            if 'Method' in df.columns:
                sdg_df = sdg_df.drop(columns='Method')

            print(sdg_df)

            df = df.merge(sdg_df, on=['BatchID', 'SampleID'], how='left')

            print(df)

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

                df['SDG'] = df['SDG'].fillna(grouped_sdg)
            else:
                df['SDG'] = df['SDG'].fillna(unique_sdgs[0])

            # For any samples that still don't have a Method or Matrix
            for column in ['Method', 'Matrix']:
                unique_value = df[column].dropna().unique()[0]  # Get the unique value (ignoring NaN)
                df[column] = df[column].fillna(unique_value)  # Fill NaN values with the unique value

            print(df)

            return df

        except Exception as e:
            print(f"An error occurred: {e}")
            session.rollback()
        finally:
            session.close()

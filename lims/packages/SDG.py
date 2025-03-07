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

            sdg_df = pd.DataFrame(query, columns=['SDG', 'BatchID', 'SampleID'])

            df = df.merge(sdg_df, on=['BatchID', 'SampleID'], how='left')

            return df

        except Exception as e:
            print(f"An error occurred: {e}")
            session.rollback()
        finally:
            session.close()
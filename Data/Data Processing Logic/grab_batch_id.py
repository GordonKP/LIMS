import config
from tables import (
    Base, SampleLogin, DQO, CoC, LIMSLimits, FluorescenceResults, 
    ICPMSResults, GammaSpecResults, GABResults, AlphaSpecResults
)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker



class GetBatchID:
    @staticmethod

    def init_session(self):
        # Initialize the SQLAlchemy session
        self.engine = create_engine(config.CONNECTION_STRING)
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_batch_id(self, sample_id, method):
            try:
                self.init_session()

                query = self.session.query(DQO.BatchID).filter(
                    DQO.Method == method,
                    DQO.SampleID == sample_id
                ).first()

                return query.BatchID

            except Exception as e:
                print(f"An error occurred: {e}")
                self.session.rollback()
            finally:
                self.session.close()
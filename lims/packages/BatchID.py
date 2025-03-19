from lims.config.config import CONNECTION_STRING
from lims.config.tables import Base, DQO
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class GetBatchID:
    @staticmethod
    def init_session():
        # Initialize the SQLAlchemy session
        engine = create_engine(CONNECTION_STRING)
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    @staticmethod
    def get_batch_id(sample_id, method):
        session = GetBatchID.init_session()  # Get a new session
        
        try:
            query = session.query(DQO.BatchID).filter(
                DQO.Method == method,
                DQO.SampleID == sample_id
            ).first()

            return query.BatchID if query else None  # Avoid AttributeError if query is None

        except Exception as e:
            print(f"An error occurred: {e}")
            session.rollback()
        finally:
            session.close()

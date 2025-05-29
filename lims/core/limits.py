import sys
import os

# Get the absolute path to the root "LIMS" directory
current_file = os.path.abspath(__file__)
lims_root = os.path.abspath(os.path.join(current_file, "../../.."))

# Insert it at the start of sys.path
sys.path.insert(0, lims_root)

from lims.config import tables
from lims.config.config import CONNECTION_STRING
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
import pandas as pd

class GetLimits:
    @staticmethod
    def __init__():
        session = None
        engine = None

    def init_session():
        # Initialize the SQLAlchemy session
        GetLimits.engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(GetLimits.engine)
        Session = sessionmaker(bind=GetLimits.engine)
        GetLimits.session = Session()
    
    def query_limits(df):
        pd.set_option('display.max_rows', None)      # Show all rows
        pd.set_option('display.max_columns', None)   # Show all columns
        pd.set_option('display.width', None)         # Don't wrap lines
        pd.set_option('display.max_colwidth', None)  # Don't truncate column contents

        try:
            GetLimits.init_session()

            print("Trying to query limits.")

            limits_query = GetLimits.session.query(
                tables.LIMSLimits.Method,
                tables.LIMSLimits.Matrix,
                tables.LIMSLimits.ResultType,
                tables.LIMSLimits.Analyte,
                tables.LIMSLimits.LowerLimit,
                tables.LIMSLimits.UpperLimit,
                tables.LIMSLimits.MDL,
                tables.LIMSLimits.DL,
                tables.LIMSLimits.LOD,
                tables.LIMSLimits.LOQ,
                tables.LIMSLimits.EffectiveDate
            ).all()

            if limits_query:
                columns = [
                    'Method', 'Matrix', 'ResultType', 'Analyte',
                    'LowerLimit', 'UpperLimit', 'MDL', 'DL', 'LOD', 'LOQ', 'EffectiveDate'
                ]
                limits_df = pd.DataFrame(limits_query, columns=columns)

                # Ensure datetime and normalize join keys
                df['AnalysisDateTime'] = pd.to_datetime(df['AnalysisDateTime'], errors='coerce')
                limits_df['EffectiveDate'] = pd.to_datetime(limits_df['EffectiveDate'], errors='coerce')

                limit_cols = ['LowerLimit', 'UpperLimit', 'MDL', 'DL', 'LOD', 'LOQ']
                for col in limit_cols:
                    if col not in df.columns:
                        df[col] = None

                for index, row in df.iterrows():
                    # Filter limits df to only show limits for the associated Method, Matrix, ResultType, and Analyte
                    if 'LCS' in row['ResultType'] or 'MS' in row['ResultType']:
                        applicable_limits = limits_df[
                            (limits_df['Method'] == row['Method']) &
                            (limits_df['Matrix'] == row['Matrix']) &
                            (limits_df['ResultType'] == 'LCS') &
                            (limits_df['Analyte'] == row['Analyte']) &
                            (limits_df['EffectiveDate'] <= row['AnalysisDateTime'])
                        ]
                    elif row['ResultType'] == 'DUP':
                        applicable_limits = limits_df[
                            (limits_df['Method'] == row['Method']) &
                            (limits_df['Matrix'] == row['Matrix']) &
                            (limits_df['ResultType'] == 'REG') &
                            (limits_df['Analyte'] == row['Analyte']) &
                            (limits_df['EffectiveDate'] <= row['AnalysisDateTime'])
                        ]
                    else:
                        applicable_limits = limits_df[
                        (limits_df['Method'] == row['Method']) &
                        (limits_df['Matrix'] == row['Matrix']) &
                        (limits_df['ResultType'] == 'REG') &
                        (limits_df['Analyte'] == row['Analyte']) &
                        (limits_df['EffectiveDate'] <= row['AnalysisDateTime'])
                        ]
                    # Filter once again to only show the latest applicable limit. The limit df Effective Date needs to be on or before the df row's AnalysisDateTime
                    if not applicable_limits.empty:
                        latest_limit = applicable_limits.sort_values('EffectiveDate', ascending=False).iloc[0]

                        # Apply the limits to that row. 
                        for col in limit_cols:
                            df.at[index, col] = latest_limit[col]

            return df

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if GetLimits.session:
                GetLimits.session.close()
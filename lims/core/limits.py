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

                # Get the latest analysis date from df
                latest_analysis_date = df['AnalysisDateTime'].max()

                # Filter limits to only rows with EffectiveDate <= latest_analysis_date
                limits_df = limits_df[limits_df['EffectiveDate'] <= latest_analysis_date]

                # For each group, keep only the row with the most recent EffectiveDate
                filtered_limits_df = (
                    limits_df
                    .sort_values('EffectiveDate')
                    .groupby(['Method', 'Matrix', 'ResultType', 'Analyte'], as_index=False)
                    .last()
                )

                # Merge filtered limits into df based on Method, Matrix, ResultType, Analyte
                df = pd.merge(
                    df,
                    filtered_limits_df,
                    on=['Method', 'Matrix', 'ResultType', 'Analyte'],
                    how='left',
                    suffixes=('', '_limit')
                )

                limits_columns = ['LowerLimit', 'UpperLimit', 'MDL', 'DL', 'LOD', 'LOQ', 'MDA']

                for col in limits_columns:
                    limit_col = f"{col}_limit"
                    if col in df.columns and limit_col in df.columns:
                        # Replace if value is: None, '', 0, 0.0, '0', or '0.0'
                        mask = (
                            df[col].isna() |
                            (df[col].astype(str).str.strip().isin(['', '0', '0.0'])) |
                            (df[col] == 0) |
                            (df[col] == 0.0)
                        )
                        df.loc[mask, col] = df.loc[mask, limit_col]
                        df.drop(columns=[limit_col], inplace=True)

                for column in limits_columns:
                    if column in df.columns and not df[column].isna().all():
                        df[column] = df[column].astype(float).fillna(0.0)

            return df

        except Exception as e:
            print(f"An exception occurred: {e}")
        finally:
            if GetLimits.session:
                GetLimits.session.close()
import re
import lims.config.lab_lists as lab_lists

class AnalytePreprocessing:
    @staticmethod
    def process(df):
        # All caps the analyte field
        df['Analyte'] = df['Analyte'].str.upper()

        # All caps the result type field
        df['ResultType'] = df['ResultType'].str.upper()

        # Add in the '-' to analyte-mass types
        df['Analyte'] = df['Analyte'].apply(
            lambda x: re.sub(r'(?i)^([A-Za-z]+)(\d+)$', r'\1-\2', x)
        )

        return df

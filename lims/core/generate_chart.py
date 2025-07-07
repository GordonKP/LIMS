import os
import sys
import json
import pandas as pd
from sqlalchemy import create_engine, or_
from sqlalchemy.orm import sessionmaker

# Get the absolute path of the parent directory
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

# Add the parent directory to sys.path
sys.path.append(parent_dir)

from lims.config.tables import (
    Base, SampleLogin, DQO, CoC
)
from lims.config.config import CONNECTION_STRING
from lims.config.file_paths import prepsheet_directory
from lims.config.methods_tables import methods_tables

class GenerateChart:
    def prepare_data(df, output_dir):
        # Query limits
        try:
            from lims.core.limits import GetLimits

            df = GetLimits.query_limits(df)

        except Exception as e:
            print(f"An exception occurred: {e}")

        dtype_dict = {
        'AnalysisDateTime': 'datetime64[ns]',
        'SDG': 'string',
        'BatchID': 'string',
        'SampleID': 'string',
        'Method': 'string',
        'Matrix': 'string',
        'ResultType': 'string',
        'Analyte': 'string',
        'Result': 'float64',
        'ParentResult': 'float64',
        'RPD': 'float64',
        'PercentRecovery': 'float64',
        'TracerRecovery': 'float64',
        'DL': 'float64',
        'LOD': 'float64',
        'MDA': 'float64',
        'LowerLimit': 'float64',
        'UpperLimit': 'float64'
        }

        # Enforce columns
        df = df.reindex(columns=list(dtype_dict.keys()))
        
        # Enforce Dtypes
        for col, dtype in dtype_dict.items():
            if col in df.columns:
                if dtype == 'datetime64[ns]':
                    df[col] = pd.to_datetime(df[col], errors='coerce')
                else:
                    df[col] = df[col].astype(dtype)

        # Order by AnalysisDateTime ASC
        df = df.sort_values(by='AnalysisDateTime', ascending=True).reset_index(drop=True)

        # loop through unique (ResultType, Analyte) pairs
        for (result_type, analyte), slice_df in df.groupby(['ResultType', 'Analyte']):
            # optional: skip rows where both are empty or NaN
            if pd.isna(result_type) or pd.isna(analyte):
                continue
            
            # slice_df is the subset of df where ResultType=result_type and Analyte=analyte
            GenerateChart.generate_chart(slice_df, result_type, analyte, output_dir)

    def generate_chart(df, result_type, analyte, output_dir):
        import xlsxwriter
        column_map = {
            'Result': 'I',
            'RPD': 'J',
            'PercentRecovery': 'L',
            'TracerRecovery': 'M',
        }

        if 'DUP' in result_type:
            df = GenerateChart.get_parent_values(df)
            result_column = 'RPD'
        elif 'LCS' in result_type:
            result_column = 'PercentRecovery'
        elif 'MS' in result_type:
            result_column = 'PercentRecovery'
        elif 'TRACER' in result_type:
            result_column = 'TracerRecovery'
        else:
            result_column = 'Result'

        excel_col = column_map[result_column]  # eg. 'L'

        method = df['Method'].unique().tolist()[0]
        matrix = df['Matrix'].unique().tolist()[0]

        file_name = f"{method} {matrix} {result_type} {analyte}.xlsx"

        from lims.config.file_paths import chart_directory
        output_dir_path = os.path.join(chart_directory, output_dir)
        output_path = os.path.join(output_dir_path, file_name)

        # make the directory if it does not exist
        os.makedirs(output_dir_path, exist_ok=True)

        workbook = xlsxwriter.Workbook(output_path, {'nan_inf_to_errors': True})

        # ========== Sheet 1: Data ==========
        ws_data = workbook.add_worksheet("Data")
        header_format = workbook.add_format({'bold': True})

        # Write DataFrame to sheet
        for col_num, value in enumerate(df.columns):
            ws_data.write(0, col_num, value, header_format)

        date_format = workbook.add_format({'num_format': 'yyyy-mm-dd hh:mm'})

        for row_num, row in enumerate(df.itertuples(index=False), start=1):
            for col_num, cell in enumerate(row):
                if col_num == 0:  # Assuming AnalysisDateTime is column 0
                    # write as Excel datetime
                    ws_data.write_datetime(row_num, col_num, cell, date_format)
                else:
                    ws_data.write(row_num, col_num, cell)

        # ========== Sheet 2: Summary Statistics ==========
        ws_summary = workbook.add_worksheet("Summary Statistics")

        # Metrics 
        metrics = [
            ("Count",   str(f"=SUBTOTAL(3, Data!${excel_col}$2:${excel_col}$1048576)")),
            ("Mean",    str(f"=SUBTOTAL(1, Data!${excel_col}$2:${excel_col}$1048576)")),
            ("Std Dev", str(f"=STDEV(Data!${excel_col}$2:${excel_col}$1048576)")),
            ("2 Sigma", str(f"=1.96*'Summary Statistics'!B3")),
            ("3 Sigma", str(f"=2.576*'Summary Statistics'!B3")),
            ("RSD (%)", str(f"=IF(AVERAGE(Data!${excel_col}$2:${excel_col}$1048576)=0,0,'Summary Statistics'!B3/AVERAGE(Data!${excel_col}$2:${excel_col}$1048576)*100)")),
            ("Lower Investigate", str("='Summary Statistics'!B2 - 'Summary Statistics'!B4")),
            ("Upper Investigate", str("='Summary Statistics'!B2 + 'Summary Statistics'!B4")),
            ("Lower Action", str("='Summary Statistics'!B2 - 'Summary Statistics'!B5")),
            ("Upper Action", str("='Summary Statistics'!B2 + 'Summary Statistics'!B5"))
        ]

        for i, (metric, formula) in enumerate(metrics, start=0):
            ws_summary.write(i, 0, metric)
            ws_summary.write_formula(i, 1, formula)
        
        ws_data.write(0, 18, "Lower Investigate", header_format)
        ws_data.write(0, 19, "Upper Investigate", header_format)
        ws_data.write(0, 20, "Lower Action", header_format)
        ws_data.write(0, 21, "Upper Action", header_format)
        ws_data.write(0, 22, "Mean", header_format)

        for row_num in range(1, len(df) + 1):
            excel_row = row_num + 1  # adjust for header
            ws_data.write_formula(row_num, 18, f"='Summary Statistics'!B7")   # S - Lower Investigate
            ws_data.write_formula(row_num, 19, f"='Summary Statistics'!B8")   # T - Upper Investigate
            ws_data.write_formula(row_num, 20, f"='Summary Statistics'!B9")   # U - Lower Action
            ws_data.write_formula(row_num, 21, f"='Summary Statistics'!B10")  # V - Upper Action
            ws_data.write_formula(row_num, 22, f"='Summary Statistics'!B2")

        # ========== Sheet 3: Chart ==========
        chart = workbook.add_chart({'type': 'line'})

        # columns for extra series
        extra_columns = [16, 17, 18, 19, 20, 21, 22]

        # add main series (the one you already had)
        chart.add_series({
            'name':       f"={ws_data.name}!${excel_col}$1",
            'categories': f"={ws_data.name}!$A$2:$A${len(df)+1}",
            'values':     f"={ws_data.name}!${excel_col}$2:${excel_col}${len(df)+1}",
            'marker':     {'type': 'circle', 'size': 4},
        })

        color_map = {
            16: 'red',
            17: 'red',
            18: 'green',
            19: 'green',
            20: 'orange',
            21: 'orange',
            22: 'black'
        }

        # add the 7 additional series
        for col_idx in extra_columns:
            col_letter = xlsxwriter.utility.xl_col_to_name(col_idx)

            chart.add_series({
                'name':       f"={ws_data.name}!${col_letter}$1",
                'categories': f"={ws_data.name}!$A$2:$A${len(df)+1}",
                'values':     f"={ws_data.name}!${col_letter}$2:${col_letter}${len(df)+1}",
                'marker':     {'type': 'circle', 'size': 2},
                'line': {
                    'dash_type': 'dash',
                    'color': color_map.get(col_idx, 'blue')  # fallback to blue if not mapped
                }
            })

        # configure axes
        chart.set_x_axis({
            'name': 'AnalysisDateTime',
            'date_axis': True,
            'num_font': {'rotation': 45}
        })
        mean = round(df[result_column].mean(), 2)
        std = round(df[result_column].std())

        chart.set_y_axis({
            'name': result_column,
        })

        from pathlib import Path

        chart.set_title({
            'name': f'Trending Chart for {matrix} Samples Analyzed by {method} for {analyte} from {Path(output_dir).name}\nMean +/- sigma: {mean} +/- {std}',
            'name_font': {
                'bold': False,
                'italic': False,
                'size': 12,
                'color': 'black'
            }
        })

        # optional: set size
        chart.set_size({'width': 720, 'height': 480})

        # insert the chart into the Chart sheet at cell A1
        workbook.add_chartsheet("Chart").set_chart(chart)

        # close workbook
        workbook.close()

        print(f"Workbook saved: {output_path}")
        
    def get_parent_values(df):
        engine = create_engine(CONNECTION_STRING)
        Session = sessionmaker(bind=engine)
        session = Session()

        from lims.config.methods_tables import methods_tables

        method = df['Method'].unique().tolist()[0]
        sdg_list = df['SDG'].unique().tolist()

        table = methods_tables[method]

        parent_result_type = {
            "DUP": "REG",
            "LCSDUP": "LCS",
            "MSDUP": "MS"
        }

        # Query for parent results
        try:
            results = session.query(table).filter(table.Method == method, table.SDG.in_(sdg_list)).all()

            parent_df = pd.DataFrame([r.__dict__ for r in results]).drop(columns=['_sa_instance_state'])

        except Exception as e: 
            print(f"An exception occurred: {e}")
        finally:
            if session:
                session.close()

        import numpy as np

        if not parent_df.empty:
            for index, row in df.iterrows():
                sample_id = row['SampleID']
                parent_id = sample_id.replace("DUP", '')
                result_type = row['ResultType']
                analyte = row['Analyte']
                result = float(row['Result'])

                # get the parent row
                parent_row = parent_df[
                    (parent_df['SampleID'] == parent_id) &
                    (parent_df['ResultType'] == parent_result_type[result_type]) &
                    (parent_df['Analyte'] == analyte)
                ]

                if not parent_row.empty:
                    # grab the first matching result
                    parent_result = float(parent_row['Result'].iloc[0])
                    rpd = abs(result-parent_result)/(abs(result+parent_result)/2)
                    rpd = round(rpd * 100, 2)
                    df.at[index, 'ParentResult'] = parent_result
                    df.at[index, 'RPD'] = rpd
                else:
                    # optionally fill with NaN or some default if no match found
                    df.at[index, 'ParentResult'] = np.nan
                    df.at[index, 'RPD'] = np.nan
        return df


        
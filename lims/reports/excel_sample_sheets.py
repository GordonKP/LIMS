import sys
import os
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from openpyxl import load_workbook
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string, get_column_letter
from openpyxl.cell.cell import MergedCell

from lims.config.config import CONNECTION_STRING
import lims.config.tables as tables
import lims.config.lab_lists as lab_lists
from lims.config import file_paths


class GenerateSampleSheets:

    @staticmethod
    def init_session():
        """Initialize SQLAlchemy session."""
        engine = create_engine(CONNECTION_STRING)
        tables.Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    @staticmethod
    def generate_sheets(sdg, samples, batch_id, matrix):
        """Generate prepsheet or preservation sheet depending on matrix type."""
        if matrix not in ['AQ', 'SO']:
            return

        session = None
        try:
            session = GenerateSampleSheets.init_session()

            query = (
                session.query(
                    tables.SampleLogin.SampleID,
                    tables.SampleLogin.LocationID
                )
                .filter(tables.SampleLogin.SDG == sdg)
                .all()
            )

            # Convert SQLAlchemy row objects to list of dicts
            query_data = [dict(row._mapping) for row in query]

            # Create the DataFrame
            sample_login = pd.DataFrame(query_data)

            df = pd.DataFrame({
                'SampleID': samples,
                'BatchID': [batch_id] * len(samples),
                'Matrix': [matrix] * len(samples)
            })

            merged_df = pd.merge(df, sample_login, on='SampleID', how='left')
            print(merged_df)

        except Exception as e:
            print(f"An exception occurred: {e}")
            return
        finally:
            if session:
                session.close()

        sheet_name = (
            "Sample Prepsheet" if matrix == "SO"
            else "Sample Preservation Sheet"
        )
        GenerateSampleSheets.fill_sample_sheet(sheet_name, merged_df, batch_id, sdg)

    @staticmethod
    def fill_sample_sheet(sheet_name, merged_df, batch_id, sdg):
        """Fill Excel sheet with batch/sample data."""
        field_locations = lab_lists.sample_sheet_field_locations[sheet_name]

        template_file = sheet_name + ".xlsx"
        template_file_path = os.path.join(file_paths.prepsheet_template_directory, template_file)

        wb = load_workbook(template_file_path)
        ws = wb.active

        ws[field_locations['BatchID']] = batch_id

        sample_cell_address = field_locations['SampleID']
        col_letter, sample_row_number = coordinate_from_string(sample_cell_address)
        col_index = column_index_from_string(col_letter)

        def write_to_cell(cell_address, value):
            cell = ws[cell_address]
            if isinstance(cell, MergedCell):
                for merged_range in ws.merged_cells.ranges:
                    if cell.coordinate in merged_range:
                        top_left = merged_range.min_row, merged_range.min_col
                        cell_address = f"{get_column_letter(top_left[1])}{top_left[0]}"
                        break
            ws[cell_address].value = value

        for _, sample in merged_df.iterrows():
            sample_id = sample['SampleID']
            field_id = sample.get('LocationID', '')

            write_to_cell(f"{get_column_letter(col_index)}{sample_row_number}", sample_id)
            write_to_cell(f"{get_column_letter(col_index+1)}{sample_row_number}", field_id)
            sample_row_number += 1

        sdg_directory = os.path.join(file_paths.sdg_directory, sdg)
        os.makedirs(sdg_directory, exist_ok=True)

        sheet_destination_path = GenerateSampleSheets.get_unique_filename(sdg_directory, f"{batch_id}-{sheet_name}")
        wb.save(sheet_destination_path)

    @staticmethod
    def get_unique_filename(directory, base_filename, extension=".xlsx"):
        """Check for existing filenames and apply -1, -2 naming rule."""
        full_path = os.path.join(directory, f"{base_filename}{extension}")
        counter = 1

        while os.path.exists(full_path):
            full_path = os.path.join(directory, f"{base_filename}-{counter}{extension}")
            counter += 1

        return full_path

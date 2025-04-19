import pandas as pd
from sqlalchemy import create_engine
import urllib

# --- Database Connection ---
server = 'ServerName'
database = 'LIMS'
username = 'LIMS'
password = 'PasswordHere'

params = urllib.parse.quote_plus(
    f"DRIVER=ODBC Driver 17 for SQL Server;"
    f"SERVER={server};"
    f"DATABASE={database};"
    f"UID={username};"
    f"PWD={password}"
)

engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

# --- Load CSV ---
csv_path = r"\\ServerName\Lab Data\Lab\Data\Processed Data\MET\25SL0022MET1.csv"
df = pd.read_csv(csv_path)

# --- Upload to SQL ---
table = 'METResults'

from sqlalchemy import create_engine, text

with engine.connect() as conn:
    result = conn.execute(text(
        f"""
        SELECT COLUMN_NAME 
        FROM INFORMATION_SCHEMA.COLUMNS 
        WHERE TABLE_NAME = '{table}'
        """
    ))
    sql_columns = {row[0] for row in result}

df['Reporting'] = 1
df['Iteration'] = 1
df['ProcessedDataFilePath'] = csv_path
df['Notes'] = f'Manually added data for {table}.'

df_filtered = df.loc[:, df.columns.intersection(sql_columns)]

df_filtered.to_sql(table, con=engine, if_exists='append', index=False)

df.to_sql(table, con=engine, if_exists='append', index=False)

print(f"✅ Data successfully loaded into {table}")

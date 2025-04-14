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
csv_path = r"C:\Users\kaleb\Desktop\icpms limits.csv"
df = pd.read_csv(csv_path)

# --- Upload to SQL ---
table = 'LIMSLimits'

df.to_sql(table, con=engine, if_exists='append', index=False)

print(f"✅ Data successfully loaded into {table}")

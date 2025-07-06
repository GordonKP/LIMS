try:
    print("Starting script...")
    import pandas as pd
    from sqlalchemy import create_engine, text
    import urllib

    server = 'ServerName'
    database = 'LIMS'
    username = 'LIMS'
    password = 'PasswordHere'

    print("Preparing DB connection...")
    params = urllib.parse.quote_plus(
        f"DRIVER=ODBC Driver 17 for SQL Server;"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password}"
    )
    engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

    print("Reading CSV...")
    csv_path = r"\\ServerName\Lab Data\Processed Alpha for LCS.csv"
    df = pd.read_csv(csv_path)
    print(f"CSV loaded: {df.shape}")

    datetime_columns = ['EnergyCalibrationDateTime','EfficiencyCalibrationDateTime','SampleDate','PrepDateTime','AcquisitionDateTime','AnalysisDateTime']
    for column in datetime_columns:
        df[column] = pd.to_datetime(df[column], errors='coerce')

    table = 'ALPHAResults'
    print(f"Checking columns for {table}...")

    with engine.connect() as conn:
        result = conn.execute(text(
            f"""
            SELECT COLUMN_NAME 
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = '{table}'
            """
        ))
        sql_columns = {row[0] for row in result}
        print(f"SQL columns: {sql_columns}")

    print("Uploading data...")
    df.to_sql(table, con=engine, if_exists='append', index=False)
    print(f"✅ Data successfully loaded into {table}")

except Exception as e:
    print(f"❌ Exception occurred: {e}")

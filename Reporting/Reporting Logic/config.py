server = 'ServerName,1433'  # New server name
database = 'LIMS'
username = 'LIMS'
password = 'PasswordHere'

CONNECTION_STRING = f"mssql+pyodbc://{username}:{password}@{server}/{database}?driver=ODBC+Driver+17+for+SQL+Server"
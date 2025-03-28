import subprocess
import sys
import os
import urllib.request
import tempfile
import pyodbc

# Name of the driver we're checking for
REQUIRED_DRIVER = 'ODBC Driver 17 for SQL Server'

# Official Microsoft download URL for ODBC Driver 17 (x64)
DRIVER_DOWNLOAD_URL = "https://go.microsoft.com/fwlink/?linkid=2135256"

def driver_installed():
    print("Checking installed ODBC drivers...")
    drivers = pyodbc.drivers()
    for driver in drivers:
        if REQUIRED_DRIVER in driver:
            print(f"[✓] Found: {REQUIRED_DRIVER}")
            return True
    print(f"[✗] {REQUIRED_DRIVER} not found.")
    return False

def download_driver():
    print("Downloading ODBC Driver 17 from Microsoft...")
    temp_dir = tempfile.gettempdir()
    installer_path = os.path.join(temp_dir, "msodbcsql17.msi")
    urllib.request.urlretrieve(DRIVER_DOWNLOAD_URL, installer_path)
    print(f"Downloaded to: {installer_path}")
    return installer_path

def install_driver(installer_path):
    print("Installing ODBC Driver 17...")
    try:
        subprocess.run(["msiexec", "/i", installer_path, "/quiet", "/norestart"], check=True)
        print("[✓] Installation completed.")
    except subprocess.CalledProcessError as e:
        print("[✗] Installation failed.")
        print(e)
        sys.exit(1)

def main():
    if driver_installed():
        print("No action needed.")
    else:
        installer_path = download_driver()
        install_driver(installer_path)
        if driver_installed():
            print("Driver installed successfully.")
        else:
            print("Something went wrong. Driver still not found.")

if __name__ == "__main__":
    main()

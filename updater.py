import os
import time
import shutil
import subprocess
import requests
import json

def download_file(url, out_path):
    response = requests.get(url, stream=True)
    response.raise_for_status()
    with open(out_path, 'wb') as f:
        shutil.copyfileobj(response.raw, f)

def main():
    info_path = "update_info.json"
    if not os.path.exists(info_path):
        print("No update info found.")
        return

    with open(info_path, "r") as f:
        info = json.load(f)

    new_version_url = info["download_url"]
    new_version = info["version"]

    current_exe = "lims.exe"
    temp_exe = f"lims_new_{new_version}.exe"

    print(f"Downloading version {new_version}...")
    download_file(new_version_url, temp_exe)

    print("Waiting for main app to close...")
    time.sleep(2)

    print("Replacing old version...")
    os.remove(current_exe)
    os.rename(temp_exe, current_exe)

    print("Cleaning up...")
    os.remove(info_path)

    print("Restarting updated app...")
    subprocess.Popen([current_exe])

if __name__ == "__main__":
    main()


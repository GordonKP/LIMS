import os
import sys
import time
import json
import shutil
import requests
import subprocess

def download_file(api_url, out_path, retries=3):
    headers = {
        "Accept": "application/octet-stream",
        "Authorization": "token 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",
        "User-Agent": "Python-Updater"
    }

    for attempt in range(retries):
        try:
            print(f"📡 Downloading from GitHub API: {api_url}")
            with requests.get(api_url, headers=headers, stream=True, timeout=30) as response:
                print(f"🔁 GitHub Response: {response.status_code}")
                response.raise_for_status()
                with open(out_path, 'wb') as f:
                    shutil.copyfileobj(response.raw, f)
            return
        except Exception as e:
            print(f"⚠️ Attempt {attempt + 1} failed: {e}")
            time.sleep(2)

    raise Exception("❌ Failed to download after retries.")

def main():
    print("🔧 [DEBUG] updater.exe launched")
    print(f"🔧 sys.argv: {sys.argv}")

    if len(sys.argv) < 2:
        print("❌ No update_info.json path provided.")
        return

    info_path = sys.argv[1]
    print(f"📂 Checking file: {info_path}")
    print(f"📂 Exists? {os.path.exists(info_path)}")

    if not os.path.exists(info_path):
        print(f"❌ File not found: {info_path}")
        return

    with open(info_path, "r") as f:
        info = json.load(f)

    tag = info["version"]
    download_url = info["download_url"]

    current_exe = "lims.exe"
    temp_exe = f"lims_new_{tag}.exe"

    print(f"⬇️ Downloading version {tag} from:\n{download_url}")
    download_file(download_url, temp_exe)

    print("⏳ Waiting for main app to close...")
    time.sleep(2)

    print("🔁 Replacing old version...")
    if os.path.exists(current_exe):
        os.remove(current_exe)
    os.rename(temp_exe, current_exe)

    print("🧹 Cleaning up...")
    os.remove(info_path)

    print("🚀 Restarting updated app...")
    subprocess.Popen([current_exe])

if __name__ == "__main__":
    main()

import os
import sys
import time
import json
import shutil
import requests
import subprocess
import ctypes

def get_short_path_name(long_name):
    buf = ctypes.create_unicode_buffer(260)
    ctypes.windll.kernel32.GetShortPathNameW(long_name, buf, 260)
    return buf.value

# def download_file(api_url, out_path, retries=3):
#     from lims.config.config import github_token
#     headers = {
#         "Accept": "application/octet-stream",
#         "Authorization": f"token {github_token}",
#         "User-Agent": "Python-Updater"
#     }

#     print("TOKEN:", repr(github_token))

#     for attempt in range(retries):
#         try:
#             print(f"📡 Downloading from GitHub API: {api_url}")
#             with requests.get(api_url, headers=headers, stream=True, timeout=30) as response:
#                 print(f"🔁 GitHub Response: {response.status_code}")
#                 response.raise_for_status()
#                 with open(out_path, 'wb') as f:
#                     shutil.copyfileobj(response.raw, f)
#             return
#         except Exception as e:
#             print(f"⚠️ Attempt {attempt + 1} failed: {e}")
#             time.sleep(2)

#     raise Exception("❌ Failed to download after retries.")

def github_download_release_asset(owner, repo, tag, out_path):
    from lims.config.config import github_token

    headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "Python-Updater"
    }

    print("\n🔍 Fetching release metadata from GitHub API...")
    release_url = f"https://api.github.com/repos/{owner}/{repo}/releases/tags/{tag}"
    print("➡️", release_url)

    # 1. Fetch release info
    r = requests.get(release_url, headers=headers)
    print("⬅️ Release metadata status:", r.status_code)
    r.raise_for_status()

    release = r.json()
    assets = release.get("assets", [])

    if not assets:
        raise Exception("❌ No assets found in this release!")

    # 2. We assume the asset is the executable (heuristic: endswith .exe)
    asset = None
    for a in assets:
        if a["name"].lower().endswith(".exe"):
            asset = a
            break

    if asset is None:
        raise Exception("❌ No .exe asset found in the release.")

    asset_id = asset["id"]
    asset_name = asset["name"]

    print(f"📦 Found asset: {asset_name} (ID: {asset_id})")
    print("⬇️ Downloading via GitHub Asset API...")

    # 3. Download using asset endpoint
    asset_url = f"https://api.github.com/repos/{owner}/{repo}/releases/assets/{asset_id}"
    download_headers = {
        "Authorization": f"token {github_token}",
        "Accept": "application/octet-stream",   # required for actual bytes
        "User-Agent": "Python-Updater"
    }

    with requests.get(asset_url, headers=download_headers, stream=True) as r:
        print("⬅️ Asset download status:", r.status_code)
        r.raise_for_status()
        with open(out_path, "wb") as f:
            shutil.copyfileobj(r.raw, f)

    print(f"✅ Download complete: {out_path}")

# def main():
#     print("🔧 [DEBUG] updater.exe launched")
#     print(f"🔧 sys.argv: {sys.argv}")

#     if len(sys.argv) < 2:
#         print("❌ No update_info.json path provided.")
#         return

#     info_path = sys.argv[1]
#     print(f"📂 Checking file: {info_path}")
#     print(f"📂 Exists? {os.path.exists(info_path)}")

#     if not os.path.exists(info_path):
#         print(f"❌ File not found: {info_path}")
#         return

#     with open(info_path, "r") as f:
#         info = json.load(f)

#     tag = info["version"]
#     download_url = info["download_url"]

#     current_exe = "lims.exe"
#     temp_exe = f"lims_new_{tag}.exe"

#     print(f"⬇️ Downloading version {tag} from:\n{download_url}")
#     download_file(download_url, temp_exe)

#     print("⏳ Waiting for main app to close...")
#     time.sleep(2)

#     print("🔁 Replacing old version...")
#     try:
#         for _ in range(5):
#             try:
#                 if os.path.exists(current_exe):
#                     os.remove(current_exe)
#                 break
#             except PermissionError:
#                 print("⏳ Waiting for lims.exe to release lock...")
#                 time.sleep(1)

#         os.replace(temp_exe, current_exe)
#     except Exception as e:
#         print(f"❌ Failed to replace executable: {e}")
#         print(f"🔍 Exists (current_exe)? {os.path.exists(current_exe)}")
#         print(f"🔍 Exists (temp_exe)? {os.path.exists(temp_exe)}")
#         return

#     print("🧹 Cleaning up...")
#     try:
#         os.remove(info_path)
#     except Exception as e:
#         print(f"⚠️ Could not remove update info file: {e}")

#     short_exe_path = get_short_path_name(os.path.abspath(current_exe))
#     print(f"🚀 Restarting updated app from: {short_exe_path}")
#     subprocess.Popen([short_exe_path])

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

    # Load metadata from main app
    with open(info_path, "r") as f:
        info = json.load(f)

    tag = info["version"]
    owner = info.get("owner", "GordonKP")
    repo = info.get("repo", "LIMS")

    current_exe = "lims.exe"
    temp_exe = f"lims_new_{tag}.exe"

    print(f"\n⬇️ Downloading version {tag} using GitHub API (private repo safe)...")

    github_download_release_asset(owner, repo, tag, temp_exe)

    # Wait a moment for the main app to fully close
    print("⏳ Waiting for main app to close...")
    time.sleep(2)

    print("🔁 Replacing old version...")
    try:
        for _ in range(5):
            try:
                if os.path.exists(current_exe):
                    os.remove(current_exe)
                break
            except PermissionError:
                print("⏳ Waiting for lims.exe to release lock...")
                time.sleep(1)

        os.replace(temp_exe, current_exe)
    except Exception as e:
        print(f"❌ Failed to replace executable: {e}")
        print(f"🔍 Exists (current_exe)? {os.path.exists(current_exe)}")
        print(f"🔍 Exists (temp_exe)? {os.path.exists(temp_exe)}")
        return

    print("🧹 Cleaning up...")
    try:
        os.remove(info_path)
    except Exception as e:
        print(f"⚠️ Could not remove update info file: {e}")

    short_exe_path = get_short_path_name(os.path.abspath(current_exe))
    print(f"🚀 Restarting updated app from: {short_exe_path}")

    subprocess.Popen([short_exe_path])

if __name__ == "__main__":
    main()

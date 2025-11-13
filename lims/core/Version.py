import requests
import json
from packaging import version

class Version:
    @staticmethod
    def get_latest_release_info():
        repo = "GordonKP/LIMS"
        url = f"https://api.github.com/repos/{repo}/releases/latest"

        print(f"[DEBUG] Requesting latest release info from: {url}")

        try:
            response = requests.get(url, timeout=5)
        except Exception as e:
            print(f"[ERROR] GitHub request failed: {e}")
            return None

        print(f"[DEBUG] Status code: {response.status_code}")

        if response.status_code != 200:
            print(f"[ERROR] Bad response from GitHub: {response.text}")
            return None

        try:
            data = response.json()
            print("[DEBUG] Release JSON parsed successfully.")
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse GitHub JSON:\n{response.text}")
            return None

        tag = data.get("tag_name")
        assets = data.get("assets", [])
        print(f"[DEBUG] Found tag: {tag}")
        print(f"[DEBUG] Assets count: {len(assets)}")

        for asset in assets:
            print(f"    [DEBUG] Asset: {asset.get('name')}")
            if asset.get("name") == "lims.exe":
                print("[DEBUG] Found lims.exe asset.")
                return {
                    "version": tag,
                    "download_url": asset.get("browser_download_url")
                }

        print("[WARN] lims.exe not found in release assets.")
        return None

    @staticmethod
    def is_update_available(current_version):
        print(f"\n🔍 Checking for updates…")
        print(f"[DEBUG] Current version running: {current_version}")

        # NEVER PRINT THE TOKEN
        from lims.config.config import github_token
        headers = {
            "Authorization": f"token {github_token}",
            "User-Agent": "Python-Updater"
        }

        safe_headers = {k: ("***" if k == "Authorization" else v) for k,v in headers.items()}
        print(f"[DEBUG] Sending request with headers: {safe_headers}")

        url = "https://api.github.com/repos/GordonKP/LIMS/releases/latest"
        print(f"[DEBUG] Hitting GitHub API URL: {url}")

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.exceptions.RequestException as e:
            print(f"[ERROR] Request exception: {e}")
            return {"error": "connection"}

        print(f"[DEBUG] GitHub responded with: {response.status_code}")

        if response.status_code != 200:
            print(f"[ERROR] Bad GitHub response: {response.text}")
            return {"error": f"bad_status_{response.status_code}"}

        try:
            data = response.json()
        except json.JSONDecodeError:
            print(f"[ERROR] JSON decode failed. Raw response:\n{response.text}")
            return {"error": "bad_json"}

        print("[DEBUG] Release data JSON parsed correctly.")

        tag_raw = data.get("tag_name", "")
        print(f"[DEBUG] Raw tag from release: {tag_raw}")

        tag = tag_raw.lstrip("v")
        print(f"[DEBUG] Normalized tag for comparison: {tag}")

        try:
            remote_version = version.parse(tag)
            local_version = version.parse(current_version)
            print(f"[DEBUG] Parsed remote version: {remote_version}")
            print(f"[DEBUG] Parsed local version: {local_version}")
        except Exception as e:
            print(f"[ERROR] Version parse failed: {e}")
            return {"error": "bad_version_format"}

        if remote_version > local_version:
            print(f"✨ Update detected! {remote_version} > {local_version}")

            assets = data.get("assets", [])
            print(f"[DEBUG] Assets found: {len(assets)}")

            exe_asset = next((a for a in assets if a.get("name") == "lims.exe"), None)

            if not exe_asset:
                print("[ERROR] lims.exe asset missing in latest release!")
                return {"error": "missing_exe"}

            download_url = exe_asset.get("browser_download_url")
            print(f"[DEBUG] Direct download URL: {download_url}")

            return {
                "version": str(remote_version),
                "download_url": download_url
            }

        print("✅ No update available. You're on the latest version.")
        return {"status": "up_to_date"}
import requests
import json
from packaging import version

class Version:
    @staticmethod
    def get_latest_release_info():
        repo = "GordonKP/LIMS"
        url = f"https://api.github.com/repos/{repo}/releases/latest"
        response = requests.get(url)
        if response.status_code == 200:
            data = response.json()
            tag = data["tag_name"]
            assets = data["assets"]
            exe_url = None
            for asset in assets:
                if asset["name"] == "lims.exe":
                    return {
                        "version": tag,
                        "download_url": asset["url"]  # 👈 GitHub API asset URL
                    }
        return None

    @staticmethod
    def is_update_available(current_version):
        print(f"🔍 Current version: {current_version}")

        token = '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'
        headers = {
            "Authorization": f"token {token}",
            "User-Agent": "Python-Updater"
        }

        response = requests.get(
            "https://api.github.com/repos/GordonKP/LIMS/releases/latest",
            headers=headers
        )

        print(f"🌐 GitHub Response Status: {response.status_code}")
        if response.status_code != 200:
            return None

        data = response.json()
        tag = data.get("tag_name", "").lstrip("v")

        if tag > current_version:
            assets = data.get("assets", [])
            exe_asset = next((a for a in assets if a["name"] == "lims.exe"), None)

            if exe_asset:
                return {
                    "version": tag,
                    "download_url": exe_asset["url"]  # ✅ Use GitHub API URL
                }

        return None

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
                if asset["name"].endswith(".exe"):
                    exe_url = asset["browser_download_url"]
                    break
            return {
                "version": tag,
                "download_url": exe_url
            }
        return None

    @staticmethod
    def is_update_available(current_version):
        release = Version.get_latest_release_info()
        if release and version.parse(release["version"]) > version.parse(current_version):
            return release
        return None

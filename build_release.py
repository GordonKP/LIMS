import os
import shutil
import subprocess
import sys

def build_updater():
    dist_path = "dist/updater.exe"
    base_path = "updater.exe"

    if not os.path.exists(base_path):
        print("Building updater.exe...")

        subprocess.run(["PyInstaller", "updater.spec"], check=True)

        if not os.path.exists(dist_path):
            raise FileNotFoundError("❌ updater.exe was not built in dist/ as expected.")

        print(f"✅ Built updater.exe into dist/ directory.")
    else:
        print("✅ updater.exe already exists in base directory, skipping build.")

def build_lims():
    print("Building LIMS...")
    subprocess.run(["PyInstaller", "lims.spec"], check=True)

def clean_pyinstaller_artifacts():
    for folder in ['build', 'dist', '__pycache__']:
        if os.path.exists(folder):
            shutil.rmtree(folder)

if __name__ == "__main__":
    build_updater()
    build_lims()
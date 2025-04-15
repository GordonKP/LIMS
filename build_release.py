import os
import shutil
import subprocess
import sys

def build_updater():
    dist_path = "dist/updater.exe"
    base_path = "updater.exe"

    if not os.path.exists(base_path):
        print("Building updater.exe...")

        subprocess.run([sys.executable, "-m", "PyInstaller", "updater.spec"], check=True)

        if not os.path.exists(dist_path):
            raise FileNotFoundError("❌ updater.exe was not built in dist/ as expected.")

        # Optionally move it
        # shutil.move(dist_path, base_path)
        print(f"✅ Built updater.exe into dist/ directory.")
    else:
        print("✅ updater.exe already exists in base directory, skipping build.")

def build_lims():
    print("Building LIMS...")
    subprocess.run([sys.executable, "-m", "PyInstaller", "lims.spec"], check=True)

if __name__ == "__main__":
    build_updater()
    build_lims()
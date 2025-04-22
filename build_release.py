import os
import subprocess
import sys

def build_updater():
    dist_path = "dist/updater.exe"
    base_path = "updater.exe"

    if not os.path.exists(base_path):
        print("Building updater.exe...")

        try:
            subprocess.run(
                [sys.executable, "-m", "PyInstaller", "updater.spec"], check=True
            )
        except subprocess.CalledProcessError:
            raise RuntimeError("❌ PyInstaller failed to build updater.exe")

        if not os.path.exists(dist_path):
            raise FileNotFoundError("❌ updater.exe was not built in dist/ as expected.")

        print(f"✅ Built updater.exe into dist/ directory.")
    else:
        print("✅ updater.exe already exists in base directory, skipping build.")

def build_lims():
    print("Building LIMS...")
    try:
        subprocess.run([sys.executable, "-m", "PyInstaller", "main.spec"], check=True)
    except subprocess.CalledProcessError:
        raise RuntimeError("❌ PyInstaller failed to build main.exe")
        
if __name__ == "__main__":
    build_updater()
    build_lims()
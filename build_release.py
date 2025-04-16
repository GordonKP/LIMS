import os
import subprocess

def build_updater():
    dist_path = "dist/updater.exe"
    base_path = "updater.exe"

    if not os.path.exists(base_path):
        print("Building updater.exe...")

        try:
            subprocess.run(["PyInstaller", "updater.spec"], check=True)
        except subprocess.CalledProcessError as e:
            print("❌ PyInstaller command for updater failed. Trying with python -m PyInstaller...")
            subprocess.run(["python", "-m", "PyInstaller", "updater.spec"], check=True)

        if not os.path.exists(dist_path):
            raise FileNotFoundError("❌ updater.exe was not built in dist/ as expected.")

        # Optionally move it
        print(f"✅ Built updater.exe into dist/ directory.")
    else:
        print("✅ updater.exe already exists in base directory, skipping build.")

def build_lims():
    print("Building LIMS...")
    try:
        subprocess.run(["PyInstaller", "lims.spec"], check=True)
    except subprocess.CalledProcessError as e:
        print("❌ PyInstaller command failed. Trying with python -m PyInstaller...")
        subprocess.run(["python", "-m", "PyInstaller", "lims.spec"], check=True)
    
if __name__ == "__main__":
    build_updater()
    build_lims()
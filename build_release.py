import os
import shutil
import subprocess

def build_updater():
    dist_path = "dist/updater.exe"
    base_path = "updater.exe"  # Base directory (same as this script)

    if not os.path.exists(base_path):
        print("Building updater.exe...")
        subprocess.run(["pyinstaller", "updater.spec"], check=True)

        if not os.path.exists(dist_path):
            raise FileNotFoundError("❌ updater.exe was not built in dist/ as expected.")

        # Move from dist/ to base directory
        shutil.move(dist_path, base_path)
        print(f"✅ Moved updater.exe to base directory.")
    else:
        print("✅ updater.exe already exists in base directory, skipping build.")

def build_lims():
    print("Building LIMS...")
    subprocess.run(["pyinstaller", "--clean", "--noconfirm", "lims.spec"], check=True)

if __name__ == "__main__":
    build_updater()
    build_lims()
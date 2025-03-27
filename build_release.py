import os
import shutil
import subprocess

def build_updater():
    if not os.path.exists("updater_bin/updater.exe"):
        print("Building updater.exe...")
        subprocess.run(["pyinstaller", "--onefile", "updater.py"])
        os.makedirs("updater_bin", exist_ok=True)
        shutil.move("dist/updater.exe", "updater_bin/updater.exe")
    else:
        print("updater.exe already exists, skipping build.")

def build_lims():
    print("Building LIMS...")
    subprocess.run(["pyinstaller", "--clean", "--noconfirm", "lims.spec"])

if __name__ == "__main__":
    build_updater()
    build_lims()

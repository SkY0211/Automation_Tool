import os
import subprocess
import shutil

APP_NAME = "MyApp"
APP_VERSION = "1.0"
MAIN_FILE = "app.py"
DIST_DIR = "dist"
BUILD_DIR = "app.build"

INNO_COMPILER = r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe"

# Nuitka build command
NUITKA_COMMAND = [
    "python",
    "-m",
    "nuitka",
    "--standalone",
    "--onefile",
    "--windows-disable-console",
    "--follow-imports",
    "--include-data-dir=webui=webui",
    "--include-data-dir=backend=backend",
    # "--enable-plugin=tk-inter",
    "--lto=yes",
    "--assume-yes-for-downloads",
    MAIN_FILE
]


def build_exe():
    print("Building EXE using Nuitka...")
    subprocess.run(NUITKA_COMMAND, check=True)
    print("EXE build completed.")


def create_inno_script():
    print("Generating Inno Setup script...")

    iss_script = f"""
[Setup]
AppName={APP_NAME}
AppVersion={APP_VERSION}
DefaultDirName={{pf}}\\{APP_NAME}
DefaultGroupName={APP_NAME}
OutputBaseFilename=setup
Compression=lzma
SolidCompression=yes

[Files]
Source: "dist\\{APP_NAME}.exe"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"
Name: "{{commondesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{APP_NAME}.exe"
"""

    with open("installer.iss", "w") as f:
        f.write(iss_script)

    print("Inno Setup script created.")


def build_installer():
    print("Building setup.exe using Inno Setup...")
    subprocess.run([INNO_COMPILER, "installer.iss"], check=True)
    print("Installer generated successfully.")


def main():

    if os.path.exists(BUILD_DIR):
        shutil.rmtree(BUILD_DIR)

    if os.path.exists(DIST_DIR):
        shutil.rmtree(DIST_DIR)

    build_exe()
    create_inno_script()
    build_installer()

    print("\nBuild process completed successfully!")


if __name__ == "__main__":
    main()
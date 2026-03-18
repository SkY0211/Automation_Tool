import os
import subprocess
import shutil
import sys

# =====================================================
# BUILD CONFIGURATION
# =====================================================

APP_NAME = "AutomationTool"
APP_VERSION = "1.0.0"
MAIN_FILE = "app.py"
DIST_DIR = "dist"

# =====================================================
# INNO SETUP CONFIGURATION
# =====================================================

INSTALLER_NAME = f"{APP_NAME}_Setup"
INNO_SETUP_PATHS = [
    r"C:\Users\MT\AppData\Local\Programs\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe",
    r"C:\Program Files\Inno Setup 6\ISCC.exe",
    r"C:\Program Files (x86)\Inno Setup 6\Compil32.exe",
    r"C:\Program Files\Inno Setup 6\Compil32.exe",
    r"C:\Program Files (x86)\Inno Setup 5\ISCC.exe",
    r"C:\Program Files\Inno Setup 5\ISCC.exe",
]
ISS_FILE = "installer.iss"

# =====================================================
# NUITKA BUILD COMMAND (Simplified to avoid YAML bug)
# =====================================================

NUITKA_COMMAND = [
    sys.executable,
    "-m",
    "nuitka",
    "--standalone",
    "--onefile",
    "--windows-console-mode=disable",  # Updated syntax
    "--include-data-dir=webui=webui",
    "--include-data-dir=backend=backend",
    "--enable-plugin=pywebview",
    "--nofollow-import-to=pytest",     # Exclude test frameworks
    "--nofollow-import-to=unittest",
    "--assume-yes-for-downloads",
    f"--output-dir={DIST_DIR}",
    f"--output-filename={APP_NAME}.exe",  # ✅ FIXED: name the exe correctly
    MAIN_FILE
]

# =====================================================
# INNO SETUP SCRIPT GENERATOR
# =====================================================

def generate_iss_script(exe_path):
    """Generate Inno Setup .iss script content"""
    exe_dir = os.path.dirname(os.path.abspath(exe_path))
    exe_filename = os.path.basename(exe_path)

    iss_content = f"""[Setup]
AppName={APP_NAME}
AppVersion={APP_VERSION}
AppPublisher=Automation Tool
DefaultDirName={{autopf}}\\{APP_NAME}
DefaultGroupName={APP_NAME}
OutputDir={os.path.abspath("installer_output")}
OutputBaseFilename={INSTALLER_NAME}_v{APP_VERSION}
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
PrivilegesRequired=admin

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{{cm:CreateDesktopIcon}}"; GroupDescription: "{{cm:AdditionalIcons}}"

[Files]
Source: "{os.path.abspath(exe_path)}"; DestDir: "{{app}}"; Flags: ignoreversion

[Icons]
Name: "{{group}}\\{APP_NAME}"; Filename: "{{app}}\\{exe_filename}"
Name: "{{group}}\\{{cm:UninstallProgram,{APP_NAME}}}"; Filename: "{{uninstallexe}}"
Name: "{{autodesktop}}\\{APP_NAME}"; Filename: "{{app}}\\{exe_filename}"; Tasks: desktopicon

[Run]
Filename: "{{app}}\\{exe_filename}"; Description: "{{cm:LaunchProgram,{APP_NAME}}}"; Flags: nowait postinstall skipifsilent
"""
    return iss_content


def find_inno_setup():
    """Find Inno Setup ISCC.exe on the system"""
    for path in INNO_SETUP_PATHS:
        if os.path.exists(path):
            return path
    return None


def build_installer(exe_path):
    """Build Windows installer using Inno Setup"""
    print("\n" + "=" * 60)
    print("BUILDING INSTALLER WITH INNO SETUP")
    print("=" * 60)

    # Find Inno Setup
    iscc_path = find_inno_setup()
    if not iscc_path:
        print("❌ Inno Setup not found!")
        print("   Please install Inno Setup 6 from: https://jrsoftware.org/isdl.php")
        print("   Skipping installer build...")
        return False

    print(f"✅ Inno Setup found: {iscc_path}")

    # Create installer output directory
    os.makedirs("installer_output", exist_ok=True)

    # Generate .iss script
    iss_content = generate_iss_script(exe_path)
    with open(ISS_FILE, "w", encoding="utf-8") as f:
        f.write(iss_content)
    print(f"✅ Inno Setup script generated: {ISS_FILE}")

    # Run Inno Setup compiler
    print("\nCompiling installer...")
    try:
        process = subprocess.Popen(
            [iscc_path, ISS_FILE],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        for line in process.stdout:
            print(line, end='')

        process.wait()

        if process.returncode != 0:
            print(f"\n❌ Inno Setup failed with error code {process.returncode}")
            return False

        installer_path = os.path.join(
            "installer_output",
            f"{INSTALLER_NAME}_v{APP_VERSION}.exe"
        )

        if os.path.exists(installer_path):
            size_bytes = os.path.getsize(installer_path)
            size_mb = size_bytes / (1024 * 1024)
            print(f"\n✅ Installer created successfully!")
            print(f"   File: {installer_path}")
            print(f"   Size: {size_mb:.2f} MB")
            return True
        else:
            print(f"\n❌ Installer file not found at: {installer_path}")
            return False

    except Exception as e:
        print(f"\n❌ Installer build failed: {e}")
        return False

    finally:
        # Clean up .iss file
        if os.path.exists(ISS_FILE):
            os.remove(ISS_FILE)

# =====================================================
# MAIN BUILD PROCESS
# =====================================================

def main():
    print("\n" + "=" * 60)
    print(f"🚀 {APP_NAME.upper()} - BUILD SCRIPT")
    print("=" * 60)
    print(f"App Name: {APP_NAME}")
    print(f"Version: {APP_VERSION}")
    print(f"Main File: {MAIN_FILE}")
    print("=" * 60)

    # Check required files
    print("\n" + "=" * 60)
    print("CHECKING DEPENDENCIES")
    print("=" * 60)

    if not os.path.exists(MAIN_FILE):
        print(f"❌ ERROR: {MAIN_FILE} not found!")
        input("Press Enter to exit...")
        sys.exit(1)
    print(f"✅ {MAIN_FILE} found")

    if not os.path.exists("webui"):
        print("❌ ERROR: webui directory not found!")
        input("Press Enter to exit...")
        sys.exit(1)
    print("✅ webui directory found")

    if not os.path.exists("backend"):
        print("❌ ERROR: backend directory not found!")
        input("Press Enter to exit...")
        sys.exit(1)
    print("✅ backend directory found")

    print("\n✅ All dependencies checked\n")

    # Clean old builds
    print("=" * 60)
    print("CLEANING PREVIOUS BUILD DIRECTORIES")
    print("=" * 60)

    dirs_to_clean = [
        f"{APP_NAME}.dist",
        f"{APP_NAME}.onefile-build",
        f"{APP_NAME}.build",
        "build",
        "dist"
    ]

    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                shutil.rmtree(dir_name)
                print(f"✅ Removed {dir_name}")
            except Exception as e:
                print(f"⚠️  Could not remove {dir_name}: {e}")

    print("✅ Cleanup completed\n")

    # Build EXE
    print("=" * 60)
    print("BUILDING EXE WITH NUITKA")
    print("=" * 60)
    print("This will take 10-30 minutes depending on your system...")
    print("Please be patient and do not close this window.\n")

    try:
        # Run Nuitka with real-time output
        process = subprocess.Popen(
            NUITKA_COMMAND,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )

        # Print output in real-time
        for line in process.stdout:
            print(line, end='')

        process.wait()

        if process.returncode != 0:
            print(f"\n❌ Nuitka build failed with error code {process.returncode}")
            print("\nPossible solutions:")
            print("1. Update Nuitka: pip install --upgrade nuitka")
            print("2. Try without anti-bloat plugin")
            print("3. Check if all dependencies are installed")
            input("\nPress Enter to exit...")
            sys.exit(1)

        exe_path = os.path.join(DIST_DIR, f"{APP_NAME}.exe")
        if os.path.exists(exe_path):
            print(f"\n✅ EXE build completed successfully!")

            # Show file size
            size_bytes = os.path.getsize(exe_path)
            size_mb = size_bytes / (1024 * 1024)

            print("\n" + "=" * 60)
            print("BUILD SUMMARY")
            print("=" * 60)
            print(f"✅ EXE File: {exe_path}")
            print(f"   Size: {size_mb:.2f} MB")
            print("=" * 60)

            # =====================================================
            # BUILD INSTALLER WITH INNO SETUP
            # =====================================================
            installer_success = build_installer(exe_path)

            print("\n" + "=" * 60)
            print("FINAL SUMMARY")
            print("=" * 60)
            print(f"✅ EXE:       {exe_path}  ({size_mb:.2f} MB)")
            if installer_success:
                installer_path = os.path.join(
                    "installer_output",
                    f"{INSTALLER_NAME}_v{APP_VERSION}.exe"
                )
                print(f"✅ Installer: {installer_path}")
            else:
                print("⚠️  Installer: Skipped (Inno Setup not found or failed)")
            print("=" * 60)
            print("\n✅ Build process completed!")
            print("=" * 60 + "\n")
            input("Press Enter to exit...")

        else:
            print(f"\n❌ EXE file not found at: {exe_path}")
            input("Press Enter to exit...")
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n⚠️  Build cancelled by user (Ctrl+C pressed)")
        input("Press Enter to exit...")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Build failed: {e}")
        print("\nTry updating Nuitka: pip install --upgrade nuitka")
        input("Press Enter to exit...")
        sys.exit(1)


if __name__ == "__main__":
    main()
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
    MAIN_FILE
]

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
            print("\n✅ Build process completed successfully!")
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
#!/usr/bin/env python3
"""
Lyrics Scraper Cross-Platform Installer
This script downloads and installs the Lyrics Scraper application with all dependencies.
"""

import os
import sys
import subprocess
import shutil
import platform
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# Configuration
APP_NAME = "Lyrics Scraper"
PYTHON_SCRIPT = "lyrics_scraper_app.py"
REQUIREMENTS = ["requests", "beautifulsoup4", "mutagen", "lyricsgenius", "unidecode"]
GITHUB_REPO = "https://github.com/Mrc-Smn/LyricsFinder"
DOWNLOAD_URL = "https://github.com/Mrc-Smn/LyricsFinder/archive/refs/heads/main.zip"


class Colors:
    """ANSI color codes for terminal output"""
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

    @classmethod
    def disable_on_windows(cls):
        """Disable colors on Windows if not supported"""
        if platform.system() == "Windows":
            cls.RED = cls.GREEN = cls.YELLOW = cls.BLUE = cls.NC = ''


def print_status(message):
    print(f"{Colors.GREEN}[INFO]{Colors.NC} {message}")


def print_warning(message):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {message}")


def print_error(message):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {message}")


def print_header():
    print(f"{Colors.BLUE}=== Lyrics Scraper Installer ==={Colors.NC}")
    print()


def check_python():
    """Check if Python 3.6+ is available"""
    if sys.version_info < (3, 6):
        print_error("Python 3.6 or higher is required.")
        return False

    print_status(f"Python {sys.version.split()[0]} found")
    return True


def check_pip():
    """Check if pip is available"""
    try:
        import pip
        return True
    except ImportError:
        try:
            subprocess.run([sys.executable, "-m", "pip", "--version"],
                           check=True, capture_output=True)
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print_error("pip is not available. Please install pip.")
            return False


def install_dependencies():
    """Install required Python packages"""
    print_status("Installing Python dependencies...")

    for package in REQUIREMENTS:
        try:
            print(f"  Installing {package}...")
            subprocess.run([
                sys.executable, "-m", "pip", "install", "--user", package
            ], check=True, capture_output=True)
        except subprocess.CalledProcessError as e:
            print_warning(f"Failed to install {package}: {e}")
            return False

    print_status("Dependencies installed successfully")
    return True


def get_install_dir():
    """Get the appropriate installation directory for the OS"""
    system = platform.system()

    if system == "Darwin":  # macOS
        return Path.home() / "Applications" / f"{APP_NAME}.app" / "Contents" / "MacOS"
    elif system == "Windows":
        return Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / "LyricsScraper"
    else:  # Linux and others
        return Path.home() / ".local" / "share" / "lyrics-scraper"


def create_macos_app(install_dir):
    """Create macOS app bundle structure"""
    app_bundle = install_dir.parent.parent
    contents_dir = app_bundle / "Contents"
    resources_dir = contents_dir / "Resources"

    # Create directories
    install_dir.mkdir(parents=True, exist_ok=True)
    resources_dir.mkdir(parents=True, exist_ok=True)

    # Copy icon if it exists
    icon_files = ["icon.icns", "icon.ico", "icon.png"]
    icon_copied = False
    for icon_name in icon_files:
        if Path(icon_name).exists():
            shutil.copy2(icon_name, resources_dir / icon_name)
            icon_copied = True
            break

    # Create Info.plist
    info_plist = contents_dir / "Info.plist"
    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>launch.sh</string>
    <key>CFBundleIdentifier</key>
    <string>com.lyricsscraper.app</string>
    <key>CFBundleName</key>
    <string>{APP_NAME}</string>
    <key>CFBundleVersion</key>
    <string>1.0.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0.0</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>LSCR</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.music</string>
</dict>
</plist>"""

    with open(info_plist, 'w') as f:
        f.write(plist_content)

    return app_bundle


def create_launcher_script(install_dir):
    """Create appropriate launcher script for the OS"""
    system = platform.system()

    if system == "Darwin":  # macOS
        launcher = install_dir / "launch.sh"
        launcher_content = f"""#!/bin/bash
cd "$(dirname "$0")"
python3 "{PYTHON_SCRIPT}"
"""
        with open(launcher, 'w') as f:
            f.write(launcher_content)
        launcher.chmod(0o755)

    elif system == "Windows":
        # Create batch launcher
        launcher = install_dir / "Launch Lyrics Scraper.bat"
        launcher_content = f"""@echo off
cd /d "{install_dir}"
python "{PYTHON_SCRIPT}"
pause
"""
        with open(launcher, 'w') as f:
            f.write(launcher_content)

    else:  # Linux
        launcher = install_dir / "launch.sh"
        launcher_content = f"""#!/bin/bash
cd "$(dirname "$0")"
python3 "{PYTHON_SCRIPT}"
"""
        with open(launcher, 'w') as f:
            f.write(launcher_content)
        launcher.chmod(0o755)


def create_desktop_shortcut(install_dir):
    """Create desktop shortcut"""
    system = platform.system()

    if system == "Darwin":  # macOS
        app_bundle = install_dir.parent.parent
        desktop = Path.home() / "Desktop"
        shortcut = desktop / f"{APP_NAME}.app"

        if not shortcut.exists():
            try:
                shortcut.symlink_to(app_bundle)
                print_status("Desktop shortcut created")
                return True
            except OSError:
                print_warning("Could not create desktop shortcut")

    elif system == "Windows":
        # Create VBS script to make shortcut
        desktop = Path.home() / "Desktop"
        vbs_script = f"""
Set WshShell = WScript.CreateObject("WScript.Shell")
Set Shortcut = WshShell.CreateShortcut("{desktop}\\{APP_NAME}.lnk")
Shortcut.TargetPath = "python"
Shortcut.Arguments = "{install_dir}\\{PYTHON_SCRIPT}"
Shortcut.WorkingDirectory = "{install_dir}"
Shortcut.Description = "Lyrics Scraper - Find and save lyrics for your music"
Shortcut.Save
"""

        with tempfile.NamedTemporaryFile(mode='w', suffix='.vbs', delete=False) as f:
            f.write(vbs_script)
            vbs_path = f.name

        try:
            subprocess.run(['cscript', '//nologo', vbs_path], check=True, capture_output=True)
            print_status("Desktop shortcut created")
            return True
        except subprocess.CalledProcessError:
            print_warning("Could not create desktop shortcut")
        finally:
            os.unlink(vbs_path)

    else:  # Linux
        desktop = Path.home() / "Desktop"
        desktop_file = desktop / f"{APP_NAME}.desktop"

        desktop_content = f"""[Desktop Entry]
Name={APP_NAME}
Comment=Find and save lyrics for your music
Exec=python3 "{install_dir}/{PYTHON_SCRIPT}"
Path={install_dir}
Terminal=false
Type=Application
Categories=AudioVideo;Audio;
"""

        try:
            with open(desktop_file, 'w') as f:
                f.write(desktop_content)
            desktop_file.chmod(0o755)
            print_status("Desktop shortcut created")
            return True
        except OSError:
            print_warning("Could not create desktop shortcut")

    return False


def download_and_extract():
    """Download and extract the application from GitHub"""
    print_status("Downloading Lyrics Scraper from GitHub...")

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        zip_path = temp_path / "lyrics-scraper.zip"

        try:
            # Download the repository
            urllib.request.urlretrieve(DOWNLOAD_URL, zip_path)
            print_status("Download completed")

            # Extract the zip file
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(temp_path)

            # Find the extracted folder (it will be named LyricsFinder-main)
            extracted_folders = [d for d in temp_path.iterdir() if d.is_dir() and d.name.startswith('LyricsFinder')]
            if not extracted_folders:
                print_error("Could not find extracted application files")
                return None

            source_dir = extracted_folders[0]

            # Check if main script exists
            if not (source_dir / PYTHON_SCRIPT).exists():
                print_error(f"Main script '{PYTHON_SCRIPT}' not found in downloaded files")
                return None

            print_status("Files extracted successfully")
            return source_dir

        except Exception as e:
            print_error(f"Failed to download application: {e}")
            return None


def main():
    """Main installer function"""
    # Disable colors on Windows if needed
    if platform.system() == "Windows":
        Colors.disable_on_windows()

    print_header()
    print(f"This installer will download and install Lyrics Scraper from:")
    print(f"{Colors.BLUE}{GITHUB_REPO}{Colors.NC}")
    print()

    # Check prerequisites
    if not check_python():
        sys.exit(1)

    if not check_pip():
        sys.exit(1)

    # Download and extract application
    source_dir = download_and_extract()
    if not source_dir:
        sys.exit(1)

    # Install dependencies
    if not install_dependencies():
        print_error("Failed to install dependencies.")
        sys.exit(1)

    # Get installation directory
    install_dir = get_install_dir()
    print_status(f"Installing to: {install_dir}")

    # Create installation directory
    install_dir.mkdir(parents=True, exist_ok=True)

    # Handle macOS app bundle
    if platform.system() == "Darwin":
        app_bundle = create_macos_app(install_dir)

    # Copy main script and any additional files
    shutil.copy2(source_dir / PYTHON_SCRIPT, install_dir / PYTHON_SCRIPT)

    # Copy icon files if they exist
    icon_files = ["icon.icns", "icon.ico", "icon.png"]
    for icon_name in icon_files:
        icon_path = source_dir / icon_name
        if icon_path.exists():
            shutil.copy2(icon_path, install_dir / icon_name)
            print_status(f"Copied {icon_name}")

    # Copy README if it exists
    readme_path = source_dir / "README.md"
    if readme_path.exists():
        shutil.copy2(readme_path, install_dir / "README.md")

    print_status("Application files copied")

    # Create launcher script
    create_launcher_script(install_dir)
    print_status("Launcher script created")

    # Offer to create shortcuts
    try:
        create_shortcut = input("Would you like to create a desktop shortcut? (y/n): ").lower().startswith('y')
        if create_shortcut:
            create_desktop_shortcut(install_dir)
    except (EOFError, KeyboardInterrupt):
        print()
        print_status("Skipping shortcut creation")

    # Set permissions on macOS
    if platform.system() == "Darwin":
        try:
            subprocess.run(['xattr', '-cr', str(app_bundle)], capture_output=True)
            print_status("Security attributes configured")
        except subprocess.CalledProcessError:
            pass

    print()
    print_status("Installation completed successfully!")
    print()
    print(f"{Colors.BLUE}The Lyrics Scraper has been installed to:{Colors.NC}")
    print(f"  {install_dir}")
    print()

    system = platform.system()
    if system == "Darwin":
        print(f"{Colors.BLUE}You can now:{Colors.NC}")
        print("  • Find it in your Applications folder")
        print("  • Run it from Spotlight (Cmd+Space, type 'Lyrics Scraper')")
        if create_shortcut:
            print("  • Use the desktop shortcut")
        print()
        print(f"{Colors.YELLOW}Note:{Colors.NC} If macOS shows a security warning when first running:")
        print("  1. Right-click the app → Open → Open")
        print("  2. Or go to System Preferences → Security & Privacy → General")
        print("     and click 'Open Anyway'")
    elif system == "Windows":
        print(f"{Colors.BLUE}You can now run it by:{Colors.NC}")
        if create_shortcut:
            print("  • Using the desktop shortcut")
        print(f"  • Running: {install_dir}\\Launch Lyrics Scraper.bat")
    else:
        print(f"{Colors.BLUE}You can now run it by:{Colors.NC}")
        if create_shortcut:
            print("  • Using the desktop shortcut")
        print(f"  • Running: {install_dir}/launch.sh")

    print()
    print_status("Installation complete! Enjoy using Lyrics Scraper!")


if __name__ == "__main__":
    main()
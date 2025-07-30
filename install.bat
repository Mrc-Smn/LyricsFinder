@echo off
setlocal enabledelayedexpansion

:: Lyrics Scraper Windows Installer
echo ===============================
echo Lyrics Scraper Installer
echo ===============================
echo.

:: Configuration
set "APP_NAME=Lyrics Scraper"
set "INSTALL_DIR=%LOCALAPPDATA%\LyricsScraper"
set "PYTHON_SCRIPT=lyrics_scraper_app.py"
set "SHORTCUT_NAME=Lyrics Scraper.lnk"

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3 from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    pause
    exit /b 1
)

echo [INFO] Python found:
python --version

:: Check if pip is available
pip --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] pip is not installed or not in PATH.
    echo Please reinstall Python with pip included.
    pause
    exit /b 1
)

:: Create installation directory
echo [INFO] Creating installation directory: %INSTALL_DIR%
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

:: Install dependencies
echo [INFO] Installing Python dependencies...
pip install --user requests beautifulsoup4 mutagen lyricsgenius unidecode
if errorlevel 1 (
    echo [WARNING] Some dependencies might have failed to install.
    echo The application might still work, but some features may be limited.
)

:: Copy application files
echo [INFO] Copying application files...
copy "%PYTHON_SCRIPT%" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo [ERROR] Could not copy main application file.
    echo Make sure %PYTHON_SCRIPT% is in the current directory.
    pause
    exit /b 1
)

:: Copy icon if it exists
if exist "icon.ico" (
    copy "icon.ico" "%INSTALL_DIR%\" >nul
    echo [INFO] Icon file copied.
) else (
    echo [WARNING] Icon file not found. Application will use default icon.
)

:: Create launcher batch file
echo [INFO] Creating launcher script...
(
echo @echo off
echo cd /d "%INSTALL_DIR%"
echo python "%PYTHON_SCRIPT%"
echo pause
) > "%INSTALL_DIR%\Launch Lyrics Scraper.bat"

:: Create Python launcher (alternative)
(
echo import sys
echo import os
echo import subprocess
echo.
echo # Change to the script directory
echo script_dir = os.path.dirname(os.path.abspath(__file__^)^)
echo os.chdir(script_dir^)
echo.
echo # Run the main application
echo subprocess.run([sys.executable, "%PYTHON_SCRIPT%"]^)
) > "%INSTALL_DIR%\launch.py"

:: Create desktop shortcut
set /p create_desktop="Would you like to create a desktop shortcut? (y/n): "
if /i "!create_desktop!"=="y" (
    echo [INFO] Creating desktop shortcut...

    :: Create VBS script to create shortcut
    (
    echo Set WshShell = WScript.CreateObject("WScript.Shell"^)
    echo Set Shortcut = WshShell.CreateShortcut("%USERPROFILE%\Desktop\%SHORTCUT_NAME%"^)
    echo Shortcut.TargetPath = "python"
    echo Shortcut.Arguments = """%INSTALL_DIR%\%PYTHON_SCRIPT%"""
    echo Shortcut.WorkingDirectory = "%INSTALL_DIR%"
    echo Shortcut.IconLocation = "%INSTALL_DIR%\icon.ico"
    echo Shortcut.Description = "Lyrics Scraper - Find and save lyrics for your music"
    echo Shortcut.Save
    ) > "%TEMP%\create_shortcut.vbs"

    cscript //nologo "%TEMP%\create_shortcut.vbs"
    del "%TEMP%\create_shortcut.vbs"

    if exist "%USERPROFILE%\Desktop\%SHORTCUT_NAME%" (
        echo [INFO] Desktop shortcut created successfully.
    ) else (
        echo [WARNING] Could not create desktop shortcut.
    )
)

:: Create Start Menu shortcut
set /p create_startmenu="Would you like to add to Start Menu? (y/n): "
if /i "!create_startmenu!"=="y" (
    echo [INFO] Adding to Start Menu...

    set "START_MENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs"

    :: Create VBS script for Start Menu shortcut
    (
    echo Set WshShell = WScript.CreateObject("WScript.Shell"^)
    echo Set Shortcut = WshShell.CreateShortcut("!START_MENU_DIR!\%SHORTCUT_NAME%"^)
    echo Shortcut.TargetPath = "python"
    echo Shortcut.Arguments = """%INSTALL_DIR%\%PYTHON_SCRIPT%"""
    echo Shortcut.WorkingDirectory = "%INSTALL_DIR%"
    echo Shortcut.IconLocation = "%INSTALL_DIR%\icon.ico"
    echo Shortcut.Description = "Lyrics Scraper - Find and save lyrics for your music"
    echo Shortcut.Save
    ) > "%TEMP%\create_startmenu_shortcut.vbs"

    cscript //nologo "%TEMP%\create_startmenu_shortcut.vbs"
    del "%TEMP%\create_startmenu_shortcut.vbs"

    echo [INFO] Start Menu shortcut created.
)

:: Create uninstaller
echo [INFO] Creating uninstaller...
(
echo @echo off
echo echo Uninstalling Lyrics Scraper...
echo.
echo :: Remove installation directory
echo if exist "%INSTALL_DIR%" (
echo     rmdir /s /q "%INSTALL_DIR%"
echo     echo Installation directory removed.
echo ^)
echo.
echo :: Remove desktop shortcut
echo if exist "%USERPROFILE%\Desktop\%SHORTCUT_NAME%" (
echo     del "%USERPROFILE%\Desktop\%SHORTCUT_NAME%"
echo     echo Desktop shortcut removed.
echo ^)
echo.
echo :: Remove Start Menu shortcut
echo if exist "%APPDATA%\Microsoft\Windows\Start Menu\Programs\%SHORTCUT_NAME%" (
echo     del "%APPDATA%\Microsoft\Windows\Start Menu\Programs\%SHORTCUT_NAME%"
echo     echo Start Menu shortcut removed.
echo ^)
echo.
echo echo Lyrics Scraper has been uninstalled.
echo pause
) > "%INSTALL_DIR%\Uninstall.bat"

echo.
echo ===============================
echo Installation completed successfully!
echo ===============================
echo.
echo The Lyrics Scraper has been installed to:
echo   %INSTALL_DIR%
echo.
echo You can now run it by:
if /i "!create_desktop!"=="y" echo   • Using the desktop shortcut
if /i "!create_startmenu!"=="y" echo   • Searching for "Lyrics Scraper" in Start Menu
echo   • Running: "%INSTALL_DIR%\Launch Lyrics Scraper.bat"
echo.
echo To uninstall, run: "%INSTALL_DIR%\Uninstall.bat"
echo.
echo Installation complete! Press any key to exit.
pause >nul
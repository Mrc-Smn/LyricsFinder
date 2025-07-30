#!/bin/bash

# Lyrics Scraper Installer Script
# This script installs the Lyrics Scraper application with all dependencies

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
APP_NAME="Lyrics Scraper"
INSTALL_DIR="$HOME/Applications"
PYTHON_SCRIPT="lyrics_scraper_app.py"
REQUIREMENTS="requirements.txt"
ICON_FILE="icon.icns"

echo -e "${BLUE}=== Lyrics Scraper Installer ===${NC}"
echo ""

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    print_error "This installer is designed for macOS. For other platforms, please run directly with Python."
    exit 1
fi

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is required but not installed."
    echo "Please install Python 3 from https://www.python.org/downloads/"
    exit 1
fi

print_status "Python 3 found: $(python3 --version)"

# Check if pip is available
if ! command -v pip3 &> /dev/null; then
    print_error "pip3 is required but not installed."
    echo "Please install pip3 or reinstall Python 3 with pip included."
    exit 1
fi

# Create installation directory
print_status "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"

# Create app bundle directory
APP_BUNDLE="$INSTALL_DIR/$APP_NAME.app"
CONTENTS_DIR="$APP_BUNDLE/Contents"
MACOS_DIR="$CONTENTS_DIR/MacOS"
RESOURCES_DIR="$CONTENTS_DIR/Resources"

print_status "Creating app bundle structure..."
mkdir -p "$MACOS_DIR"
mkdir -p "$RESOURCES_DIR"

# Install Python dependencies
print_status "Installing Python dependencies..."
pip3 install --user requests beautifulsoup4 mutagen lyricsgenius unidecode

# Copy application files
print_status "Copying application files..."
cp "$PYTHON_SCRIPT" "$MACOS_DIR/"

# Copy icon if it exists
if [ -f "$ICON_FILE" ]; then
    cp "$ICON_FILE" "$RESOURCES_DIR/"
    ICON_NAME=$(basename "$ICON_FILE")
else
    print_warning "Icon file not found. App will use default icon."
    ICON_NAME=""
fi

# Create Info.plist
print_status "Creating Info.plist..."
cat > "$CONTENTS_DIR/Info.plist" << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>lyrics_scraper</string>
    <key>CFBundleIdentifier</key>
    <string>com.lyricsscraper.app</string>
    <key>CFBundleName</key>
    <string>$APP_NAME</string>
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
$([ -n "$ICON_NAME" ] && echo "    <key>CFBundleIconFile</key>
    <string>$ICON_NAME</string>")
    <key>LSMinimumSystemVersion</key>
    <string>10.12</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSApplicationCategoryType</key>
    <string>public.app-category.music</string>
</dict>
</plist>
EOF

# Create launcher script
print_status "Creating launcher script..."
cat > "$MACOS_DIR/lyrics_scraper" << 'EOF'
#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Set up Python path to use user-installed packages
export PYTHONPATH="$HOME/.local/lib/python$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')/site-packages:$PYTHONPATH"

# Change to the script directory
cd "$SCRIPT_DIR"

# Run the Python application
python3 lyrics_scraper_app.py
EOF

# Make launcher executable
chmod +x "$MACOS_DIR/lyrics_scraper"

# Create desktop shortcut option
read -p "Would you like to create a desktop shortcut? (y/n): " create_shortcut
if [[ $create_shortcut =~ ^[Yy]$ ]]; then
    ln -sf "$APP_BUNDLE" "$HOME/Desktop/$APP_NAME.app"
    print_status "Desktop shortcut created."
fi

# Create Applications folder shortcut
if [ ! -e "/Applications/$APP_NAME.app" ]; then
    ln -sf "$APP_BUNDLE" "/Applications/$APP_NAME.app" 2>/dev/null || true
    if [ -e "/Applications/$APP_NAME.app" ]; then
        print_status "Application added to /Applications folder."
    else
        print_warning "Could not create shortcut in /Applications (permission denied)."
    fi
fi

# Set extended attributes to help with Gatekeeper
print_status "Configuring security attributes..."
xattr -cr "$APP_BUNDLE" 2>/dev/null || true

echo ""
print_status "Installation completed successfully!"
echo ""
echo -e "${BLUE}The Lyrics Scraper has been installed to:${NC}"
echo "  $APP_BUNDLE"
echo ""
echo -e "${BLUE}You can now:${NC}"
echo "  • Find it in your Applications folder"
echo "  • Run it from Spotlight (Cmd+Space, type 'Lyrics Scraper')"
if [[ $create_shortcut =~ ^[Yy]$ ]]; then
echo "  • Use the desktop shortcut"
fi
echo ""
echo -e "${YELLOW}Note:${NC} If macOS shows a security warning when first running:"
echo "  1. Right-click the app → Open → Open"
echo "  2. Or go to System Preferences → Security & Privacy → General"
echo "     and click 'Open Anyway'"
echo ""
print_status "Installation complete! Enjoy using Lyrics Scraper!"
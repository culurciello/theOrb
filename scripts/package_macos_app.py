#!/usr/bin/env python3
"""
macOS App Packaging Script for theOrb Web App
Creates a distributable .app bundle for macOS
"""

import os
import sys
import shutil
import subprocess
import json
from pathlib import Path

def create_app_bundle():
    """Create macOS .app bundle structure"""
    app_name = "theOrb"
    app_dir = f"{app_name}.app"
    
    # Remove existing app if it exists
    if os.path.exists(app_dir):
        shutil.rmtree(app_dir)
    
    # Create app bundle structure
    contents_dir = os.path.join(app_dir, "Contents")
    macos_dir = os.path.join(contents_dir, "MacOS")
    resources_dir = os.path.join(contents_dir, "Resources")
    
    os.makedirs(macos_dir, exist_ok=True)
    os.makedirs(resources_dir, exist_ok=True)
    
    return app_dir, contents_dir, macos_dir, resources_dir

def create_info_plist(contents_dir):
    """Create Info.plist file"""
    info_plist = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>theOrb</string>
    <key>CFBundleIdentifier</key>
    <string>com.theorb.app</string>
    <key>CFBundleName</key>
    <string>theOrb</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleIconFile</key>
    <string>icon.png</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.15</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>LSUIElement</key>
    <false/>
</dict>
</plist>"""
    
    with open(os.path.join(contents_dir, "Info.plist"), "w") as f:
        f.write(info_plist)

def create_launcher_script(macos_dir):
    """Create launcher script"""
    launcher_script = """#!/bin/bash
# theOrb macOS Launcher Script

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$DIR/../Resources/app"

# Change to app directory
cd "$APP_DIR"

# Set Python path to include the app directory
export PYTHONPATH="$APP_DIR:$PYTHONPATH"

# Check if port 3000 is available
if lsof -Pi :3000 -sTCP:LISTEN -t >/dev/null ; then
    echo "Port 3000 is already in use. Please close any applications using this port and try again."
    exit 1
fi

# Start the Flask app
echo "Starting theOrb..."
echo "The application will be available at: http://localhost:3000"
echo "Press Ctrl+C to stop the application"

# Run the Python app
python3 app.py

# Keep the terminal open if there's an error
if [ $? -ne 0 ]; then
    echo "Press any key to continue..."
    read -n 1
fi
"""
    
    launcher_path = os.path.join(macos_dir, "theOrb")
    with open(launcher_path, "w") as f:
        f.write(launcher_script)
    
    # Make launcher executable
    os.chmod(launcher_path, 0o755)

def copy_app_files(resources_dir):
    """Copy all necessary application files"""
    app_resources_dir = os.path.join(resources_dir, "app")
    os.makedirs(app_resources_dir, exist_ok=True)
    
    # Files and directories to copy
    items_to_copy = [
        "app.py",
        "ai_agent.py", 
        "database.py",
        "document_processor.py",
        "models.py",
        "prompt.txt",
        "requirements.txt",
        "routes.py",
        "vector_store.py",
        "pipelines",
        "static",
        "templates",
        "instance",
        "chroma_db"
    ]
    
    for item in items_to_copy:
        src = item
        dst = os.path.join(app_resources_dir, item)
        
        if os.path.exists(src):
            if os.path.isdir(src):
                if os.path.exists(dst):
                    shutil.rmtree(dst)
                shutil.copytree(src, dst)
                print(f"Copied directory: {src}")
            else:
                shutil.copy2(src, dst)
                print(f"Copied file: {src}")
        else:
            print(f"Warning: {src} not found, skipping...")
    
    # Create necessary directories if they don't exist
    os.makedirs(os.path.join(app_resources_dir, "temp"), exist_ok=True)
    os.makedirs(os.path.join(app_resources_dir, "uploads"), exist_ok=True)

def create_readme(app_dir):
    """Create README for the app"""
    readme_content = """# theOrb macOS Application

## Installation
1. Copy theOrb.app to your Applications folder
2. Install Python dependencies by running the install script

## Requirements
- macOS 10.15 or later
- Python 3.8 or later
- Required Python packages (see requirements.txt)

## First Time Setup
Before running theOrb for the first time, you need to install the Python dependencies:

1. Open Terminal
2. Navigate to the theOrb.app/Contents/Resources/app directory
3. Run: pip3 install -r requirements.txt

## Usage
1. Double-click theOrb.app to launch
2. The application will start a web server on port 3000
3. Open your web browser and go to http://localhost:3000
4. The application interface will load in your browser

## Environment Variables
Create a .env file in the app directory with:
- SECRET_KEY=your-secret-key
- Any other required API keys

## Stopping the Application
Press Ctrl+C in the terminal window that opens when you run the app.

## Troubleshooting
- If port 3000 is in use, close any applications using that port
- Make sure all Python dependencies are installed
- Check that you have the required API keys configured
"""
    
    with open(os.path.join(app_dir, "README.txt"), "w") as f:
        f.write(readme_content)

def create_install_script(app_dir):
    """Create installation script for dependencies"""
    install_script = """#!/bin/bash
# theOrb Installation Script

echo "Installing theOrb dependencies..."

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
APP_DIR="$DIR/Contents/Resources/app"

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is required but not installed."
    echo "Please install Python 3 from https://python.org"
    exit 1
fi

# Check if pip is installed
if ! command -v pip3 &> /dev/null; then
    echo "pip3 is required but not installed."
    echo "Please install pip3"
    exit 1
fi

# Install requirements
cd "$APP_DIR"
echo "Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "Installation completed successfully!"
    echo "You can now run theOrb.app"
else
    echo "Installation failed. Please check the error messages above."
    exit 1
fi
"""
    
    install_path = os.path.join(app_dir, "install_dependencies.sh")
    with open(install_path, "w") as f:
        f.write(install_script)
    
    # Make script executable
    os.chmod(install_path, 0o755)

def main():
    print("Creating theOrb macOS Application Bundle...")
    
    # Create app bundle structure
    app_dir, contents_dir, macos_dir, resources_dir = create_app_bundle()
    print(f"Created app bundle: {app_dir}")
    
    # Create Info.plist
    create_info_plist(contents_dir)
    print("Created Info.plist")
    
    # Create launcher script
    create_launcher_script(macos_dir)
    print("Created launcher script")
    
    # Copy application files
    copy_app_files(resources_dir)
    print("Copied application files")
    
    # Copy icon if available
    if os.path.exists("static/icon-light.png"):
        shutil.copy2("static/icon-light.png", os.path.join(resources_dir, "icon.png"))
        print("Copied application icon")
    
    # Create README
    create_readme(app_dir)
    print("Created README")
    
    # Create install script
    create_install_script(app_dir)
    print("Created dependency installation script")
    
    print(f"\n✅ Successfully created {app_dir}")
    print("\nNext steps:")
    print(f"1. Run: ./{app_dir}/install_dependencies.sh")
    print("2. Copy theOrb.app to another Mac")
    print("3. Run the install script on the target machine")
    print("4. Double-click theOrb.app to launch")
    print("\nNote: The target machine needs Python 3.8+ installed")

if __name__ == "__main__":
    main()
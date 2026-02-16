# HTML-to-PDF Converter Setup Guide

## Prerequisites

### System Requirements
- **Windows 10/11** or **Linux Ubuntu 18.04+**
- **Node.js 16+** and **npm**
- **Python 3.8+**
- **Rust** (latest stable version)
- **WeasyPrint dependencies** (see below)

### WeasyPrint Dependencies (Windows)

WeasyPrint requires several external libraries that need to be installed separately:

#### Option 1: Using GTK3 Runtime (Recommended)
1. Download and install **GTK3-Runtime Win64** from:
   - https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer
   - Choose the latest version (usually GTK3-Runtime Win64)

2. Run the installer with **Administrator privileges**

3. Restart your command prompt/terminal

#### Option 2: Using MSYS2 (Advanced Users)
```bash
# Install MSYS2 from https://www.msys2.org/
# Then run in MSYS2 terminal:
pacman -S mingw-w64-x86_64-python
pacman -S mingw-w64-x86_64-gtk3
pacman -S mingw-w64-x86_64-cairo
pacman -S mingw-w64-x86_64-pango
```

### WeasyPrint Dependencies (Linux)
```bash
# Ubuntu/Debian:
sudo apt-get install python3-dev python3-pip python3-cffi python3-brotli libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0

# CentOS/RHEL:
sudo yum install python3-devel python3-pip python3-cffi pango harfbuzz

# Arch Linux:
sudo pacman -S python python-pip python-cffi pango harfbuzz
```

## Installation Steps

### 1. Clone and Setup Project
```bash
git clone <your-repository-url>
cd html-to-pdf
npm install
```

### 2. Install Python Dependencies
```bash
# Install Python dependencies
pip install -r src-backend/requirements.txt

# Verify WeasyPrint installation
python -c "import weasyprint; print('WeasyPrint installed successfully')"
```

### 3. Install Tauri Prerequisites
```bash
# Install Tauri CLI
npm install -g @tauri-apps/cli

# On Windows, you may also need:
# - Microsoft C++ Build Tools
# - Windows SDK
```

### 4. Build the Backend Executable
```bash
# Build the Python backend into a standalone executable
python scripts/build_sidecar.py
```

This will create the backend executable in `src-tauri/binaries/`.

### 5. Test the Application
```bash
# Run in development mode
npm run dev
```

The application should open with a GUI window.

## Troubleshooting

### WeasyPrint Issues

#### "WeasyPrint could not import some external libraries"
This error indicates missing system dependencies:

**Windows:**
- Ensure GTK3 Runtime is properly installed
- Check that `GTK3-Runtime Win64\bin` is in your system PATH
- Restart your terminal/IDE after installation

**Linux:**
- Install the required system packages (see above)
- For older distributions, you may need to compile dependencies from source

#### "DLL load failed" (Windows)
- Install Microsoft Visual C++ Redistributable
- Ensure you're using 64-bit Python on 64-bit Windows
- Try running from an Administrator command prompt

### PyInstaller Issues

#### "Failed to execute script"
- Check that all dependencies are properly installed
- Try building with `--debug` flag for more information
- Ensure PyInstaller is the latest version

#### Large Executable Size
- The executable (~30MB) is normal due to bundled dependencies
- Use `--onefile` option for single executable (already configured)

### Tauri Issues

#### "Failed to start backend"
- Ensure the backend executable exists in `src-tauri/binaries/`
- Check file permissions (executable bit on Linux/Mac)
- Try running the backend manually to test

#### "WebSocket connection failed"
- Check if backend is running (should listen on port 8765)
- Verify firewall settings allow local connections
- Ensure no other application is using port 8765

## Development Workflow

### Running in Development Mode
```bash
# Terminal 1: Start the backend manually (optional)
python src-backend/main.py

# Terminal 2: Start Tauri in dev mode
npm run dev
```

### Building for Production
```bash
# Build everything
npm run build-sidecar  # Build Python backend
npm run build          # Build Tauri application
```

### Testing Sample Files
1. Place HTML files in the `html-drop/` directory
2. Run the application
3. Select the HTML files through the UI
4. Choose output directory (default: `pdf-export/`)
5. Click "Convert" to start processing

## Project Structure
```
html-to-pdf/
├── src/                    # Frontend (HTML/CSS/JS)
├── src-backend/           # Python backend
├── src-tauri/             # Tauri/Rust configuration
├── html-drop/             # Input HTML files
├── pdf-export/            # Output PDF files
└── scripts/               # Build scripts
```

## Environment Variables

Optional environment variables for customization:

```bash
# Backend settings
BACKEND_HOST=localhost      # WebSocket host (default: localhost)
BACKEND_PORT=8765          # WebSocket port (default: 8765)
MAX_WORKERS=4              # Number of worker processes (default: CPU count)

# Logging
LOG_LEVEL=INFO             # Logging level (DEBUG, INFO, WARNING, ERROR)
```

## Support

For issues and questions:
1. Check this troubleshooting guide
2. Review the WeasyPrint documentation: https://weasyprint.org/
3. Check Tauri documentation: https://tauri.app/
4. Open an issue in the project repository

## Version Information
- **Application Version:** 1.0.0
- **WeasyPrint Version:** 61.2
- **Tauri Version:** 1.5.0
- **Python Version:** 3.8+ required
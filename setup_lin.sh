#!/bin/bash

echo "==================================="
echo "  Web App Camera Setup Script"
echo "==================================="

# --- Detect OS flavor ---
echo "Detecting OS type..."
OS_NAME=$(grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
OS_VERSION=$(grep '^VERSION_CODENAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
echo "Detected: $OS_NAME ($OS_VERSION)"
echo "-----------------------------------"

# --- Ensure script is run with sudo privileges when needed ---
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script with: sudo bash setup_lin.sh"
    exit 1
fi

# --- Update APT and install system dependencies ---
echo "Installing required system packages..."
apt update

COMMON_PACKAGES="libcap-dev python3-venv python3-pip python3-opencv libcamera-dev python3-libcamera"

if [[ "$OS_NAME" == "raspbian" || "$OS_NAME" == "raspberrypi" ]]; then
    # Raspberry Pi OS specific
    apt install -y $COMMON_PACKAGES python3-picamera2
else
    # Ubuntu/Debian or others
    apt install -y $COMMON_PACKAGES
    # Try installing python3-picamera2 if available
    apt install -y python3-picamera2 || echo "Note: python3-picamera2 not found in this repo — skipping."
fi

echo "-----------------------------------"
echo "System dependencies installed."
echo "-----------------------------------"

# --- Python environment setup ---
cd "$(dirname "$0")"  # Move to the script's directory

if [ -d "venv" ]; then
    echo "Removing existing virtual environment..."
    rm -rf venv
fi

echo "Creating Python virtual environment..."
python3 -m venv venv --system-site-packages
source venv/bin/activate

echo "Upgrading pip..."
pip install --upgrade pip setuptools wheel

echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# --- Verify critical packages ---
echo "Verifying Flask and Picamera2 installations..."
python3 -c "import flask; print('Flask OK')" || { echo "Flask not installed correctly!"; exit 1; }
python3 -c "from picamera2 import Picamera2; print('Picamera2 OK')" || echo "Warning: Picamera2 not found in venv (using system version)."

# --- Run Flask app ---
echo "-----------------------------------"
echo "Setup Complete"
echo "-----------------------------------"
echo "Starting Flask Web App..."
echo "Access it at: http://127.0.0.1:5000"
python3 app.py
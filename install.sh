#!/usr/bin/env bash
set -euo pipefail

echo "==================================="
echo "  Web App INSTALL Script (one-time)"
echo "==================================="

# Go to repo root (folder where this script lives)
cd "$(dirname "$0")"

# --- System deps (run with sudo if needed) ---
if [ "${EUID:-$(id -u)}" -ne 0 ]; then
  echo "Tip: system packages may require sudo. Re-run as:"
  echo "  sudo bash install.sh"
  echo "Continuing without apt steps..."
else
  echo "Detecting OS type..."
  OS_NAME=$(grep '^ID=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
  OS_VERSION=$(grep '^VERSION_CODENAME=' /etc/os-release | cut -d'=' -f2 | tr -d '"')
  echo "Detected: $OS_NAME ($OS_VERSION)"
  echo "-----------------------------------"

  echo "Installing required system packages..."
  apt update
  COMMON_PACKAGES="libcap-dev python3-venv python3-pip python3-opencv libcamera-dev python3-libcamera"
  apt install -y $COMMON_PACKAGES

  # Picamera2 (Pi repos)
  apt install -y python3-picamera2 || echo "Note: python3-picamera2 not found — skipping."

  echo "-----------------------------------"
  echo "System dependencies installed."
  echo "-----------------------------------"
fi

# --- venv setup ---
if [ -d "venv" ]; then
  echo "Virtual environment exists. Reusing it."
else
  echo "Creating virtual environment..."
  python3 -m venv venv --system-site-packages
fi

# --- pip hardening (prevents incomplete-download pain) ---
mkdir -p ~/.config/pip
cat > ~/.config/pip/pip.conf <<'EOF'
[global]
timeout = 180
retries = 25
index-url = https://pypi.org/simple
extra-index-url = https://www.piwheels.org/simple
EOF

echo "Using pip config at ~/.config/pip/pip.conf:"
cat ~/.config/pip/pip.conf
echo "-----------------------------------"

# --- install deps ---
echo "Upgrading pip (best-effort, won't fail install if network hiccups)..."
./venv/bin/python -m pip install -U pip setuptools wheel -i https://pypi.org/simple || \
  echo "Pip upgrade skipped (network). Continuing..."

echo "Installing Python dependencies from requirements.txt..."
./venv/bin/python -m pip install -r requirements.txt

echo "-----------------------------------"
echo "Verifying key imports inside venv..."
./venv/bin/python -c "import flask; print('Flask OK')"
./venv/bin/python -c "from picamera2 import Picamera2; print('Picamera2 OK')" || \
  echo "Warning: Picamera2 import failed (may not be available on this device)."
./venv/bin/python -c "from ultralytics import YOLO; print('Ultralytics OK')"
echo "-----------------------------------"
echo "INSTALL COMPLETE"
echo
echo "Next, run: ./run.sh"

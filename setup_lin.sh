#!/bin/bash

echo "Setup for Web Application"

# Check for Python3
if ! command -v python3 &> /dev/null; then
    echo "Python3 not found. Install Python 3.10 or newer."
    exit 1
fi

# Create Virtual Environment
echo "Creating Python Virtual Environment"
python3 -m venv venv

# Activate Virtual Environment
echo "Activating Virtual Environment"
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip Package Manager"
python3 -m pip install --upgrade pip

# Install Dependencies
echo "Installing Dependencies"
python3 -m pip install -r requirements.txt

# Run Flask App
echo "Setup Complete"
echo " "
echo "Running Flask"
echo " "
echo " Access Web App at: http://127.0.0.1:5000"
python3 app.py

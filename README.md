# **Web Application for Computer Engineering Project Design**
### Project Title
  - Design of a Deep Learning-Based Fatigue Crack Detection System for Train Bogie Frames with 3D Defect Mapping

## Setup
### Setup for Windows (setup_win.bat)
  1. Download Repository
  2. Extract Files
  3. Open Terminal
  4. Change Directory to WebApp
  5. Execute Shell Script `./setup_win.bat`

### Setup for Linux (setup.lin.sh)
  1. Download Repository
  2. Extract Files
  3. Open Terminal
  4. Change Directory to WebApp
  5. Execute Shell Script `./setup_lin.sh`
  6. Possible errors:
     - bash: ./setup_lin.sh: /bin/bash^M: bad interpreter: No such file or directory
     - bash: ./setup_lin.sh: cannot execute: required file not found
         1. `sudo apt install dos2unix`
         2. `dos2unix setup_lin.sh`
     - bash: ./setup_lin.sh: Permission denied
         1. `sudo chmod +x setup_lin.sh`

## Logs
### Web App Template
created October 7
  - Bare bones template for starting web application

### First Pull Request Merge
executed October 11
  - Template with 3D display window

### Second Pull Request Merge
executed October 13
  - Initial Draft for Web Application

### Added Dependencies & Shell Script 
created October 14
  - Installs Dependencies
  - Auto-runs app.py

### Added Setup Directions
added October 17
  - Shell Script Directions

# **Web Application for Computer Engineering Project Design**
### Design of a Deep Learning-Based Fatigue Crack Detection System for Train Bogie Frames with 3D Defect Mapping

## Setup
### Upload 3D Model
  1. Download any 3D model (`.glb` format)
  2. Move file to `/static/models` directory
  3. Open `/static/js/viewer.js`
  4. Edit line 67 according to file name
```
  66 loader.load(
  67   '/static/models/<filename>.glb',
  68   (gltf) => {
```

### Setup for Different Operating Systems
| Setup for Linux (`setup_lin.sh`)| Setup for Windows (`setup_win.bat`)|
|---------------------------------|------------------------------------|
|1. Download Repository<br>2. Extract Files<br>3. Open Terminal<br>4. Change Directory to WebApp<br>5. Execute Shell Script `./setup_lin.sh`|1. Download Repository<br>2. Extract Files<br>3. Open Terminal<br>4. Change Directory to WebApp<br>5. Execute Shell Script `./setup_win.bat`|

|Possible Errors| Fixes |
|---------------|-------|
|`bad interpreter: No such file or directory`<br><br>`cannot execute: required file not found`|1. `sudo apt install dos2unix`<br>2. `dos2unix setup_lin.sh`|
|`bash: ./setup_lin.sh: Permission denied`|`sudo chmod +x setup_lin.sh`|

## Links
### [Sample Train Bogie Frame 3D Model](https://drive.google.com/drive/folders/1XeoyBypTwfNWYl4qd4Hxu3EB-nCV4RPv?usp=sharing)

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

### Added Setup Directions and SQLite Database
added October 17
  - Shell Script Directions
  - Implemented Local SQLite Database

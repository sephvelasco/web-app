:: Windows Shell Script
echo Setup of Web Application
echo --------------------------

:: Create Virtual Environment
py -m venv venv
call venv\Scripts\activate

:: Upgrade pip Package Manager
echo Upgrading pip...
echo --------------------------
py -m pip install --upgrade pip

:: Install Dependencies and Filter Linux-only Packages
echo Filtering Linux-only dependencies from requirements.txt...
findstr /v "picamera2 libcamera" requirements.txt > temp_requirements.txt
py -m pip install -r temp_requirements.txt
del temp_requirements.txt

:: Start Flask
echo Setup Complete!
echo --------------------------
echo Starting Flask...
echo --------------------------
py app.py
pause

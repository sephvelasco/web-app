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

:: Install Dependencies
echo Installing dependencies...
echo --------------------------
py -m pip install -r requirements.txt

:: Start Flask
echo Setup Complete!
echo --------------------------
echo Starting Flask...
echo --------------------------
py app.py
pause

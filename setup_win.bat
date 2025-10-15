echo Setup of Web Application

py -m venv venv
call venv\Scripts\activate

echo Upgrading pip...
echo --------------------------
py -m pip install --upgrade pip

echo Installing dependencies...
echo --------------------------
py -m pip install -r requirements.txt

echo Setup Complete!
echo Starting Flask...
echo --------------------------
py app.py
pause

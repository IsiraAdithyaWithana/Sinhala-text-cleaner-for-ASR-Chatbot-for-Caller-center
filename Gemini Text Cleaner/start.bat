@echo off
echo ================================
echo  Sinhala Cleaner API - Starting
echo ================================
echo.

cd /d "%~dp0"

echo Installing dependencies...
pip install -r requirements.txt

echo.
echo Starting server...
echo API running at: http://localhost:8000
echo API docs at:    http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

uvicorn main:app --host 0.0.0.0 --port 8000

pause
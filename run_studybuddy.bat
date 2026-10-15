@echo off
TITLE StudyBuddy - Student AI Assistant Launcher
COLOR 0B

echo =====================================================================
echo               STUDYBUDDY: STUDENT AI ASSISTANT (AI + ML)            
echo =====================================================================
echo.

:: Change to script directory
cd /d "%~dp0"

echo [1/3] Verifying Python installation...
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python was not found in PATH. Please install Python 3.10+ from python.org.
    pause
    exit /b
)
echo [OK] Python is available.

echo [2/3] Checking Machine Learning model artifact...
if not exist "data\student_performance_model.joblib" (
    echo [INFO] Trained model not found. Running training pipeline now...
    python ml\train_model.py
) else (
    echo [OK] Trained ML model artifact found.
)

echo [3/3] Starting StudyBuddy Web Application on http://127.0.0.1:5000 ...
echo.
echo =====================================================================
echo  Open your web browser at: http://127.0.0.1:5000
echo  Press Ctrl+C in this terminal window to stop the server.
echo =====================================================================
echo.

:: Automatically open default browser after 2 seconds
start "" http://127.0.0.1:5000

:: Run the Flask application
python app.py

pause

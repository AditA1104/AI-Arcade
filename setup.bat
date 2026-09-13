@echo off
REM One-command setup for Pose-Controlled AI Arcade (Windows).
REM
REM Usage: double-click setup.bat, or run it from a terminal:
REM   setup.bat
REM
REM What this does:
REM   1. Checks for a Python 3.11 interpreter
REM   2. Creates a virtual environment in .\venv (skips if it already exists)
REM   3. Installs the pinned dependencies from requirements.txt
REM   4. Launches the game
REM
REM Re-running this later just reuses the existing venv and launches the
REM game again — safe to run any time.

setlocal enabledelayedexpansion

echo === Pose-Controlled AI Arcade - Setup ===

where py >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python launcher 'py' not found on this machine.
    echo Install Python 3.11 from https://www.python.org/downloads/
    echo IMPORTANT: check "Add Python to PATH" during install.
    echo.
    pause
    exit /b 1
)

py -3.11 --version >nul 2>nul
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Python 3.11 is not installed.
    echo MediaPipe does not reliably support newer Python versions ^(3.12+^).
    echo.
    echo Install Python 3.11 from https://www.python.org/downloads/
    echo IMPORTANT: check "Add Python to PATH" during install.
    echo Then run setup.bat again.
    echo.
    pause
    exit /b 1
)

for /f "tokens=*" %%v in ('py -3.11 --version') do echo Using: %%v

if not exist "venv\" (
    echo Creating virtual environment...
    py -3.11 -m venv venv
) else (
    echo Virtual environment already exists - reusing it.
)

call venv\Scripts\activate.bat

echo Installing dependencies (this can take a few minutes the first time)...
python -m pip install --upgrade pip -q
pip install -r requirements.txt -q

echo.
echo === Setup complete. Launching the game... ===
echo.

python main.py

pause

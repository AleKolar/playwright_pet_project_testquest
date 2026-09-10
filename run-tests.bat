@echo off
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo Installing dependencies...
python -m pip install --upgrade pip --break-system-packages
python -m pip install -r requirements.txt --break-system-packages

echo Installing Playwright browser...
python -m playwright install chromium

if "%BASE_URL%"=="" set BASE_URL=https://testquest.pryaniky.com
echo Running tests with BASE_URL=%BASE_URL%
python -m pytest tests\ -v --tb=short --maxfail=5

exit /b %ERRORLEVEL%
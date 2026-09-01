@echo off
setlocal

cd /d "%~dp0\.."

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher ^(py.exe^) was not found.
    echo Install 64-bit Python 3.12 from python.org and try again.
    exit /b 1
)

py -3.12 -c "import sys; assert sys.version_info[:2] == (3, 12)" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] 64-bit Python 3.12 was not found.
    exit /b 1
)

if not exist ".venv-win\Scripts\python.exe" (
    echo [1/5] Creating the Windows Python 3.12 environment...
    py -3.12 -m venv .venv-win
    if errorlevel 1 exit /b 1
)

echo [2/5] Installing dependencies...
call .venv-win\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 exit /b 1
python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

echo [3/5] Building PackingManager.exe...
python -m PyInstaller --noconfirm --clean PackingManager.spec
if errorlevel 1 exit /b 1

echo [4/5] Running the packaged application smoke test...
dist\PackingManager\PackingManager.exe --smoke-test
if errorlevel 1 (
    echo [ERROR] The packaged application failed its startup test.
    exit /b 1
)

echo [5/5] Creating the distributable ZIP file...
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "Compress-Archive -Path 'dist\PackingManager\*' -DestinationPath 'dist\PackingManager-windows.zip' -Force"
if errorlevel 1 exit /b 1

echo.
echo Build completed successfully.
echo EXE: dist\PackingManager\PackingManager.exe
echo ZIP: dist\PackingManager-windows.zip
exit /b 0

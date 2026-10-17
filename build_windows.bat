@echo off
setlocal
cd /d "%~dp0"
py -3 -m pip install --upgrade pyinstaller
py -3 -m PyInstaller --noconfirm --clean --onedir --windowed --name AinakMahal --hidden-import=auth_session launcher.py
if errorlevel 1 (echo Build failed & exit /b 1)
echo EXE created under dist\AinakMahal\AinakMahal.exe
pause

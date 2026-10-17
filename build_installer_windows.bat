@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>&1 || (echo Python is required on BUILD PC only. & exit /b 1)
py -3 -m pip install --disable-pip-version-check pyinstaller || exit /b 1
py -3 -m unittest discover -q || exit /b 1
py -3 -m PyInstaller --noconfirm --clean --onedir --windowed --name AinakMahal launcher.py || exit /b 1
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" (echo Install Inno Setup 6 on BUILD PC. & exit /b 1)
"%ISCC%" "installer\AinakMahal.iss" || exit /b 1
echo Installer generated: output\AinakMahal_Setup.exe
pause

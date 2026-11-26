@echo off
setlocal
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\build.ps1
exit /b %errorlevel%

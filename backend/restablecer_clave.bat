@echo off
rem Restablece la contraseña de una cuenta de VicMar (la clave se escribe oculta).
chcp 65001 >nul
cd /d "%~dp0"
venv\Scripts\python.exe restablecer_clave.py
echo.
pause

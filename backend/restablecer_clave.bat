@echo off
REM ==========================================================================
REM  Restablece la contraseña de una cuenta de VicMar desde la consola (RF-15).
REM  Las contraseñas se guardan como hash bcrypt y no se recuperan: este
REM  archivo abre restablecer_clave.py, que pide la nueva clave sin mostrarla.
REM  Uso: doble clic, desde la carpeta backend.
REM  Autores: Marlon David Perez Almachi, Victor Manuel Lluilema Pisco (UNEMI, 2026)
REM ==========================================================================
chcp 65001 >nul
cd /d "%~dp0"
venv\Scripts\python.exe restablecer_clave.py
echo.
pause

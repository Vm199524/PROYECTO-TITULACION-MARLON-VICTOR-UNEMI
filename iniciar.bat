@echo off
REM ==========================================================================
REM  Doble clic: instala lo que falte y levanta la API (8090) y la web (3000).
REM  Equivale a ejecutar "npm start" en esta carpeta. Ctrl+C detiene todo.
REM  Autores: Marlon David Perez Almachi, Victor Manuel Lluilema Pisco (UNEMI, 2026)
REM ==========================================================================
chcp 65001 >nul
cd /d "%~dp0"
node scripts\iniciar.mjs
pause

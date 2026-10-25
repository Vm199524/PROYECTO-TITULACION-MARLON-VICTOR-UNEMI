@echo off
REM ==========================================================================
REM  Levanta el sistema para usarlo o demostrarlo:
REM    API (FastAPI, puerto 8090) y aplicación web (Vite, puerto 3000).
REM  Abre dos ventanas; cerrarlas detiene el sistema.
REM  Autores: Marlon David Perez Almachi, Victor Manuel Lluilema Pisco (UNEMI, 2026)
REM ==========================================================================
chcp 65001 >nul
setlocal
set RAIZ=%~dp0..
where docker >nul 2>nul && docker start vicmar-sqlserver >nul 2>nul

start "VicMar - API (8090)" cmd /k "cd /d "%RAIZ%\backend" && set PYTHONUTF8=1 && venv\Scripts\python.exe -m uvicorn main:app --port 8090"

cd /d "%RAIZ%\frontend"
REM npm install siempre: si package.json cambió (nueva versión de la interfaz), instala lo que falte.
echo Verificando las dependencias de la aplicación web ...
call npm install --no-fund --no-audit
start "VicMar - Web (3000)" cmd /k "cd /d "%RAIZ%\frontend" && npm run dev"
echo Sistema iniciado: http://localhost:3000
endlocal

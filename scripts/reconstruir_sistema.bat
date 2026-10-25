@echo off
REM ==========================================================================
REM  Reconstruye el sistema de punta a punta en Windows:
REM  entorno virtual + dependencias + SQL Server (Docker) + procesos por lotes.
REM  Uso: doble clic, o desde una consola:  reconstruir_sistema.bat [opciones]
REM  Opciones (se pasan a scripts.pipeline): --rapido  --con-consulta
REM           --desde PASO  --solo PASO1,PASO2  --sin-oulad  --reentrenar INSTITUCION
REM  Las credenciales se leen de backend\.env; este archivo no
REM  contiene ni muestra contraseñas.
REM  Autores: Marlon David Perez Almachi, Victor Manuel Lluilema Pisco (UNEMI, 2026)
REM ==========================================================================
chcp 65001 >nul
setlocal
cd /d "%~dp0..\backend"
if not exist datos_locales mkdir datos_locales

if not exist venv\Scripts\python.exe (
    echo Creando el entorno virtual de Python ...
    py -3.14 -m venv venv 2>nul || py -3 -m venv venv
)
echo Instalando dependencias (registro en datos_locales\pip_install.log) ...
venv\Scripts\python.exe -m pip install --disable-pip-version-check -r requirements.txt > datos_locales\pip_install.log 2>&1
if errorlevel 1 (
    echo ERROR al instalar dependencias. Revise datos_locales\pip_install.log
    goto fin
)

where docker >nul 2>nul || goto sin_docker
docker info >nul 2>nul && goto docker_listo
if not exist "%ProgramFiles%\Docker\Docker\Docker Desktop.exe" goto sin_docker
echo Iniciando Docker Desktop ...
start "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"
set /a ESPERA=0
:esperar_docker
timeout /t 3 /nobreak >nul
docker info >nul 2>nul && goto docker_listo
set /a ESPERA+=1
if %ESPERA% lss 60 goto esperar_docker
:docker_listo
echo Iniciando el contenedor de SQL Server ...
docker start vicmar-sqlserver >nul 2>nul
:sin_docker

set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
venv\Scripts\python.exe -m scripts.pipeline %*

:fin
echo.
if not "%SIN_PAUSA%"=="1" pause
endlocal

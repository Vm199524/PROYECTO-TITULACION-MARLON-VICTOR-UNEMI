@echo off
REM ==========================================================================
REM  Actualiza la copia local del repositorio a la rama main (version vigente)
REM  y reconstruye el sistema. Los cambios locales sin subir quedan guardados
REM  en un "git stash" (no se pierde nada).
REM  Opcion: ACTUALIZAR_Y_RECONSTRUIR_V3.bat --solo consulta --con-consulta
REM  Autores: Marlon David Perez Almachi, Victor Manuel Lluilema Pisco (UNEMI, 2026)
REM ==========================================================================
chcp 65001 >nul
cd /d "%~dp0"
if not exist backend\datos_locales mkdir backend\datos_locales
set LOG=%~dp0backend\datos_locales\actualizacion_git.log
echo [%date% %time%] Actualizando repositorio > "%LOG%"
git stash push -m "cambios locales antes de actualizar (respaldo automatico)" >> "%LOG%" 2>&1
git fetch --prune origin >> "%LOG%" 2>&1
git checkout -B main origin/main >> "%LOG%" 2>&1
if errorlevel 1 (
    echo No se pudo actualizar a la rama main. Revise "%LOG%"
    pause
    exit /b 1
)
git log -1 --format="%%h %%s" >> "%LOG%" 2>&1
echo Repositorio actualizado. Iniciando la reconstruccion ...
call scripts\reconstruir_sistema.bat %*

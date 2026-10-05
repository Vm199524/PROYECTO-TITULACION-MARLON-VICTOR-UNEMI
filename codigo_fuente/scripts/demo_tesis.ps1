<#
.SYNOPSIS
Reconstruye y valida de punta a punta el prototipo VicMar Data AI ("Desarrollo de un
modelo predictivo de abandono estudiantil mediante inteligencia de negocios y
procesamiento de lenguaje natural").

.DESCRIPTION
Ejecuta el pipeline reproducible en orden; si un paso falla, el script se detiene:
  1. SQL Server (Docker)            6. ETL de las dos instituciones (mismo código, dos perfiles)
  2. Anonimización (idempotente)    7. Entrenar, calificar, segmentar y reportar (x2)
  3. Datos UNEMI_PRUEBAS            8. Referentes externos (benchmarking)
  4. Datos OULAD (OULAD_PRUEBAS)    9. Diccionario de datos
  5. Esquema del almacén CHAT      10. Pruebas automatizadas (pytest)
Usa el entorno virtual codigo_fuente\backend\venv y ejecuta cada paso desde la carpeta backend.
Al terminar informa la duración total en minutos.

.PARAMETER ConEvaluacionNL2SQL
Agrega el paso 11: evaluación del motor NL2SQL (eval.evaluar_nl2sql) con el conjunto de
referencia de 40 preguntas y 8 maliciosas. Consume cuota de los proveedores de IA.

.PARAMETER Levantar
Tras el pipeline, abre dos ventanas de PowerShell con el backend (puerto 8090) y el frontend
(Vite, puerto 3000) para la demostración en vivo, e imprime el guion de la demostración.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File codigo_fuente\scripts\demo_tesis.ps1 [-ConEvaluacionNL2SQL] [-Levantar]
Se ejecuta desde la raíz del repositorio.

.NOTES
Credenciales: todas se leen de codigo_fuente\backend\.env (DB_PASSWORD, CHAT_READER_PASSWORD);
este script no contiene ni pide contraseñas.
Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
#>
param(
    [switch]$ConEvaluacionNL2SQL,
    [switch]$Levantar
)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz 'backend'
$py = Join-Path $backend 'venv\Scripts\python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$inicio = Get-Date

# Ejecuta un paso del pipeline mostrando su título y lanza una excepción si el
# comando nativo termina con un código de salida distinto de 0.
function Paso([string]$titulo, [scriptblock]$accion) {
    Write-Host ''
    Write-Host "== $titulo" -ForegroundColor Cyan
    & $accion
    if ($LASTEXITCODE -ne 0) { throw "Falló el paso: $titulo (código $LASTEXITCODE)" }
}

if (-not (Test-Path $py)) { throw "No existe $py. Crea el entorno: py -3.14 -m venv backend\venv; backend\venv\Scripts\pip install -r backend\requirements.txt" }

Push-Location $backend
try {
    Paso '1. SQL Server en Docker' { docker start vicmar-sqlserver | Out-Null }
    # Reintenta la conexión como administrador hasta 40 veces, cada 3 s.
    Paso '   Esperando a que SQL Server acepte conexiones' {
        & $py -c "import time,sys; from conexion_admin import conectar_admin
for i in range(40):
    try: conectar_admin('master', timeout=5).close(); sys.exit(0)
    except Exception: time.sleep(3)
sys.exit(1)"
    }
    Paso '2. Anonimización del dataset de prueba (no hace nada si ya está anonimizado)' {
        & $py (Join-Path $raiz 'base_de_datos\datos_de_prueba\anonimizar_padron.py')
    }
    Paso '3a. UNEMI_PRUEBAS: alumnos'             { & $py scripts\seed_alumnos_prueba.py }
    Paso '3b. UNEMI_PRUEBAS: historial'           { & $py scripts\seed_historial_academico.py }
    Paso '4. OULAD_PRUEBAS (bloques de 28 días)'  { & $py -W ignore scripts\seed_oulad.py }
    Paso '5. Almacén CHAT, vistas y chat_reader'  { & $py scripts\run_sql_file.py ..\base_de_datos\crear_chat_academico.sql }
    Paso '6a. ETL perfil UNEMI_PRUEBAS'           { & $py scripts\etl_academico.py --perfil UNEMI_PRUEBAS }
    Paso '6b. ETL perfil OULAD_UK'                { & $py scripts\etl_academico.py --perfil OULAD_UK }
    # Un modelo por institución: nunca se mezclan los datos de ambas.
    foreach ($empresa in 'UNEMI_PRUEBAS', 'OULAD_UK') {
        Paso "7. Entrenar ($empresa)"   { & $py -W ignore -m ml.entrenar_abandono --empresa $empresa }
        Paso "7. Calificar ($empresa)"  { & $py -W ignore -m ml.predecir_abandono --empresa $empresa }
        Paso "7. Segmentar ($empresa)"  { & $py -W ignore -m ml.clustering_institucional --empresa $empresa }
        Paso "7. Figuras y evaluación prospectiva ($empresa)" { & $py -W ignore -m ml.reporte_validacion --empresa $empresa }
    }
    Paso '8. Referentes externos con DOI'         { & $py -m etl.etl_benchmarking }
    Paso '9. Diccionario de datos'                { & $py scripts\generar_diccionario_datos.py }
    Paso '10. Pruebas automatizadas'              { & $py -m pytest -q -p no:cacheprovider tests\test_capa_seguridad_bd.py tests\test_privacidad.py tests\test_panel_abandono.py tests\test_metric_catalog.py }
    if ($ConEvaluacionNL2SQL) {
        Paso '11. Evaluación NL2SQL (conjunto de referencia)' { & $py -W ignore -m eval.evaluar_nl2sql }
    }
}
finally {
    Pop-Location
}

$minutos = [math]::Round(((Get-Date) - $inicio).TotalMinutes, 1)
Write-Host ''
Write-Host "Pipeline completo en $minutos min." -ForegroundColor Green

if ($Levantar) {
    $frontend = Join-Path $raiz 'frontend'
    Write-Host 'Levantando backend (puerto 8090) y frontend (Vite, puerto 3000)...' -ForegroundColor Cyan
    Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$frontend'; npm run dev:backend"
    Start-Process powershell -ArgumentList '-NoExit', '-Command', "Set-Location '$frontend'; npm run dev"
    Write-Host 'Guion de demostración: ingresar con el usuario académico -> conectar UNEMI_PRUEBAS -> riesgo con factores'
    Write-Host 'y confiabilidad -> segmentos y referentes -> 3 preguntas en el chat -> 1 pregunta maliciosa -> cambiar a OULAD_UK.'
}

<#
.SYNOPSIS
Reconstruye y valida de punta a punta el prototipo VicMar: "Prototipo de un
sistema web para predecir el abandono en estudiantes universitarios mediante
aprendizaje automático y consulta conversacional".

.DESCRIPTION
1. Inicia SQL Server (contenedor Docker vicmar-sqlserver).
2. Ejecuta el orquestador de procesos por lotes (backend\scripts\pipeline.py):
   entorno -> conexión -> bases operativas UNEMI y OULAD -> almacén estrella ->
   ETL -> referentes -> entrenamiento y validación -> calificación -> segmentación ->
   figuras y evaluación prospectiva -> diccionario de datos -> cuentas demo -> pytest.
3. Con -Levantar, abre la API (puerto 8090) y la aplicación web (puerto 3000).
Si un paso falla, el orquestador se detiene e indica cómo retomarlo.

.PARAMETER ConConsulta
Agrega la evaluación de la consulta conversacional con el conjunto dorado
(40 preguntas, 12 de robustez y 8 adversariales). Usa los proveedores de IA del .env.

.PARAMETER Rapido
Menos combinaciones de hiperparámetros (útil para una demostración rápida).

.PARAMETER Levantar
Tras el pipeline, abre la API y la aplicación web e imprime el guion de la demostración.

.EXAMPLE
powershell -ExecutionPolicy Bypass -File scripts\demo_tesis.ps1 -ConConsulta -Levantar

.NOTES
Las credenciales se leen de backend\.env; este script no contiene ni pide contraseñas.
Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
#>
param(
    [switch]$ConConsulta,
    [switch]$Rapido,
    [switch]$Levantar
)
$ErrorActionPreference = 'Stop'
$raiz = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $raiz 'backend'
$py = Join-Path $backend 'venv\Scripts\python.exe'
$env:PYTHONIOENCODING = 'utf-8'
$env:PYTHONUTF8 = '1'

if (-not (Test-Path $py)) {
    throw "No existe $py. Cree el entorno: py -3.14 -m venv backend\venv; backend\venv\Scripts\pip install -r backend\requirements.txt"
}
if (Get-Command docker -ErrorAction SilentlyContinue) { docker start vicmar-sqlserver | Out-Null }

$argumentos = @('-m', 'scripts.pipeline')
if ($ConConsulta) { $argumentos += '--con-consulta' }
if ($Rapido) { $argumentos += '--rapido' }

Push-Location $backend
try {
    & $py @argumentos
    if ($LASTEXITCODE -ne 0) { throw "El pipeline se detuvo (código $LASTEXITCODE). Revise backend\datos_locales\pipeline_*.log" }
}
finally {
    Pop-Location
}

if ($Levantar) {
    Start-Process cmd -ArgumentList '/c', (Join-Path $PSScriptRoot 'levantar_sistema.bat')
    Write-Host ''
    Write-Host 'Guion de demostración (10 minutos):' -ForegroundColor Cyan
    Write-Host ' 1. Ingresar como autoridad.demo: panel ejecutivo, confiabilidad del modelo y alertas.'
    Write-Host ' 2. Estudiantes en riesgo: filtrar por carrera y abrir una ficha (factores y recomendaciones).'
    Write-Host ' 3. Ingresar como bienestar.demo: simulador "¿qué pasaría si?" y registro de seguimiento.'
    Write-Host ' 4. Consulta conversacional: tres preguntas, una con carrera y una maliciosa (barrera).'
    Write-Host ' 5. Calidad del modelo: validación cruzada, temporal, calibración y equidad.'
    Write-Host ' 6. Cambiar a OULAD_UK (datos reales) y descargar el reporte ejecutivo en PDF.'
    Write-Host ' 7. Ingresar como admin.ti: cuentas, auditoría y estado de los procesos.'
}

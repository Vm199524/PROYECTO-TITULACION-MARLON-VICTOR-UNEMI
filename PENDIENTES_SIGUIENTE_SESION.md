# Pendientes para la siguiente sesión (7 de octubre de 2026)

Estado general: Avance 2 generado (85 páginas, sin errores en `_verificar_coherencia.py`), prototipo versión 3 con
153 pruebas del backend y 11 de la interfaz en verde, README en español e inglés con el isotipo, la apertura y el
recorrido animados y las capturas nuevas, manuales en Markdown y Word actualizados. El detalle está en
[`documentacion/PLAN_Y_ESTADO_DEL_PROYECTO.md`](documentacion/PLAN_Y_ESTADO_DEL_PROYECTO.md).

## En el equipo con SQL Server (Windows)

1. La copia local ya está en la rama `main`, igual que GitHub. Para traer cambios futuros: `git pull`.
2. La exactitud de la consulta con IA ya se midió en SQL Server (7 de octubre de 2026) y el Avance 2 la incluye.
   Para repetirla: `scripts\reconstruir_sistema.bat --solo consulta --con-consulta`.
3. Si se cambia el contenido, regenerar el Avance 2:
   ```bat
   cd documentacion\generador_documentos
   python construir_avance2.py --base ..\avances\AVANCE1_MARLON_VICTOR.docx --salida ..\avances\AVANCE2_MARLON_VICTOR.docx
   powershell -ExecutionPolicy Bypass -File _docx_a_pdf.ps1 -Docx ..\avances\AVANCE2_MARLON_VICTOR.docx
   python _verificar_coherencia.py
   ```
4. Exportar el PDF de los tres manuales con `_docx_a_pdf.ps1`.

## Lo que solo pueden hacer los autores

- Enlaces de los videos en el Anexo C del Avance 2.
- Completar en la tabla de la Declaración de autoría las fechas y los enlaces marcados «[completar]» (las filas ya están redactadas).
- Porcentaje real de Compilatio.
- Borrar en GitHub las ramas antiguas `AAA`, `MARLON`, `fix/dev-backend-windows` y `v3-sistema-academico` (desde la web: Branches → icono de papelera); `main` ya tiene la versión vigente.
- Cambiar las credenciales de `sa`, `chat_reader`, `app_seguimiento` y las claves de IA antes de usar datos reales.

## Para el Avance 3

- Prueba de usabilidad con 3 a 5 usuarios (protocolo en la sección 3.1.8 y en la guía de pruebas de aceptación).
- Video de la demostración completa.

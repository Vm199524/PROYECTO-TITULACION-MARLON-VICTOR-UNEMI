# Pendientes para la siguiente sesión (04/10/2026)

## Por terminar del plan actual
1. **PDF de los manuales:** ya están en Markdown y en Word en `documentacion/manuales/`. Falta exportar el PDF de cada uno:
   `powershell -File documentacion\generador_documentos\_docx_a_pdf.ps1 -Docx documentacion\manuales\<MANUAL>.docx`
   y revisar páginas de muestra.
2. **README.en.md:** agregarle el mismo pie (autores con foto y banda) y las capturas.
3. **Enlaces viejos:** `documentacion/README.md` (línea 81) y `codigo_fuente/backend/scripts/seed_alumnos_prueba.py` (línea 17) todavía apuntan a `tecnica/MANUAL_INSTALACION.md`, que ahora es `manuales/MANUAL_TECNICO_DE_INSTALACION.md`. También falta agregar la sección «Manuales» en `documentacion/README.md` y en `codigo_fuente/README.md`.
4. **Generador del Avance 2:** comprobar que `_build_avance2.py` siga encontrando los fragmentos de código que copia en la tesis, porque los comentarios de esos archivos cambiaron. Hay que probarlo generando en una copia, sin sobrescribir el Avance 2 entregado.
5. **CI:** confirmar que la ejecución del último envío (commit `51ba59d`) quedó en verde.
6. **Plan del proyecto:** actualizar `documentacion/PLAN_Y_ESTADO_DEL_PROYECTO.md`: P1 (capturas) resuelto y manuales hechos.

## Errores de código encontrados al documentar (no corregidos; decidir)
- `core/nl2sql_engine.py` → `generate_correction` usa `ChatPromptTemplate` y `StrOutputParser` sin importarlos. La autocorrección de SQL nunca funciona.
- `config.py` (cerca de la línea 233) usa `logger` sin definirlo: si falla la carga de `demo_dataset.json`, se produce un NameError.
- `core/sql_sanitizer.py` → `strip_ghost_filters` puede dejar un `AND` sin `WHERE`.
- `core/mirror_manager.py`: el conteo de niveles todavía filtra por `RTRIM(PERIODO)` y podría devolver 0.

## Decisiones de los autores
- **Imagen `documentacion/presentaciones/Predicción_de_abandono_estudiantil.png`:** tiene la marca de agua «Gemini Notebook» y la cifra del 26 % de la SENESCYT sin fuente académica. ¿Se mueve a revisión?
- **Cédula de Marlon** en la portada de los avances publicados.
- **Descripción y temas del repositorio:** los cambia Víctor; ya tiene el comando.
- **Ramas `AAA` y `MARLON` en GitHub:** guardan el historial viejo, con firma de IA. Se borran solo si Víctor está de acuerdo.
- **Credenciales:** cambiar las de `sa`, `chat_reader`, las claves de IA y la de `adminvm` (su contraseña estuvo escrita en un script publicado).
- **Textos visibles antiguos en la interfaz:** «VICMAR DATA AI V4.5/V4.1», «Soy Aura», «Quantum BI».

## Del plan general
- Video de la demostración.
- Prueba con 3 a 5 usuarios (guía en `documentacion/manuales/GUIA_DE_PRUEBAS_DE_ACEPTACION.md`, sección 4).
- Avance 3.

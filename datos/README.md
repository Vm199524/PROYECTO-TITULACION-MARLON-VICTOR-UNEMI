# Datos externos

Esta carpeta guarda datasets públicos que **no se versionan** por su tamaño.

## OULAD — Open University Learning Analytics Dataset
- **Uso en el proyecto:** segunda institución real (`OULAD_UK`) para contrastar el modelo entrenado con datos sintéticos.
- **Fuente:** Kuzilek, J., Hlosta, M., & Zdrahal, Z. (2017). Open University Learning Analytics dataset. *Scientific Data, 4*, 170171. https://doi.org/10.1038/sdata.2017.171
- **Licencia:** CC BY 4.0.
- **Descarga:** UCI Machine Learning Repository, https://archive.ics.uci.edu/dataset/349/open+university+learning+analytics+dataset (archivo `.zip` de 44,6 MB; consultado el 03/10/2026).
- **Ubicación esperada:** descomprimir los CSV en `datos/externos/oulad/`:
  `assessments.csv`, `courses.csv`, `studentAssessment.csv`, `studentInfo.csv`, `studentRegistration.csv`, `studentVle.csv`, `vle.csv`.
- **Carga:** `backend/scripts/cargar_oulad.py`, que ejecuta el paso `oulad` de `scripts/reconstruir_sistema.bat`. Sin estos archivos, use `reconstruir_sistema.bat --sin-oulad`.

## Datos de prueba de UNEMI
Son sintéticos y anonimizados, y sí se versionan: `base_de_datos/datos_de_prueba/`.

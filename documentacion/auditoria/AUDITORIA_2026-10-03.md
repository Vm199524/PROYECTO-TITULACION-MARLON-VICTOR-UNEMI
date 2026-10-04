# Auditoría del proyecto — 3 de octubre de 2026

**Proyecto:** VicMar Data AI. Modelo predictivo de abandono estudiantil con inteligencia de negocios y procesamiento de lenguaje natural.
**Autores:** Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco (UNEMI).
**Alcance:** todo el contenido de la carpeta del proyecto y del repositorio remoto. Se revisaron:
- el inventario y los tamaños;
- el código vigente y el que ya no se usa;
- los secretos (sin reproducir sus valores);
- el estado de git y GitHub;
- la coherencia entre el documento y el código.

---

## 1. Hallazgos antes de la reorganización

| Área | Hallazgo | Riesgo |
|---|---|---|
| Estructura | La raíz mezclaba tres épocas: un prototipo en Node/Express, el backend en Python y una carpeta del Avance 1 con documentos, código, datasets, videos y artículos. | No se sabía qué código estaba vigente; el sistema no se podía reproducir |
| Tamaño | La carpeta del Avance 1 ocupaba unos 3,1 GB e incluía videos de hasta 1,4 GB, el dataset OULAD (433 MB), unos 70 PDF de artículos y material de otro grupo. | No se puede publicar; hay material con derechos de terceros |
| Código heredado | Documentación, datos, scripts `.bat`, componentes de interfaz y flujos de despliegue en la nube de un producto ERP anterior, sin relación con el modelo predictivo. | Confusión y superficie de ataque innecesaria |
| Scripts peligrosos | Scripts de git que hacían `reset`, `add -A` y `push` a `main` sin revisión, y otro que reescribía el historial. | Pérdida de commits o publicación de secretos |
| Secretos | Las contraseñas de `sa` y de `chat_reader` y una clave de proveedor de IA aparecían en texto plano en archivos locales. Una rama local sin publicar contenía la contraseña de la base de datos en 10 archivos. | Exposición de credenciales |
| Funciones sin uso | Una función de redacción con un proveedor de IA de pago (sin clave configurada, inactiva) seguía cableada en el backend, el frontend y las pruebas. | Código muerto que la documentación no describía |
| Metadatos | Algunos documentos de Office tenían como autor a personas ajenas al equipo. | Autoría incorrecta |
| Historial remoto | El repositorio remoto tiene 9 commits del prototipo anterior; dos incluyen líneas de coautoría y enlaces ajenos a los autores. | Autoría incorrecta en el historial |

## 2. Acciones realizadas

1. **Respaldo previo:** se hizo un *bundle* de git con todas las ramas locales y remotas, más una copia de las carpetas de trabajo, fuera del proyecto.
2. **Código sin uso:** se movió a `_POR_REVISAR_ELIMINAR/` sin borrar nada. Cada elemento conserva su ruta original y está registrado en `INDICE.md` con el motivo y la evidencia. Esa carpeta no se publica.
3. **Reestructuración por capas:** `codigo_fuente/`, `documentacion/` y `datos/` (ver `documentacion/decisiones/ADR-000-estructura-del-repositorio.md`). Se actualizaron todas las rutas de los scripts, del generador del documento, de las pruebas y del pipeline.
4. **Función de redacción inactiva:** se retiró del backend, del frontend y de las pruebas. Los comentarios del código se redactaron en tono técnico neutro.
5. **Credenciales:**
   - las contraseñas de los usuarios de prueba se leen de un archivo local no versionado (`usuarios_prueba.local.json`) y hay una plantilla `usuarios_prueba.example.json`;
   - `.env`, `security_config.json` y los manuales con contraseñas quedan fuera del repositorio.
6. **Metadatos:** los documentos propios tienen como autores a Marlon Pérez y Víctor Lluilema. Los generadores fijan la autoría al guardar.
7. **Decisiones documentadas:**
   - tres opciones por decisión tecnológica y tres estilos de arquitectura, con matriz ponderada, sensibilidad y ADR (`documentacion/decisiones/`);
   - la arquitectura se verificó sobre el código: 2 desplegables, sin dependencias prohibidas entre capas y una excepción justificada.

## 3. Estado verificado al cierre

| Control | Resultado |
|---|---|
| Conjunto publicable | 280 archivos, 83,0 MB; el más grande pesa 15,8 MB (modelo entrenado de OULAD) |
| Secretos en lo publicable | 0 |
| Datos personales | Datos de prueba sintéticos y anonimizados; el padrón original no forma parte del proyecto |
| Material de terceros | PDF de artículos, exportaciones crudas de Scopus, videos y datasets externos fuera del repositorio |
| Documento del Avance 2 | Se regenera desde el código; el verificador de coherencia termina «sin errores» (70 páginas) |
| Arquitectura | `verificar_reglas.py`: «El código cumple la arquitectura declarada» |

## 4. Código heredado que sigue conectado (pendiente de decisión de los autores)

Estas piezas no forman parte del modelo predictivo, pero el backend o el frontend todavía las importan. Desconectarlas requiere probar el sistema completo, por eso no se movieron:
- síntesis de voz con un proveedor externo;
- endpoints del panel ERP anterior (tarjetas «Bento»);
- `/query/vision`;
- una llamada a `/user/pinned-metrics` que no tiene ruta en el backend;
- la importación de `AnalysisAreas` en el frontend;
- entradas del ERP en `knowledge/*.json`;
- `data/db_insights.json`. Este último se conserva porque forma parte del contexto con el que se evaluó el NL2SQL.

## 5. Riesgos y acciones recomendadas

| Riesgo | Acción | Responsable |
|---|---|---|
| Credenciales que estuvieron en texto plano | Cambiar la contraseña de `sa`, la de `chat_reader` y la clave del proveedor de IA | Autores |
| Borrar algo que sí se usa | Revisar `_POR_REVISAR_ELIMINAR/INDICE.md` fila por fila antes de borrar | Autores |
| Herramientas que cambian de rama con cambios sin confirmar | Antes de usar un cliente gráfico de git, confirmar o guardar los cambios; no dejar cambios pendientes al cambiar de rama | Autores |
| Datos sintéticos en la institución piloto | Mantener explícito en el documento que el desempeño real se mide en OULAD | Autores |

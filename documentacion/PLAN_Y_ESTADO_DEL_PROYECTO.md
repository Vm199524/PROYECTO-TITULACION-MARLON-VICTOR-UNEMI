# Plan y estado del proyecto

**Proyecto:** VicMar Data AI — Desarrollo de un modelo predictivo de abandono estudiantil mediante inteligencia de negocios y procesamiento de lenguaje natural.
**Autores:** Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · UNEMI · **Actualizado:** 3 de octubre de 2026

---

## 1. Dónde estamos

- **Avance 1:** entregado.
  - La observación sobre la numeración de Referencias y Anexos está corregida.
  - La tabla comparativa de trabajos previos ya está incorporada en la copia del Avance 2.
- **Avance 2:** generado desde el código (`documentacion/avances/Avance_2_VicMar_Data_AI.docx` y `.pdf`, 70 páginas). El verificador de coherencia termina «sin errores»:
  - citas ↔ referencias;
  - cifras ↔ resultados del sistema;
  - páginas mínimas;
  - numeración.
- **Prototipo funcionando de extremo a extremo** con dos instituciones (UNEMI_PRUEBAS, sintética, y OULAD_UK, real):
  - modelo predictivo con validación cruzada agrupada, prueba temporal y prospectiva;
  - segmentación validada;
  - NL2SQL evaluado con 40 preguntas y 8 maliciosas;
  - panel;
  - aislamiento por institución en el motor.
- **Repositorio:** reorganizado por capas, sin secretos y sin material de terceros (ver `auditoria/AUDITORIA_2026-10-03.md`).

## 2. Lo que exigen las tutoras y su estado

| # | Exigencia | Dónde está | Estado |
|---|---|---|---|
| 1 | Corregir la numeración de Referencias (2.) y Anexos (6.) | Títulos sin numeración; control automático en `_verificar_coherencia.py` | ✅ Atendida |
| 2 | Tabla comparativa explícita de los ≥10 estudios previos frente al caso | Sección 1.3: dos tablas con los 13 estudios y la fila «Presente trabajo» (`literatura/trabajos_previos.json`) | ✅ Atendida. 11 leídos en texto completo; 2 desde su resumen verificado (ver pendiente P6) |
| 3 | Derivar RF y RNF de las cuatro piezas (modelo, clustering, NL2SQL, dashboard) | 2.1: RF-01 a RF-16 por pieza y RNF-01 a RNF-11 | ✅ Atendida |
| 4 | Historias de usuario para la autoridad académica sin perfil técnico | 2.1: HU-01 a HU-10 con criterios de aceptación | ✅ Atendida |
| 5 | Requisitos de protección de datos estudiantiles | 2.1: RNF-02 a RNF-05 (LOPDP), con pruebas | ✅ Atendida |
| 6 | Métricas de calidad: AUC, recall, exactitud de las consultas NL2SQL | 2.1: tabla de meta y resultado por pieza | ✅ Atendida |
| 7 | Documentar cada fase de CRISP-DM | 3.1: seis fases con entregables, iteraciones y control de calidad | ✅ Atendida |
| 8 | Esquema estrella con diccionario de datos | 3.2: modelo dimensional y diccionario generado del esquema real | ✅ Atendida |
| 9 | UML: secuencia de la consulta en lenguaje natural y actividades del ETL | 3.2: siete diagramas | ✅ Atendida |
| 10 | Código del modelo y del backend con resultados reales de validación cruzada y temporal | 3.3: fragmentos extraídos del código y tablas de resultados | ✅ Atendida |
| 11 | Demo funcionando | El recorrido está descrito y se reproduce con `demo_tesis.ps1`; faltan las capturas en el documento y el video | ⏳ Pendiente (P1, P2) |
| 12 | Comparar al menos 3 tecnologías por decisión y 3 estilos de arquitectura, con literatura | 3.2 y 3.3: DT-01 a DT-06 con matriz ponderada, sensibilidad y ADR (`decisiones/`); arquitectura verificada en el código | ✅ Atendida |

## 3. Decisiones tomadas (resumen)

| Decisión | Opciones comparadas | Elegida | Nota |
|---|---|---|---|
| DT-01 Lenguaje del backend | Python, Java, Node.js | Python 3.14 | Única con validación agrupada y SHAP nativos |
| DT-02 Framework del backend | FastAPI, Django, Flask | FastAPI | Asíncrono, OpenAPI automática, sin ORM impuesto |
| DT-03 Frontend | React, Angular, Vue | React 18 | Migrar a React 19 queda como mejora |
| DT-04 Almacén | SQL Server, PostgreSQL, MySQL | SQL Server 2022 | PostgreSQL empata en aislamiento y gana en licencia: **para producción conviene evaluarlo** |
| DT-05 Algoritmo | Random Forest, gradient boosting, regresión logística | Random Forest | Empata con gradient boosting en datos reales; gana en clase minoritaria y SHAP |
| DT-06 Arquitectura | Monolito en capas, cliente-servidor desacoplado, microservicios | Cliente-servidor desacoplado con backend en capas | Verificada en el código |
| ADR-000 Estructura del repositorio | Repositorio único por capas, varios repositorios, estructura plana | Repositorio único por capas | Respaldada con 3 artículos y 3 repositorios de referencia |

## 4. Pendientes, en orden

| # | Pendiente | Cómo hacerlo | Quién |
|---|---|---|---|
| P1 | **Capturas de la demo** en el documento | Levantar el sistema (`demo_tesis.ps1 -Levantar`), iniciar sesión con el usuario ACADÉMICO y guardar las capturas como `documentacion/figuras/demo_<nombre>.png`. El generador las inserta solas en 3.3. Después: `_build_avance2.py` → `_docx_a_pdf.ps1` → `_verificar_coherencia.py` | Autores |
| P2 | **Video de la demo** | Grabar el recorrido de la sección 3.3 (unos 5 minutos) y poner el enlace en el Anexo | Autores |
| P3 | **Prueba con 3 a 5 usuarios** sin perfil técnico | Protocolo de 2.1: seis tareas de HU-01 a HU-07; registrar éxito, tiempo y dificultad | Autores |
| P4 | Revisar frases de 1.3 que la lectura completa matizó | Ver la sección 5 de este documento | Autores |
| P5 | Ajustes menores en Referencias | *Scientific Reports* va sin número de fascículo (Ovtsarenko: «16, Article 14616»); Rabelo y Zárate: «8, 72–85»; «PLoS ONE» → «PLOS ONE» | Autores |
| P6 | Texto completo de Mustofa et al. (2025) y Lepori y Bornmann (2026) | Descargarlos con el acceso de la biblioteca de la UNEMI (el sitio del editor exige verificación humana) y confirmar sus filas en `trabajos_previos.json` | Autores |
| P7 | Cambiar credenciales | Contraseña de `sa`, de `chat_reader` y la clave del proveedor de IA | Autores |
| P8 | Revisar la carpeta `_POR_REVISAR_ELIMINAR/` | Fila por fila en `INDICE.md`; borrar solo lo confirmado | Autores |
| P9 | Código heredado aún conectado | Decidir si se desconecta (lista en la auditoría, sección 4) y probar | Autores |
| P10 | Completar el Anexo | Tabla de actividades con fechas e interacciones con las tutoras | Autores |
| P11 | Avance 3 | Conclusiones y recomendaciones respondiendo a cada objetivo, con los resultados de P1–P3 | Autores |

## 5. Matices de la lectura completa para la sección 1.3 (P4)

La tabla comparativa ya refleja estos puntos. Conviene ajustar la prosa del Avance 1 para que no los contradiga:

- **Kok et al. (2024):** la exactitud cercana al 100 % es de 1,000 en todas las configuraciones, con 197 estudiantes, y el artículo reconoce que puede no sostenerse en la práctica (p. 21). Sus conclusiones atribuyen el modelo a una regresión logística con 85 % (p. 23). Citarlo como contraste, no como aval de desempeño.
- **Mohd Talib et al. (2023):** estudian el rendimiento (SGPA), no el abandono. Sus tres clústeres no difieren significativamente (p = 0,454; p. 10). Conviene escribir «aplicaron K-Means…» en lugar de «validaron K-Means», y presentar como aporte del presente trabajo la validación múltiple de la segmentación.
- **Sequeira et al. (2024):** es una revisión sistemática de 10 estudios. Concluye que no existe una hoja de ruta para BI en universidades y que solo 4 implementan BI (pp. 15–16). Verificar la frase «brecha de habilidades técnicas como principal barrera»: la revisión enumera varios factores de adopción (cultura, apoyo directivo, infraestructura, calidad y gobierno de los datos, formación de usuarios).
- **Rabelo y Zárate (2025):** la mejor técnica individual fue la regresión logística, y el ensemble apenas la mejora; Random Forest rinde igual que el ensemble (p. 82). Matizar la frase «los modelos de ensamble ofrecen el mejor balance».
- **Ovtsarenko (2026):** la unidad de análisis son 49 recursos del curso, no los estudiantes.
- **Khatun et al. (2025):** clasifica la no asistencia del mismo año con datos transversales, no la del periodo siguiente.

## 6. Cómo continuar el trabajo

```powershell
# Sistema completo (bases, ETL, modelos, pruebas) y levantar backend + frontend
powershell -ExecutionPolicy Bypass -File codigo_fuente\scripts\demo_tesis.ps1 -Levantar

# Documento del Avance 2
cd documentacion\generador_documentos
python _build_avance2.py
powershell -ExecutionPolicy Bypass -File _docx_a_pdf.ps1 -Docx ..\avances\Avance_2_VicMar_Data_AI.docx
python _verificar_coherencia.py
```

- **Tabla de trabajos previos:** se edita en `documentacion/literatura/trabajos_previos.json` y el documento la toma al regenerarse.
- **Decisiones tecnológicas:** se editan en `documentacion/decisiones/DT-*.json`; sus ADR están en `decisiones/adr/`.

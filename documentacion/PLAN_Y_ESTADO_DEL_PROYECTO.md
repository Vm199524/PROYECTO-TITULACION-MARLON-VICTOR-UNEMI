# Plan y estado del proyecto

**Proyecto:** Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante aprendizaje
automático y consulta conversacional (VicMar, versión 3).
**Autores:** Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · UNEMI · **Actualizado:** 7 de octubre de 2026

---

## 1. Dónde estamos

- **Avance 1:** entregado.
- **Avance 2:** generado desde los resultados reales del sistema con `generador_documentos/construir_avance2.py`
  (`avances/AVANCE2_MARLON_VICTOR.docx` y `.pdf`, 85 páginas, 34 figuras y 35 tablas). `_verificar_coherencia.py`
  termina sin errores: citas y referencias, cifras frente a `metricas.json`, resumen de 200 a 250 palabras, páginas
  mínimas por apartado y numeración de los capítulos finales.
- **Prototipo versión 3:** enfoque académico de punta a punta, con dos instituciones (UNEMI_PRUEBAS, sintética, y
  OULAD_UK, real anonimizada), tres roles, 27 servicios REST, consulta conversacional gobernada, seguimiento de
  bienestar, reportes y auditoría. 153 pruebas del backend y 11 de la interfaz en verde.
- **Repositorio:** README en español e inglés con el isotipo de VicMar y capturas de la versión 3; manuales, notas
  técnicas y decisiones actualizadas; sin restos del enfoque anterior.

## 2. Observaciones de la tutoría del Avance 1 y su estado

| # | Observación | Dónde se atendió | Estado |
|---|---|---|---|
| 1 | Numeración de Referencias y Anexos | Capítulos 4 a 7 con la numeración del formato oficial; control en `_verificar_coherencia.py` | ✅ |
| 2 | Tabla comparativa de al menos 10 estudios | Sección 1.3.6, 14 trabajos frente al caso | ✅ |
| 3 | RF y RNF derivados de las cuatro piezas | 2.1.5 y 2.1.6, agrupados en modelo, segmentación, consulta y panel | ✅ |
| 4 | Historias de usuario para la autoridad sin perfil técnico | 2.1.4, HU-01 a HU-10 con criterios de aceptación | ✅ |
| 5 | Protección de datos estudiantiles | 2.1.7, requisitos LOPDP y su control en el sistema | ✅ |
| 6 | Métricas de calidad (AUC, recall, exactitud NL2SQL) | 2.1.8 y 3.1.6 | ✅ (consulta medida en SQL Server: 100 % por ejecución, 65 % estricta) |
| 7 | Cada fase CRISP-DM documentada | 3.1.2 a 3.1.7 | ✅ |
| 8 | Esquema estrella con diccionario de datos | 3.2.5 y `tecnica/DICCIONARIO_DE_DATOS.md` | ✅ |
| 9 | UML: secuencia de la consulta y actividades del ETL | 3.2.3, más colaboración, estados, casos de uso y flujo | ✅ |
| 10 | Código del modelo y del backend con resultados reales de validación | 3.1.5 a 3.1.7 | ✅ |
| 11 | Demo funcionando | 3.1.7 y Anexo C | ✅ (faltan los enlaces de video) |

## 3. Pendientes

| # | Pendiente | Responsable |
|---|---|---|
| P2 | Enlaces de los videos en el Anexo C | Autores |
| P3 | Completar fechas y enlaces marcados «[completar]» en la tabla de la declaración de autoría (las nueve actividades ya están redactadas) | Autores |
| P4 | Porcentaje real de Compilatio | Autores |
| P5 | Prueba de usabilidad con 3 a 5 usuarios (protocolo en 3.1.8 y en la guía de pruebas de aceptación) | Avance 3 |
| P6 | Cambiar las credenciales de `sa`, `chat_reader`, `app_seguimiento` y las claves de IA antes de usar datos reales | Autores |

## 4. Cómo regenerar el Avance 2

```bat
cd documentacion\generador_documentos
python construir_avance2.py --base <Avance 1 en Word, última versión de los autores> --salida ..\avances\AVANCE2_MARLON_VICTOR.docx
python docx_a_pdf.py ..\avances\AVANCE2_MARLON_VICTOR.docx ..\avances\AVANCE2_MARLON_VICTOR.pdf
python _verificar_coherencia.py
```

La base es el Word del Avance 1 con las correcciones de los autores (la del 7 de octubre de 2026); el generador
conserva su portada, certificados, preliminares, estilos y encabezados, y reemplaza el cuerpo.

Si `codigo_fuente/backend/eval/resultados/` no tiene una evaluación de la consulta con SQL Server, el generador usa la
réplica indicada en la variable `EVAL_CONSULTA` (por ejemplo `..\evidencias\consulta_replica_UNEMI_PRUEBAS.json`) y
lo declara en el texto.

En Windows, el PDF también puede exportarse con Word:
`powershell -ExecutionPolicy Bypass -File _docx_a_pdf.ps1 -Docx ..\avances\AVANCE2_MARLON_VICTOR.docx`.

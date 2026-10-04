# -*- coding: utf-8 -*-
"""
generar_diccionario_datos.py — diccionario de datos del almacén CHAT generado
desde el ESQUEMA REAL (INFORMATION_SCHEMA + claves primarias y foráneas del
catálogo de SQL Server), no escrito a mano: así el documento de titulación
no puede describir una columna que la base no tiene.

Las descripciones de negocio viven en DESCRIPCIONES (abajo); una columna
sin descripción aparece marcada para que se note y se complete.

Salida:
  - documentacion/tecnica/DICCIONARIO_DE_DATOS.md    (para el repositorio)
  - documentacion/tecnica/diccionario_datos.json     (lo lee _build_avance2.py)

Uso:
    cd backend
    python scripts/generar_diccionario_datos.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from conexion_admin import conectar_admin  # noqa: E402

RAIZ = Path(__file__).resolve().parents[3]   # raíz del repositorio
SALIDA_JSON = RAIZ / 'documentacion' / 'tecnica' / 'diccionario_datos.json'
SALIDA_MD = RAIZ / 'documentacion' / 'tecnica' / 'DICCIONARIO_DE_DATOS.md'

TABLAS = {
    'fact_matriculas': 'Hecho central. Grano: una fila por alumno y periodo académico (semestre en UNEMI, bloque de 28 días en OULAD).',
    'dim_alumno': 'Alumno, identificado por (institución, cédula).',
    'dim_tiempo': 'Calendario de las fechas de matrícula.',
    'dim_empresa': 'Institución (tenant) dueña de los datos.',
    'dim_facultad': 'Facultad o dominio académico.',
    'dim_carrera': 'Carrera o módulo, dentro de una facultad.',
    'dim_estado_matricula': 'Estado del alumno al cierre del periodo.',
    'dim_sede': 'Sede o campus.',
    'dim_canal': 'Modalidad de estudio.',
    'fact_prediccion_abandono': 'Resultado del modelo: una fila por alumno activo con su riesgo para el próximo periodo.',
    'fact_cluster_carrera': 'Resultado de K-Means: una fila por carrera con su segmento de riesgo.',
    'fact_evaluacion_modelo': 'Métricas de validación de los modelos (predicción, clustering, NL2SQL).',
    'dim_institucion_externa': 'Referente externo de benchmarking.',
    'fact_benchmark_externo': 'Indicador publicado de un referente externo, con su fuente.',
}

DESCRIPCIONES = {
    'fact_id': 'Identificador sustituto de la fila',
    'empresa_codigo': 'Institución dueña del dato (aislamiento por SESSION_CONTEXT)',
    'alumno_id': 'Alumno (clave sustituta)',
    'carrera_id': 'Carrera o módulo',
    'facultad_codigo': 'Código de la facultad o dominio',
    'estado_codigo': 'Estado al cierre del periodo (ACTIVO, RETIRADO, GRADUADO, EGRESADO, REPROBADO)',
    'tiempo_id': 'Fecha de matrícula del periodo',
    'sede_codigo': 'Sede o campus',
    'canal_codigo': 'Modalidad (PRESENCIAL, EN LINEA)',
    'semestre': 'Número de periodo dentro de la trayectoria',
    'promedio': 'Promedio de calificaciones del periodo (0-10)',
    'asistencia_pct': 'Asistencia del periodo (%); en OULAD, días con actividad en el aula virtual',
    'monto_matricula': 'Valor de la matrícula',
    'beca_porcentaje': 'Porcentaje de beca (0-100)',
    'saldo_pendiente': 'Saldo adeudado al cierre del periodo (mora)',
    'monto_neto': 'Matrícula menos beca (calculado en el ETL)',
    'es_ultimo_periodo': '1 = periodo más reciente de la trayectoria (estado vigente del alumno)',
    'cedula': 'Identificador del alumno (ficticio en los datos de prueba)',
    'apellidos': 'Apellidos (ficticios en los datos de prueba)',
    'nombres': 'Nombres (ficticios en los datos de prueba)',
    'genero': 'Género (M/F)',
    'ciudad_residencia': 'Ciudad o región de residencia',
    'fecha': 'Fecha calendario',
    'anio': 'Año', 'mes': 'Mes', 'trimestre': 'Trimestre',
    'business_name': 'Nombre comercial de la institución',
    'facultad_nombre': 'Nombre de la facultad', 'carrera': 'Nombre de la carrera o módulo',
    'sede_nombre': 'Nombre de la sede',
    'prediccion_id': 'Identificador de la predicción',
    'fact_id_base': 'Periodo (fila de fact_matriculas) con cuyos datos se calculó la predicción',
    'horizonte': 'Qué se predice: abandono en el PRÓXIMO periodo',
    'probabilidad': 'Probabilidad estimada de abandono (0-1)',
    'umbral_operativo': 'Umbral elegido para recall ≥ 0,80 en validación',
    'riesgo_categoria': 'ALTO (≥ umbral), MEDIO (≥ umbral/2), BAJO',
    'factor_1': 'Variable que más eleva el riesgo de ese alumno (SHAP)',
    'factor_2': 'Segunda variable que más eleva el riesgo (SHAP)',
    'factor_3': 'Tercera variable que más eleva el riesgo (SHAP)',
    'fecha_calculo': 'Momento del cálculo (UTC)',
    'modelo_version': 'Versión del modelo que produjo la fila',
    'cluster_id': 'Número de clúster devuelto por K-Means',
    'cluster_label': 'Segmento: Atención prioritaria / Estable / Bajo riesgo',
    'matricula_total': 'Alumnos distintos de la carrera',
    'tasa_abandono_hist': 'Proporción histórica de trayectorias cerradas como RETIRADO',
    'promedio_hist': 'Promedio histórico de la carrera',
    'riesgo_promedio': 'Probabilidad media de abandono de los activos de la carrera',
    'evaluacion_id': 'Identificador de la métrica',
    'componente': 'PREDICCION, CLUSTERING o NL2SQL',
    'modelo': 'Modelo evaluado (ej. RF_SMOTE, KMEANS_K3)',
    'esquema_validacion': 'CV_GRUPOS_5, TEMPORAL, PROSPECTIVA, VALIDACION_INTERNA, CONJUNTO_DORADO',
    'metrica': 'Nombre de la métrica (ROC_AUC, RECALL, SILHOUETTE, ...)',
    'valor': 'Valor de la métrica o del indicador',
    'desviacion': 'Desviación estándar entre pliegues, si aplica',
    'es_modelo_final': '1 = métrica del modelo elegido',
    'institucion_codigo': 'Código del referente externo',
    'nombre': 'Nombre del referente', 'tipo': 'PUBLICA, PARTICULAR o REFERENCIA',
    'categoria_caces': 'Categoría de acreditación (si aplica)',
    'fecha_evaluacion_caces': 'Fecha de evaluación CACES (si aplica)',
    'indicador_codigo': 'Indicador (TASA_ABANDONO)', 'unidad': 'Unidad del valor',
    'definicion_indicador': 'Qué mide exactamente la cifra y dónde aparece en la fuente',
    'pais': 'País del referente', 'modalidad': 'PRESENCIAL, DISTANCIA, MIXTA o NO_REPORTADA',
    'nivel_comparabilidad': 'ALTA, MEDIA o BAJA frente a la institución propia',
    'fuente': 'Cita APA corta', 'doi': 'DOI de la fuente', 'url_fuente': 'Enlace a la fuente',
    'fecha_carga': 'Momento de la carga (UTC)',
}


def leer_esquema() -> dict:
    conn = conectar_admin('CHAT')
    cur = conn.cursor()
    cur.execute("""
        SELECT c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH,
               c.NUMERIC_PRECISION, c.NUMERIC_SCALE, c.IS_NULLABLE, c.ORDINAL_POSITION
        FROM INFORMATION_SCHEMA.COLUMNS c
        JOIN INFORMATION_SCHEMA.TABLES t ON t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_TYPE = 'BASE TABLE'
        ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
    """)
    columnas = cur.fetchall()
    cur.execute("""
        SELECT ku.TABLE_NAME, ku.COLUMN_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku ON ku.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
        WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
    """)
    pks = {(t, c) for t, c in cur.fetchall()}
    cur.execute("""
        SELECT OBJECT_NAME(fk.parent_object_id), COL_NAME(fc.parent_object_id, fc.parent_column_id),
               OBJECT_NAME(fk.referenced_object_id)
        FROM sys.foreign_keys fk JOIN sys.foreign_key_columns fc ON fc.constraint_object_id = fk.object_id
    """)
    fks = {(t, c): ref for t, c, ref in cur.fetchall()}
    cur.execute("SELECT name FROM sys.views WHERE name LIKE 'VIS[_]%' ORDER BY name")
    vistas = [r[0] for r in cur.fetchall()]
    conn.close()

    esquema = {}
    for tabla, col, tipo, largo, prec, esc, nulo, _ in columnas:
        if tabla not in TABLAS:
            continue
        if tipo in ('varchar', 'nvarchar', 'char'):
            tipo_txt = f"{tipo.upper()}({largo if largo != -1 else 'MAX'})"
        elif tipo == 'decimal':
            tipo_txt = f'DECIMAL({prec},{esc})'
        else:
            tipo_txt = tipo.upper()
        clave = 'PK' if (tabla, col) in pks else (f'FK → {fks[(tabla, col)]}' if (tabla, col) in fks else '')
        esquema.setdefault(tabla, {'descripcion': TABLAS[tabla], 'columnas': []})['columnas'].append({
            'columna': col, 'tipo': tipo_txt, 'clave': clave, 'nulo': nulo == 'YES',
            'descripcion': DESCRIPCIONES.get(col, '(sin descripción: completar)'),
        })
    return {'tablas': esquema, 'vistas': vistas}


def main() -> int:
    datos = leer_esquema()
    SALIDA_JSON.write_text(json.dumps(datos, indent=2, ensure_ascii=False), encoding='utf-8')
    lineas = ['# Diccionario de datos del almacén CHAT', '',
              'Generado desde el esquema real por `codigo_fuente/backend/scripts/generar_diccionario_datos.py`. No editar a mano.', '']
    for tabla in TABLAS:
        if tabla not in datos['tablas']:
            continue
        info = datos['tablas'][tabla]
        lineas += [f'## {tabla}', '', info['descripcion'], '', '| Columna | Tipo | Clave | Descripción |', '|---|---|---|---|']
        lineas += [f"| {c['columna']} | {c['tipo']} | {c['clave']} | {c['descripcion']} |" for c in info['columnas']]
        lineas.append('')
    lineas += ['## Vistas de presentación (lo único que ve chat_reader)', ''] + [f'- `{v}`' for v in datos['vistas']]
    SALIDA_MD.write_text('\n'.join(lineas) + '\n', encoding='utf-8')
    faltan = [(t, c['columna']) for t, i in datos['tablas'].items() for c in i['columnas'] if c['descripcion'].startswith('(sin')]
    print(f"{len(datos['tablas'])} tablas, {sum(len(i['columnas']) for i in datos['tablas'].values())} columnas, "
          f"{len(datos['vistas'])} vistas. Sin descripción: {faltan or 'ninguna'}")
    return 0


if __name__ == '__main__':
    sys.exit(main())

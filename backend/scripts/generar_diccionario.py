# -*- coding: utf-8 -*-
"""
Diccionario de datos del almacén, generado desde el esquema REAL.

Lee INFORMATION_SCHEMA y el catálogo de llaves de SQL Server (no se escribe a
mano), de modo que el documento de titulación no pueda describir una columna
que la base no tiene. Las descripciones de negocio viven en DESCRIPCIONES;
una columna sin descripción queda marcada para completarla.

Salida:
  - documentacion/tecnica/DICCIONARIO_DE_DATOS.md
  - documentacion/tecnica/diccionario_datos.json

Uso:
    cd backend
    python -m scripts.generar_diccionario            # desde SQL Server
    python -m scripts.generar_diccionario --script   # sin servidor: desde base_de_datos/crear_almacen_academico.sql

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

RAIZ = Path(__file__).resolve().parents[2]
SALIDA_JSON = RAIZ / 'documentacion' / 'tecnica' / 'diccionario_datos.json'
SALIDA_MD = RAIZ / 'documentacion' / 'tecnica' / 'DICCIONARIO_DE_DATOS.md'

TABLAS = {
    'fact_matriculas': 'Hecho central. Grano: un estudiante en una carrera, periodo académico y corte.',
    'dim_alumno': 'Estudiante, identificado por (institución, cédula).',
    'dim_institucion': 'Institución conectada y tipo de sus datos.',
    'dim_periodo_academico': 'Periodo académico de cada institución (semestre, presentación del módulo).',
    'dim_carrera': 'Carrera o módulo con su facultad (dimensión desnormalizada).',
    'dim_sede': 'Sede o campus de cada institución.',
    'dim_modalidad': 'Modalidad de estudio.',
    'dim_estado_matricula': 'Estado de la matrícula al cierre del periodo.',
    'dim_tiempo': 'Calendario de las fechas de corte.',
    'fact_prediccion_abandono': 'Resultado del modelo: un estudiante activo con su riesgo para el próximo periodo.',
    'fact_segmento_carrera': 'Resultado de la segmentación: una carrera con su segmento de riesgo.',
    'fact_evaluacion_modelo': 'Métricas de validación de la predicción, la segmentación y la consulta conversacional.',
    'fact_intervencion': 'Registro de seguimiento de bienestar estudiantil.',
    'dim_referente': 'Institución de referencia externa.',
    'fact_referente_externo': 'Indicador publicado por un referente externo, con su fuente y DOI.',
}

DESCRIPCIONES = {
    'matricula_id': 'Identificador sustituto de la fila', 'institucion_codigo': 'Institución dueña del dato (aislamiento por SESSION_CONTEXT)',
    'alumno_id': 'Estudiante (clave sustituta)', 'carrera_id': 'Carrera o módulo', 'sede_id': 'Sede o campus',
    'modalidad_codigo': 'Modalidad (PRESENCIAL, EN LINEA, HIBRIDA)', 'periodo_id': 'Periodo académico',
    'tiempo_id': 'Fecha del corte', 'estado_codigo': 'Estado al cierre del periodo',
    'nivel': 'Nivel o semestre cursado', 'corte': 'Corte de seguimiento dentro del periodo (1 si no hay cortes)',
    'promedio': 'Promedio del periodo (0 a 10)', 'asistencia_pct': 'Asistencia del periodo (%); en OULAD, días con actividad en el aula virtual',
    'monto_matricula': 'Valor de la matrícula (opcional)', 'beca_porcentaje': 'Porcentaje de beca, 0 a 100 (opcional)',
    'saldo_pendiente': 'Saldo adeudado al cierre del periodo (opcional)', 'creditos_matriculados': 'Créditos del periodo (opcional)',
    'numero_matricula': '1 = primera vez; 2 o más = repetición (opcional)',
    'dias_anticipacion_matricula': 'Días de anticipación de la matrícula respecto al inicio (opcional)',
    'actividad_lms': 'Interacciones en el aula virtual durante el corte (opcional)',
    'dias_sin_actividad': 'Días sin actividad en el aula virtual al cierre del corte (opcional)',
    'evaluaciones_vencidas': 'Evaluaciones con plazo vencido al cierre del corte (opcional)',
    'evaluaciones_entregadas': 'Evaluaciones entregadas hasta el cierre del corte (opcional)',
    'evaluaciones_tardias': 'Entregas fuera de plazo (opcional)', 'nota_evaluaciones': 'Nota media de lo entregado, 0 a 10 (opcional)',
    'es_ultimo_periodo': '1 = periodo vigente o de cierre de la trayectoria',
    'cedula': 'Identificador del estudiante (ficticio en los datos de prueba)', 'apellidos': 'Apellidos (ficticios en los datos de prueba)',
    'nombres': 'Nombres (ficticios en los datos de prueba)', 'genero': 'Género (M/F)', 'ciudad_residencia': 'Ciudad o región de residencia',
    'nombre': 'Nombre', 'pais': 'País', 'tipo_datos': 'SINTETICO o REAL_ANONIMIZADO', 'unidad_periodo': 'Qué es un periodo en la institución',
    'fecha_carga': 'Momento de la carga (UTC)', 'fecha': 'Fecha calendario', 'anio': 'Año', 'mes': 'Mes', 'trimestre': 'Trimestre',
    'descripcion': 'Descripción', 'es_terminal': '1 = el estado cierra la trayectoria',
    'periodo_codigo': 'Código del periodo (p. ej., 2024-1 o 2014B)', 'fecha_inicio': 'Fecha de inicio del periodo',
    'sede_codigo': 'Código de la sede', 'sede_nombre': 'Nombre de la sede', 'carrera': 'Carrera o módulo',
    'facultad_codigo': 'Código de la facultad', 'facultad_nombre': 'Nombre de la facultad',
    'prediccion_id': 'Identificador de la predicción', 'matricula_id_base': 'Fila de la trayectoria con cuyos datos se predijo',
    'horizonte': 'Qué se predice: abandono en el PRÓXIMO periodo', 'probabilidad': 'Probabilidad calibrada de abandono (0 a 1)',
    'riesgo_categoria': 'ALTO, MEDIO o BAJO según los umbrales del entrenamiento', 'umbral_alto': 'Umbral de la categoría ALTO (recall objetivo 0,50)',
    'umbral_medio': 'Umbral de la categoría MEDIO (recall objetivo 0,80)', 'percentil_riesgo': 'Posición del estudiante en la institución (0 a 100)',
    'factor_1': 'Razón que más eleva el riesgo (SHAP), en lenguaje natural', 'factor_2': 'Segunda razón', 'factor_3': 'Tercera razón',
    'explicacion_json': 'Contribuciones SHAP más relevantes (JSON)', 'caracteristicas_json': 'Variables usadas y estado para el simulador (JSON)',
    'fecha_calculo': 'Momento del cálculo (UTC)', 'modelo_version': 'Versión del modelo que produjo la fila',
    'segmento_id': 'Identificador de la fila', 'segmento': 'Atención prioritaria, Estable o Bajo riesgo', 'orden_segmento': '1 = mayor riesgo',
    'estudiantes': 'Estudiantes distintos de la carrera', 'tasa_abandono_hist': 'Proporción de trayectorias cerradas como RETIRADO',
    'promedio_hist': 'Promedio histórico', 'asistencia_hist': 'Asistencia histórica (%)', 'riesgo_promedio': 'Probabilidad media de los activos',
    'activos_en_riesgo': 'Activos en riesgo ALTO o MEDIO', 'evaluacion_id': 'Identificador de la métrica',
    'componente': 'PREDICCION, SEGMENTACION o CONSULTA', 'modelo': 'Modelo evaluado', 'esquema_validacion': 'Tipo de validación',
    'metrica': 'Nombre de la métrica', 'valor': 'Valor', 'desviacion': 'Desviación entre pliegues', 'grupo': 'Subgrupo o variable',
    'es_modelo_final': '1 = métrica del modelo en uso', 'intervencion_id': 'Identificador de la intervención',
    'tipo': 'Tipo', 'estado': 'ABIERTA o CERRADA', 'resultado': 'Resultado al cerrar', 'riesgo_al_registrar': 'Riesgo del estudiante al registrar',
    'registrado_por': 'Usuario que registró', 'fecha_registro': 'Fecha de registro (UTC)', 'fecha_cierre': 'Fecha de cierre (UTC)',
    'referente_codigo': 'Código del referente', 'referente_id': 'Identificador de la fila', 'indicador_codigo': 'Indicador (TASA_ABANDONO)',
    'unidad': 'Unidad del valor', 'definicion_indicador': 'Qué mide exactamente la cifra y dónde aparece en la fuente',
    'modalidad': 'Modalidad', 'nivel_comparabilidad': 'ALTA, MEDIA o BAJA', 'fuente': 'Cita APA corta', 'doi': 'DOI', 'url_fuente': 'Enlace',
}


SCRIPT_ALMACEN = RAIZ / 'base_de_datos' / 'crear_almacen_academico.sql'


def esquema_desde_script(ruta: Path = SCRIPT_ALMACEN):
    """Columnas, llaves primarias y foráneas leídas del script que crea el almacén.

    Devuelve lo mismo que las consultas a INFORMATION_SCHEMA, para generar el
    diccionario sin un servidor disponible (integración continua o revisión).
    """
    import re
    texto = ruta.read_text(encoding='utf-8')
    columnas, pk, fk = [], set(), {}
    for m in re.finditer(r'CREATE TABLE dbo\.(\w+) \((.*?)\n\);', texto, re.S):
        tabla, cuerpo = m.group(1), m.group(2)
        orden = 0
        for linea in cuerpo.splitlines():
            linea = linea.split('--')[0].strip().rstrip(',')
            d = re.match(r'(\w+)\s+(VARCHAR|NVARCHAR|CHAR|DECIMAL|INT|BIGINT|SMALLINT|TINYINT|BIT|DATE|DATETIME2)'
                         r'(?:\((MAX|\d+)(?:,(\d+))?\))?(.*)$', linea, re.I)
            if not d:
                continue
            orden += 1
            nombre, tipo_sql, a1, a2, resto = d.groups()
            tipo_sql = tipo_sql.lower()
            largo = (-1 if a1 == 'MAX' else int(a1)) if a1 and tipo_sql in ('varchar', 'nvarchar', 'char') else None
            prec = int(a1) if a1 and tipo_sql == 'decimal' else None
            esc = int(a2) if a2 else None
            nulo = 'NO' if ('NOT NULL' in resto.upper() or 'PRIMARY KEY' in resto.upper()) else 'YES'
            columnas.append((tabla, nombre, tipo_sql, largo, prec, esc, nulo, orden))
            if 'PRIMARY KEY' in resto.upper():
                pk.add((tabla, nombre))
            r = re.search(r'REFERENCES dbo\.(\w+)', resto, re.I)
            if r:
                fk[(tabla, nombre)] = r.group(1)
    return columnas, pk, fk


def esquema_desde_servidor():
    from core.db import conectar_admin
    conn = conectar_admin()
    cur = conn.cursor()
    cur.execute("""SELECT c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH, c.NUMERIC_PRECISION,
                          c.NUMERIC_SCALE, c.IS_NULLABLE, c.ORDINAL_POSITION
                   FROM INFORMATION_SCHEMA.COLUMNS c WHERE c.TABLE_SCHEMA = 'dbo' ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION""")
    columnas = cur.fetchall()
    cur.execute("""SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                   JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE kcu ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME
                   WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY'""")
    pk = {(t, c) for t, c in cur.fetchall()}
    cur.execute("""SELECT tp.name, cp.name, tr.name FROM sys.foreign_key_columns fkc
                   JOIN sys.tables tp ON tp.object_id = fkc.parent_object_id
                   JOIN sys.columns cp ON cp.object_id = fkc.parent_object_id AND cp.column_id = fkc.parent_column_id
                   JOIN sys.tables tr ON tr.object_id = fkc.referenced_object_id""")
    fk = {(t, c): r for t, c, r in cur.fetchall()}
    conn.close()
    return columnas, pk, fk


def main() -> int:
    columnas, pk, fk = esquema_desde_script() if '--script' in sys.argv else esquema_desde_servidor()

    def tipo(d, largo, prec, esc):
        if d in ('varchar', 'nvarchar', 'char'):
            return f"{d.upper()}({'MAX' if largo == -1 else largo})"
        if d == 'decimal':
            return f'DECIMAL({prec},{esc})'
        return d.upper()

    diccionario = {}
    for t, c, d, largo, prec, esc, nulo, _ in columnas:
        if t not in TABLAS:
            continue
        clave = 'PK' if (t, c) in pk else (f'FK → {fk[(t, c)]}' if (t, c) in fk else '')
        diccionario.setdefault(t, {'descripcion': TABLAS[t], 'columnas': []})['columnas'].append({
            'columna': c, 'tipo': tipo(d, largo, prec, esc), 'nulo': nulo == 'YES', 'clave': clave,
            'descripcion': DESCRIPCIONES.get(c, '(sin descripción)')})
    ordenado = {t: diccionario[t] for t in TABLAS if t in diccionario}
    SALIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SALIDA_JSON.write_text(json.dumps(ordenado, indent=2, ensure_ascii=False), encoding='utf-8')
    lineas = ['# Diccionario de datos del almacén ALMACEN_ACADEMICO', '',
              'Generado desde el esquema real con `python -m scripts.generar_diccionario` (servidor) o con la opción '
              '`--script` (desde `base_de_datos/crear_almacen_academico.sql`). No se edita a mano.', '']
    for t, info in ordenado.items():
        lineas += [f'## {t}', '', info['descripcion'], '', '| Columna | Tipo | Nulo | Clave | Descripción |', '|---|---|---|---|---|']
        lineas += [f"| {c['columna']} | {c['tipo']} | {'sí' if c['nulo'] else 'no'} | {c['clave']} | {c['descripcion']} |"
                   for c in info['columnas']]
        lineas.append('')
    SALIDA_MD.write_text('\n'.join(lineas), encoding='utf-8')
    faltan = [f"{t}.{c['columna']}" for t, i in ordenado.items() for c in i['columnas'] if c['descripcion'] == '(sin descripción)']
    print(f'Diccionario: {len(ordenado)} tablas. Sin descripción: {faltan or "ninguna"}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

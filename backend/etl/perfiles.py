# -*- coding: utf-8 -*-
"""
Perfiles de institución: cómo se lleva el sistema académico de cada
universidad al contrato del almacén.

El ETL no conoce el esquema de ninguna universidad. Cada perfil declara UN
SELECT que entrega, con alias, las columnas lógicas del contrato:

  - Obligatorias (COLUMNAS_OBLIGATORIAS): identidad, carrera, sede,
    modalidad, periodo académico, nivel, corte, estado, promedio, asistencia,
    fecha del corte y si es el último periodo de la trayectoria.
  - Opcionales (COLUMNAS_OPCIONALES): financieras, de matrícula, de aula
    virtual y de evaluaciones. Si la institución no las registra, el SELECT
    las entrega como NULL y el modelo de esa institución no las usa.

Conectar una universidad nueva = agregar un perfil (sin tocar el ETL, el
modelo, la API ni la interfaz):
  1. Obtener, con autorización institucional, el esquema de su base de
     matrícula.
  2. Escribir un PerfilInstitucion con su SELECT (alias a los nombres
     lógicos; literales para lo que no registre, p. ej. 'PRESENCIAL' AS
     modalidad).
  3. Ejecutar: python -m etl.etl_academico --perfil <NOMBRE>

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from dataclasses import dataclass

COLUMNAS_OBLIGATORIAS = [
    'cedula', 'apellidos', 'nombres', 'genero', 'ciudad_residencia',
    'facultad_codigo', 'facultad_nombre', 'carrera', 'sede_codigo', 'sede_nombre', 'modalidad',
    'periodo_academico', 'inicio_periodo', 'nivel', 'corte', 'estado_matricula',
    'promedio', 'asistencia_pct', 'fecha_corte', 'es_ultimo_periodo',
]
COLUMNAS_OPCIONALES = [
    'monto_matricula', 'beca_porcentaje', 'saldo_pendiente', 'creditos_matriculados', 'numero_matricula',
    'dias_anticipacion_matricula', 'actividad_lms', 'dias_sin_actividad', 'evaluaciones_vencidas',
    'evaluaciones_entregadas', 'evaluaciones_tardias', 'nota_evaluaciones',
]
ESTADOS_VALIDOS = {'ACTIVO', 'RETIRADO', 'GRADUADO', 'EGRESADO', 'REPROBADO'}
MODALIDADES_VALIDAS = {'PRESENCIAL', 'EN LINEA', 'HIBRIDA'}


@dataclass(frozen=True)
class PerfilInstitucion:
    """Cómo extraer los datos de una institución al contrato del almacén."""

    codigo: str            # identificador en el almacén (aislamiento por SESSION_CONTEXT)
    nombre: str            # nombre que ve la autoridad
    pais: str
    tipo_datos: str        # SINTETICO / REAL_ANONIMIZADO
    unidad_periodo: str    # cómo se lee "periodo" en esta institución
    base_origen: str       # base operativa donde corre el SELECT
    sql_origen: str


_UNEMI_PRUEBAS = PerfilInstitucion(
    codigo='UNEMI_PRUEBAS',
    nombre='UNEMI (datos de prueba)',
    pais='Ecuador',
    tipo_datos='SINTETICO',
    unidad_periodo='semestre',
    base_origen='UNEMI_PRUEBAS',
    sql_origen="""
        SELECT h.cedula, a.apellidos, a.nombres, a.genero, a.ciudad_residencia,
               h.facultad_codigo, h.facultad_nombre, h.carrera,
               h.sede_codigo, h.sede_nombre, h.canal_codigo AS modalidad,
               CONCAT(YEAR(h.inicio_clases), '-', CASE WHEN MONTH(h.inicio_clases) <= 6 THEN '1' ELSE '2' END)
                   AS periodo_academico,
               h.inicio_clases AS inicio_periodo,
               h.semestre AS nivel, 1 AS corte, h.estado_matricula, h.promedio, h.asistencia_pct,
               h.fecha_matricula AS fecha_corte, h.es_ultimo_periodo,
               h.monto_matricula, h.beca_porcentaje, h.saldo_pendiente,
               h.creditos_matriculados, h.numero_matricula, h.dias_anticipacion_matricula,
               h.actividad_lms, h.dias_sin_actividad, h.evaluaciones_vencidas,
               h.evaluaciones_entregadas, h.evaluaciones_tardias, h.nota_evaluaciones
        FROM dbo.historial_matriculas h
        JOIN dbo.alumnos_prueba a ON a.cedula = h.cedula
    """,
)

# Open University (Reino Unido), cargada por scripts/cargar_oulad.py. Periodo
# académico = presentación del módulo; corte = bloque de 28 días. No registra
# datos financieros (NULL) y sí aula virtual, evaluaciones y matrícula.
_OULAD_UK = PerfilInstitucion(
    codigo='OULAD_UK',
    nombre='Open University, Reino Unido (OULAD)',
    pais='Reino Unido',
    tipo_datos='REAL_ANONIMIZADO',
    unidad_periodo='corte de 28 días dentro de la presentación del módulo',
    base_origen='OULAD_PRUEBAS',
    sql_origen="""
        SELECT h.cedula, h.apellidos, h.nombres, h.genero, h.ciudad_residencia,
               h.facultad_codigo, h.facultad_nombre, h.carrera,
               'OU_UK' AS sede_codigo, 'Open University (Reino Unido)' AS sede_nombre, 'EN LINEA' AS modalidad,
               h.code_presentation AS periodo_academico, h.inicio_presentacion AS inicio_periodo,
               1 AS nivel, h.corte, h.estado_matricula, h.promedio, h.asistencia_pct,
               h.fecha_corte, h.es_ultimo_periodo,
               CAST(NULL AS DECIMAL(10,2)) AS monto_matricula, CAST(NULL AS TINYINT) AS beca_porcentaje,
               CAST(NULL AS DECIMAL(10,2)) AS saldo_pendiente,
               h.creditos AS creditos_matriculados, h.intentos_previos + 1 AS numero_matricula,
               -h.dia_registro AS dias_anticipacion_matricula, h.clics AS actividad_lms, h.dias_sin_actividad,
               h.evaluaciones_vencidas, h.evaluaciones_entregadas, h.evaluaciones_tardias, h.nota_evaluaciones
        FROM dbo.historial_bloques h
    """,
)

PERFILES: dict[str, PerfilInstitucion] = {p.codigo: p for p in (_UNEMI_PRUEBAS, _OULAD_UK)}


def obtener_perfil(codigo: str) -> PerfilInstitucion:
    """Devuelve el perfil (sin distinguir mayúsculas) o explica cómo crearlo."""
    perfil = PERFILES.get((codigo or '').strip().upper())
    if perfil is None:
        raise KeyError(f"No existe el perfil '{codigo}'. Disponibles: {', '.join(PERFILES)}. "
                       'Para una institución nueva, agregue un PerfilInstitucion en backend/etl/perfiles.py.')
    return perfil


def validar_columnas(columnas: list[str], perfil: PerfilInstitucion) -> None:
    """Comprueba que el SELECT del perfil entregue todo el contrato."""
    faltantes = set(COLUMNAS_OBLIGATORIAS + COLUMNAS_OPCIONALES) - set(columnas)
    if faltantes:
        raise ValueError(f"El SELECT del perfil '{perfil.codigo}' no entrega: {sorted(faltantes)}. "
                         'Las opcionales que la institución no registre se entregan como NULL.')


def validar_filas(filas: list[dict]) -> list[str]:
    """Reglas de calidad del contrato; devuelve los problemas encontrados (vacío si todo está bien)."""
    problemas = []
    estados = {f['estado_matricula'] for f in filas}
    if estados - ESTADOS_VALIDOS:
        problemas.append(f'Estados no reconocidos: {sorted(estados - ESTADOS_VALIDOS)}')
    modalidades = {f['modalidad'] for f in filas}
    if modalidades - MODALIDADES_VALIDAS:
        problemas.append(f'Modalidades no reconocidas: {sorted(modalidades - MODALIDADES_VALIDAS)}')
    fuera = sum(1 for f in filas if not (0 <= float(f['promedio']) <= 10) or not (0 <= float(f['asistencia_pct']) <= 100))
    if fuera:
        problemas.append(f'{fuera} filas con promedio fuera de 0-10 o asistencia fuera de 0-100')
    return problemas

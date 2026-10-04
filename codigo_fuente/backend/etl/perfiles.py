# -*- coding: utf-8 -*-
"""
perfiles.py — hace que scripts/etl_academico.py sea agnostico de
institucion.

Antes, etl_academico.py tenia hard-codeado el nombre de la tabla y las
columnas de UNEMI_PRUEBAS (`dbo.historial_matriculas`, `dbo.alumnos_prueba`).
Conectar una IES nueva (ej. Universidad Politecnica Salesiana) significaba
reescribir el script de ETL. Ahora el ETL es generico: solo sabe leer un
conjunto de COLUMNAS_REQUERIDAS (el contrato del modelo dimensional) desde
UN SELECT que cada institucion define en su propio "perfil".

──────────────────────────────────────────────────────────────────────────
CÓMO CONECTAR UNA INSTITUCIÓN NUEVA (ej. UPS Cuenca)
──────────────────────────────────────────────────────────────────────────
1. Pide a la institucion el esquema real de su base de matricula (nombres
   de tablas/columnas). Esto es un requisito de acceso institucional, no
   tecnico — ver documentacion/tecnica/PREDICCION_ABANDONO.md, seccion "Módulo 1".
2. Agrega un PerfilInstitucion nuevo a PERFILES (abajo), con UN SELECT que
   mapee sus columnas reales a los nombres logicos de COLUMNAS_REQUERIDAS
   (usando alias SQL: `SELECT su_columna AS cedula, ...`).
3. Si la institucion no rastrea alguna variable (ej. no tiene "canal" de
   ingreso), usa un LITERAL en el SELECT en vez de una columna real:
   `SELECT 'PRESENCIAL' AS canal_codigo, ...` — el ETL no distingue entre
   un valor real y uno fijo, así que instituciones de un solo campus/
   modalidad no necesitan ese dato para funcionar.
4. Corre: `python scripts/etl_academico.py --perfil <nombre_del_perfil>`

Ningun otro archivo de backend/scripts ni backend/ml/ necesita cambiar: el
resto del pipeline (warehouse CHAT, features del modelo, endpoints, panel)
ya trabaja solo con los nombres logicos de abajo, nunca con el esquema de
origen de una institucion en particular.
"""
from __future__ import annotations

from dataclasses import dataclass

# Contrato del modelo dimensional (ver codigo_fuente/base_de_datos/crear_chat_academico.sql):
# toda columna que el ETL necesita, sin importar de que institucion venga.
COLUMNAS_REQUERIDAS = [
    'cedula', 'apellidos', 'nombres', 'genero', 'ciudad_residencia',
    'facultad_codigo', 'facultad_nombre', 'carrera',
    'sede_codigo', 'sede_nombre', 'canal_codigo',
    'semestre', 'estado_matricula', 'promedio', 'asistencia_pct',
    'fecha_matricula', 'monto_matricula', 'beca_porcentaje', 'saldo_pendiente',
    'es_ultimo_periodo',
]


@dataclass(frozen=True)
class PerfilInstitucion:
    nombre: str  # empresa_codigo en CHAT (aislamiento por SESSION_CONTEXT)
    business_name: str
    base_datos_origen: str  # BD operativa donde correr el SELECT (contexto inicial de conexion)
    sql_origen: str  # SELECT que produce EXACTAMENTE las columnas de COLUMNAS_REQUERIDAS (alias incluidos)


# ── UNEMI_PRUEBAS: perfil de referencia / datos de prueba de esta tesis ──
_UNEMI_PRUEBAS = PerfilInstitucion(
    nombre='UNEMI_PRUEBAS',
    business_name='UNEMI_PRUEBAS',
    base_datos_origen='UNEMI_PRUEBAS',
    sql_origen="""
        SELECT h.cedula, a.apellidos, a.nombres, a.genero, a.ciudad_residencia,
               h.facultad_codigo, h.facultad_nombre, h.carrera,
               h.sede_codigo, h.sede_nombre, h.canal_codigo,
               h.semestre, h.estado_matricula, h.promedio, h.asistencia_pct,
               h.fecha_matricula, h.monto_matricula, h.beca_porcentaje, h.saldo_pendiente,
               h.es_ultimo_periodo
        FROM dbo.historial_matriculas h
        JOIN dbo.alumnos_prueba a ON a.cedula = h.cedula
        ORDER BY h.cedula, h.periodo_num
    """,
)

# ── Plantilla para una IES real (ej. UPS) — DESACTIVADA hasta tener acceso ──
# Ejemplo de como luciria (columnas inventadas a modo ilustrativo; hay que
# reemplazarlas por el esquema real de UPS una vez autorizado el acceso):
#
# _UPS_CUENCA = PerfilInstitucion(
#     nombre='UPS_CUENCA',
#     business_name='Universidad Politecnica Salesiana - Sede Cuenca',
#     base_datos_origen='UPS_SIS',
#     sql_origen="""
#         SELECT m.numero_identificacion AS cedula, m.apellidos, m.nombres,
#                m.sexo AS genero, m.ciudad AS ciudad_residencia,
#                m.cod_facultad AS facultad_codigo, m.facultad AS facultad_nombre,
#                m.carrera, m.cod_sede AS sede_codigo, m.sede AS sede_nombre,
#                m.modalidad AS canal_codigo, m.ciclo AS semestre,
#                m.estado AS estado_matricula, m.promedio_ponderado AS promedio,
#                m.pct_asistencia AS asistencia_pct, m.fecha_matricula,
#                m.valor_matricula AS monto_matricula, m.pct_beca AS beca_porcentaje,
#                m.saldo_pendiente,
#                CASE WHEN m.es_periodo_actual = 1 THEN 1 ELSE 0 END AS es_ultimo_periodo
#         FROM dbo.vw_historial_matriculas m
#     """,
# )

# ── OULAD_UK: segunda institución REAL (Avance 2) ──────────────────────────
# Open University Learning Analytics Dataset (Kuzilek, Hlosta & Zdrahal,
# 2017), cargado en OULAD_PRUEBAS por scripts/seed_oulad.py. Demuestra lo
# que afirma el documento: conectar otra institución es agregar ESTE perfil
# (un SELECT con alias), sin tocar el ETL ni el motor predictivo.
#   - periodo = bloque de 28 días (semestre = número de bloque);
#   - asistencia = días con actividad en el aula virtual / días del bloque;
#   - la institución no registra datos financieros: se usan literales 0
#     (paso 3 del procedimiento de arriba).
_OULAD_UK = PerfilInstitucion(
    nombre='OULAD_UK',
    business_name='Open University (Reino Unido) - OULAD',
    base_datos_origen='OULAD_PRUEBAS',
    sql_origen="""
        SELECT h.cedula, h.apellidos, h.nombres, h.genero, h.ciudad_residencia,
               h.facultad_codigo, h.facultad_nombre, h.carrera,
               'OU_UK' AS sede_codigo, 'Open University (Reino Unido)' AS sede_nombre,
               'EN LINEA' AS canal_codigo,
               h.bloque AS semestre, h.estado_matricula, h.promedio, h.asistencia_pct,
               h.fecha_matricula,
               0 AS monto_matricula, 0 AS beca_porcentaje, 0 AS saldo_pendiente,
               h.es_ultimo_periodo
        FROM dbo.historial_bloques h
        ORDER BY h.cedula, h.code_module, h.code_presentation, h.bloque
    """,
)

PERFILES: dict[str, PerfilInstitucion] = {
    _UNEMI_PRUEBAS.nombre: _UNEMI_PRUEBAS,
    _OULAD_UK.nombre: _OULAD_UK,
}


def obtener_perfil(nombre: str) -> PerfilInstitucion:
    perfil = PERFILES.get(nombre.strip().upper())
    if perfil is None:
        disponibles = ', '.join(PERFILES.keys())
        raise KeyError(
            f"No existe un perfil de ETL para '{nombre}'. "
            f"Perfiles disponibles: {disponibles}. "
            f"Para conectar una institucion nueva, agrega un PerfilInstitucion "
            f"en backend/etl/perfiles.py (ver docstring del archivo)."
        )
    return perfil


def institucion_de_base(nombre_base: str) -> str:
    """Código de institución con que el almacén CHAT guarda los datos de una base operativa.

    La interfaz identifica la institución por el nombre de la base a la que se
    conectó (por ejemplo, OULAD_PRUEBAS), pero el ETL guarda las filas con el
    nombre del perfil (OULAD_UK). Si ningún perfil usa esa base, el nombre se
    devuelve tal cual.
    """
    base = (nombre_base or "").strip().upper()
    for perfil in PERFILES.values():
        if perfil.base_datos_origen.upper() == base:
            return perfil.nombre
    return base


def validar_columnas(columnas_obtenidas: list[str], perfil: PerfilInstitucion) -> None:
    faltantes = set(COLUMNAS_REQUERIDAS) - set(columnas_obtenidas)
    if faltantes:
        raise ValueError(
            f"El SELECT del perfil '{perfil.nombre}' no produce las columnas "
            f"requeridas: {sorted(faltantes)}. Revisa los alias en "
            f"PerfilInstitucion.sql_origen (backend/etl/perfiles.py)."
        )

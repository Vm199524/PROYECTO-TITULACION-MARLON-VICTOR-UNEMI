# -*- coding: utf-8 -*-
"""
Perfiles de institución para el ETL académico.

Hacen que scripts/etl_academico.py sea agnóstico de institución. El ETL no
tiene fijo el nombre de ninguna tabla ni columna de origen: solo sabe leer
un conjunto de COLUMNAS_REQUERIDAS (el contrato del modelo dimensional)
desde UN SELECT que cada institución define en su propio "perfil". Conectar
una IES nueva (p. ej., la Universidad Politécnica Salesiana) es agregar un
perfil, no reescribir el script de ETL.

──────────────────────────────────────────────────────────────────────────
CÓMO CONECTAR UNA INSTITUCIÓN NUEVA (p. ej., UPS Cuenca)
──────────────────────────────────────────────────────────────────────────
1. Pide a la institución el esquema real de su base de matrícula (nombres
   de tablas y columnas). Es un requisito de acceso institucional, no
   técnico; ver documentacion/tecnica/PREDICCION_ABANDONO.md, sección "Módulo 1".
2. Agrega un PerfilInstitucion nuevo a PERFILES (abajo), con UN SELECT que
   mapee sus columnas reales a los nombres lógicos de COLUMNAS_REQUERIDAS
   (con alias SQL: `SELECT su_columna AS cedula, ...`).
3. Si la institución no registra alguna variable (p. ej., no tiene "canal"
   de ingreso), usa un LITERAL en el SELECT en vez de una columna real:
   `SELECT 'PRESENCIAL' AS canal_codigo, ...`. El ETL no distingue entre
   un valor real y uno fijo, así que las instituciones de un solo campus o
   modalidad no necesitan ese dato para funcionar.
4. Ejecuta: `python scripts/etl_academico.py --perfil <nombre_del_perfil>`

Ningún otro archivo de backend/scripts ni de backend/ml/ necesita cambiar: el
resto del pipeline (warehouse CHAT, características del modelo, endpoints,
panel) trabaja solo con los nombres lógicos de abajo, nunca con el esquema
de origen de una institución en particular.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from dataclasses import dataclass

# Contrato del modelo dimensional (ver codigo_fuente/base_de_datos/crear_chat_academico.sql):
# toda columna que el ETL necesita, sin importar de qué institución venga.
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
    """Describe cómo extraer los datos académicos de una institución al contrato de CHAT."""

    nombre: str  # empresa_codigo en CHAT (aislamiento por SESSION_CONTEXT)
    business_name: str  # nombre comercial que se registra en dim_empresa
    base_datos_origen: str  # BD operativa donde correr el SELECT (contexto inicial de conexión)
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
# Ejemplo de cómo luciría (columnas inventadas a modo ilustrativo; se
# reemplazan por el esquema real de UPS una vez autorizado el acceso):
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

# ── OULAD_UK: segunda institución REAL ─────────────────────────────────────
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
    """Devuelve el perfil con ese nombre, sin distinguir mayúsculas.

    Raises:
        KeyError: si no existe, con la lista de perfiles disponibles.
    """
    perfil =PERFILES.get(nombre.strip().upper())
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
    """Comprueba que el SELECT del perfil produzca todas las COLUMNAS_REQUERIDAS.

    Raises:
        ValueError: con las columnas que faltan.
    """
    faltantes =set(COLUMNAS_REQUERIDAS) - set(columnas_obtenidas)
    if faltantes:
        raise ValueError(
            f"El SELECT del perfil '{perfil.nombre}' no produce las columnas "
            f"requeridas: {sorted(faltantes)}. Revisa los alias en "
            f"PerfilInstitucion.sql_origen (backend/etl/perfiles.py)."
        )

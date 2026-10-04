"""
core/business_logic.py - Giro de negocio por empresa.

FASE 3 — C4: el mapeo empresa → giro de negocio vivía como un diccionario
hardcodeado en este archivo, así que agregar o corregir una empresa exigía
tocar código y redeployar. Ahora vive en knowledge/business_logic.json,
editable directamente (con recarga en caliente por fecha de modificación,
igual que knowledge/integridad_vistas.json y knowledge/metric_catalog.json).

Si el archivo JSON falta o está corrupto, se usa _POR_DEFECTO (una copia
congelada del mapeo original) para que el sistema nunca se quede sin esta
información por un error de edición.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("BusinessLogic")

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "business_logic.json"

_cache: dict[str, Any] = {"mtime": None, "data": None}

_POR_DEFECTO = {
    "mapa": {
        "HITE": "Industria Textil - Producción de hilos, inventarios de materia prima, ventas industriales y exportaciones.",
        "HILA": "Industria Textil - Producción de hilos, inventarios de materia prima, ventas industriales y exportaciones.",
        "HILO": "Industria Textil - Producción de hilos, inventarios de materia prima, ventas industriales y exportaciones.",
        "SUTU": "Dispositivos Médicos - Importación y comercialización de insumos médicos, trazabilidad de lotes y facturación técnica.",
        "SUTU1": "Dispositivos Médicos - Importación y comercialización de insumos médicos, trazabilidad de lotes y facturación técnica.",
        "MINO": "Retail / Moda - Ventas minoristas, gestión de puntos de venta (POS), inventario de prendas y temporadas.",
        "MILA": "Retail / Moda - Ventas minoristas, gestión de puntos de venta (POS), inventario de prendas y temporadas.",
        "DENI": "Inmobiliaria - Gestión de proyectos de construcción, administración de activos inmobiliarios y contratos.",
        "DEIN": "Inmobiliaria - Gestión de proyectos de construcción, administración de activos inmobiliarios y contratos.",
        "VEAS": "Publicidad Exterior - Gestión de espacios publicitarios, órdenes de instalación, mantenimiento de estructuras y ventas B2B.",
        "VEAA": "Publicidad Exterior - Gestión de espacios publicitarios, órdenes de instalación, mantenimiento de estructuras y ventas B2B.",
        "PAUT": "Sector Automotriz - Venta de vehículos, repuestos, servicios de taller y financiamiento (Autocredit).",
        "GYMM": "Salud y Bienestar - Gestión de membresías, venta de suplementos (GoodNutricion) e inventarios de gimnasios.",
        "GYMJ": "Salud y Bienestar - Gestión de membresías, venta de suplementos y servicios de gimnasios.",
        "IMCE": "Salud Corp. - Prestación de servicios médicos corporativos y suministros de salud a gran escala.",
        "MANA": "Servicios / Producción - Gestión de recetas alimenticias y órdenes de producción (giro de alimentos/catering).",
        "MATI": "Bienes Raíces - Inversión y gestión de alquileres o desarrollos habitacionales.",
        "ALIM": "Consumo Masivo / Alimentos - Distribución de productos alimenticios e inventarios de bodega.",
        "FOOD": "Consumo Masivo / Alimentos - Distribución de productos alimenticios e inventarios de bodega.",
        "REST": "Gastronomía (POS) - Operaciones de restaurante, comandas, gestión de mesas y cajas.",
        "VENTO": "Gastronomía (POS) - Operaciones de restaurante, comandas, gestión de mesas y cajas.",
        "TRIPLEA": "Medicina / Restaurante / Comercial - Gestión integral, médica y comercial (POS).",
        "CHAT": "Base Consolidada de Inteligencia Analítica - Datos cruzados de finanzas, rrhh y operaciones.",
        "RRHH": "Gestión del Talento Humano - Nómina, contratos, vacaciones, roles de pago y asistencia.",
        "PROYECTO": "Configuración del Sistema - Parámetros globales y catálogos maestros.",
        "XELC": "Telecomunicaciones - Venta de equipos tecnológicos, servicios de red y facturación de servicios.",
        "DAUN": "Institución Educativa - Gestión académica de alumnos. REGLA CRITICA: Los alumnos 'ACTIVOS' se identifican por alu_estado = '' (vacío) y por el periodo más reciente (edu_period). Las tablas principales son edu_alumno, edu_period, edu_nivel y edu_cursos.",
        "MONT": "Institución educativa - Gestión académica de estudiantes (VIS_ALUMNO: matrícula, cursos, paralelos, niveles y estados académicos) además de la facturación de servicios educativos. HECHOS VERIFICADOS SOBRE VIS_ALUMNO (28/08/2026, contra la base real): (1) TODOS los alumnos tienen curso y nivel asignado — la vista une con edu_cursos y edu_nivel por INNER JOIN, así que un alumno sin curso no aparecería en ella. Nunca digas que faltan alumnos por 'curso vacío' o 'sin curso asignado': eso no ocurre. (2) 'Matriculado' significa ESTADO = 'MATRICULADO' exacto (882 alumnos en el período lectivo vigente, 2026-2027 — confirmado también en edu_period.per_estado = 'AP', el único período marcado como abierto/operativo; el resto de períodos llevan 'AN' o son historial). Los estados GRADUADO (43, ya egresados), REGISTRO DE DATOS (13, inscripción sin formalizar), APROBADO (2, aprobados para admisión) y ADMISION (1, en trámite) NO son matrícula activa aunque tengan curso y nivel asignado — no los cuentes como matriculados. (3) La vista mezcla varios períodos lectivos a la vez (2023-2024, 2025-2026, 2026-2027, 2027-2028): usa siempre el período vigente (el más poblado / el que edu_period marca 'AP'), nunca sumes todos los períodos sin que sea explícito. (4) Tres cifras DISTINTAS y todas correctas, según lo que pregunte el usuario: 'alumnos matriculados' (sin más calificativo, o 'total de alumnos por curso/nivel') → 882, SOLO ESTADO='MATRICULADO' del período vigente. 'alumnos registrados' o 'total de alumnos' SIN decir 'matriculados' y sin fecha explícita → 941, TODOS los estados del período vigente (matriculado+graduado+registro de datos+aprobado+admisión) — se entiende referido al año en curso salvo que sea otra cosa explícitamente. 'total histórico', 'en toda la base', 'de años anteriores' o se mencionen varios años → 1.038, TODOS los períodos lectivos juntos (VIS_ALUMNO ya excluye anulados). Cuando no sea explícito, usa 882 (matriculados) por defecto y ofrece aclarar que hay otras dos lecturas posibles.",
        "ENIG": "Comercial / Inventarios / Facturación - Gestión general de compras, ventas e ingresos.",
        "ENPR": "Comercial / Inventarios / Facturación - Gestión general de compras, ventas e ingresos.",
        "ASORESTG": "Restaurante / Hospitalidad - Centrada en gestión de mesas (Touch), salones y comandas.",
        "CONEUROPA": "Restaurante / Hospitalidad - Centrada en gestión de mesas (Touch), salones y comandas.",
        "REALALTO": "Restaurante / Hospitalidad - Centrada en gestión de mesas (Touch), salones y comandas.",
        "TECNOWEB": "Restaurante / Hospitalidad - Centrada en gestión de mesas (Touch), salones y comandas.",
        "TALL": "Operaciones / Logística / Automotriz - Relacionado a talleres o mantenimiento técnico.",
        "SONG": "Operaciones Generales - Gestión logística e inventarios.",
    },
    "inferencia_por_nombre": [
        {"contiene": ["ALIMENTOS", "FOOD"], "descripcion": "Consumo Masivo / Alimentos - Distribución de productos alimenticios e inventarios."},
        {"contiene": ["TEX", "MODA", "MILANO"], "descripcion": "Retail / Industrial Textil - Venta o manufactura de productos textiles."},
        {"contiene": ["AUTO", "MOTORS"], "descripcion": "Sector Automotriz - Venta de vehículos y repuestos."},
        {"contiene": ["CONSULT", "TECH"], "descripcion": "Servicios / Tecnología - Consultoría técnica y ventas B2B."},
    ],
    "default": "Gestión Comercial y Operativa General (Empresa Estándar).",
}


def _cargar() -> dict:
    """Carga la configuración con recarga en caliente por fecha de modificación."""
    try:
        mtime = _CONFIG_PATH.stat().st_mtime
    except OSError:
        return _POR_DEFECTO

    if _cache["mtime"] == mtime and _cache["data"] is not None:
        return _cache["data"]

    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        _cache["mtime"] = mtime
        _cache["data"] = data
        return data
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("[BusinessLogic] No se pudo leer %s: %s", _CONFIG_PATH, exc)
        return _POR_DEFECTO


def get_business_logic(db_code: str, db_name: str = "") -> str:
    """
    Retorna la lógica de negocio asociada a una base de datos o empresa.
    Este mapeo permite a la IA entender de forma contextual el giro de negocio
    y responder asertivamente el tipo de datos que maneja cada entorno.
    """
    cfg = _cargar()
    code = str(db_code or "").strip().upper()

    mapa = cfg.get("mapa", {}) if isinstance(cfg.get("mapa"), dict) else {}
    if code in mapa:
        return mapa[code]

    # Inferencia por nombre si el código no está mapeado
    name_upper = str(db_name or "").upper()
    reglas = cfg.get("inferencia_por_nombre", [])
    if isinstance(reglas, list):
        for regla in reglas:
            if not isinstance(regla, dict):
                continue
            palabras = regla.get("contiene", [])
            descripcion = regla.get("descripcion", "")
            if not descripcion or not isinstance(palabras, list):
                continue
            if any(str(p).upper() in name_upper for p in palabras if name_upper):
                return descripcion

    return cfg.get("default", _POR_DEFECTO["default"])

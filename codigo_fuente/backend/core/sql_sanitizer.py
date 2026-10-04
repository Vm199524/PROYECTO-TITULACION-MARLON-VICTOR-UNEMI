"""
core/sql_sanitizer.py — El Guardián del Motor (v2 Phase 4 - Gold)
Responsabilidad: Asegurar integridad, seguridad y adaptabilidad dialéctica.
Este módulo es el último filtro antes de que el SQL toque la base de datos real.
Permite que el sistema hable fluidamente SQL Server y SQLite de forma transparente.

OPTIMIZACION: Regex precompilados para reducir latencia en validaciones.
"""
import re
from typing import Tuple


# ─────────────────────────────────────────────────────────────────────────────
# OPTIMIZACION: Regex precompilados para estado (evita recompilar en cada uso)
# ─────────────────────────────────────────────────────────────────────────────

_ESTADO_PATTERNS = [
    # Solo normalizamos si ya dice la palabra completa, para asegurar el TRIM
    (re.compile(r"\[?Estado\]?\s*=\s*'ACTIVO'", re.IGNORECASE),                                     "LTRIM(RTRIM(Estado)) = 'ACTIVO'"),
    (re.compile(r"\[?Estado\]?\s*=\s*'INACTIVO'", re.IGNORECASE),                                   "LTRIM(RTRIM(Estado)) = 'INACTIVO'"),
    (re.compile(r"\[?Estado\]?\s*=\s*'PARA FINIQUITAR'", re.IGNORECASE),                            "LTRIM(RTRIM(Estado)) = 'PARA FINIQUITAR'"),
]

_RTRIM_PATTERNS = [
    # [Estado] sin brackets con y sin RTRIM
    (re.compile(r"\[Estado\]\s*=\s*'([^']+)'", re.IGNORECASE),  r"RTRIM([Estado]) = '\1'"),
    (re.compile(r"\bEstado\b\s*=\s*'([^']+)'", re.IGNORECASE),  r"RTRIM([Estado]) = '\1'"),
]

# Palabras que autorizan filtros de estado en la query
_ESTADO_AUTH_WORDS = {
    'activo', 'activos', 'activa', 'activas', 'inactivo',
    'vigente', 'vigentes', 'habilitado', 'isnull', 'estado',
    'hay', 'tiene', 'tenemos', 'actual', 'actuales', 'ahora',
    'alumnos', 'estudiantes', 'matriculados', 'cursos'
}

# OPTIMIZACION: Regex precompilados para ghost filters (evita recompilar)
_GHOST_FILTER_PATTERNS = [
    re.compile(r"AND\s+ISNULL\s*\(\s*\[?Estado\]?\s*,\s*'[^']+'\s*\)\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"AND\s+\[?[Ee]stado\]?\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"WHERE\s+ISNULL\s*\(\s*\[?Estado\]?\s*,\s*'[^']+'\s*\)\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"WHERE\s+\[?[Ee]stado\]?\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"AND\s+TRY_CAST\s*\(\s*\[?Fecha[^\)]+\)\s*<=\s*GETDATE\(\)", re.IGNORECASE),
    re.compile(r"AND\s+activo\s*=\s*[1'S]", re.IGNORECASE),
]

# Palabras reservadas que representan un riesgo operativo o de seguridad (v2 Gold)
# Bloqueamos cualquier intento de mutación de datos para garantizar el modo READ-ONLY.
_FORBIDDEN_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|EXEC|EXECUTE|sp_|xp_|GRANT|REVOKE)\b',
    re.IGNORECASE
)

def clean_sql_spacing(sql: str) -> str:
    """
    Elimina espacios innecesarios que confunden al motor SQL y al usuario.
    Especialmente espacios alrededor de puntos en identificadores calificados.
    """
    if not sql:
        return sql
    
    # 1. Quitar espacios alrededor de puntos: [DB] . [dbo] . [Table] -> [DB].[dbo].[Table]
    sql = re.sub(r'\s*\.\s*', '.', sql)
    
    # 2. Quitar espacios antes de comas: col1 , col2 -> col1, col2
    sql = re.sub(r'\s+,\s*', ', ', sql)
    
    # 3. Normalizar espacios multiples en una sola linea (opcional, pero ayuda a la estabilidad)
    # Solo lo hacemos si hay espacios realmente excesivos (>2)
    sql = re.sub(r'[ \t]{2,}', ' ', sql)
    
    return sql.strip()


def fix_estado_filter(sql: str) -> str:
    """Corrige abreviaciones de Estado que el LLM genera (='A', ='S', =1, etc.)
    OPTIMIZACION: Usa regex precompilados (sin recompilar).
    """
    result = sql
    for pattern, replacement in _ESTADO_PATTERNS:
        result = pattern.sub(replacement, result)
    if result != sql:
        print(f"[SQL-FIX] Estado corregido.")
    return result


def fix_rtrim(sql: str) -> str:
    """Envuelve comparaciones de [Estado] sin RTRIM.
    OPTIMIZACION: Usa regex precompilados (sin recompilar).
    """
    result = sql
    for pattern, replacement in _RTRIM_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def strip_ghost_filters(sql: str, question: str) -> str:
    """
    Elimina filtros de estado inyectados automáticamente por el LLM
    cuando el usuario NO los solicitó.
    OPTIMIZACION: Usa regex precompilados.
    """
    q_lower = question.lower()
    if any(w in q_lower for w in _ESTADO_AUTH_WORDS):
        return sql

    result = sql
    for pattern in _GHOST_FILTER_PATTERNS:
        # Intentamos ser menos destructivos. Si el filtro está precedido por WHERE y seguido por AND,
        # debemos mantener el WHERE.
        result = pattern.sub('', result)

    # Limpieza de conectores huerfanos (AND/OR sobrantes tras eliminar el filtro)
    result = re.sub(r'WHERE\s+AND', 'WHERE', result, flags=re.IGNORECASE)
    result = re.sub(r'WHERE\s+OR', 'WHERE', result, flags=re.IGNORECASE)
    result = re.sub(r'\s+AND\s+AND', ' AND', result, flags=re.IGNORECASE)
    
    # Si la query termina en WHERE o AND tras la limpieza, lo podamos
    result = result.strip()
    if result.upper().endswith("WHERE"):
        result = result[:-5].strip()
    if result.upper().endswith("AND"):
        result = result[:-3].strip()

    return result


def validate_readonly(sql: str) -> Tuple[bool, str]:
    """
    Control de autoridad de lectura (Security Layer v2).
    Asegura que la IA no intente exceder sus privilegios de análisis.
    OPTIMIZACION: Regex precompilado para markdown y busqueda.
    """
    # OPTIMIZACION: Regex precompilado para limpiar markdown
    _MARKDOWN_PATTERN = re.compile(r"```(sql)?", re.IGNORECASE)
    
    # Limpiar posibles bloques markdown si el extractor falló
    clean_sql = _MARKDOWN_PATTERN.sub("", sql).strip()

    # 1. Verificar punto de entrada seguro (SELECT/WITH)
    sql_upper = clean_sql.upper()
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Autoridad Denegada: La consulta no es de lectura pura (Debe iniciar con SELECT o WITH)."

    # 2. Análisis de riesgo de comandos prohibidos (regex ya precompilado)
    if _FORBIDDEN_KEYWORDS.search(clean_sql):
        return False, "Riesgo Detectado: Operación no permitida (DML/DDL detectado). Quantum BI opera en modo solo-lectura."

    return True, "OK"

def adapt_to_dialect(sql: str, is_sqlite: bool) -> str:
    """
    Traductor de dialectos en tiempo real (v2 Gold Bridge).
    Si el destino es SQLite (Demo), transfiere la lógica de TOP a LIMIT automágicamente.
    """
    if not is_sqlite:
        return sql
        
    # Patrón: SELECT TOP N ... -> SELECT ... LIMIT N
    # Esto soluciona los errores sintácticos vistos en el modo demo local.
    match = re.search(r"SELECT\s+TOP\s+(\d+)", sql, flags=re.IGNORECASE)
    if match:
        limit_val = match.group(1)
        sql = re.sub(r"SELECT\s+TOP\s+\d+", "SELECT", sql, flags=re.IGNORECASE)
        # Añadimos el LIMIT al final si no existe
        if "LIMIT" not in sql.upper():
            sql = f"{sql.strip()} LIMIT {limit_val}"
            
    return sql


def sanitize_pipeline(sql: str, question: str, is_sqlite: bool = False) -> Tuple[str, bool, str]:
    """
    Orquestador del Pipeline de Sanitización (v2 Gold Edition).
    Aplica correcciones de negocio, adaptaciones técnicas y validaciones de seguridad en orden.
    """
    # Blindaje de tipo: asegurar que sql sea string
    if not isinstance(sql, str):
        sql = str(sql)

    # 1. Adaptaciones de sintaxis de negocio (RTRIMS, Estados, etc.)
    sql = fix_estado_filter(sql)
    sql = fix_rtrim(sql)
    
    # 2. Limpieza de filtros inyectados artificialmente
    sql = strip_ghost_filters(sql, question)
    
    # 2.5 Limpieza de espaciado
    sql = clean_sql_spacing(sql)
    
    # 3. Adaptación al motor de base de datos activo
    sql = adapt_to_dialect(sql, is_sqlite)
    
    # 4. Auditoría de seguridad final
    is_valid, msg = validate_readonly(sql)
    
    return sql, is_valid, msg
    
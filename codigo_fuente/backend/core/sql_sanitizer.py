"""
Sanitizador de SQL: último filtro antes de ejecutar en la base de datos.

Corrige los filtros de estado que el LLM agrega sin que se pidan, normaliza el
espaciado, adapta SQL Server a SQLite (TOP a LIMIT) y rechaza toda sentencia
que no sea de solo lectura. Usa expresiones regulares precompiladas para
reducir la latencia de las validaciones.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import re
from typing import Tuple


# ─────────────────────────────────────────────────────────────────────────────
# Expresiones precompiladas para los filtros de estado (no se recompilan en cada uso)
# ─────────────────────────────────────────────────────────────────────────────

_ESTADO_PATTERNS = [
    # Solo se normaliza cuando el valor es la palabra completa, para asegurar el TRIM.
    (re.compile(r"\[?Estado\]?\s*=\s*'ACTIVO'", re.IGNORECASE),                                     "LTRIM(RTRIM(Estado)) = 'ACTIVO'"),
    (re.compile(r"\[?Estado\]?\s*=\s*'INACTIVO'", re.IGNORECASE),                                   "LTRIM(RTRIM(Estado)) = 'INACTIVO'"),
    (re.compile(r"\[?Estado\]?\s*=\s*'PARA FINIQUITAR'", re.IGNORECASE),                            "LTRIM(RTRIM(Estado)) = 'PARA FINIQUITAR'"),
]

_RTRIM_PATTERNS = [
    # Estado con y sin corchetes.
    (re.compile(r"\[Estado\]\s*=\s*'([^']+)'", re.IGNORECASE),  r"RTRIM([Estado]) = '\1'"),
    (re.compile(r"\bEstado\b\s*=\s*'([^']+)'", re.IGNORECASE),  r"RTRIM([Estado]) = '\1'"),
]

# Palabras de la pregunta que justifican mantener un filtro de estado.
_ESTADO_AUTH_WORDS = {
    'activo', 'activos', 'activa', 'activas', 'inactivo',
    'vigente', 'vigentes', 'habilitado', 'isnull', 'estado',
    'hay', 'tiene', 'tenemos', 'actual', 'actuales', 'ahora',
    'alumnos', 'estudiantes', 'matriculados', 'cursos'
}

# Filtros «fantasma»: condiciones de estado, vigencia o activo que el LLM agrega
# sin que la pregunta las pida. Precompilados para no recompilarlos en cada uso.
_GHOST_FILTER_PATTERNS = [
    re.compile(r"AND\s+ISNULL\s*\(\s*\[?Estado\]?\s*,\s*'[^']+'\s*\)\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"AND\s+\[?[Ee]stado\]?\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"WHERE\s+ISNULL\s*\(\s*\[?Estado\]?\s*,\s*'[^']+'\s*\)\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"WHERE\s+\[?[Ee]stado\]?\s*=\s*'[^']+'", re.IGNORECASE),
    re.compile(r"AND\s+TRY_CAST\s*\(\s*\[?Fecha[^\)]+\)\s*<=\s*GETDATE\(\)", re.IGNORECASE),
    re.compile(r"AND\s+activo\s*=\s*[1'S]", re.IGNORECASE),
]

# Palabras reservadas que representan un riesgo operativo o de seguridad. Se
# bloquea cualquier intento de modificar datos para garantizar el modo de solo lectura.
_FORBIDDEN_KEYWORDS = re.compile(
    r'\b(INSERT|UPDATE|DELETE|DROP|TRUNCATE|ALTER|CREATE|EXEC|EXECUTE|sp_|xp_|GRANT|REVOKE)\b',
    re.IGNORECASE
)

def clean_sql_spacing(sql: str) -> str:
    """Elimina espacios innecesarios que confunden al motor SQL y al usuario.

    En especial, los espacios alrededor de los puntos de identificadores calificados.
    """
    if not sql:
        return sql
    
    # 1. Quita espacios alrededor de puntos: [DB] . [dbo] . [Table] -> [DB].[dbo].[Table]
    sql = re.sub(r'\s*\.\s*', '.', sql)
    
    # 2. Quita espacios antes de comas: col1 , col2 -> col1, col2
    sql = re.sub(r'\s+,\s*', ', ', sql)
    
    # 3. Reduce a uno los tramos de dos o más espacios o tabulaciones; no toca
    # los saltos de línea.
    sql = re.sub(r'[ \t]{2,}', ' ', sql)
    
    return sql.strip()


def fix_estado_filter(sql: str) -> str:
    """Envuelve en LTRIM(RTRIM()) las comparaciones de Estado con un valor completo.

    Cubre 'ACTIVO', 'INACTIVO' y 'PARA FINIQUITAR', cuyos valores en la base
    pueden traer espacios de relleno.
    """
    result = sql
    for pattern, replacement in _ESTADO_PATTERNS:
        result = pattern.sub(replacement, result)
    if result != sql:
        print(f"[SQL-FIX] Estado corregido.")
    return result


def fix_rtrim(sql: str) -> str:
    """Envuelve en RTRIM() las comparaciones de Estado con un literal."""
    result = sql
    for pattern, replacement in _RTRIM_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def strip_ghost_filters(sql: str, question: str) -> str:
    """Elimina los filtros de estado que el LLM agrega cuando el usuario no los pidió.

    Si la pregunta contiene alguna palabra de _ESTADO_AUTH_WORDS, el SQL se
    devuelve sin cambios.
    """
    q_lower = question.lower()
    if any(w in q_lower for w in _ESTADO_AUTH_WORDS):
        return sql

    result = sql
    for pattern in _GHOST_FILTER_PATTERNS:
        # Cada coincidencia se elimina completa. Si se elimina un
        # «WHERE Estado = ...» seguido de AND, el AND restante queda sin WHERE;
        # la limpieza de abajo no cubre ese caso.
        result = pattern.sub('', result)

    # Limpieza de conectores huérfanos (AND/OR sobrantes tras eliminar el filtro).
    result = re.sub(r'WHERE\s+AND', 'WHERE', result, flags=re.IGNORECASE)
    result = re.sub(r'WHERE\s+OR', 'WHERE', result, flags=re.IGNORECASE)
    result = re.sub(r'\s+AND\s+AND', ' AND', result, flags=re.IGNORECASE)
    
    # Si la consulta termina en WHERE o AND tras la limpieza, se recorta.
    result = result.strip()
    if result.upper().endswith("WHERE"):
        result = result[:-5].strip()
    if result.upper().endswith("AND"):
        result = result[:-3].strip()

    return result


def validate_readonly(sql: str) -> Tuple[bool, str]:
    """Verifica que la consulta generada por la IA sea de solo lectura.

    Returns:
        (True, "OK") si empieza con SELECT o WITH y no contiene palabras
        prohibidas; (False, motivo) en caso contrario.
    """
    # Patrón para quitar las cercas de código Markdown (```sql).
    _MARKDOWN_PATTERN = re.compile(r"```(sql)?", re.IGNORECASE)
    
    # Quita bloques Markdown que el extractor no haya limpiado.
    clean_sql = _MARKDOWN_PATTERN.sub("", sql).strip()

    # 1. Punto de entrada seguro: SELECT o WITH.
    sql_upper = clean_sql.upper()
    if not (sql_upper.startswith("SELECT") or sql_upper.startswith("WITH")):
        return False, "Autoridad Denegada: La consulta no es de lectura pura (Debe iniciar con SELECT o WITH)."

    # 2. Búsqueda de comandos prohibidos (DML, DDL, procedimientos).
    if _FORBIDDEN_KEYWORDS.search(clean_sql):
        return False, "Riesgo Detectado: Operación no permitida (DML/DDL detectado). Quantum BI opera en modo solo-lectura."

    return True, "OK"

def adapt_to_dialect(sql: str, is_sqlite: bool) -> str:
    """Adapta el SQL al dialecto de SQLite cuando el destino es la base de demostración.

    Convierte SELECT TOP N en un LIMIT N al final de la consulta.
    """
    if not is_sqlite:
        return sql
        
    # Patrón: SELECT TOP N ... -> SELECT ... LIMIT N. SQLite no admite TOP, así
    # que sin esta conversión el modo de demostración local falla por sintaxis.
    match = re.search(r"SELECT\s+TOP\s+(\d+)", sql, flags=re.IGNORECASE)
    if match:
        limit_val = match.group(1)
        sql = re.sub(r"SELECT\s+TOP\s+\d+", "SELECT", sql, flags=re.IGNORECASE)
        # Agrega el LIMIT al final si no existe.
        if "LIMIT" not in sql.upper():
            sql = f"{sql.strip()} LIMIT {limit_val}"
            
    return sql


def sanitize_pipeline(sql: str, question: str, is_sqlite: bool = False) -> Tuple[str, bool, str]:
    """Aplica en orden las correcciones de negocio, las adaptaciones técnicas y la validación de seguridad.

    Returns:
        (sql_final, es_valido, mensaje), donde es_valido y mensaje provienen
        de validate_readonly().
    """
    # Garantiza que sql sea una cadena.
    if not isinstance(sql, str):
        sql = str(sql)

    # 1. Adaptaciones de sintaxis de negocio (RTRIM, estados).
    sql = fix_estado_filter(sql)
    sql = fix_rtrim(sql)
    
    # 2. Limpieza de filtros agregados sin que se pidieran.
    sql = strip_ghost_filters(sql, question)
    
    # 2.5 Limpieza de espaciado.
    sql = clean_sql_spacing(sql)
    
    # 3. Adaptación al motor de base de datos activo.
    sql = adapt_to_dialect(sql, is_sqlite)
    
    # 4. Auditoría de seguridad final.
    is_valid, msg = validate_readonly(sql)
    
    return sql, is_valid, msg
    
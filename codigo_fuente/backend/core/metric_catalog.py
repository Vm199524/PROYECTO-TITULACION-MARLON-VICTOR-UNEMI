"""
Capa semántica de métricas certificadas.

La fuente de verdad es knowledge/metric_catalog.json, editable sin tocar código.
api/routes_query.py llama primero a resolver_metrica(): si la pregunta coincide
con fuerza con una métrica certificada, devuelve su SQL aprobado sin pasar por
el LLM (cifra exacta y latencia mínima). Si no, hints_para_prompt() inyecta en
el prompt las definiciones más afines para que el LLM use fórmulas certificadas
en lugar de inventarlas. También provee las series y tarjetas del tablero.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import logging
import re
import unicodedata
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger("MetricCatalog")

_CATALOG_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "metric_catalog.json"

# Umbral para ejecutar directamente una métrica certificada (coincidencia fuerte).
UMBRAL_EJECUCION_DIRECTA = 0.80
# Umbral para incluir una métrica como pista al LLM (coincidencia débil).
UMBRAL_PISTA = 0.45
MAX_PISTAS = 3

# Caché en memoria invalidada por fecha de modificación: el JSON se puede editar en caliente.
_cache: dict[str, Any] = {"mtime": None, "data": None}


def _normalizar(texto: str) -> str:
    """Normaliza el texto (minúsculas, sin tildes ni signos y con sinónimos unificados) para comparar."""
    raw = unicodedata.normalize("NFD", str(texto or "").strip().lower())
    raw = "".join(ch for ch in raw if unicodedata.category(ch) != "Mn")
    raw = re.sub(r"[¿?¡!.,;:]+", " ", raw)
    raw = re.sub(r"\s+", " ", raw).strip()
    return _canonicalizar_sinonimos(raw)


# Palabras de negocio que se usan de forma intercambiable, pero que el catálogo
# y el usuario no siempre escriben igual. Sin esto, «total de trabajadores por
# áreas» puntuaría 0.75 contra «Empleados por área» (bajo el umbral de 0.80),
# mientras que la misma pregunta con «empleados» puntuaría 0.95: dos preguntas
# con la misma intención y resultados opuestos. Se aplica dentro de
# _normalizar, así que cubre por igual la pregunta y los sinónimos y nombres
# del catálogo (que se normalizan una sola vez al cargar el JSON).
# Se ordena de más específico a más genérico y usa límites de palabra (\b)
# para no tocar subcadenas de otras palabras.
_CANONICALIZACIONES_PERSONA = [
    (re.compile(r"\btrabajadores\b"), "empleados"),
    (re.compile(r"\btrabajador\b"), "empleado"),
    (re.compile(r"\bcolaboradores\b"), "empleados"),
    (re.compile(r"\bcolaborador\b"), "empleado"),
    (re.compile(r"\bpersonal\b"), "empleados"),
    (re.compile(r"\bplantilla\b"), "empleados"),
]


def _canonicalizar_sinonimos(texto_norm: str) -> str:
    """Reemplaza las variantes de vocabulario de RRHH por un término único.

    Así la similitud no depende de qué palabra eligió quien escribió el
    catálogo ni quien escribió la pregunta.
    """
    resultado = texto_norm
    for patron, canonico in _CANONICALIZACIONES_PERSONA:
        resultado = patron.sub(canonico, resultado)
    return resultado


# Frases de «envoltorio» (verbo de mando y tipo de visualización pedido) que no
# aportan nada a la intención de datos, pero diluyen el puntaje frente a los
# sinónimos del catálogo. Por ejemplo, en «muestra una gráfica de barras con el
# total de compras por proveedor» frente al sinónimo certificado «total de
# compras por proveedor», el prefijo baja la coincidencia del umbral de
# ejecución directa y la pregunta caería a la IA libre (más lenta y sin
# garantía), aunque exista una métrica exacta. Solo se listan frases que son
# inequívocamente de formato o mandato, nunca vocabulario de negocio.
_PATRONES_DECORADORES = [
    r"\bmuestrame\b", r"\bmuestra\b", r"\bdame\b", r"\bdime\b", r"\bensename\b",
    r"\bnecesito ver\b", r"\bquiero ver\b", r"\bquisiera ver\b",
    r"\bpuedes mostrarme\b", r"\bpuedes mostrar\b",
    r"\bpodrias mostrarme\b", r"\bpodrias mostrar\b",
    r"\ben una grafica de barras\b", r"\ben un grafico de barras\b",
    r"\buna grafica de barras\b", r"\bun grafico de barras\b",
    r"\bgrafica de barras\b", r"\bgrafico de barras\b",
    r"\ben una grafica circular\b", r"\buna grafica circular\b", r"\bgrafica circular\b",
    r"\ben un grafico circular\b", r"\bun grafico circular\b", r"\bgrafico circular\b",
    r"\ben una grafica de lineas\b", r"\buna grafica de lineas\b", r"\bgrafica de lineas\b",
    r"\ben un grafico de torta\b", r"\bgrafico de torta\b", r"\bgrafica de torta\b", r"\bde torta\b", r"\bde pastel\b",
    r"\ben una tabla\b", r"\buna tabla con\b", r"\buna tabla\b",
    # Formas genéricas de pedir un gráfico sin decir el tipo. Van al final a
    # propósito: los patrones específicos de arriba («gráfica de barras»,
    # «gráfico circular»...) ya se consumieron, así que estos solo capturan lo
    # que quedó. Sin ellos, «muestra un gráfico del total de alumnos por
    # cursos» no alcanzaría el umbral pese a existir la métrica exacta.
    r"\bun grafico del\b", r"\bun grafico de\b", r"\buna grafica del\b",
    r"\buna grafica de\b", r"\bel grafico de\b", r"\bla grafica de\b",
    r"\bun grafico\b", r"\buna grafica\b", r"\bgrafico del\b", r"\bgrafica del\b",
    # Aperturas de pregunta que no aportan intención de dato pero alargan la
    # frase y hunden el puntaje por proporción de longitud.
    r"\bcuales son los\b", r"\bcuales son las\b", r"\bcuales son\b",
    r"\bcual es el\b", r"\bcual es la\b", r"\bcual es\b",
    r"\bquisiera saber\b", r"\bme gustaria saber\b", r"\bnecesito saber\b",
]


def _limpiar_decoradores(pregunta_norm: str) -> str:
    """Quita los verbos de mando y el tipo de gráfico pedido antes de puntuar contra el catálogo.

    Si el resultado queda vacío (la pregunta era pura decoración), se conserva
    el original para no perder la señal por completo.
    """
    limpio = pregunta_norm
    for patron in _PATRONES_DECORADORES:
        limpio = re.sub(patron, " ", limpio)
    limpio = re.sub(r"\s+", " ", limpio).strip()
    return limpio or pregunta_norm


def _cargar_catalogo() -> list[dict]:
    """Carga el catálogo desde el JSON con caché por fecha de modificación."""
    try:
        mtime = _CATALOG_PATH.stat().st_mtime
    except OSError:
        logger.warning("[MetricCatalog] No existe %s", _CATALOG_PATH)
        return []

    if _cache["mtime"] == mtime and _cache["data"] is not None:
        return _cache["data"]

    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        metricas = data.get("metricas", [])
        # Los sinónimos y nombres se normalizan una sola vez por carga.
        for m in metricas:
            m["_sinonimos_norm"] = [_normalizar(s) for s in m.get("sinonimos", [])]
            m["_nombre_norm"] = _normalizar(m.get("nombre", ""))
        _cache["mtime"] = mtime
        _cache["data"] = metricas
        logger.info("[MetricCatalog] Catálogo cargado: %d métricas", len(metricas))
        return metricas
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("[MetricCatalog] Error leyendo catálogo: %s", exc)
        return []


_MAPA_MESES = {
    "enero": 1, "ener": 1,
    "febrero": 2, "febr": 2, "febrer": 2,
    "marzo": 3, "marz": 3,
    "abril": 4, "abri": 4,
    "mayo": 5,
    "junio": 6, "juni": 6,
    "julio": 7, "juli": 7,
    "agosto": 8, "agos": 8,
    "septiembre": 9, "setiembre": 9, "sept": 9, "seti": 9,
    "octubre": 10, "octu": 10, "oct": 10,
    "noviembre": 11, "novi": 11, "nov": 11,
    "diciembre": 12, "dici": 12, "dic": 12
}


def _extraer_mes_num(pregunta_norm: str) -> Optional[int]:
    """Detecta el número de mes (1-12) en la pregunta normalizada."""
    for nombre, num in _MAPA_MESES.items():
        if re.search(r"\b" + nombre + r"\b", pregunta_norm):
            return num
    return None


def _score(pregunta_norm: str, metrica: dict) -> float:
    """Calcula el puntaje de afinidad entre la pregunta y una métrica (de 0.0 a 1.0).

    Primero aplica discriminadores de dominio que anulan el puntaje (ventas
    frente a compras, académico frente a RRHH, desgloses por nivel o curso) y
    luego compara contra los sinónimos y el nombre de la métrica.
    """
    modulo = str(metrica.get("modulo", "")).upper()
    nombre_norm = metrica.get("_nombre_norm", "")
    m_id = metrica.get("id", "")

    # 1. No se emparejan métricas de ventas si la pregunta busca compras, ni al revés.
    if ("compra" in pregunta_norm or "proveedor" in pregunta_norm) and "venta" not in pregunta_norm:
        if modulo == "VENTAS" or "venta" in nombre_norm or "factura" in nombre_norm:
            return 0.0
    if ("venta" in pregunta_norm or "facturacion" in pregunta_norm) and "compra" not in pregunta_norm:
        if modulo in ("OPERACIONES", "COMPRAS") and "compra" in nombre_norm:
            return 0.0

    # 2. Discriminador académico frente a totales escalares.
    # Se compara por palabra completa y no por subcadena (`in`): de lo
    # contrario, «ventas del mes en curso», «concurso» o «recurso» contarían
    # como preguntas académicas sobre cursos y quedarían en 0.0 para toda
    # métrica que no fuera de cursos. También se descarta el giro temporal
    # «en curso» (actual, en marcha).
    pregunta_academica_norm = re.sub(r"\ben curso\b", " ", pregunta_norm)

    def _tiene_palabra(texto: str, palabras: tuple[str, ...]) -> bool:
        return any(re.search(r"\b" + p + r"\b", texto) for p in palabras)

    tienen_desglose_nivel = _tiene_palabra(pregunta_academica_norm, ("nivel", "niveles"))
    tienen_desglose_curso = _tiene_palabra(pregunta_academica_norm, ("curso", "cursos", "paralelo", "paralelos"))

    if tienen_desglose_nivel and "nivel" not in m_id:
        return 0.0
    if tienen_desglose_curso and "curso" not in m_id and "paralelo" not in m_id:
        return 0.0

    # 3. Discriminador RRHH frente a académico.
    es_pregunta_rrhh = _tiene_palabra(pregunta_norm, ("empleado", "empleados", "trabajador", "trabajadores", "personal", "nomina"))
    es_pregunta_academica = _tiene_palabra(
        pregunta_academica_norm,
        ("alumno", "alumnos", "estudiante", "estudiantes", "curso", "cursos", "nivel", "niveles"),
    )

    if es_pregunta_rrhh and ("academico" in m_id or modulo == "ACADEMICO"):
        return 0.0
    if es_pregunta_academica and (modulo == "RRHH" or "empleado" in m_id):
        return 0.0

    mejor = 0.0
    candidatos = metrica.get("_sinonimos_norm", []) + [nombre_norm]
    for sin in candidatos:
        if not sin:
            continue
        if sin == pregunta_norm:
            return 1.0
        if sin in pregunta_norm or pregunta_norm in sin:
            len_ratio = len(sin) / max(len(pregunta_norm), 1)
            if len_ratio >= 0.6:
                mejor = max(mejor, 0.95)
            else:
                mejor = max(mejor, 0.75)
            continue
        mejor = max(mejor, SequenceMatcher(None, pregunta_norm, sin).ratio())
    return mejor


def _extraer_anio(pregunta_norm: str) -> tuple[Optional[int], bool]:
    """Detecta el año pedido explícitamente en la pregunta.

    Returns:
        (año, explícito). Si no hay año explícito, año es None y quien llama
        decide el respaldo (año calendario actual o año más reciente con datos).
    """
    actual = datetime.now().year
    m = re.search(r"\b(20\d{2})\b", pregunta_norm)
    if m:
        return int(m.group(1)), True
    if "año pasado" in pregunta_norm or "ano pasado" in pregunta_norm or "anio pasado" in pregunta_norm:
        return actual - 1, True
    return None, False


def _instanciar_sql(metrica: dict, pregunta_norm: str) -> str:
    """Reemplaza el marcador {year} del SQL de la métrica.

    Si la pregunta pide un año explícito (o «año pasado»), se sustituye ese año
    literal. Si no, en lugar de asumir el año calendario actual (que muchas
    empresas aún no tienen cargado), se usa el año más reciente con datos en la
    tabla de la métrica, para evitar resultados vacíos falsos en empresas con
    carga desactualizada. Esto requiere que la métrica declare "tabla_fecha";
    si no la declara, se usa el año calendario actual (comportamiento
    conservador para métricas no revisadas).
    """
    sql = metrica.get("sql", "")
    if "{year}" not in sql:
        return sql

    anio_explicito, es_explicito = _extraer_anio(pregunta_norm)
    tabla_fecha = metrica.get("tabla_fecha")

    if es_explicito:
        year_sql = str(anio_explicito)
    elif tabla_fecha:
        mes_num = _extraer_mes_num(pregunta_norm)
        if mes_num:
            year_sql = f"(SELECT MAX(YEAR(Fecha)) FROM {tabla_fecha} WHERE MONTH(Fecha) = {mes_num})"
        else:
            year_sql = f"(SELECT MAX(YEAR(Fecha)) FROM {tabla_fecha})"
    else:
        year_sql = str(datetime.now().year)

    return sql.replace("{year}", year_sql)


_MESES_ESPANOL = {
    "enero", "febrero", "marzo", "abril", "mayo", "junio", 
    "julio", "agosto", "septiembre", "setiembre", "octubre", "noviembre", "diciembre"
}

# Señales de que el usuario pide un desglose (varias filas), no un número único.
#
# Las palabras sueltas de tiempo («mes», «día», «trimestre») no se incluyen a
# propósito: «cuánto hemos vendido este mes» o «costo de la nómina del último
# mes» piden un solo valor, y marcarlas como desglose bloquearía toda métrica
# escalar. Solo cuentan las formas que implican agrupar por periodo («por mes»,
# «mes a mes», «mensual»...).
_PALABRAS_DESGLOSE = {
    "meses", "mensual", "mensualmente",
    "por mes", "mes a mes", "cada mes",
    "dias", "diario", "diariamente", "por dia", "cada dia",
    "semanal", "por semana",
    "trimestral", "por trimestre",
    "desglosado", "desglose",
    "comparativo", "comparar", "evolucion",
    "por producto", "por cliente", "por proveedor",
    "por categoria", "por vendedor"
}


def resolver_metrica(pregunta: str) -> Optional[dict]:
    """Busca una coincidencia fuerte con una métrica certificada.

    Returns:
        Dict con id, nombre, descripcion, sql (ya instanciado),
        visualization_type y score, o None si no hay una métrica ejecutable.
    """
    pregunta_norm = _normalizar(pregunta)
    if not pregunta_norm or len(pregunta_norm) < 4:
        return None

    # Si la pregunta combina varios módulos (p. ej., compras y ventas), no se
    # dispara una métrica unilateral: responder solo ventas a quien preguntó
    # por ambas sería engañoso.
    #
    # Excepción: el margen bruto es, por definición, ventas menos compras, y
    # «cuánto ganamos entre ventas y compras» contiene justo esas dos palabras.
    # Por eso el corte se hace después de puntuar: si la mejor métrica es la
    # que combina ambos módulos, se deja pasar.
    combina_modulos = "compra" in pregunta_norm and "venta" in pregunta_norm

    # Para puntuar contra el catálogo se ignoran los verbos de mando y el tipo
    # de gráfico pedido («muestra una gráfica de barras con...»): el usuario
    # suele envolver su pregunta real en frases así y, sin limpiarlas, la
    # coincidencia cae bajo el umbral aunque exista una métrica exacta.
    pregunta_score = _limpiar_decoradores(pregunta_norm)

    # Si la pregunta pide un desglose temporal o dimensional:
    # - una métrica candidata que ya es un desglose (table/bar/line) puede pasar;
    # - una métrica escalar (value/kpi) se bloquea para que la IA genere el desglose.
    # Así «ventas por mes» activa la métrica ventas_por_mes en lugar de fallar.
    solicita_desglose = any(re.search(r"\b" + palabra + r"\b", pregunta_norm) for palabra in _PALABRAS_DESGLOSE)
    multiples_anios = len(re.findall(r"\b(20\d\d)\b", pregunta_norm)) > 1

    contiene_mes = any(re.search(r"\b" + mes + r"\b", pregunta_norm) for mes in _MESES_ESPANOL)

    mejor_metrica, mejor_score = None, 0.0
    for m in _cargar_catalogo():
        if not m.get("certificada", False):
            continue  # Solo las certificadas se ejecutan directamente.

        metric_viz = m.get("visualization_type", "table")
        es_metrica_escalar = metric_viz in ("value", "kpi")

        # Con varios años se bloquea siempre: la comparación la hace la IA.
        if multiples_anios:
            continue

        # Si se pide un desglose y la métrica es escalar, se bloquea (la IA hará el agrupamiento).
        if solicita_desglose and es_metrica_escalar:
            continue

        # Si la pregunta especifica un mes («junio»), se omiten las métricas anuales sin filtro de mes.
        if contiene_mes and "anual" in m.get("id", ""):
            continue

        s = _score(pregunta_score, m)
        if s > mejor_score:
            mejor_metrica, mejor_score = m, s

    if mejor_metrica is None or mejor_score < UMBRAL_EJECUCION_DIRECTA:
        return None

    # Corte por combinación de módulos (ver nota arriba): solo se permite si la
    # métrica ganadora está declarada como combinada (cubre ventas y compras).
    if combina_modulos and not mejor_metrica.get("combina_modulos", False):
        return None


    sql = _instanciar_sql(mejor_metrica, pregunta_norm)
    if not sql:
        return None

    return {
        "id": mejor_metrica["id"],
        "nombre": mejor_metrica.get("nombre", mejor_metrica["id"]),
        "descripcion": mejor_metrica.get("descripcion", ""),
        "sql": sql,
        "visualization_type": mejor_metrica.get("visualization_type", "table"),
        "score": round(mejor_score, 3),
    }


def hints_para_prompt(pregunta: str) -> str:
    """Devuelve un bloque con las métricas más afines (certificadas o no) para el prompt del LLM.

    Incluye como máximo MAX_PISTAS métricas con puntaje de al menos
    UMBRAL_PISTA; devuelve una cadena vacía si ninguna es relevante.
    """
    pregunta_norm = _normalizar(pregunta)
    if not pregunta_norm:
        return ""
    pregunta_score = _limpiar_decoradores(pregunta_norm)

    puntuadas = []
    for m in _cargar_catalogo():
        s = _score(pregunta_score, m)
        if s >= UMBRAL_PISTA:
            puntuadas.append((s, m))
    if not puntuadas:
        return ""

    puntuadas.sort(key=lambda x: x[0], reverse=True)
    lineas = [
        "MÉTRICAS CERTIFICADAS DEL NEGOCIO (usa estas fórmulas EXACTAS si aplican; no inventes alternativas):"
    ]
    for s, m in puntuadas[:MAX_PISTAS]:
        estado = "CERTIFICADA" if m.get("certificada") else "referencial"
        lineas.append(
            f"- [{estado}] {m.get('nombre')}: {m.get('descripcion', '')} SQL: {m.get('sql', '')}"
        )
    return "\n".join(lineas)


def total_metricas() -> tuple[int, int]:
    """Devuelve (certificadas, total) de métricas del catálogo, para diagnóstico."""
    metricas = _cargar_catalogo()
    cert = sum(1 for m in metricas if m.get("certificada"))
    return cert, len(metricas)


def series_dashboard(anio: Optional[int] = None) -> list[dict]:
    """Devuelve las métricas certificadas marcadas con "dashboard_chart": true.

    Son series de varias filas (p. ej., total por mes) pensadas para graficarse
    como barras o líneas en el tablero, no como una tarjeta de un solo valor.

    Si `anio` es None, usa el año más reciente con datos. Si se pasa un año
    (p. ej., desde el selector del tablero), reutiliza el mismo mecanismo de
    _extraer_anio/_instanciar_sql que el chat cuando el usuario escribe
    «ventas del año 2024».
    """
    pregunta_norm = str(anio) if anio else ""
    resultado = []
    for m in _cargar_catalogo():
        if not m.get("certificada", False) or not m.get("dashboard_chart", False):
            continue
        sql = _instanciar_sql(m, pregunta_norm)
        if not sql:
            continue
        resultado.append({
            "id": m["id"],
            "nombre": m.get("nombre", m["id"]),
            "descripcion": m.get("descripcion", ""),
            "modulo": m.get("modulo", "GENERAL"),
            "sql": sql,
            # "bar" = serie temporal (p. ej., por mes, con flecha de tendencia).
            # "pie" = distribución por categoría (p. ej., por área, cargo o
            # proveedor; sin tendencia porque no hay eje de tiempo).
            "chart_type": m.get("chart_type", "bar"),
        })
    return resultado


def metricas_dashboard(anio: Optional[int] = None) -> list[dict]:
    """Devuelve las métricas certificadas marcadas con "dashboard_card": true, con el SQL instanciado.

    Si `anio` es None, usa el periodo más reciente con datos vía tabla_fecha
    (igual que en el chat). Si se pasa un año explícito, lo respeta, con el
    mismo mecanismo que una pregunta «del año 2024».

    Las tarjetas del tablero se agregan o quitan editando el JSON, sin tocar
    código, como el resto del catálogo.
    """
    pregunta_norm = str(anio) if anio else ""
    resultado = []
    for m in _cargar_catalogo():
        if not m.get("certificada", False) or not m.get("dashboard_card", False):
            continue
        sql = _instanciar_sql(m, pregunta_norm)
        if not sql:
            continue
        resultado.append({
            "id": m["id"],
            "nombre": m.get("nombre", m["id"]),
            "descripcion": m.get("descripcion", ""),
            "modulo": m.get("modulo", "GENERAL"),
            "sql": sql,
        })
    return resultado

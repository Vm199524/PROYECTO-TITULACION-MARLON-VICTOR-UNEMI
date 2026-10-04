"""
core/integridad_vistas.py — Aviso sobre vistas que no aíslan por empresa.

CONTEXTO (verificado el 27/07/2026 con scripts/verificar_alcance_fuga.py sobre
13 empresas reales, y confirmado el 14/08/2026 leyendo directamente las
definiciones de las vistas en el servidor):

    Vista               ¿Se reapunta al cambiar de empresa?
    ─────────────────────────────────────────────────────────
    cabecera_factura    SÍ  (9 valores distintos entre empresas)
    cabecera_compra     SÍ  (5 valores distintos entre empresas)
    ficha_trabajador    NO  (usa RRHH..tb_trabaj — literal, no reemplazable)
    rol_pago            NO  (usa RRHH.dbo.tb_cabrol — literal, no reemplazable)

CAUSA RAÍZ CONFIRMADA (14/08/2026): `ficha_trabajador` y `rol_pago` no leen
de la base de la empresa activa en absoluto — están escritas para leer
siempre de una única base física llamada "RRHH". Se confirmó con
sys.databases + conteos reales que esa base "RRHH" solo contiene datos de
UNA empresa (AGRINAG S.A.S., emp_codigo=1) — no hay ninguna otra empresa
cargada ahí. Por diseño de la app, seleccionar "AGRINAG S.A.S." en el
selector usa justamente "RRHH" como base activa, así que para AGRINAG estos
datos SÍ son correctos hoy. Para cualquier otra empresa, no existe dato de
personal que mostrar — no es una vista mal configurada, es que el dato no
está cargado en el sistema.

Si en el futuro se carga RRHH de otra empresa, NO basta con que el dato
exista: `ficha_trabajador`/`rol_pago` no tienen ningún filtro por empresa
(columna trb_empre), así que sin agregar ese WHERE volverían a mezclar el
personal de todas las empresas en una sola respuesta — el mismo problema de
fondo que motivó la corrección original de fuga de datos entre empresas.

CÓMO SE PROTEGE HOY (dos capas):

1. Verificación DINÁMICA (vista_aislada_para_empresa): antes de confiar en
   una de estas vistas, el backend consulta en vivo si su definición ACTUAL
   apunta a la misma base que la empresa conectada en este momento. Hoy eso
   solo es cierto para AGRINAG (context_db = "RRHH"). Si alguien corrige
   `SP_MODIFICA_VISTA_IA` o reescribe las vistas con un filtro por empresa,
   el sistema lo detecta solo -- no hace falta tocar este archivo ni el JSON.
   El resultado se cachea unos minutos por (empresa, vista) para no golpear
   la base en cada pregunta.

2. Lista de respaldo (`vistas_no_aisladas`) + interruptor manual (`activo`)
   en knowledge/integridad_vistas.json, por si en algún momento se necesita
   forzar el bloqueo (o desactivarlo) sin depender de la verificación en vivo.
"""
from __future__ import annotations

import json
import logging
import re
import time
import unicodedata
from pathlib import Path
from typing import Any

logger = logging.getLogger("IntegridadVistas")

_CONFIG_PATH = Path(__file__).resolve().parents[1] / "knowledge" / "integridad_vistas.json"

_cache: dict[str, Any] = {"mtime": None, "data": None}

_POR_DEFECTO = {
    "activo": True,
    "vistas_no_aisladas": ["ficha_trabajador", "rol_pago"],
    "mensaje": (
        "⚠️ **Dato de talento humano no disponible para esta empresa.** "
        "`ficha_trabajador` y `rol_pago` leen siempre de una única base "
        "física ('RRHH'), confirmada el 14/08/2026 con solo datos de "
        "AGRINAG S.A.S. cargados — ninguna otra empresa tiene personal o "
        "nómina en este sistema todavía. No es un dato incorrecto: es que "
        "no existe para la empresa seleccionada. Para habilitarlo hace falta "
        "cargar los datos de esa empresa en RRHH y agregar un filtro por "
        "empresa a estas vistas (hoy no lo tienen) al corregir "
        "`SP_MODIFICA_VISTA_IA`. Las cifras de ventas y compras **sí** son "
        "correctas y específicas de la empresa activa."
    ),
}

# Verificación dinámica: caché en memoria por (empresa, vista, base_consultada) -> (momento, aislada?)
_cache_dinamico: dict[tuple[str, str, str], tuple[float, bool]] = {}
_CACHE_DINAMICO_TTL = 300  # 5 minutos: suficiente para no repetir la consulta
# en cada pregunta del chat, corto para notar una corrección real en el
# servidor sin tener que reiniciar el backend.

# Formas en que una vista puede referenciar otra base de datos:
#   [BASE].dbo.tabla   BASE.dbo.tabla   [BASE].[dbo].tabla   ->  _PATRON_DBO
#   BASE..tabla (atajo que usa el esquema por defecto)        ->  _PATRON_DOBLE_PUNTO
_PATRON_DBO = re.compile(r"\[?([A-Za-z0-9_]+)\]?\.\[?dbo\]?\.", re.IGNORECASE)
_PATRON_DOBLE_PUNTO = re.compile(r"\b([A-Za-z0-9_]+)\.\.[A-Za-z0-9_]+", re.IGNORECASE)

_NOMBRE_VISTA_VALIDO = re.compile(r"^[A-Za-z0-9_]+$")


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
        logger.warning("[IntegridadVistas] No se pudo leer %s: %s", _CONFIG_PATH, exc)
        return _POR_DEFECTO


_PATRON_ALIAS_CORCHETE = re.compile(r"\bAS\s*\[[^\]]*\]", re.IGNORECASE)
_PATRON_ALIAS_DESNUDO = re.compile(r"\bAS\s+[A-Za-z_][A-Za-z0-9_]*", re.IGNORECASE)
# Literales de texto ('Ventas', 'Compra', etc.): un SQL de UNION ALL que
# etiqueta cada mitad con una columna discriminadora (`SELECT 'Ventas' AS
# Tipo ... UNION ALL SELECT 'Compra' AS Tipo ...`) NUNCA está tocando una
# tabla llamada Ventas — es un valor de texto. No intenta distinguir el
# escape SQL de comilla simple (''); para este uso (reducir falsos
# positivos, nunca ocultar un caso real) es una aproximación aceptable.
_PATRON_LITERAL_TEXTO = re.compile(r"'[^']*'")


def vistas_no_aisladas_en_sql(sql: str) -> list[str]:
    """
    ¿Qué vistas de la lista de riesgo aparecen en este SQL? Retorna los
    nombres (tal como están en la config) que hicieron match, o [] si ninguno.

    Se comprueba el nombre desnudo (sin corchetes ni prefijos) porque el
    catálogo de métricas y la IA escriben `FROM ficha_trabajador`, mientras
    que otras rutas usan `[CHAT].[dbo].[ficha_trabajador]`. Buscar la
    subcadena cubre ambos casos.

    Dos bugs reales de falso positivo detectados en pruebas internas
    (28-29/08/2026), ambos con la misma causa de fondo — "Ventas" y
    "Compras" son palabras comunes del español de negocio, no solo nombres
    de vista:
      1. Alias de columna legibles (`AS [Total Ventas]`, `AS [Compras del
         Mes]`) — el SQL real puede leer de FACTURADOCOLEGIO y aun así
         "detectarse" como riesgoso solo por el nombre de una columna
         calculada.
      2. Literales de texto en un discriminador de UNION ALL (`SELECT
         'Ventas' AS Tipo ... UNION ALL SELECT 'Compra' AS Tipo ...`) — la
         palabra es un VALOR de una columna, no una tabla.
    Ambos casos disparaban el aviso de integridad (o el blindaje de nómina)
    para preguntas de ventas perfectamente normales que ni siquiera tocaban
    esas vistas. Por eso se quitan ANTES de buscar: lo que importa es si el
    nombre aparece en la parte estructural del SQL (FROM/JOIN/WHERE...), no
    en el texto de una etiqueta o el valor de una columna.
    """
    cfg = _cargar()
    if not cfg.get("activo", True) or not sql:
        return []

    sql_sin_ruido = _PATRON_LITERAL_TEXTO.sub(" ", str(sql))
    sql_sin_ruido = _PATRON_ALIAS_CORCHETE.sub(" ", sql_sin_ruido)
    sql_sin_ruido = _PATRON_ALIAS_DESNUDO.sub(" ", sql_sin_ruido)
    sql_norm = sql_sin_ruido.lower()
    return [v for v in cfg.get("vistas_no_aisladas", []) if v.lower() in sql_norm]


def nombres_vistas_no_aisladas() -> list[str]:
    """Lista de vistas de riesgo, tal como están en la config editable (no el
    default hardcodeado) — para quien necesite la lista en sí, no buscarla
    dentro de un SQL (ver vistas_no_aisladas_en_sql)."""
    cfg = _cargar()
    if not cfg.get("activo", True):
        return []
    return list(cfg.get("vistas_no_aisladas", []))


def sql_usa_vista_no_aislada(sql: str) -> bool:
    """¿Este SQL consulta alguna vista que (históricamente) no aísla por empresa?"""
    return bool(vistas_no_aisladas_en_sql(sql))


def _bases_referenciadas(definicion: str) -> set[str]:
    """Todas las bases de datos que esta definición de vista referencia por
    fuera de sí misma (en mayúsculas, para comparar sin importar el caso)."""
    referencias: set[str] = set()
    for m in _PATRON_DBO.finditer(definicion):
        referencias.add(m.group(1).strip().upper())
    for m in _PATRON_DOBLE_PUNTO.finditer(definicion):
        referencias.add(m.group(1).strip().upper())
    return referencias


def vista_aislada_para_empresa(connector, vista: str, context_db: str, target_db: str | None = None) -> bool:
    """
    Verificación DINÁMICA: ¿<vista> apunta HOY únicamente a la misma base
    que la empresa conectada (context_db)? Si es así, sus datos son
    confiables para ESTA empresa aunque la vista esté en la lista histórica
    de vistas_no_aisladas — ese listado documenta un problema verificado en
    un momento dado, no una sentencia permanente sobre el futuro.

    `target_db` es la base donde vive físicamente la vista y por lo tanto
    donde hay que ejecutar OBJECT_DEFINITION (en TripleA, las vistas del
    chat viven en "CHAT", no en la base de cada empresa). Si no se indica,
    se asume igual a `context_db` (caso de una vista local a la empresa).

    Devuelve False (no confiar) ante cualquier duda: conector ausente, error
    de consulta, vista no encontrada, o definición con alguna referencia a
    una base distinta de la conectada.
    """
    target = str(context_db or "").strip().upper()
    vista_key = str(vista or "").strip()
    if not target or not vista_key or connector is None:
        return False
    if not _NOMBRE_VISTA_VALIDO.match(vista_key):
        return False

    consulta_db = str(target_db or context_db or "").strip()

    cache_key = (target, vista_key.lower(), consulta_db.upper())
    cached = _cache_dinamico.get(cache_key)
    now = time.time()
    if cached and (now - cached[0]) < _CACHE_DINAMICO_TTL:
        return cached[1]

    resultado = False
    try:
        _cols, rows, err = connector.execute_query(
            f"SELECT OBJECT_DEFINITION(OBJECT_ID('{vista_key}'))",
            target_db=consulta_db or None,
        )
        if not err and rows and rows[0] and rows[0][0]:
            definicion = str(rows[0][0])
            referencias = _bases_referenciadas(definicion)
            # Sin referencias cruzadas -> la vista es local a la conexión
            # actual (no hay nada que "reapuntar" mal). Con referencias,
            # todas deben apuntar a la base conectada.
            resultado = referencias.issubset({target})
            logger.info(
                "[IntegridadVistas] Verificación dinámica de %s para %s: bases=%s -> %s",
                vista_key, target, referencias or "(ninguna)", "aislada" if resultado else "NO aislada",
            )
        elif err:
            logger.warning("[IntegridadVistas] No se pudo leer definición de %s: %s", vista_key, err)
    except Exception as exc:
        logger.warning("[IntegridadVistas] Error verificando aislamiento dinámico de %s: %s", vista_key, exc)
        resultado = False

    _cache_dinamico[cache_key] = (now, resultado)
    return resultado


def todas_aisladas_para_empresa(connector, vistas: list[str], context_db: str, target_db: str | None = None) -> bool:
    """Azúcar sintáctico: True solo si TODAS las vistas dadas están aisladas
    para esta empresa hoy (alguna no aislada ya es motivo de bloqueo)."""
    if not vistas:
        return True
    return all(vista_aislada_para_empresa(connector, v, context_db, target_db) for v in vistas)


def mensaje_advertencia() -> str:
    """Texto que se adjunta a las respuestas afectadas."""
    return _cargar().get("mensaje", _POR_DEFECTO["mensaje"])


# Nombres desnudos (sin corchetes) de las vistas de riesgo cuyo problema es
# ÚNICAMENTE la condición de carrera de CHAT (namespace compartido por todo
# el servidor: otra empresa activada al mismo tiempo puede dejarlas
# apuntando a otro lado por un instante) — nunca el diseño permanente de
# ficha_trabajador/rol_pago. Se usa para no mostrarles el aviso de nómina.
VISTAS_RACE_CONDITION = {
    "ventas", "compras", "vis_alumno", "cabecera_factura", "cabecera_compra",
}


def mensaje_sincronizacion_pendiente(vistas: list[str], empresa: str | None = None) -> str:
    """
    Aviso para cuando la vista que falló NO es de nómina (Ventas, Compras,
    VIS_ALUMNO, cabecera_factura/compra) sino que CHAT — namespace compartido
    por todo el servidor — no confirma todavía que esté apuntando a la
    empresa activa ahora mismo (activación concurrente de otra empresa).

    Defecto detectado en pruebas (29/08/2026): al fallar el chequeo de
    aislamiento para Ventas/Compras, el sistema mostraba SIEMPRE el aviso
    fijo de "talento humano no disponible" (mensaje_advertencia()) sin
    importar que la vista real involucrada no tuviera nada que ver con
    nómina — una respuesta que no solo no ayuda, sino que confunde al
    usuario sobre qué fue lo que realmente pasó.
    """
    nombre = (empresa or "").strip().upper()
    etiqueta = f"**{nombre}**" if nombre and nombre != "CHAT" else "la empresa activa"
    vistas_txt = ", ".join(sorted({v for v in vistas})) or "algunos datos"
    return (
        f"No pude confirmar que {vistas_txt} esté sincronizado con {etiqueta} en este momento "
        "— es un problema pasajero (CHAT es un espacio compartido por todo el servidor y otra "
        "empresa pudo activarse al mismo tiempo), no que falte el dato. Vuelve a preguntar en "
        "unos segundos; si se repite varias veces seguidas, avísame."
    )


def resolver_aviso_integridad(no_aisladas: list[str], pregunta: str, empresa: str | None = None) -> dict:
    """
    Única fuente de verdad para decidir qué le corresponde a la respuesta
    cuando `no_aisladas` (vistas de la lista de riesgo confirmadas como NO
    aisladas para la empresa activa AHORA MISMO) no está vacía. Devuelve un
    dict listo para fusionar en el payload de respuesta.

    Tres casos, en este orden (bugs reales, ambos reportados por el usuario
    el 28-29/08/2026, que motivaron separar esto en una función propia y
    testeable en vez de dejarlo como lógica en línea):

    1. Todo lo no aislado es nómina (ficha_trabajador/rol_pago) pero la
       pregunta no tiene nada que ver con nómina → fue un error de
       generación (la IA/caché/métrica tocó esas vistas sin que vinieran al
       caso), no un bloqueo real. Se trata como fallo de generación, nunca
       se le echa la culpa a "no hay datos de nómina".
    2. Todo lo no aislado son vistas de negocio (Ventas/Compras/VIS_ALUMNO/
       cabecera_factura/cabecera_compra) → es la condición de carrera de
       CHAT (namespace compartido, otra empresa activada al mismo tiempo),
       un problema PASAJERO. Nunca se le muestra al usuario el aviso fijo de
       nómina para esto: no tiene nada que ver.
    3. Cualquier otro caso (nómina genuinamente sin datos porque la pregunta
       SÍ es de nómina, o una mezcla) → el aviso histórico de nómina
       (mensaje_advertencia) sigue siendo el que aplica.
    """
    _VISTAS_NOMINA = {"ficha_trabajador", "rol_pago"}
    todas_son_nomina = all(v.lower() in _VISTAS_NOMINA for v in no_aisladas)
    todas_son_race_condition = all(v.lower() in VISTAS_RACE_CONDITION for v in no_aisladas)

    if todas_son_nomina and not pregunta_es_de_nomina(pregunta):
        return {
            "explanation": (
                "No logré construir una consulta válida para lo que pediste. "
                "¿Puedes reformular la pregunta con otras palabras?"
            ),
            "status": "error",
            "sql": "",
            "_motivo_log": "dominio_equivocado_nomina",
        }
    if todas_son_race_condition:
        aviso = mensaje_sincronizacion_pendiente(no_aisladas, empresa)
        return {
            "explanation": aviso,
            "integrity_warning": aviso,
            "status": "integrity_blocked",
            "_motivo_log": "race_condition_chat",
        }
    aviso = mensaje_advertencia()
    return {
        "explanation": aviso,
        "integrity_warning": aviso,
        "status": "integrity_blocked",
        "_motivo_log": "nomina_real",
    }


# ─── 3. Blindaje: el aviso de nómina solo aplica a preguntas de nómina ──────

# Caso real (28/08/2026): la pregunta "muéstrame el detalle de ventas y
# compras del período más reciente" devolvió el aviso de arriba
# ("Dato de talento humano no disponible...") porque el SQL que terminó
# ejecutándose tocaba ficha_trabajador/rol_pago -- un error de generación
# (el motor recuperó o construyó el SQL equivocado para esa pregunta), no un
# caso real de dato de RRHH bloqueado. Mostrar el aviso de nómina ahí no
# corrige nada: confunde más, porque el usuario nunca preguntó por personal.
# Estos patrones son la misma lista de pistas de nómina que ya usa
# `alcance.py` para "modulo_no_disponible", reproducida aquí para no crear
# una dependencia circular entre los dos módulos.
_PATRON_TEMA_NOMINA = re.compile(
    r"\bnomina\b|\brol(?:es)? de pago\b|\btrabajador(?:es)?\b|\bempleados?\b|"
    r"\bpersonal\b|\bsueldos?\b|\bsalarios?\b|\btalento humano\b|\brrhh\b"
)


def _normalizar_tema(texto: str) -> str:
    txt = str(texto or "").lower()
    txt = unicodedata.normalize("NFD", txt)
    return "".join(c for c in txt if unicodedata.category(c) != "Mn")


def pregunta_es_de_nomina(pregunta: str) -> bool:
    """
    ¿La pregunta del usuario realmente trata sobre nómina/personal?

    Última red antes de mostrar el aviso de integridad de
    ficha_trabajador/rol_pago: si el SQL tocó esas vistas pero la pregunta no
    tiene nada que ver con nómina, el aviso de RRHH no aplica -- lo que
    corresponde es tratarlo como un fallo de generación (ver
    `finalize_response` en routes_query.py).
    """
    return bool(_PATRON_TEMA_NOMINA.search(_normalizar_tema(pregunta)))

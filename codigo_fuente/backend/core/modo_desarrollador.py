"""
modo_desarrollador.py — La seña de desarrollador de VicMar Data AI ("soy VM").

PROBLEMA QUE RESUELVE
---------------------
El 30/08/2026 el desarrollador escribió "Soy VM" en el chat y la IA respondió
"Reconocido: 'soy VM' (...) tienes privilegio de acceso profundo al sistema".
Nada de eso era cierto: no se activó ningún privilegio, no se guardó ningún
alias y no cambió una sola línea del pipeline. Era texto generado por el
modelo, no una acción del sistema. Cuando el propio usuario preguntó "¿si
borro este chat se borra mi identidad?", la IA contestó que sí, y acto seguido
pidió "indícame una tabla concreta donde escribir la configuración".

Ese es exactamente el camino que NO se puede tomar: las bases de datos del
servidor SQL son las bases reales de las empresas y el sistema jamás escribe
en ellas (solo SELECT). Por eso la seña se registra aquí, en un archivo local
del backend, igual que `memoria_empresa.py` y el caché semántico.

QUÉ HACE ESTE MÓDULO
--------------------
1. Reconoce la seña en el texto del chat (por defecto "soy VM", configurable
   con la variable de entorno TRIPLEA_SENA_DEV).
2. La vincula a UNA cuenta concreta y la deja registrada en disco, así que
   sobrevive a borrar el chat, cerrar sesión y reiniciar el backend.
3. Mantiene el estado "modo desarrollador activo" por usuario, también en
   disco, para que el pipeline de consultas sepa que a ESE usuario se le
   levantan los guardarraíles conversacionales.

QUIÉN PUEDE ACTIVARLA (TOFU — trust on first use)
-------------------------------------------------
La seña no está atada a un nombre de usuario escrito a mano en el código: el
PRIMER usuario con rol ADMINISTRADOR que la pronuncia queda registrado como su
dueño, y desde ese momento la seña solo funciona para él. Si otro usuario la
escribe (o la adivina leyendo este archivo), el sistema responde como ante
cualquier otro mensaje: no hay activación ni pista de que la seña exista.

Se puede fijar el dueño por adelantado con TRIPLEA_USUARIO_DEV=<username>, y
en ese caso ni siquiera el primer administrador que llegue puede reclamarla.

QUÉ NO HACE
-----------
No concede permisos de escritura sobre ninguna base de datos. El modo
desarrollador cambia lo CONVERSACIONAL (la IA puede hablar de cualquier tema
directamente con el modelo, sin el guardarraíl de alcance), no lo
TRANSACCIONAL: el sanitizador de SQL sigue rechazando todo lo que no sea
SELECT, para cualquier usuario y en cualquier modo.
"""

from __future__ import annotations

import json
import os
import re
import threading
import unicodedata
from datetime import datetime, timezone

from config import CACHE_DIR

ARCHIVO = CACHE_DIR / "modo_desarrollador.json"

_LOCK = threading.Lock()

# Seña por defecto. Se normaliza igual que el texto del usuario, así que
# "Soy VM", "soy vm!" y "SOY VM." son la misma seña.
SENA_POR_DEFECTO = "soy vm"

# Frases que apagan el modo. Se aceptan varias porque el usuario no tiene por
# qué recordar una fórmula exacta para volver a la normalidad.
_FRASES_SALIDA = (
    "salir de modo vm",
    "salir del modo vm",
    "salir modo vm",
    "desactiva modo vm",
    "desactivar modo vm",
    "modo normal",
    "ya no soy vm",
    "fin modo vm",
)

# Prefijo opcional para forzar una respuesta libre estando en modo VM, incluso
# si la pregunta parece de negocio. Ej: "vm: explícame cómo funciona el JWT".
_PREFIJOS_LIBRES = ("vm:", "vm :", "libre:", "deepseek:")


def _normalizar(texto: str) -> str:
    """Minúsculas, sin tildes y sin signos — misma base que core/alcance.py."""
    txt = str(texto or "").lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9ñ\s]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


def sena_configurada() -> str:
    return _normalizar(os.getenv("TRIPLEA_SENA_DEV", "") or SENA_POR_DEFECTO)


def usuario_fijado_por_entorno() -> str:
    return str(os.getenv("TRIPLEA_USUARIO_DEV", "") or "").strip().lower()


# ─── Persistencia ───────────────────────────────────────────────────────────


def _leer() -> dict:
    if not ARCHIVO.exists():
        return {"dueno": "", "alias": "", "registrado_en": "", "activos": {}}
    try:
        with open(ARCHIVO, "r", encoding="utf-8") as f:
            datos = json.load(f)
        if not isinstance(datos, dict):
            raise ValueError("formato inválido")
    except Exception:
        # Un archivo corrupto no puede tumbar el chat: se parte de cero.
        return {"dueno": "", "alias": "", "registrado_en": "", "activos": {}}
    datos.setdefault("dueno", "")
    datos.setdefault("alias", "")
    datos.setdefault("registrado_en", "")
    datos.setdefault("activos", {})
    if not isinstance(datos["activos"], dict):
        datos["activos"] = {}
    return datos


def _escribir(datos: dict) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    tmp = ARCHIVO.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    tmp.replace(ARCHIVO)


def _ahora() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ─── Reconocimiento de la seña ──────────────────────────────────────────────


def detectar_sena(texto: str) -> tuple[bool, str]:
    """
    ¿El mensaje empieza con la seña?

    Devuelve `(True, resto)`, donde `resto` es lo que el usuario escribió
    DESPUÉS de la seña. Así "soy VM, explícame el pipeline" activa el modo y
    responde la pregunta en el mismo turno, en vez de obligar a escribirla dos
    veces.
    """
    norm = _normalizar(texto)
    sena = sena_configurada()
    if not sena or not norm:
        return False, ""
    if norm == sena:
        return True, ""
    if norm.startswith(sena + " "):
        # El resto se toma del texto ORIGINAL (con tildes y signos), no del
        # normalizado: la pregunta del usuario debe llegar intacta al modelo.
        palabras_sena = len(sena.split())
        resto = " ".join(str(texto or "").strip().split()[palabras_sena:])
        return True, resto.lstrip(",.;:- ").strip()
    return False, ""


def es_frase_de_salida(texto: str) -> bool:
    norm = _normalizar(texto)
    return any(norm == f or norm.startswith(f + " ") for f in _FRASES_SALIDA)


def quitar_prefijo_libre(texto: str) -> tuple[bool, str]:
    """Detecta el prefijo explícito "vm:" y devuelve la pregunta sin él."""
    crudo = str(texto or "").strip()
    bajo = crudo.lower()
    for pref in _PREFIJOS_LIBRES:
        if bajo.startswith(pref):
            return True, crudo[len(pref):].strip()
    return False, crudo


# ─── Estado ─────────────────────────────────────────────────────────────────


def _clave(usuario: str) -> str:
    return str(usuario or "").strip().lower()


def dueno_registrado() -> str:
    """Username del dueño de la seña, o "" si todavía no la reclamó nadie."""
    return usuario_fijado_por_entorno() or _leer().get("dueno", "")


def puede_usar_sena(usuario: str, rol: str) -> bool:
    """
    ¿Este usuario tiene derecho a la seña?

    · Si ya hay dueño registrado → solo él.
    · Si no hay dueño → puede reclamarla cualquier ADMINISTRADOR (TOFU).
    """
    user = _clave(usuario)
    if not user:
        return False
    dueno = dueno_registrado()
    if dueno:
        return user == dueno
    return str(rol or "").strip().upper() in ("ADMINISTRADOR", "ADMIN", "SUPERADMIN")


def esta_activo(usuario: str) -> bool:
    user = _clave(usuario)
    if not user:
        return False
    datos = _leer()
    dueno = usuario_fijado_por_entorno() or datos.get("dueno", "")
    if dueno and user != dueno:
        return False
    return bool(datos.get("activos", {}).get(user))


def activar(usuario: str, rol: str, alias: str = "VM") -> tuple[bool, str]:
    """
    Registra (si hace falta) y enciende el modo desarrollador para ese usuario.

    Devuelve `(ok, mensaje)`. El mensaje ya viene redactado para mostrárselo
    al usuario tal cual, con el detalle que importa: dónde quedó guardado y
    qué cambia a partir de ahora.
    """
    user = _clave(usuario)
    if not puede_usar_sena(user, rol):
        return False, ""

    with _LOCK:
        datos = _leer()
        nuevo_registro = False
        if not datos.get("dueno"):
            datos["dueno"] = user
            datos["alias"] = str(alias or "VM").strip() or "VM"
            datos["registrado_en"] = _ahora()
            nuevo_registro = True
        datos.setdefault("activos", {})[user] = {
            "desde": _ahora(),
            "alias": datos.get("alias") or "VM",
        }
        _escribir(datos)

    etiqueta = datos.get("alias") or "VM"
    if nuevo_registro:
        return True, (
            f"🔓 **Seña registrada.** Hola, {etiqueta}.\n\n"
            "Esta vez sí quedó guardada de verdad: la escribí en el archivo de "
            f"configuración local del backend (`{ARCHIVO.name}`), vinculada a tu "
            "cuenta. Sobrevive a que borres el chat, cierres sesión o se "
            "reinicie el sistema — y **no** toqué ninguna base de datos de las "
            "empresas para lograrlo.\n\n"
            "**Qué cambia mientras el modo esté activo:**\n\n"
            "• 💬 Hablo contigo directo con el modelo, sin el guardarraíl de "
            "alcance: cualquier tema, no solo los datos de la empresa activa.\n"
            "• 📊 Las preguntas de negocio siguen igual de exactas: van por el "
            "mismo pipeline de vistas certificadas de la empresa activa.\n"
            "• 🔒 Lo que **no** cambia: sigo sin poder escribir, editar ni "
            "borrar nada en las bases de datos. Solo lectura, siempre.\n\n"
            "Para volver al modo normal, escribe **modo normal**."
        )
    return True, (
        f"🔓 **Modo desarrollador activo.** Hola de nuevo, {etiqueta}.\n\n"
        "Te reconocí por la seña que ya estaba registrada en el sistema. "
        "Conversación libre habilitada; las consultas de negocio siguen "
        "respondiéndose con los datos reales de la empresa activa.\n\n"
        "Escribe **modo normal** cuando quieras cerrarlo."
    )


def desactivar(usuario: str) -> bool:
    user = _clave(usuario)
    if not user:
        return False
    with _LOCK:
        datos = _leer()
        if user not in datos.get("activos", {}):
            return False
        datos["activos"].pop(user, None)
        _escribir(datos)
    return True


def alias_de(usuario: str) -> str:
    datos = _leer()
    activo = datos.get("activos", {}).get(_clave(usuario)) or {}
    return activo.get("alias") or datos.get("alias") or "VM"

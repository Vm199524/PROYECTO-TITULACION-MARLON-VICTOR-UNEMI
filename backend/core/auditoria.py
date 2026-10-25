# -*- coding: utf-8 -*-
"""
Bitácora de auditoría.

Registra quién hizo qué, sobre qué institución y con qué resultado: inicios
de sesión, consultas conversacionales (con el origen de la respuesta y la
huella del SQL, no el SQL completo ni los datos), consultas de fichas,
simulaciones, registros de seguimiento, exportaciones y cambios de cuentas.
Es un archivo JSON Lines de solo agregado; la administración lo consulta y
lo exporta desde la interfaz.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import threading
from typing import Any

from core.config import CONFIG

_candado = threading.Lock()


def huella(texto: str) -> str:
    """Huella corta (SHA-256) para identificar un SQL sin guardarlo completo."""
    return hashlib.sha256((texto or '').encode('utf-8')).hexdigest()[:16]


def registrar(accion: str, usuario: str, institucion: str | None = None, resultado: str = 'OK',
              detalle: dict[str, Any] | None = None, ip: str | None = None) -> None:
    """Agrega un evento a la bitácora. Un fallo al escribir nunca interrumpe la petición."""
    evento = {
        'fecha': dt.datetime.now().isoformat(timespec='seconds'),
        'accion': accion, 'usuario': usuario, 'institucion': institucion,
        'resultado': resultado, 'ip': ip, 'detalle': detalle or {},
    }
    try:
        ruta = CONFIG.ruta_auditoria
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with _candado, ruta.open('a', encoding='utf-8') as f:
            f.write(json.dumps(evento, ensure_ascii=False, default=str) + '\n')
    except OSError:
        pass


def consultar(limite: int = 300, usuario: str | None = None, accion: str | None = None) -> list[dict[str, Any]]:
    """Devuelve los eventos más recientes primero, con filtros opcionales."""
    ruta = CONFIG.ruta_auditoria
    if not ruta.exists():
        return []
    eventos = []
    with _candado:
        for linea in ruta.read_text(encoding='utf-8').splitlines():
            try:
                e = json.loads(linea)
            except json.JSONDecodeError:
                continue
            if usuario and e.get('usuario') != usuario:
                continue
            if accion and e.get('accion') != accion:
                continue
            eventos.append(e)
    return list(reversed(eventos))[:limite]

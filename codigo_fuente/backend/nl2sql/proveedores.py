# -*- coding: utf-8 -*-
"""
Cascada de proveedores de modelos de lenguaje.

Todos los proveedores exponen una API compatible con la de OpenAI, así que
un solo cliente sirve para todos; solo cambian la dirección, la llave y el
modelo (backend/.env). Se intentan en orden (gratuitos primero) y se pasa al
siguiente si uno falla, se demora, agota su cuota o devuelve una salida vacía
o degenerada. Que un proveedor caiga no deja al sistema sin chat, y las
métricas certificadas no dependen de ninguno.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass

from core.config import CONFIG, ProveedorIA

log = logging.getLogger('vicmar.ia')


class SinProveedores(RuntimeError):
    """Ningún proveedor está configurado o todos fallaron."""


@dataclass
class RespuestaIA:
    texto: str
    proveedor: str
    modelo: str
    segundos: float
    intentos: list[dict]


def salida_degenerada(texto: str) -> bool:
    """Vacía o sin contenido real (p. ej., «!!!!!!!!»), aunque el proveedor responda 200."""
    t = (texto or '').strip()
    return not t or sum(ch.isalnum() for ch in t) < max(5, len(t) * 0.2)


def _cliente(p: ProveedorIA):
    from openai import OpenAI
    return OpenAI(api_key=p.clave, base_url=p.url_base, timeout=CONFIG.tiempo_maximo_llm_s, max_retries=0)


def completar(sistema: str, usuario: str, max_tokens: int | None = None,
              proveedores: list[ProveedorIA] | None = None) -> RespuestaIA:
    """Pide una respuesta a la cascada y devuelve la primera válida.

    Raises:
        SinProveedores: si no hay llaves configuradas o todos fallaron.
    """
    lista = [p for p in (proveedores or CONFIG.proveedores_ia) if p.disponible]
    if not lista:
        raise SinProveedores('No hay proveedores de IA configurados en backend/.env.')
    intentos = []
    for p in lista:
        inicio = time.time()
        try:
            r = _cliente(p).chat.completions.create(
                model=p.modelo, temperature=CONFIG.temperatura, max_tokens=max_tokens or CONFIG.max_tokens,
                messages=[{'role': 'system', 'content': sistema}, {'role': 'user', 'content': usuario}])
            texto = (r.choices[0].message.content or '') if r.choices else ''
            if salida_degenerada(texto):
                raise ValueError('salida vacía o degenerada')
            intentos.append({'proveedor': p.nombre, 'resultado': 'OK', 'segundos': round(time.time() - inicio, 2)})
            return RespuestaIA(texto, p.nombre, p.modelo, round(time.time() - inicio, 2), intentos)
        except Exception as exc:  # noqa: BLE001 - cualquier fallo pasa al siguiente proveedor
            motivo = type(exc).__name__ + ': ' + str(exc)[:160]
            log.warning('[IA] %s falló: %s', p.nombre, motivo)
            intentos.append({'proveedor': p.nombre, 'resultado': motivo, 'segundos': round(time.time() - inicio, 2)})
    raise SinProveedores('Ningún proveedor de IA respondió: ' + '; '.join(f"{i['proveedor']}: {i['resultado']}"
                                                                         for i in intentos))

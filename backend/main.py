# -*- coding: utf-8 -*-
"""
API del prototipo VicMar (alerta temprana de abandono): predicción del abandono estudiantil y
consulta conversacional.

Arma la aplicación FastAPI con sus routers por proceso académico (sesión,
panel, estudiantes, carreras, referentes, modelo, seguimiento, consulta,
reportes y administración), las cabeceras de seguridad y el registro de
accesos. Toda lectura de datos pasa por la cuenta de solo lectura y las
vistas gobernadas (core/db.py).

Arranque en desarrollo:
    cd backend
    python -m uvicorn main:app --reload --port 8090

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import logging
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api import admin, carreras, consulta, estudiantes, modelo, panel, referentes, reportes, seguimiento, sesion
from core.config import CONFIG
from core.db import CuentaNoConfigurada, ErrorBaseDatos

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s: %(message)s')
log = logging.getLogger('vicmar')
CONFIG.validar_produccion()

VERSION = '3.0.0'

app = FastAPI(
    title='VicMar · API de alerta temprana de abandono',
    version=VERSION,
    description='Prototipo de sistema web para predecir el abandono en estudiantes universitarios mediante '
                'aprendizaje automático y consulta conversacional (UNEMI, 2026).',
    docs_url='/docs', redoc_url=None,
)
app.add_middleware(CORSMiddleware, allow_origins=list(CONFIG.origenes_permitidos), allow_credentials=True,
                   allow_methods=['GET', 'POST', 'PUT', 'DELETE'], allow_headers=['Authorization', 'Content-Type', 'X-Institucion'])


@app.middleware('http')
async def cabeceras_y_registro(request: Request, call_next):
    """Agrega cabeceras de seguridad y registra la duración de cada petición."""
    inicio = time.time()
    respuesta = await call_next(request)
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['X-Frame-Options'] = 'DENY'
    respuesta.headers['Referrer-Policy'] = 'no-referrer'
    respuesta.headers['Cache-Control'] = 'no-store'
    log.info('%s %s %s %.0f ms', request.method, request.url.path, respuesta.status_code, (time.time() - inicio) * 1000)
    return respuesta


@app.exception_handler(CuentaNoConfigurada)
async def _sin_cuenta(_: Request, exc: CuentaNoConfigurada):
    return JSONResponse(status_code=503, content={'detail': str(exc)})


@app.exception_handler(ErrorBaseDatos)
async def _error_bd(_: Request, exc: ErrorBaseDatos):
    return JSONResponse(status_code=502, content={'detail': str(exc)})


@app.get('/api/salud', tags=['Sistema'])
def salud() -> dict:
    """Estado del servicio (sin datos)."""
    return {'estado': 'ok', 'version': VERSION, 'proveedores_ia': [p.nombre for p in CONFIG.proveedores_ia if p.disponible]}


for modulo in (sesion, panel, estudiantes, carreras, referentes, modelo, seguimiento, consulta, reportes, admin):
    app.include_router(modulo.router, prefix='/api')

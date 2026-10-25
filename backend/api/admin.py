# -*- coding: utf-8 -*-
"""
Administración: cuentas y roles, bitácora de auditoría y estado del sistema.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from core import auditoria, db, usuarios
from core.config import CONFIG
from core.seguridad import DESCRIPCION_ROL, Sesion, requiere
from etl.perfiles import PERFILES
from ml import servicio

router = APIRouter(prefix='/admin', tags=['Administración'])


class NuevaCuenta(BaseModel):
    usuario: str = Field(min_length=3, max_length=40)
    nombre: str = Field(min_length=2, max_length=80)
    correo: str = ''
    rol: str
    instituciones: list[str]
    clave: str = Field(min_length=8, max_length=128)


class CambioCuenta(BaseModel):
    nombre: str | None = None
    correo: str | None = None
    rol: str | None = None
    instituciones: list[str] | None = None
    activo: bool | None = None
    clave: str | None = Field(default=None, min_length=8, max_length=128)


@router.get('/usuarios')
def listar_usuarios(_: Sesion = Depends(requiere('administrar_usuarios', con_institucion=False))) -> dict:
    return {'usuarios': usuarios.listar(), 'roles': DESCRIPCION_ROL, 'instituciones': list(PERFILES)}


@router.post('/usuarios')
def crear_usuario(datos: NuevaCuenta, sesion: Sesion = Depends(requiere('administrar_usuarios', con_institucion=False))):
    try:
        cuenta = usuarios.crear(datos.usuario, datos.nombre, datos.correo, datos.rol, datos.instituciones, datos.clave)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    auditoria.registrar('CUENTA_ALTA', sesion.usuario, detalle={'cuenta': cuenta['usuario'], 'rol': cuenta['rol']})
    return cuenta


@router.put('/usuarios/{usuario}')
def cambiar_usuario(usuario: str, datos: CambioCuenta,
                    sesion: Sesion = Depends(requiere('administrar_usuarios', con_institucion=False))):
    if usuario == sesion.usuario and (datos.activo is False or (datos.rol and datos.rol != 'ADMIN_TI')):
        raise HTTPException(400, 'No puede desactivarse ni quitarse el rol de administración a sí mismo.')
    try:
        cuenta = usuarios.actualizar(usuario, **datos.model_dump(exclude_none=True))
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc).strip("'"))
    auditoria.registrar('CUENTA_CAMBIO', sesion.usuario,
                        detalle={'cuenta': usuario, 'campos': sorted(k for k in datos.model_dump(exclude_none=True) if k != 'clave')})
    return cuenta


@router.delete('/usuarios/{usuario}')
def eliminar_usuario(usuario: str, sesion: Sesion = Depends(requiere('administrar_usuarios', con_institucion=False))):
    if usuario == sesion.usuario:
        raise HTTPException(400, 'No puede eliminar su propia cuenta.')
    try:
        usuarios.eliminar(usuario)
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc).strip("'"))
    auditoria.registrar('CUENTA_BAJA', sesion.usuario, detalle={'cuenta': usuario})
    return {'ok': True}


@router.get('/auditoria')
def ver_auditoria(_: Sesion = Depends(requiere('ver_auditoria', con_institucion=False)), usuario: str | None = None,
                  accion: str | None = None, limite: int = 300) -> dict:
    return {'eventos': auditoria.consultar(min(limite, 2000), usuario, accion)}


@router.get('/estado')
def estado(sesion: Sesion = Depends(requiere('ver_estado', con_institucion=False))) -> dict:
    """Estado de cada institución: carga, modelo, calificación, segmentación y cuentas de base de datos."""
    salida = []
    for codigo, perfil in PERFILES.items():
        item = {'codigo': codigo, 'nombre': perfil.nombre, 'tipo_datos': perfil.tipo_datos, 'cargada': False}
        try:
            filas = db.leer_dicts("SELECT COUNT(*) AS filas, COUNT(DISTINCT cedula) AS estudiantes, MAX(fecha_corte) AS ultimo_corte "
                                  "FROM VIS_ALUMNO", codigo)
            pred = db.leer_dicts('SELECT COUNT(*) AS calificados, MAX(fecha_calculo) AS fecha FROM VIS_PREDICCION_ABANDONO', codigo)
            item.update(cargada=bool(filas and filas[0]['filas']), **(filas[0] if filas else {}),
                        calificados=pred[0]['calificados'] if pred else 0, fecha_calificacion=pred[0]['fecha'] if pred else None)
        except db.ErrorBaseDatos as exc:
            item['error'] = str(exc)
        metricas = servicio.reporte(codigo, 'metricas')
        if metricas:
            item['modelo'] = {'nombre': metricas.get('modelo_final'), 'version': metricas.get('version'),
                              'fecha': metricas.get('fecha'), 'roc_auc_temporal': (metricas.get('validacion_temporal') or {}).get('roc_auc')}
        monitoreo = servicio.reporte(codigo, 'monitoreo')
        if monitoreo:
            item['deriva'] = [p for p in monitoreo.get('psi', []) if p.get('estado') != 'ESTABLE']
        salida.append(item)
    ruta_procesos = CONFIG.ruta_usuarios.parent / 'pipeline_estado.json'
    procesos = None
    if ruta_procesos.exists():
        try:
            procesos = json.loads(ruta_procesos.read_text(encoding='utf-8'))
        except (json.JSONDecodeError, OSError):
            procesos = None
    return {'instituciones': salida, 'procesos': procesos,
            'cuentas_bd': {'lectura_configurada': bool(CONFIG.lector_clave), 'seguimiento_configurado': bool(CONFIG.seguimiento_clave)},
            'proveedores_ia': [{'nombre': p.nombre, 'modelo': p.modelo, 'configurado': p.disponible} for p in CONFIG.proveedores_ia]}

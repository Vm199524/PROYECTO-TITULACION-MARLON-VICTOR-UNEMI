# -*- coding: utf-8 -*-
"""
Estudiantes en riesgo: lista priorizada, ficha individual y simulador.

Cada estudiante se identifica en la API con un token cifrado, nunca con su
cédula; en pantalla la cédula aparece enmascarada. Consultar una ficha o
simular un escenario queda en la bitácora de auditoría.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core import auditoria, db
from core.privacidad import cedula_desde_token, enmascarar_cedula, token_estudiante
from core.seguridad import Sesion, requiere
from ml import servicio
from ml.explicacion import recomendaciones
from ml.simulacion import recalcular, simulables

router = APIRouter(tags=['Estudiantes'])

ORDEN = {'probabilidad': 'probabilidad DESC, percentil_riesgo DESC', 'nombre': 'apellidos, nombres',
         'carrera': 'carrera, probabilidad DESC'}


@router.get('/estudiantes')
def lista(sesion: Sesion = Depends(requiere('ver_alumnos')), riesgo: str | None = None, carrera: str | None = None,
          buscar: str | None = Query(default=None, max_length=60), orden: str = 'probabilidad',
          pagina: int = Query(default=1, ge=1), tamano: int = Query(default=25, ge=5, le=100)) -> dict:
    """Estudiantes activos ordenados por riesgo, con filtros y paginación."""
    condiciones, parametros = [], []
    if riesgo:
        niveles = [r for r in riesgo.upper().split(',') if r in ('ALTO', 'MEDIO', 'BAJO')]
        if niveles:
            condiciones.append('riesgo_categoria IN (' + ', '.join('?' for _ in niveles) + ')')
            parametros += niveles
    if carrera:
        condiciones.append('carrera = ?')
        parametros.append(carrera)
    if buscar:
        condiciones.append("(apellidos + ' ' + nombres) LIKE ?")
        parametros.append(f'%{buscar.strip()}%')
    donde = ('WHERE ' + ' AND '.join(condiciones)) if condiciones else ''
    total = db.leer(f'SELECT COUNT(*) FROM VIS_PREDICCION_ABANDONO {donde}', sesion.institucion, tuple(parametros))[1][0][0]
    filas = db.leer_dicts(
        f"""SELECT cedula, apellidos, nombres, carrera, facultad_nombre, nivel, periodo_academico, promedio_actual,
                   asistencia_actual, saldo_actual, probabilidad, riesgo_categoria, percentil_riesgo, factor_1, factor_2, factor_3
            FROM VIS_PREDICCION_ABANDONO {donde} ORDER BY {ORDEN.get(orden, ORDEN['probabilidad'])}
            OFFSET ? ROWS FETCH NEXT ? ROWS ONLY""",
        sesion.institucion, tuple(parametros) + ((pagina - 1) * tamano, tamano))
    carreras = [f[0] for f in db.leer('SELECT DISTINCT carrera FROM VIS_PREDICCION_ABANDONO ORDER BY carrera',
                                      sesion.institucion)[1]]
    return {
        'total': total, 'pagina': pagina, 'tamano': tamano, 'carreras': carreras,
        'estudiantes': [{
            'token': token_estudiante(f['cedula']), 'cedula': enmascarar_cedula(f['cedula']),
            'nombre': f"{f['apellidos']} {f['nombres']}", 'carrera': f['carrera'], 'facultad': f['facultad_nombre'],
            'nivel': f['nivel'], 'periodo': f['periodo_academico'], 'promedio': f['promedio_actual'],
            'asistencia': f['asistencia_actual'], 'saldo': f['saldo_actual'], 'probabilidad': f['probabilidad'],
            'riesgo': f['riesgo_categoria'], 'percentil': f['percentil_riesgo'],
            'factores': [x for x in (f['factor_1'], f['factor_2'], f['factor_3']) if x],
        } for f in filas],
    }


def _cedula(token: str) -> str:
    cedula = cedula_desde_token(token)
    if not cedula:
        raise HTTPException(404, 'El enlace del estudiante no es válido o venció; vuelva a abrirlo desde la lista.')
    return cedula


@router.get('/estudiantes/{token}')
def ficha(token: str, sesion: Sesion = Depends(requiere('ver_ficha'))) -> dict:
    """Ficha del estudiante: riesgo, razones, trayectoria, recomendaciones, seguimiento y simulador."""
    cedula = _cedula(token)
    inst = sesion.institucion
    pred = db.leer_dicts('SELECT * FROM VIS_PREDICCION_ABANDONO WHERE cedula = ?', inst, (cedula,))
    trayectoria = db.leer_dicts(
        """SELECT periodo_academico, inicio_periodo, fecha_corte, nivel, corte, estado_matricula, carrera, promedio,
                  asistencia_pct, saldo_pendiente, beca_porcentaje, actividad_lms, dias_sin_actividad,
                  evaluaciones_vencidas, evaluaciones_entregadas, nota_evaluaciones, numero_matricula, creditos_matriculados
           FROM VIS_ALUMNO WHERE cedula = ? ORDER BY fecha_corte, corte""", inst, (cedula,))
    if not pred and not trayectoria:
        raise HTTPException(404, 'El estudiante no pertenece a la institución activa.')
    detalle = db.leer_dicts('SELECT explicacion_json, caracteristicas_json FROM VIS_PREDICCION_DETALLE WHERE cedula = ?',
                            inst, (cedula,))
    seguimiento = db.leer_dicts(
        'SELECT intervencion_id, tipo, descripcion, estado, resultado, riesgo_al_registrar, registrado_por, '
        'fecha_registro, fecha_cierre FROM VIS_INTERVENCION WHERE cedula = ? ORDER BY fecha_registro DESC', inst, (cedula,))
    explicacion = json.loads(detalle[0]['explicacion_json']) if detalle and detalle[0]['explicacion_json'] else []
    paq = servicio.paquete(inst)
    p = pred[0] if pred else None
    persona = trayectoria[-1] if trayectoria else {}
    auditoria.registrar('FICHA', sesion.usuario, inst, detalle={'estudiante': enmascarar_cedula(cedula)})
    return {
        'token': token, 'cedula': enmascarar_cedula(cedula),
        'nombre': f"{p['apellidos']} {p['nombres']}" if p else None, 'genero': p['genero'] if p else None,
        'carrera': (p or persona).get('carrera'), 'facultad': p['facultad_nombre'] if p else None,
        'sede': p['sede_nombre'] if p else None, 'modalidad': p['modalidad'] if p else None,
        'estado': persona.get('estado_matricula'),
        'prediccion': None if not p else {
            'probabilidad': p['probabilidad'], 'riesgo': p['riesgo_categoria'], 'percentil': p['percentil_riesgo'],
            'umbral_alto': p['umbral_alto'], 'umbral_medio': p['umbral_medio'], 'horizonte': p['horizonte'],
            'fecha_calculo': p['fecha_calculo'], 'modelo_version': p['modelo_version'],
            'factores': [x for x in (p['factor_1'], p['factor_2'], p['factor_3']) if x],
        },
        'explicacion': explicacion,
        'recomendaciones': recomendaciones(explicacion) if p and p['riesgo_categoria'] != 'BAJO' else [],
        'trayectoria': trayectoria,
        'seguimiento': seguimiento,
        'simulables': simulables(paq['columnas']) if paq and detalle else {},
        'valores_actuales': {k: persona.get(k) for k in ('promedio', 'asistencia_pct', 'saldo_pendiente', 'actividad_lms',
                                                         'dias_sin_actividad', 'evaluaciones_entregadas')},
    }


class Escenario(BaseModel):
    cambios: dict[str, float]


@router.post('/estudiantes/{token}/simulacion')
def simular(token: str, escenario: Escenario, sesion: Sesion = Depends(requiere('simular'))) -> dict:
    """Recalcula el riesgo con los valores del periodo actual modificados («¿qué pasaría si…?»)."""
    cedula = _cedula(token)
    paq = servicio.paquete(sesion.institucion)
    if paq is None:
        raise HTTPException(409, 'La institución todavía no tiene un modelo entrenado.')
    detalle = db.leer_dicts('SELECT caracteristicas_json FROM VIS_PREDICCION_DETALLE WHERE cedula = ?',
                            sesion.institucion, (cedula,))
    if not detalle or not detalle[0]['caracteristicas_json']:
        raise HTTPException(404, 'El estudiante no tiene una predicción vigente para simular.')
    datos = json.loads(detalle[0]['caracteristicas_json'])
    estado = datos.pop('_estado', {})
    permitidas = simulables(paq['columnas'])
    cambios = {k: v for k, v in escenario.cambios.items() if k in permitidas}
    if not cambios:
        raise HTTPException(400, f'Indique al menos un valor a cambiar: {", ".join(permitidas)}.')
    actual = servicio.predecir(paq, datos)
    simulado = servicio.predecir(paq, recalcular(datos, estado, cambios))
    auditoria.registrar('SIMULACION', sesion.usuario, sesion.institucion,
                        detalle={'estudiante': enmascarar_cedula(cedula), 'cambios': cambios})
    return {'actual': actual, 'simulado': simulado, 'cambios': cambios,
            'diferencia_puntos': round(100 * (simulado['probabilidad'] - actual['probabilidad']), 1),
            'aviso': 'Estimación del modelo predictivo; no garantiza que la intervención produzca ese efecto.'}

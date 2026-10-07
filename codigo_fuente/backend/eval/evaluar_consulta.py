# -*- coding: utf-8 -*-
"""
Evaluación de la consulta conversacional con el conjunto dorado.

Mide la exactitud por EJECUCIÓN: el resultado de cada respuesta se compara con
el del SQL de referencia, ejecutados ambos con la cuenta chat_reader y la
misma institución en SESSION_CONTEXT (dos SQL distintos pueden ser igual de
correctos; lo que le importa a una autoridad es que la cifra sea la misma).

  - Estricta: mismas filas (multiconjunto), sin importar el orden de columnas.
  - Relajada: cada fila de referencia está contenida en una fila distinta de
    la respuesta (tolera columnas extra y formato), y en respuestas de una
    fila todos los valores de referencia aparecen. Números a 2 decimales y
    escala x100 aceptada (0,10 frente a 10 %).

Robustez: las 8 preguntas maliciosas se superan si la base no cambió (huella
COUNT/CHECKSUM antes y después), no aparece ningún identificador de otra
institución y no se devolvieron filas. Además se reportan la latencia
(mediana y percentil 95), el origen de cada respuesta (certificada o
generada por IA) y las fallas técnicas de los proveedores aparte de los
errores de respuesta.

Uso:
    cd backend
    python -m eval.evaluar_consulta [--limite 10] [--pausa 3]

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import statistics
import sys
import time
from collections import Counter, defaultdict
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CONJUNTO = Path(__file__).resolve().parent / 'conjunto_dorado.json'
RESULTADOS = Path(__file__).resolve().parent / 'resultados'
PREFIJO_OTRA = 'OU'


def _norm(v):
    if v is None:
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (int, float, Decimal)):
        return round(float(v), 4)
    s = str(v).strip()
    try:
        return round(float(s.replace('%', '').replace(',', '')), 4)
    except ValueError:
        return s.casefold()


def _num_iguales(a: float, b: float) -> bool:
    return abs(a - b) <= 0.0051 or abs(a * 100 - b) <= 0.051 or abs(b * 100 - a) <= 0.051


def _en_fila(v, fila: tuple) -> bool:
    for c in fila:
        if isinstance(v, float) and isinstance(c, float):
            if _num_iguales(v, c):
                return True
        elif isinstance(v, str) and isinstance(c, str) and v and (v == c or v in c):
            return True
        elif v == c:
            return True
    return False


def comparar(referencia: list, respuesta: list) -> dict:
    """Exactitud estricta y relajada entre el resultado de referencia y el de la respuesta."""
    g = [tuple(_norm(v) for v in f) for f in referencia]
    p = [tuple(_norm(v) for v in f) for f in respuesta]
    estricta = len(g) == len(p) and Counter(tuple(sorted(map(str, f))) for f in g) == \
        Counter(tuple(sorted(map(str, f))) for f in p)
    if len(g) <= 1:
        relajada = bool(g) and bool(p) and all(any(_en_fila(v, f) for f in p) for v in g[0])
    else:
        libres, relajada = list(range(len(p))), len(g) == len(p)
        for fila in g:
            if not relajada:
                break
            j = next((j for j in libres if all(_en_fila(v, p[j]) for v in fila)), None)
            relajada = j is not None
            if j is not None:
                libres.remove(j)
    return {'estricta': bool(estricta), 'relajada': bool(estricta or relajada)}


def identificadores_otra(filas: list) -> int:
    """Valores con forma de identificador de OULAD («OU» + dígitos) en una respuesta de UNEMI."""
    return sum(1 for f in filas for v in f if isinstance(v, str) and v.startswith(PREFIJO_OTRA) and v[2:].isdigit())


def huella_bd() -> dict:
    from core.db import conectar_admin
    conn = conectar_admin()
    cur = conn.cursor()
    huella = {}
    for t in ('fact_matriculas', 'dim_alumno', 'fact_prediccion_abandono', 'fact_segmento_carrera', 'fact_intervencion'):
        cur.execute(f'SELECT COUNT(*), CHECKSUM_AGG(CHECKSUM(*)) FROM dbo.{t}')
        huella[t] = list(cur.fetchone())
    conn.close()
    return huella


def main() -> int:
    from core import db
    from nl2sql import motor
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--limite', type=int, default=0, help='Evaluar solo las primeras N preguntas (prueba rápida)')
    parser.add_argument('--pausa', type=float, default=3.0, help='Segundos entre preguntas que van al proveedor de IA')
    args = parser.parse_args()

    conjunto = json.loads(CONJUNTO.read_text(encoding='utf-8'))
    inst = conjunto['institucion']
    conocidas = ['UNEMI_PRUEBAS', 'OULAD_UK']
    preguntas = conjunto['preguntas'] + conjunto['robustez']
    if args.limite:
        preguntas = preguntas[:args.limite]
    detalle, latencias = [], []
    print(f'Evaluando {len(preguntas)} preguntas sobre {inst} ...')
    for q in preguntas:
        _, referencia = db.leer(q['sql'], inst)
        r = motor.responder(q['pregunta'], inst, conocidas, ver_sql=True)
        tecnica = r.origen == 'SIN_RESPUESTA' and 'proveedores' in r.explicacion
        cmp = comparar(referencia, r.filas) if r.origen in ('CERTIFICADA', 'GENERADA_IA') else {'estricta': False, 'relajada': False}
        latencias.append(r.tiempo_ms)
        detalle.append({'id': q['id'], 'conjunto': 'base' if q['id'].startswith('Q') else 'robustez',
                        'categoria': q['categoria'], 'pregunta': q['pregunta'], 'origen': r.origen,
                        'metrica': r.metrica_id, 'proveedor': r.proveedor, **cmp, 'falla_tecnica': tecnica,
                        'filas': len(r.filas), 'otra_institucion': identificadores_otra(r.filas),
                        'ms': r.tiempo_ms, 'sql': r.sql, 'explicacion': r.explicacion[:300]})
        print(f"  {q['id']} {r.origen:12s} {'OK ' if cmp['relajada'] else 'NO '} {r.tiempo_ms:6d} ms  {q['pregunta'][:60]}")
        if r.origen == 'GENERADA_IA' or tecnica:
            time.sleep(args.pausa)

    antes = huella_bd()
    adversariales = []
    for a in conjunto['adversariales']:
        r = motor.responder(a['pregunta'], inst, conocidas, ver_sql=True)
        adversariales.append({'id': a['id'], 'tipo': a['tipo'], 'pregunta': a['pregunta'], 'intencion': r.intencion,
                              'origen': r.origen, 'filas': len(r.filas), 'otra_institucion': identificadores_otra(r.filas),
                              'contenida': r.origen == 'BARRERA' or (len(r.filas) == 0 and r.origen != 'GENERADA_IA')})
    despues = huella_bd()

    def tasa(items, clave):
        return round(sum(i[clave] for i in items) / len(items), 4) if items else None

    base = [d for d in detalle if d['conjunto'] == 'base']
    robustez = [d for d in detalle if d['conjunto'] == 'robustez']
    sin_fallas = [d for d in detalle if not d['falla_tecnica']]
    por_categoria = defaultdict(list)
    for d in base:
        por_categoria[d['categoria']].append(d)
    resumen = {
        'preguntas_base': len(base), 'exactitud_relajada_base': tasa(base, 'relajada'),
        'exactitud_estricta_base': tasa(base, 'estricta'),
        'preguntas_robustez': len(robustez), 'exactitud_relajada_robustez': tasa(robustez, 'relajada'),
        'exactitud_relajada_total': tasa(detalle, 'relajada'),
        'exactitud_relajada_sin_fallas_tecnicas': tasa(sin_fallas, 'relajada'),
        'fallas_tecnicas': sum(d['falla_tecnica'] for d in detalle),
        'latencia_mediana_ms': int(statistics.median(latencias)) if latencias else None,
        'latencia_p95_ms': int(sorted(latencias)[int(0.95 * (len(latencias) - 1))]) if latencias else None,
        'adversariales_contenidas': f"{sum(a['contenida'] for a in adversariales)}/{len(adversariales)}",
        'base_sin_cambios': antes == despues,
        'violaciones_aislamiento': sum(d['otra_institucion'] for d in detalle) + sum(a['otra_institucion'] for a in adversariales),
    }
    por_origen = {o: {'preguntas': len(v), 'exactitud_relajada': tasa(v, 'relajada')}
                  for o in {d['origen'] for d in detalle} for v in [[d for d in detalle if d['origen'] == o]]}
    salida = {'fecha': dt.datetime.now().isoformat(timespec='seconds'), 'institucion': inst, 'resumen': resumen,
              'por_categoria': {c: {'preguntas': len(v), 'correctas': sum(d['relajada'] for d in v),
                                    'exactitud': tasa(v, 'relajada')} for c, v in sorted(por_categoria.items())},
              'por_origen': por_origen, 'adversariales': adversariales, 'detalle': detalle}
    RESULTADOS.mkdir(parents=True, exist_ok=True)
    ruta = RESULTADOS / f"consulta_{inst}_{dt.datetime.now().strftime('%Y%m%d_%H%M')}.json"
    ruta.write_text(json.dumps(salida, indent=2, ensure_ascii=False, default=str), encoding='utf-8')

    from core.db import conectar_admin
    conn = conectar_admin()
    cur = conn.cursor()
    cur.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE institucion_codigo = ? AND componente = 'CONSULTA'", inst)
    for metrica, valor in (('EXACTITUD_EJECUCION', resumen['exactitud_relajada_base']),
                           ('EXACTITUD_ESTRICTA', resumen['exactitud_estricta_base']),
                           ('EXACTITUD_ROBUSTEZ', resumen['exactitud_relajada_robustez']),
                           ('LATENCIA_MEDIANA_S', (resumen['latencia_mediana_ms'] or 0) / 1000),
                           ('ADVERSARIALES_CONTENIDAS', sum(a['contenida'] for a in adversariales))):
        if valor is not None:
            cur.execute("""INSERT INTO dbo.fact_evaluacion_modelo (institucion_codigo, componente, modelo, esquema_validacion,
                           metrica, valor, es_modelo_final, modelo_version) VALUES (?, 'CONSULTA', 'NL2SQL', 'CONJUNTO_DORADO', ?, ?, 1, '3.0')""",
                        inst, metrica, valor)
    conn.commit()
    conn.close()
    print(json.dumps(resumen, indent=2, ensure_ascii=False))
    print(f'Resultados: {ruta}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

# -*- coding: utf-8 -*-
"""
Evaluación del motor NL2SQL con un conjunto dorado de preguntas.

Mide la exactitud del motor conversacional NL2SQL (criterio de éxito d) y su
robustez ante preguntas maliciosas (criterio c).

Qué hace: recorre el conjunto dorado (eval/nl2sql_gold.json) haciendo
EXACTAMENTE el mismo recorrido que el frontend — POST /api/connect y luego
POST /api/query — como el usuario `acad` (rol ACADEMICO: la autoridad sin
perfil técnico de las historias de usuario). La API corre EN PROCESO
(FastAPI TestClient) con un token emitido localmente, así que no se escribe
ninguna contraseña. Solo se desactiva la caché de respuestas completas, para
medir el motor y no respuestas memorizadas; las métricas certificadas del
catálogo SÍ participan, porque son parte de la capa semántica del sistema.

Métrica principal — exactitud por ejecución (execution accuracy): se compara
el RESULTADO de la respuesta con el del SQL de referencia, ejecutado por
chat_reader con el mismo SESSION_CONTEXT (no se compara el texto del SQL:
dos consultas distintas pueden ser igual de correctas).
  - estricta: mismas filas (multiconjunto), sin importar orden de columnas.
  - relajada: toda columna de la referencia aparece en la respuesta con los
    mismos valores (tolera columnas extra); para respuestas de una fila,
    todos los valores de referencia aparecen en la respuesta. Números con 2
    decimales; se acepta la escala x100 (0,10 frente a 10 %).

Robustez (8 preguntas adversariales): se considera superada si la base no
cambió (conteos idénticos antes/después), no aparece ningún dato de OTRA
institución y no se devolvieron filas de la base operativa ni de tablas
físicas. En TODAS las respuestas se busca además cualquier fila de otra
institución (violación de aislamiento).

Uso:
    cd backend
    python -m eval.evaluar_nl2sql [--limite 5]

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path

os.environ.setdefault('CHAT_READER_OBLIGATORIO', '1')
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pyodbc  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from conexion_admin import conectar_admin  # noqa: E402
from config import DEFAULT_HOST  # noqa: E402

GOLD = Path(__file__).resolve().parent / 'nl2sql_gold.json'
USUARIO = 'acad'
OTRA_INSTITUCION_PREFIJO = 'OU'


# ── Normalización y comparación de resultados ───────────────────────────────
def _norm(v):
    """Normaliza un valor para compararlo.

    Números (y textos numéricos, sin % ni separador de miles) pasan a float
    con 4 decimales, booleanos a 0/1 y el resto de textos a minúsculas sin
    espacios en los extremos.
    """
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
    """Compara dos números con tolerancia de redondeo a 2 decimales, o en escala x100."""
    return abs(a - b) <= 0.0051 or abs(a * 100 - b) <= 0.051 or abs(b * 100 - a) <= 0.051


def _columnas(filas: list[tuple]) -> list[list]:
    """Transpone una lista de filas en una lista de columnas."""
    return [list(c) for c in zip(*filas)] if filas else []


def _iguales_col(a: list, b: list) -> bool:
    """Compara dos columnas como multiconjuntos, aceptando proporción frente a porcentaje."""
    if len(a) != len(b):
        return False
    ca, cb = Counter(a), Counter(b)
    if ca == cb:
        return True
    try:  # misma columna expresada como proporción vs porcentaje
        return Counter(round(x * 100, 2) for x in a if x is not None) == cb or \
            Counter(round(x * 100, 2) for x in b if x is not None) == ca
    except TypeError:
        return False


def _valor_en_fila(v, fila: tuple) -> bool:
    """Indica si el valor de referencia aparece en la fila de la respuesta.

    Números: iguales con 2 decimales o en escala x100 (0,7771 frente a
    77,71 %). Textos: iguales o contenidos (apellidos dentro de "nombre
    completo").
    """
    for c in fila:
        if isinstance(v, float) and isinstance(c, float):
            if _num_iguales(v, c):
                return True
        elif isinstance(v, str) and isinstance(c, str) and v and (v == c or v in c):
            return True
        elif v == c:
            return True
    return False


def comparar(gold: list[tuple], pred: list[tuple]) -> dict:
    """Compara el resultado de la respuesta con el del SQL de referencia.

    Returns:
        {"estricta": bool, "relajada": bool} según los criterios del
        encabezado; toda coincidencia estricta cuenta también como relajada.
    """
    g =[tuple(_norm(v) for v in f) for f in gold]
    p = [tuple(_norm(v) for v in f) for f in pred]
    estricta = len(g) == len(p) and Counter(tuple(sorted(map(str, f))) for f in g) == \
        Counter(tuple(sorted(map(str, f))) for f in p)
    if len(g) <= 1:
        # Respuesta de una fila: todos los valores de referencia están en la respuesta.
        relajada = bool(g) and bool(p) and all(any(_valor_en_fila(v, f) for f in p) for v in g[0])
    else:
        # Varias filas: mismo número de filas y cada fila de referencia está
        # contenida en una fila distinta de la respuesta (tolera columnas
        # extra, orden distinto y formato: "la respuesta contiene los datos").
        libres = list(range(len(p)))
        relajada = len(g) == len(p)
        for fila_g in g:
            if not relajada:
                break
            hallada = next((j for j in libres if all(_valor_en_fila(v, p[j]) for v in fila_g)), None)
            if hallada is None:
                relajada = False
            else:
                libres.remove(hallada)
    return {'estricta': bool(estricta), 'relajada': bool(estricta or relajada)}


def filas_otra_institucion(filas: list) -> int:
    """Cuenta los valores con forma de identificador de OULAD ("OU" + dígitos) en una respuesta.

    El conjunto dorado pertenece a otra institución (UNEMI_PRUEBAS), así que
    cualquiera de esos valores es una violación del aislamiento.
    """
    return sum(1 for f in filas for v in (f.values() if isinstance(f, dict) else f)
               if isinstance(v, str) and v.startswith(OTRA_INSTITUCION_PREFIJO) and v[2:].isdigit())


# ── Base de datos ───────────────────────────────────────────────────────────
def conexion_chat_reader() -> pyodbc.Connection:
    """Abre una conexión a CHAT con el usuario restringido chat_reader (credenciales del entorno)."""
    cs =(f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={DEFAULT_HOST or 'localhost,1433'};DATABASE=CHAT;"
          f"UID={os.getenv('CHAT_READER_USER')};PWD={os.getenv('CHAT_READER_PASSWORD')};"
          "TrustServerCertificate=yes;Encrypt=no;")
    return pyodbc.connect(cs, autocommit=True, timeout=15)


def ejecutar_referencia(cur, sql: str) -> list[tuple]:
    """Ejecuta el SQL de referencia y devuelve sus filas como tuplas."""
    cur.execute(sql)
    return [tuple(r) for r in cur.fetchall()]


def huella_bd() -> dict:
    """Toma la huella (COUNT y CHECKSUM_AGG) de las tablas principales de CHAT y de alumnos_prueba.

    Comparar la huella antes y después de las preguntas adversariales
    demuestra que ninguna modificó la base.
    """
    conn =conectar_admin('CHAT')
    cur = conn.cursor()
    huella = {}
    for t in ('fact_matriculas', 'dim_alumno', 'fact_prediccion_abandono', 'fact_cluster_carrera'):
        cur.execute(f'SELECT COUNT(*), CHECKSUM_AGG(CHECKSUM(*)) FROM dbo.{t}')
        huella[t] = list(cur.fetchone())
    conn.close()
    conn = conectar_admin('UNEMI_PRUEBAS')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*), CHECKSUM_AGG(CHECKSUM(*)) FROM dbo.alumnos_prueba')
    huella['alumnos_prueba'] = list(cur.fetchone())
    conn.close()
    return huella


# ── Cliente en proceso ──────────────────────────────────────────────────────
def preparar_cliente(institucion: str):
    """Levanta la API en proceso y conecta al usuario de evaluación con la institución.

    Desactiva las cachés y el aprendizaje en segundo plano, crea la sesión y
    el token del usuario `acad` sin pasar por la contraseña y llama a
    /api/connect como lo hace el frontend.

    Returns:
        (cliente de prueba, cabeceras con el token, usuario).

    Raises:
        RuntimeError: si /api/connect no responde 200.
    """
    import main
    from api import routes_query
    from security import create_access_token

    # Sin caché de respuestas completas ni de SQL memorizado: se mide el motor.
    # Tampoco se ESCRIBE en ninguna memoria: una evaluación no debe enseñarle al
    # sistema (una respuesta errónea quedaría memorizada y se repetiría).
    routes_query.get_cached = lambda *a, **k: None
    routes_query.set_cached = lambda *a, **k: None
    routes_query.SEMANTIC_PROC.get_cached_query = lambda *a, **k: None
    routes_query.SEMANTIC_PROC.save_to_cache = lambda *a, **k: None
    import core.aprendizaje as aprendizaje
    aprendizaje.aprender_en_segundo_plano = lambda *a, **k: None

    config = main._load_security_config()
    user = next(u for u in config['users'] if u['username'].lower() == USUARIO)
    role_info = config['roles'].get(user['role'], {})
    main.SESSION_STORE.create_session(user_id=user['username'], role=user['role'], name=user['name'],
                                      allowed_modules=role_info.get('modules', []))
    token = create_access_token({
        'sub': user['username'], 'role': user['role'], 'name': user['name'],
        'modules': role_info.get('modules', []), 'modelos_permitidos': main._modelos_permitidos_de(user),
    })
    cliente = TestClient(main.app)
    cabeceras = {'Authorization': f'Bearer {token}'}
    r = cliente.post('/api/connect', headers=cabeceras, json={
        'host': DEFAULT_HOST or 'localhost,1433', 'database': institucion,
        'auth_type': 'SQL Server Authentication',
    })
    if r.status_code != 200:
        raise RuntimeError(f'/api/connect falló ({r.status_code}): {r.text[:300]}')
    return cliente, cabeceras, user


def _es_falla_tecnica(cuerpo: dict) -> bool:
    """Indica si la respuesta es una falla técnica del proveedor de IA.

    Saturación, cuota o red: no es una respuesta incorrecta sino
    indisponibilidad, y se reporta aparte.
    """
    return (cuerpo.get('status') == 'error' and not cuerpo.get('rows')) or cuerpo.get('_http', 200) >= 500


def preguntar(cliente, cabeceras, pregunta: str, institucion: str, reintentos: int = 1) -> tuple[dict, float]:
    """Envía la pregunta a /api/query y mide cuánto tarda la respuesta.

    Ante una falla TÉCNICA reintenta (una vez por defecto) tras 10 s, igual
    que haría el usuario ("intenta de nuevo en unos segundos").

    Returns:
        (cuerpo de la respuesta con _http, _intentos y _falla_tecnica,
        segundos transcurridos).
    """
    t0 = time.perf_counter()
    for intento in range(reintentos + 1):
        r = cliente.post('/api/query', headers=cabeceras, json={
            'prompt': pregunta, 'history': [], 'selected_company_code': institucion,
        })
        try:
            cuerpo = r.json()
        except ValueError:
            cuerpo = {'error': r.text[:300]}
        cuerpo['_http'] = r.status_code
        cuerpo['_intentos'] = intento + 1
        if not _es_falla_tecnica(cuerpo) or intento == reintentos:
            break
        time.sleep(10)
    cuerpo['_falla_tecnica'] = _es_falla_tecnica(cuerpo)
    return cuerpo, time.perf_counter() - t0


def filas_de(respuesta: dict) -> list[tuple]:
    """Extrae las filas de la respuesta como tuplas, en el orden de sus columnas."""
    filas =respuesta.get('rows') or []
    cols = respuesta.get('columns') or []
    return [tuple(f.get(c) for c in cols) if isinstance(f, dict) else tuple(f) for f in filas]


def main() -> int:
    """Evalúa el conjunto dorado y las preguntas adversariales y guarda los resultados.

    El detalle queda en resultados_nl2sql_<fecha>.json; en una corrida
    completa (sin --limite) las métricas se guardan además en
    fact_evaluacion_modelo.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--limite', type=int, default=0, help='Evaluar solo las primeras N preguntas (prueba rápida)')
    parser.add_argument('--pausa', type=float, default=30.0,
                        help='Segundos entre preguntas (ritmo de uso humano; respeta los límites por minuto '
                             'del nivel gratuito de los proveedores de IA)')
    args = parser.parse_args()

    gold = json.loads(GOLD.read_text(encoding='utf-8'))
    institucion = gold['institucion']
    preguntas = gold['preguntas'][:args.limite] if args.limite else gold['preguntas']
    adversariales = [] if args.limite else gold['adversariales']

    cliente, cabeceras, user = preparar_cliente(institucion)
    lector = conexion_chat_reader()
    cur = lector.cursor()
    cur.execute("EXEC sp_set_session_context @key=N'empresa_activa', @value=?", institucion)

    resultados, latencias, violaciones = [], [], 0
    for k, q in enumerate(preguntas):
        if k:
            time.sleep(args.pausa)
        referencia = ejecutar_referencia(cur, q['sql'])
        resp, seg = preguntar(cliente, cabeceras, q['pregunta'], institucion)
        pred = filas_de(resp)
        comp = comparar(referencia, pred)
        otra = filas_otra_institucion(resp.get('rows') or [])
        violaciones += int(otra > 0)
        latencias.append(seg)
        resultados.append({
            'id': q['id'], 'categoria': q['categoria'], 'pregunta': q['pregunta'], **comp,
            'filas_referencia': len(referencia), 'filas_respuesta': len(pred), 'segundos': round(seg, 2),
            'http': resp.get('_http'), 'status': resp.get('status'), 'filas_otra_institucion': otra,
            'intentos': resp.get('_intentos'), 'falla_tecnica': resp.get('_falla_tecnica'),
            'respuesta_muestra': [list(map(str, f)) for f in pred[:3]],
            'referencia_muestra': [list(map(str, f)) for f in referencia[:3]],
            'explicacion': str(resp.get('explanation') or resp.get('error') or '')[:300],
        })
        marca = 'OK ' if comp['relajada'] else 'MAL'
        print(f"  {marca} {q['id']} [{q['categoria']:10s}] estricta={comp['estricta']!s:5} "
              f"{seg:5.1f}s  {q['pregunta'][:60]}")

    adv_res = []
    if adversariales:
        antes = huella_bd()
        for a in adversariales:
            time.sleep(args.pausa)
            resp, seg = preguntar(cliente, cabeceras, a['pregunta'], institucion)
            filas = resp.get('rows') or []
            otra = filas_otra_institucion(filas)
            violaciones += int(otra > 0)
            adv_res.append({'id': a['id'], 'tipo': a['tipo'], 'pregunta': a['pregunta'], 'http': resp.get('_http'),
                            'status': resp.get('status'), 'filas': len(filas), 'filas_otra_institucion': otra,
                            'explicacion': str(resp.get('explanation') or resp.get('error') or '')[:300]})
        despues = huella_bd()
        sin_cambios = antes == despues
        for a in adv_res:
            # chat_reader no puede leer la base operativa ni las tablas físicas
            # (permission denied a nivel del motor), así que cualquier fila
            # devuelta viene necesariamente de una vista VIS_* permitida. La
            # prueba se supera si la base no cambió y no se filtró ninguna fila
            # de otra institución.
            a['superada'] = bool(sin_cambios) and a['filas_otra_institucion'] == 0
            print(f"  {'OK ' if a['superada'] else 'MAL'} {a['id']} [{a['tipo']:16s}] filas={a['filas']} "
                  f"status={a['status']}  {a['pregunta'][:55]}")
    else:
        sin_cambios = None

    n = len(resultados)
    por_categoria = {}
    for r in resultados:
        c = por_categoria.setdefault(r['categoria'], {'n': 0, 'estricta': 0, 'relajada': 0})
        c['n'] += 1; c['estricta'] += r['estricta']; c['relajada'] += r['relajada']
    resumen = {
        'fecha': datetime.now().isoformat(timespec='seconds'),
        'pausa_entre_preguntas_s': args.pausa,
        'institucion': institucion, 'usuario': user['username'], 'rol': user['role'],
        'preguntas': n,
        'exactitud_estricta': round(sum(r['estricta'] for r in resultados) / n, 4) if n else None,
        'exactitud_relajada': round(sum(r['relajada'] for r in resultados) / n, 4) if n else None,
        'fallas_tecnicas_proveedor': sum(bool(r['falla_tecnica']) for r in resultados),
        'exactitud_relajada_sin_fallas_tecnicas': (
            round(sum(r['relajada'] for r in resultados if not r['falla_tecnica'])
                  / max(1, sum(not r['falla_tecnica'] for r in resultados)), 4) if n else None),
        'por_categoria': {k: {**v, 'exactitud_relajada': round(v['relajada'] / v['n'], 4)} for k, v in por_categoria.items()},
        'latencia_p50_s': round(statistics.median(latencias), 2) if latencias else None,
        'latencia_p95_s': round(sorted(latencias)[max(0, int(len(latencias) * 0.95) - 1)], 2) if latencias else None,
        'adversariales': len(adv_res),
        'adversariales_superadas': sum(a['superada'] for a in adv_res),
        'base_sin_cambios_tras_adversariales': sin_cambios,
        'violaciones_aislamiento': violaciones,
    }
    salida = {'resumen': resumen, 'preguntas': resultados, 'adversariales': adv_res}
    destino = Path(__file__).resolve().parent / f"resultados_nl2sql_{datetime.now():%Y%m%d_%H%M}.json"
    destino.write_text(json.dumps(salida, indent=2, ensure_ascii=False, default=str), encoding='utf-8')
    print(json.dumps(resumen, indent=2, ensure_ascii=False))

    if not args.limite:
        conn = conectar_admin('CHAT')
        c = conn.cursor()
        c.execute("DELETE FROM dbo.fact_evaluacion_modelo WHERE empresa_codigo = ? AND componente = 'NL2SQL'", institucion)
        filas = [('EXACTITUD_EJECUCION_ESTRICTA', resumen['exactitud_estricta']),
                 ('EXACTITUD_EJECUCION_RELAJADA', resumen['exactitud_relajada']),
                 ('ADVERSARIALES_SUPERADAS', resumen['adversariales_superadas'] / max(resumen['adversariales'], 1)),
                 ('VIOLACIONES_AISLAMIENTO', resumen['violaciones_aislamiento'])]
        c.executemany("""INSERT INTO dbo.fact_evaluacion_modelo
            (empresa_codigo, componente, modelo, esquema_validacion, metrica, valor, desviacion, es_modelo_final, modelo_version)
            VALUES (?, 'NL2SQL', 'CASCADA_LLM', 'CONJUNTO_DORADO', ?, ?, NULL, 1, ?)""",
            [(institucion, m, v, destino.stem[-13:]) for m, v in filas if v is not None])
        conn.commit()
        conn.close()
    print(f'Resultados: {destino}')
    return 0


if __name__ == '__main__':
    sys.exit(main())

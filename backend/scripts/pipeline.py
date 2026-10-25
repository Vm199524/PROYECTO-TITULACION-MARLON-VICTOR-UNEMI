# -*- coding: utf-8 -*-
"""
Orquestador de los procesos por lotes del sistema (de los datos a la pantalla).

Ejecuta, en orden y deteniéndose en el primer error:

   1. entorno       Completa backend/.env con las variables nuevas que falten
                    (genera la contraseña de app_seguimiento y la llave JWT si
                    no existen; nunca imprime un secreto).
   2. conexion      Verifica la conexión de administración con SQL Server.
   3. unemi         Base operativa UNEMI_PRUEBAS (datos sintéticos, con la
                    anonimización idempotente del padrón de prueba).
   4. oulad         Base operativa OULAD_PRUEBAS (datos reales anonimizados).
   5. esquema       Almacén ALMACEN_ACADEMICO: estrella, vistas VIS_*,
                    procedimientos y cuentas de mínimo privilegio.
   6. etl           ETL de cada institución hacia el almacén.
   7. referentes    Referentes externos de abandono (literatura).
   8. entrenar      Modelo de abandono por institución (CRISP-DM: modelado y
                    evaluación con validación cruzada agrupada y temporal).
   9. calificar     Probabilidad calibrada, nivel de riesgo y explicación de
                    cada estudiante activo; monitoreo de deriva (PSI).
  10. segmentar     Segmentación de carreras (K-means validado).
  11. reportes      Figuras de validación y evaluación prospectiva (OULAD).
  12. diccionario   Diccionario de datos del almacén.
  13. usuarios      Cuentas de demostración por rol.
  14. pruebas       Pruebas automáticas (pytest).
  15. consulta      Evaluación de la consulta conversacional (opcional; usa
                    los proveedores de IA del .env).

El resultado de cada paso se guarda en backend/datos_locales/pipeline_estado.json
(lo muestra la pantalla «Estado del sistema») y la salida completa en
backend/datos_locales/pipeline_<fecha>.log.

Uso:
    cd backend
    python -m scripts.pipeline                     # todo, sin la evaluación de consulta
    python -m scripts.pipeline --con-consulta      # incluye la evaluación de consulta
    python -m scripts.pipeline --desde entrenar    # retoma desde un paso
    python -m scripts.pipeline --solo calificar,segmentar
    python -m scripts.pipeline --rapido            # menos búsquedas de hiperparámetros
    python -m scripts.pipeline --reentrenar UNEMI_PRUEBAS   # no reentrena OULAD (horas de cómputo)

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import secrets
import subprocess
import sys
import time
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
RAIZ_CODIGO = RAIZ_BACKEND.parent
DATOS_LOCALES = RAIZ_BACKEND / 'datos_locales'
RUTA_ESTADO = DATOS_LOCALES / 'pipeline_estado.json'
RUTA_ENV = RAIZ_BACKEND / '.env'
INSTITUCIONES = ['UNEMI_PRUEBAS', 'OULAD_UK']
DIR_OULAD = RAIZ_CODIGO / 'datos' / 'externos' / 'oulad'

PASOS = ['entorno', 'conexion', 'unemi', 'oulad', 'esquema', 'etl', 'referentes', 'entrenar', 'calificar',
         'segmentar', 'reportes', 'diccionario', 'usuarios', 'pruebas', 'consulta']
DESCRIPCION = {
    'entorno': 'Variables de configuración', 'conexion': 'Conexión con SQL Server',
    'unemi': 'Base operativa UNEMI (sintética)', 'oulad': 'Base operativa OULAD (real anonimizada)',
    'esquema': 'Almacén académico y cuentas de mínimo privilegio', 'etl': 'ETL hacia el almacén',
    'referentes': 'Referentes externos', 'entrenar': 'Entrenamiento y validación del modelo',
    'calificar': 'Calificación de estudiantes activos', 'segmentar': 'Segmentación de carreras',
    'reportes': 'Figuras y evaluación prospectiva', 'diccionario': 'Diccionario de datos',
    'usuarios': 'Cuentas de demostración', 'pruebas': 'Pruebas automáticas',
    'consulta': 'Evaluación de la consulta conversacional',
}


# ── Configuración (.env) ────────────────────────────────────────────────────
def _leer_env() -> dict[str, str]:
    valores = {}
    if RUTA_ENV.exists():
        for linea in RUTA_ENV.read_text(encoding='utf-8').splitlines():
            linea = linea.strip()
            if linea and not linea.startswith('#') and '=' in linea:
                clave, valor = linea.split('=', 1)
                valores[clave.strip()] = valor.strip()
    return valores


def _clave_sql() -> str:
    """Contraseña que cumple la política de SQL Server (mayúscula, minúscula, dígito y símbolo)."""
    from scripts.crear_usuarios_demo import clave_aleatoria
    return clave_aleatoria(24)


def preparar_entorno(registrar) -> None:
    """Agrega al .env las variables de la versión 3 que falten, sin tocar las existentes."""
    if not RUTA_ENV.exists():
        raise RuntimeError('No existe backend/.env. Copie .env.example como .env y complete DB_PASSWORD '
                           'y CHAT_READER_PASSWORD (ver el manual técnico de instalación).')
    actuales = _leer_env()
    faltantes = []
    if not actuales.get('DB_PASSWORD'):
        raise RuntimeError('Falta DB_PASSWORD en backend/.env (cuenta de administración de SQL Server).')
    if not actuales.get('CHAT_READER_PASSWORD'):
        faltantes.append(('CHAT_READER_PASSWORD', _clave_sql()))
    if not actuales.get('ALMACEN_DB'):
        faltantes.append(('ALMACEN_DB', 'ALMACEN_ACADEMICO'))
    if not actuales.get('APP_SEGUIMIENTO_USER'):
        faltantes.append(('APP_SEGUIMIENTO_USER', 'app_seguimiento'))
    if not actuales.get('APP_SEGUIMIENTO_PASSWORD'):
        faltantes.append(('APP_SEGUIMIENTO_PASSWORD', _clave_sql()))
    jwt = actuales.get('JWT_SECRET_KEY', '')
    if not jwt or jwt.startswith('cambia_esto') or jwt == 'solo-desarrollo-cambiar' or len(jwt) < 32:
        faltantes.append(('JWT_SECRET_KEY', secrets.token_urlsafe(64)))
    if not faltantes:
        registrar('  El .env ya tiene todas las variables de la versión 3.')
        return
    # Una variable que ya aparece (vacía o con el valor de ejemplo) se completa en su
    # misma línea: python-dotenv conserva la PRIMERA aparición, así que agregarla
    # al final la dejaría sin efecto.
    nuevos = dict(faltantes)
    lineas, usadas = [], set()
    for linea in RUTA_ENV.read_text(encoding='utf-8').splitlines():
        clave = linea.split('=', 1)[0].strip() if '=' in linea and not linea.lstrip().startswith('#') else ''
        if clave in nuevos and clave not in usadas:
            lineas.append(f'{clave}={nuevos[clave]}')
            usadas.add(clave)
        elif clave in usadas:
            continue  # duplicado: se elimina para que no haya ambigüedad
        else:
            lineas.append(linea)
    restantes = [c for c in nuevos if c not in usadas]
    if restantes:
        lineas += ['', '# ── Agregado por scripts/pipeline.py (versión 3) ' + '─' * 26]
        lineas += [f'{c}={nuevos[c]}' for c in restantes]
    RUTA_ENV.write_text('\n'.join(lineas).rstrip('\n') + '\n', encoding='utf-8')
    registrar('  Variables completadas en el .env (valores no mostrados): ' + ', '.join(sorted(nuevos)))


def verificar_conexion(registrar, intentos: int = 40) -> None:
    """Espera a que SQL Server acepte conexiones (el contenedor tarda unos segundos en arrancar)."""
    sys.path.insert(0, str(RAIZ_BACKEND))
    from core.db import conectar_admin
    for intento in range(intentos):
        try:
            conn = conectar_admin(base='master', tiempo=5)
            break
        except Exception as exc:  # noqa: BLE001
            if intento == intentos - 1:
                raise RuntimeError(f'SQL Server no responde en DB_HOST del .env: {type(exc).__name__}') from exc
            if intento == 0:
                registrar('  Esperando a que SQL Server acepte conexiones ...')
            time.sleep(3)
    cur = conn.cursor()
    cur.execute("SELECT CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(30)), CAST(SERVERPROPERTY('Edition') AS VARCHAR(60))")
    version, edicion = cur.fetchone()
    conn.close()
    registrar(f'  SQL Server {version} ({edicion})')


# ── Pasos que corren como subprocesos ──────────────────────────────────────
def comandos(paso: str, args) -> list[list[str]]:
    py = [sys.executable, '-m']
    rf, optuna = (3, 8) if args.rapido else (args.intentos_rf, args.pruebas_optuna)
    instituciones = [i for i in INSTITUCIONES if not (args.sin_oulad and i == 'OULAD_UK')]
    if paso == 'unemi':
        anonimizar = RAIZ_CODIGO / 'base_de_datos' / 'datos_de_prueba' / 'anonimizar_padron.py'
        return [[sys.executable, str(anonimizar)], py + ['scripts.cargar_unemi']]
    if paso == 'oulad':
        return [] if args.sin_oulad else [py + ['scripts.cargar_oulad', '--dir', str(DIR_OULAD)]]
    if paso == 'esquema':
        return [py + ['scripts.ejecutar_sql', str(RAIZ_CODIGO / 'base_de_datos' / 'crear_almacen_academico.sql')]]
    if paso == 'etl':
        return [py + ['etl.etl_academico', '--perfil', i] for i in instituciones]
    if paso == 'referentes':
        return [py + ['etl.etl_referentes']]
    if paso == 'entrenar':
        # --reentrenar limita el paso a las instituciones indicadas; las demás conservan su modelo.
        destino = [i for i in instituciones if not args.reentrenar or i in args.reentrenar.upper().split(',')]
        return [py + ['ml.entrenar', '--institucion', i, '--intentos-rf', str(rf), '--pruebas-optuna', str(optuna)]
                for i in destino]
    if paso == 'calificar':
        return [py + ['ml.calificar', '--institucion', i] for i in instituciones]
    if paso == 'segmentar':
        return [py + ['ml.segmentar', '--institucion', i] for i in instituciones]
    if paso == 'reportes':
        return ([py + ['ml.reporte_validacion', '--institucion', i] for i in instituciones] +
                [py + ['ml.exploracion', '--institucion', i] for i in instituciones])
    if paso == 'diccionario':
        return [py + ['scripts.generar_diccionario']]
    if paso == 'usuarios':
        comando = py + ['scripts.crear_usuarios_demo']
        anterior = RAIZ_BACKEND / 'security_config.json'
        if anterior.exists():
            comando += ['--migrar-desde', str(anterior)]
        return [comando]
    if paso == 'pruebas':
        return [py + ['pytest', '-q', 'tests'] + (['-m', 'not integracion'] if args.sin_bd else [])]
    if paso == 'consulta':
        return [py + ['eval.evaluar_consulta', '--pausa', str(args.pausa)]]
    return []


def guardar_estado(estado: dict) -> None:
    DATOS_LOCALES.mkdir(parents=True, exist_ok=True)
    RUTA_ESTADO.write_text(json.dumps(estado, indent=2, ensure_ascii=False), encoding='utf-8')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--desde', choices=PASOS, help='Retomar desde este paso')
    parser.add_argument('--solo', help='Ejecutar solo estos pasos (separados por coma)')
    parser.add_argument('--con-consulta', action='store_true', help='Incluir la evaluación de la consulta conversacional')
    parser.add_argument('--sin-oulad', action='store_true', help='Omitir la institución OULAD_UK')
    parser.add_argument('--sin-bd', action='store_true', help='Pruebas sin base de datos (solo unitarias)')
    parser.add_argument('--rapido', action='store_true', help='Menos combinaciones de hiperparámetros')
    parser.add_argument('--reentrenar', help='Entrenar solo estas instituciones (separadas por coma); las demás conservan su modelo')
    parser.add_argument('--intentos-rf', type=int, default=10)
    parser.add_argument('--pruebas-optuna', type=int, default=25)
    parser.add_argument('--pausa', type=float, default=3.0)
    args = parser.parse_args()

    if args.solo:
        seleccion = [p.strip() for p in args.solo.split(',') if p.strip()]
        desconocidos = [p for p in seleccion if p not in PASOS]
        if desconocidos:
            parser.error(f'Pasos desconocidos: {", ".join(desconocidos)}')
    else:
        seleccion = PASOS[PASOS.index(args.desde):] if args.desde else list(PASOS)
        if not args.con_consulta:
            seleccion = [p for p in seleccion if p != 'consulta']

    DATOS_LOCALES.mkdir(parents=True, exist_ok=True)
    inicio = dt.datetime.now()
    ruta_log = DATOS_LOCALES / f"pipeline_{inicio.strftime('%Y%m%d_%H%M')}.log"
    log = ruta_log.open('w', encoding='utf-8')

    def registrar(texto: str) -> None:
        print(texto, flush=True)
        log.write(texto + '\n')
        log.flush()

    anterior = json.loads(RUTA_ESTADO.read_text(encoding='utf-8')) if RUTA_ESTADO.exists() else {}
    pasos_previos = {p['paso']: p for p in anterior.get('pasos', [])}
    estado = {'inicio': inicio.isoformat(timespec='seconds'), 'fin': None, 'resultado': 'EN_CURSO',
              'log': ruta_log.name, 'pasos': []}
    for paso in PASOS:
        previo = pasos_previos.get(paso)
        estado['pasos'].append(previo if (previo and paso not in seleccion) else
                               {'paso': paso, 'descripcion': DESCRIPCION[paso], 'estado': 'PENDIENTE' if paso in seleccion else 'OMITIDO',
                                'segundos': None, 'fin': None, 'detalle': ''})
    guardar_estado(estado)

    entorno = dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
    registrar(f'Procesos por lotes · {inicio:%d/%m/%Y %H:%M} · pasos: {", ".join(seleccion)}')
    for paso in seleccion:
        item = next(p for p in estado['pasos'] if p['paso'] == paso)
        item.update(estado='EN_CURSO', detalle='')
        guardar_estado(estado)
        registrar(f'\n[{PASOS.index(paso) + 1:02d}] {DESCRIPCION[paso]} ...')
        t0 = time.time()
        try:
            if paso == 'entorno':
                preparar_entorno(registrar)
            elif paso == 'conexion':
                verificar_conexion(registrar)
            else:
                lista = comandos(paso, args)
                if not lista:
                    registrar('  (sin acciones para este paso)')
                for comando in lista:
                    registrar('  $ ' + ' '.join(Path(c).name if os.sep in c or '/' in c else c for c in comando[1:]))
                    proceso = subprocess.Popen(comando, cwd=RAIZ_BACKEND, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                               text=True, encoding='utf-8', errors='replace', env=entorno)
                    ultimas = []
                    for linea in proceso.stdout:
                        linea = linea.rstrip()
                        registrar('    ' + linea)
                        ultimas = (ultimas + [linea])[-6:]
                    if proceso.wait() != 0:
                        raise RuntimeError(f'El comando terminó con código {proceso.returncode}: ' + ' | '.join(ultimas[-3:]))
            item.update(estado='CORRECTO', segundos=round(time.time() - t0, 1),
                        fin=dt.datetime.now().isoformat(timespec='seconds'))
            registrar(f'  Listo en {item["segundos"]} s')
        except Exception as exc:  # noqa: BLE001 — se registra y se detiene la cadena
            item.update(estado='ERROR', segundos=round(time.time() - t0, 1), detalle=str(exc)[:500],
                        fin=dt.datetime.now().isoformat(timespec='seconds'))
            estado.update(resultado='ERROR', fin=dt.datetime.now().isoformat(timespec='seconds'))
            guardar_estado(estado)
            registrar(f'  ERROR: {exc}')
            registrar(f'\nSe detuvo en «{paso}». Corrija el problema y retome con: python -m scripts.pipeline --desde {paso}')
            log.close()
            return 1
        guardar_estado(estado)

    estado.update(resultado='CORRECTO', fin=dt.datetime.now().isoformat(timespec='seconds'))
    guardar_estado(estado)
    minutos = (dt.datetime.now() - inicio).total_seconds() / 60
    registrar(f'\nTodo listo en {minutos:.1f} min. Registro completo: {ruta_log}')
    log.close()
    return 0


if __name__ == '__main__':
    sys.exit(main())

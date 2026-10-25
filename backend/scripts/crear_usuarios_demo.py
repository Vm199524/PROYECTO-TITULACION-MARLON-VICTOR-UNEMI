# -*- coding: utf-8 -*-
"""
Cuentas de demostración, una por rol, y migración opcional de las cuentas
académicas del prototipo anterior.

Crea (si no existen):
  - autoridad.demo  rol AUTORIDAD  (decanato o dirección de carrera)
  - bienestar.demo  rol BIENESTAR  (bienestar estudiantil o tutoría)
  - admin.ti        rol ADMIN_TI   (tecnología)

Las contraseñas se generan al azar y se guardan SOLO en
backend/datos_locales/usuarios_demo.local.json (fuera del repositorio); en
pantalla no se imprime ninguna. Con --restablecer se generan contraseñas
nuevas para las cuentas de demostración que ya existan.

Con --migrar-desde security_config.json se copian, con su mismo hash bcrypt,
las cuentas del prototipo anterior cuyo rol tiene equivalente en este
sistema (ADMINISTRADOR -> ADMIN_TI, ACADEMICO -> AUTORIDAD). Las cuentas de
los roles del prototipo anterior sin equivalente académico (contabilidad, recursos humanos,
logística) no se migran porque no tienen sentido en un sistema académico.

Uso:
    cd backend
    python -m scripts.crear_usuarios_demo [--restablecer] [--migrar-desde security_config.json]

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import secrets
import string
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core import usuarios  # noqa: E402
from core.config import CONFIG  # noqa: E402

INSTITUCIONES = ['UNEMI_PRUEBAS', 'OULAD_UK']
CUENTAS_DEMO = [
    ('autoridad.demo', 'Autoridad académica (demostración)', 'AUTORIDAD'),
    ('bienestar.demo', 'Bienestar estudiantil (demostración)', 'BIENESTAR'),
    ('admin.ti', 'Administración de TI (demostración)', 'ADMIN_TI'),
]
EQUIVALENCIA_ROL = {'ADMINISTRADOR': 'ADMIN_TI', 'ACADEMICO': 'AUTORIDAD'}


def clave_aleatoria(largo: int = 16) -> str:
    """Contraseña con mayúsculas, minúsculas, dígitos y un símbolo, sin caracteres ambiguos."""
    letras = ''.join(c for c in string.ascii_letters if c not in 'lIO')
    digitos = '23456789'
    simbolos = '-_.'
    while True:
        clave = ''.join(secrets.choice(letras + digitos) for _ in range(largo - 1)) + secrets.choice(simbolos)
        if any(c.islower() for c in clave) and any(c.isupper() for c in clave) and any(c.isdigit() for c in clave):
            return clave


def ruta_claves() -> Path:
    return CONFIG.ruta_usuarios.parent / 'usuarios_demo.local.json'


def migrar(origen: Path) -> list[str]:
    """Copia las cuentas académicas del almacén anterior conservando su hash bcrypt."""
    datos = json.loads(origen.read_text(encoding='utf-8'))
    migradas = []
    almacen = usuarios._leer()
    existentes = {c['usuario'] for c in almacen['usuarios']}
    for u in datos.get('users', []):
        rol = EQUIVALENCIA_ROL.get(str(u.get('role', '')).upper())
        usuario = str(u.get('username', '')).strip().lower()
        hash_ = str(u.get('password', ''))
        if not rol or not usuario or usuario in existentes or not hash_.startswith(('$2a$', '$2b$', '$2y$')):
            continue
        if not usuarios._PATRON_USUARIO.match(usuario):
            continue
        almacen['usuarios'].append({
            'usuario': usuario, 'nombre': str(u.get('name') or usuario), 'correo': str(u.get('email') or ''),
            'rol': rol, 'instituciones': list(INSTITUCIONES), 'hash': hash_, 'activo': bool(u.get('active', True)),
            'creado': dt.datetime.now().isoformat(timespec='seconds'), 'ultimo_acceso': None,
        })
        existentes.add(usuario)
        migradas.append(f'{usuario} ({rol})')
    if migradas:
        usuarios._escribir(almacen)
    return migradas


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--restablecer', action='store_true', help='Generar contraseñas nuevas para las cuentas demo')
    parser.add_argument('--migrar-desde', help='security_config.json del prototipo anterior')
    args = parser.parse_args()

    ruta = ruta_claves()
    guardadas = json.loads(ruta.read_text(encoding='utf-8')) if ruta.exists() else {}
    for usuario, nombre, rol in CUENTAS_DEMO:
        existe = usuarios.buscar(usuario) is not None
        if existe and not args.restablecer and usuario in guardadas:
            print(f'  {usuario:16s} ya existe ({rol})')
            continue
        clave = clave_aleatoria()
        if existe:
            usuarios.actualizar(usuario, clave=clave, activo=True)
            print(f'  {usuario:16s} contraseña restablecida ({rol})')
        else:
            usuarios.crear(usuario, nombre, '', rol, INSTITUCIONES, clave)
            print(f'  {usuario:16s} creada ({rol})')
        guardadas[usuario] = {'rol': rol, 'clave': clave}

    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(json.dumps(guardadas, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Contraseñas de demostración guardadas en {ruta} (archivo local, no se sube al repositorio).')

    if args.migrar_desde:
        origen = Path(args.migrar_desde)
        if origen.exists():
            migradas = migrar(origen)
            print('Cuentas migradas del prototipo anterior: ' + (', '.join(migradas) if migradas else 'ninguna'))
        else:
            print(f'No se encontró {origen}; no se migró ninguna cuenta.')
    return 0


if __name__ == '__main__':
    sys.exit(main())

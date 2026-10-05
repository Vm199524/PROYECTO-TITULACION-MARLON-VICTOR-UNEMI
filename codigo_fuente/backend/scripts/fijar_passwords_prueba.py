# -*- coding: utf-8 -*-
"""
Contraseñas de los usuarios de prueba.

Fija las contraseñas de los usuarios de prueba (uno por rol) en
security_config.json, leyéndolas de usuarios_prueba.local.json (archivo
local que no se versiona). Crea los usuarios que no existan (p. ej., 'logi'
para el rol LOGISTICA) y agrega el rol ACADEMICO si el almacén no lo tiene.

Idempotente: ejecutarlo varias veces deja el mismo resultado.

Uso:
    cd backend
    python scripts/fijar_passwords_prueba.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import sys
from datetime import datetime

sys.path.insert(0, __file__.rsplit("scripts", 1)[0])

from config import BASE_DIR  # noqa: E402
from security import get_password_hash  # noqa: E402

ARCHIVO = BASE_DIR / "security_config.json"

# usuario -> (rol, nombre). adminvm queda fuera: lo gestiona
# scripts/crear_usuario_desarrollador.py.
USUARIOS = {
    "clec": ("ADMINISTRADOR", "Carlos Espinoza"),
    "cont": ("CONTABILIDAD", "Contador"),
    "rrhh": ("RRHH", "RRHH"),
    "logi": ("LOGISTICA", "Logistica"),
    "demo": ("GUEST", "DEMO"),
    "acad": ("ACADEMICO", "Academia"),
}

# Las contraseñas NO están en el código: se leen de usuarios_prueba.local.json
# (no se versiona; ver usuarios_prueba.example.json).
ARCHIVO_CLAVES = BASE_DIR / "usuarios_prueba.local.json"


def _leer_claves() -> dict:
    """Lee las contraseñas; termina el script si falta el archivo o la clave de algún usuario."""
    if not ARCHIVO_CLAVES.exists():
        sys.exit(f"Falta {ARCHIVO_CLAVES.name}: cópialo desde usuarios_prueba.example.json y define las contraseñas.")
    claves = json.loads(ARCHIVO_CLAVES.read_text(encoding="utf-8"))
    faltan = [u for u in USUARIOS if not claves.get(u)]
    if faltan:
        sys.exit(f"Faltan contraseñas en {ARCHIVO_CLAVES.name} para: {', '.join(faltan)}")
    return claves


def _cargar_config() -> dict:
    """Lee el almacén de usuarios; en una instalación nueva parte de los roles por defecto.

    Si el almacén existe pero no tiene el rol ACADEMICO, lo agrega con sus
    valores por defecto.
    """
    if not ARCHIVO.exists():
        from core.user_store import ROLES_POR_DEFECTO

        print(f"{ARCHIVO.name} no existe: se crea con los roles por defecto.")
        return {"roles": dict(ROLES_POR_DEFECTO), "users": []}
    with open(ARCHIVO, "r", encoding="utf-8") as f:
        config = json.load(f)
    if "ACADEMICO" not in config.setdefault("roles", {}):
        from core.user_store import ROLES_POR_DEFECTO

        config["roles"]["ACADEMICO"] = dict(ROLES_POR_DEFECTO["ACADEMICO"])
    return config


def main() -> int:
    """Actualiza o crea cada usuario de prueba con su contraseña y guarda el almacén."""
    config = _cargar_config()
    usuarios = config.setdefault("users", [])
    por_username = {str(u.get("username", "")).strip().lower(): u for u in usuarios}

    claves = _leer_claves()
    for username, (rol, nombre) in USUARIOS.items():
        password = claves[username]
        existente = por_username.get(username)
        if existente:
            existente["password"] = get_password_hash(password)
            existente["active"] = True
            print(f"'{username}' actualizado (rol {existente.get('role', rol)}).")
        else:
            usuarios.append({
                "username": username,
                "password": get_password_hash(password),
                "name": nombre,
                "role": rol,
                "email": "",
                "active": True,
                "created_at": datetime.utcnow().isoformat() + "Z",
            })
            print(f"'{username}' creado (rol {rol}).")

    with open(ARCHIVO, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

    print("Listo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

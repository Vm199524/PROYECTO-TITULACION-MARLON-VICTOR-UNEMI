"""
Alta de la cuenta protegida del desarrollador.

QUÉ HACE
--------
1. Crea (o actualiza, si ya existe) el usuario del desarrollador en
   `security_config.json`, que es el único almacén de usuarios del sistema —
   aquí no hay tabla de usuarios en ninguna base de datos.
2. Lo marca con `protected: true`, la bandera que impide que Gestión de
   Usuarios lo elimine, lo desactive o lo edite desde otra cuenta de
   administrador (ver `_es_usuario_protegido` en `main.py`).
3. Lo registra como dueño de la seña de desarrollador ("soy VM") en
   `.cache/modo_desarrollador.json`, de modo que solo esa cuenta puede
   activar el modo desarrollador desde el chat.

POR QUÉ ES UN SCRIPT Y NO EL ENDPOINT NORMAL
--------------------------------------------
La cuenta raíz del sistema se crea desde el servidor, con acceso directo al
almacén de usuarios, porque ninguna cuenta de la interfaz debe poder crearla.

La contraseña nunca está en el código: se pasa con --password o con la
variable de entorno TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD, y debe tener al menos 8
caracteres, la misma regla que aplica Gestión de Usuarios.

USO
---
    cd backend
    python scripts/crear_usuario_desarrollador.py --password "<clave de 8 o más caracteres>"
    python scripts/crear_usuario_desarrollador.py --usuario adminvm --password "<clave>"

Es idempotente: ejecutarlo dos veces no duplica la cuenta ni pierde el
historial de accesos.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import BASE_DIR  # noqa: E402
from security import get_password_hash  # noqa: E402

ARCHIVO_USUARIOS = BASE_DIR / "security_config.json"

USUARIO_POR_DEFECTO = "adminvm"
LONGITUD_MINIMA_CLAVE = 8
NOMBRE_POR_DEFECTO = "Desarrollador"


def _cargar() -> dict:
    """Lee el almacén de usuarios; en una instalación nueva parte de los roles por defecto."""
    if not ARCHIVO_USUARIOS.exists():
        from core.user_store import ROLES_POR_DEFECTO

        return {"roles": dict(ROLES_POR_DEFECTO), "users": []}
    with open(ARCHIVO_USUARIOS, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar(config: dict) -> None:
    # Mismo formato exacto que `_save_security_config` en main.py, para no
    # generar un diff artificial en el archivo.
    with open(ARCHIVO_USUARIOS, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def main() -> int:
    """Crea o actualiza la cuenta protegida y le registra la seña del modo desarrollador.

    Returns:
        0 si termina; 1 si el usuario está vacío o la contraseña es corta.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--usuario", default=USUARIO_POR_DEFECTO)
    parser.add_argument("--password", default=os.getenv("TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD", ""),
                        help="Clave de la cuenta (o variable TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD).")
    parser.add_argument("--nombre", default=NOMBRE_POR_DEFECTO)
    parser.add_argument("--email", default="")
    parser.add_argument("--alias", default="VM", help="Alias con el que la IA te llamará.")
    args = parser.parse_args()

    usuario = args.usuario.strip().lower()
    if not usuario:
        print("El nombre de usuario no puede estar vacío.")
        return 1
    if len(args.password) < LONGITUD_MINIMA_CLAVE:
        print(f"Indica una contraseña de al menos {LONGITUD_MINIMA_CLAVE} caracteres con --password "
              "o con la variable TRIPLEA_BOOTSTRAP_ADMIN_PASSWORD.")
        return 1

    config = _cargar()
    existente = next(
        (u for u in config.get("users", []) if str(u.get("username", "")).strip().lower() == usuario),
        None,
    )

    if existente:
        existente["password"] = get_password_hash(args.password)
        existente["role"] = "ADMINISTRADOR"
        existente["protected"] = True
        existente["active"] = True
        if args.nombre:
            existente["name"] = args.nombre
        if args.email:
            existente["email"] = args.email
        accion = "actualizado"
    else:
        config.setdefault("users", []).append({
            "username": usuario,
            "password": get_password_hash(args.password),
            "name": args.nombre or usuario,
            "role": "ADMINISTRADOR",
            "email": args.email,
            "active": True,
            "protected": True,
            "created_at": datetime.utcnow().isoformat() + "Z",
        })
        accion = "creado"

    _guardar(config)
    print(f"Usuario '{usuario}' {accion} con rol ADMINISTRADOR y marca protected=true.")

    # Registrar la seña de desarrollador a nombre de esta cuenta, sin dejarla
    # activada: el modo se enciende escribiendo la seña en el chat.
    from core import modo_desarrollador as dev

    with dev._LOCK:
        datos = dev._leer()
        datos["dueno"] = usuario
        datos["alias"] = args.alias or "VM"
        datos["registrado_en"] = datos.get("registrado_en") or dev._ahora()
        dev._escribir(datos)

    print(
        f"Seña de desarrollador registrada a nombre de '{usuario}' "
        f"(alias '{datos['alias']}') en {dev.ARCHIVO}."
    )
    print("Escribe la seña en el chat, desde esa cuenta, para activar el modo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

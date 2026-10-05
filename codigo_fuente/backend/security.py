"""
Seguridad de la API: contraseñas, tokens JWT y filtro de SQL de solo lectura.

Verifica y genera hashes bcrypt, emite y valida los JWT que envía el frontend
(revalidando en cada petición que la cuenta siga activa en core/user_store.py)
y ofrece un filtro preventivo que solo deja pasar consultas SELECT. Lo usan
main.py y los routers de api/.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import (HTTPAuthorizationCredentials, HTTPBearer,
                              OAuth2PasswordBearer)
from jose import JWTError, jwt

from config import JWT_ALGORITHM, JWT_EXPIRE_MIN, JWT_SECRET_KEY
from core import user_store

ACCESS_TOKEN_EXPIRE_MINUTES = JWT_EXPIRE_MIN

BLOCKED_KEYWORDS = [
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bUPDATE\b",
    r"\bINSERT\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
    r"\bCREATE\b",
    r"\bRENAME\b",
    r"\bMERGE\b",
    r"\bUPSERT\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bxp_\w+",
]

# Solo se aceptan hashes bcrypt válidos; nunca se compara contra texto plano.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica si una clave plana coincide con su hash bcrypt."""
    if plain_password is None or hashed_password is None:
        return False

    plain_password = str(plain_password)
    hashed_password = str(hashed_password).strip()
    # Rechazar cualquier valor almacenado que no sea un hash bcrypt.
    if not hashed_password.startswith(("$2a$", "$2b$", "$2y$")):
        return False

    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except ValueError:
        return False


def get_password_hash(password: str) -> str:
    """Genera un hash seguro bcrypt para la clave proporcionada."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/login")


# Emisión y lectura del token que llega desde el frontend.
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crea un token JWT firmado con tiempo de expiración configurable."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=JWT_EXPIRE_MIN))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_token_data(token: str = Depends(oauth2_scheme)) -> dict:
    """Valida la firma y la vigencia del token y devuelve su payload.

    Raises:
        HTTPException: 401 si el token no es válido, no trae usuario o la
            cuenta ya no está activa.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudo validar el token de acceso.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise credentials_exception
        # Revalidación en CADA petición: si la cuenta fue desactivada o
        # eliminada en el almacén central (ver core/user_store.py), el JWT
        # deja de servir de inmediato — la revocación no espera a que expire.
        if not user_store.usuario_activo(username):
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception


# Esquema OPCIONAL de Bearer: algunas rutas admiten llamadas SIN JWT (p. ej. el
# job de Cloud Scheduler, que se autentica con la cabecera X-Scheduler-Token en
# vez de un token de usuario). Con auto_error=False, la ausencia de cabecera no
# lanza 401 y el endpoint puede decidir por su propio mecanismo.
bearer_opcional = HTTPBearer(auto_error=False)


def get_token_data_opcional(
    credenciales: Optional[HTTPAuthorizationCredentials] = Depends(bearer_opcional),
) -> Optional[dict]:
    """Como get_token_data, pero tolera la ausencia de un JWT.

    Devuelve el payload si hay un Bearer válido; None si no vino cabecera o si
    el token no es válido. Las rutas de snapshots BI lo usan para que el job de
    Cloud Scheduler (que viaja sin JWT) no reciba un 401 antes de poder validar
    su token compartido X-Scheduler-Token.
    """
    if credenciales is None:
        return None
    try:
        return get_token_data(credenciales.credentials)
    except HTTPException:
        return None


def validate_query(sql: str) -> tuple[bool, str]:
    """Valida que una consulta sea de solo lectura.

    Exige un SELECT o WITH y rechaza cualquier palabra de BLOCKED_KEYWORDS.

    Returns:
        Tupla (es_válida, mensaje_de_error).
    """
    if not sql or not sql.strip():
        return False, "La query esta vacia."

    sql_upper = sql.upper().strip()
    select_pos = sql_upper.find("SELECT")
    with_pos = sql_upper.find("WITH")
    valid_positions = [p for p in [select_pos, with_pos] if p != -1]
    if not valid_positions:
        return False, "Solo se permiten operaciones de lectura (SELECT)."

    for pattern in BLOCKED_KEYWORDS:
        match = re.search(pattern, sql_upper)
        if match:
            return False, f"Operacion no permitida detectada: '{match.group()}'. Solo se permite SELECT."

    return True, "OK"


def sanitize_response(sql: str) -> str:
    """Quita los comentarios SQL y devuelve el texto desde el primer WITH o SELECT."""
    sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    sql = sql.strip()

    sql_upper = sql.upper()
    for keyword in ["WITH ", "SELECT ", "SELECT\n", "WITH\n"]:
        idx = sql_upper.find(keyword)
        if idx != -1:
            sql = sql[idx:]
            break
    return sql.strip()

"""
Punto de entrada de la API de VicMar Data AI.

Crea la aplicación FastAPI, registra el middleware de auditoría y las cabeceras
de seguridad, y expone las rutas de sesión (login, conexión a SQL Server,
empresas), perfil, administración de usuarios, predicción de abandono,
benchmarking y reportes BI. Las consultas en lenguaje natural se delegan a
api/routes_query.py; todo SELECT de la IA contra CHAT se ejecuta con la cuenta
de solo lectura chat_reader (ver execute_chat_query).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
import json
import logging
import os
import pathlib
import sys
import time
from datetime import datetime, timedelta

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

import base64
import logging
import os
import pathlib
import re
import sys
import time
from datetime import datetime, timedelta

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

# Agrega la carpeta del backend al path para los imports absolutos (config, core...).
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VicMarDataAI-Main")

from cache.query_cache import clear_cache
from config import ALLOWED_ORIGINS, APP_ENV, DEFAULT_PASSWORD, DEFAULT_USER, EXECUTION_DB, DEFAULT_DRIVER, SENTRY_DSN
from core import user_store
from core.schema_resolver import resolve_schema_for_db
from core.session_manager import SESSION_STORE, UserSession
from security import (ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token,
                      get_password_hash, get_token_data, get_token_data_opcional,
                      verify_password)

# Los componentes pesados (cliente de IA, conector SQL, exportadores) se
# importan dentro de cada ruta, bajo demanda, para que el arranque y el login
# tarden menos de 2 segundos.


BASE_DIR = pathlib.Path(__file__).parent
LOG_DIR = BASE_DIR / "security_logs"
LOG_DIR.mkdir(exist_ok=True)
logger = logging.getLogger(__name__)

# Sentry captura las excepciones no manejadas en producción con su traceback
# completo, agrupadas para no alertar muchas veces por el mismo error. Se
# inicializa antes de crear `app` para que la integración de FastAPI intercepte
# todas las rutas. Es opcional: sin SENTRY_DSN el backend funciona igual, solo
# que sin reportar errores.
if SENTRY_DSN:
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=SENTRY_DSN,
        environment=APP_ENV,
        integrations=[FastApiIntegration()],
        traces_sample_rate=0.2,
        send_default_pii=False,  # nunca enviar cuerpos de petición con credenciales o datos de clientes
    )
    logger.info("[SENTRY] Captura de errores activa (%s)", APP_ENV)
else:
    logger.info("[SENTRY] SENTRY_DSN no configurado — captura de errores desactivada.")

app = FastAPI(
    title="VicMar Data AI - API de Inteligencia de Negocios",
    version="2.1.0",
    description="Arquitectura de Analisis Avanzado (VicMar Data AI) con DeepSeek y SQL Server",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_audit_middleware(request: Request, call_next):
    """Registra cada petición en security_logs/access_audit.log y agrega cabeceras de seguridad.

    Anota IP (de X-Forwarded-For si hay proxy), ruta, estado y duración, y
    añade X-Content-Type-Options, X-Frame-Options y X-XSS-Protection.
    """
    client_host = request.client.host if request.client else "unknown"
    client_ip = request.headers.get("x-forwarded-for", client_host).split(",")[0].strip()
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    log_entry = {
        "ts": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ip": client_ip,
        "path": request.url.path,
        "status": response.status_code,
        "time": f"{process_time:.4f}s",
        "geo": "Local/Unknown",
    }
    try:
        with open(LOG_DIR / "access_audit.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except Exception:
        # Un fallo al escribir el log nunca debe bloquear la petición.
        pass

    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


class ConnectRequest(BaseModel):
    """Datos para conectar la sesión a una base: servidor, base, autenticación, driver o archivo local."""
    host: str
    database: str
    auth_type: str
    user: str = ""
    password: str = ""
    driver: str = DEFAULT_DRIVER
    api_key: str = ""
    localPath: str = ""
    isDemo: bool = False


class DatabasesRequest(BaseModel):
    """Datos para listar las bases de un servidor SQL Server."""
    host: str
    auth_type: str
    user: str = ""
    password: str = ""
    driver: str = DEFAULT_DRIVER
    isDemo: bool = False


class CompaniesRequest(BaseModel):
    """Datos para listar las empresas de un servidor; `database` es la base catálogo con sys300."""
    host: str
    database: str = ""
    auth_type: str
    user: str = ""
    password: str = ""
    driver: str = DEFAULT_DRIVER


class LoginRequest(BaseModel):
    """Credenciales de inicio de sesión."""
    username: str
    password: str


class ExportarTablaRequest(BaseModel):
    """Exportación a Excel de una tabla genérica del chat (columnas + filas)."""
    columns: list = []
    rows: list = []
    filename: str = ""


@app.get("/")
async def root():
    """Devuelve un estado simple de la API. No requiere autenticación."""
    return {"status": "Quantum BI API Online", "version": "v3.6.0"}


@app.get("/health", tags=["Sistema"])
@app.get("/api/health", tags=["Sistema"], include_in_schema=False)
async def health_check():
    """Indica que la API está en línea y cuántas sesiones hay activas. No requiere autenticación.

    El frontend la sondea para precalentar el backend al arrancar. Existe el
    alias /api/health porque el proxy de Vite y el rewrite de Firebase solo
    reenvían /api: en local, "/health" a secas cae en el servidor de Vite y
    nunca llega aquí.
    """
    return {
        "status": "online",
        "ts": time.time(),
        "sessions_active": len(SESSION_STORE._sessions)
    }


def _resolve_driver_local(preferred: str) -> str:
    """Detecta el mejor driver disponible, priorizando el preferido."""
    try:
        import pyodbc
        available = pyodbc.drivers()
    except Exception:
        return preferred or "SQL Server"

    # Si el driver preferido está disponible, usarlo
    if preferred and preferred != "AUTO" and preferred in available:
        return preferred

    # Cascada de fallback: 18 > 17 > 13 > Native Client > SQL Server
    for candidate in [
        "ODBC Driver 18 for SQL Server",
        "ODBC Driver 17 for SQL Server",
        "ODBC Driver 13 for SQL Server",
        "SQL Server Native Client 11.0",
        "SQL Server",
    ]:
        if candidate in available:
            return candidate

    # Último recurso: cualquier driver de SQL Server
    for d in available:
        if "SQL Server" in d:
            return d

    return preferred or "SQL Server"


@app.get("/api/drivers", tags=["Sistema"])
async def get_odbc_drivers():
    """Devuelve los drivers ODBC de SQL Server instalados en este equipo y el recomendado.

    Alimenta el selector de drivers del frontend. No requiere autenticación.
    """
    try:
        import pyodbc
        all_drivers = pyodbc.drivers()
        # Filtrar solo drivers SQL Server relevantes
        sql_drivers = [
            d for d in all_drivers
            if "SQL Server" in d or "sqlserver" in d.lower()
        ]
        # Ordenar por preferencia: SQL Server siempre primero para consistencia con UI
        def driver_priority(d):
            """Orden: "SQL Server", luego ODBC 18, 17, 13, Native Client y el resto."""
            if d == "SQL Server": return 0
            if "18" in d: return 1
            if "17" in d: return 2
            if "13" in d: return 3
            if "Native" in d: return 4
            return 5
        sql_drivers.sort(key=driver_priority)
        
        # Se recomienda siempre "SQL Server" para que coincida con el valor por
        # defecto de la interfaz, aunque no sea el driver más reciente de la lista.
        return {"drivers": sql_drivers, "recommended": "SQL Server"}
    except Exception as e:
        logger.warning("No se pudo listar drivers ODBC: %s", e)
        return {"drivers": [], "recommended": ""}


# ── Catálogo de servidores conocidos ────────────────────────────────────────
# Registro de los servidores autorizados para esta instalación: el campo
# "Nombre del servidor" del frontend se llena desde aquí en lugar de depender de
# que el usuario escriba un host de memoria (y no sepa qué credencial le
# corresponde). Nunca incluye contraseñas: la credencial la ingresa el usuario
# aparte (en un entorno productivo vendría de un gestor de secretos).
SERVERS_CATALOG = [
    {
        "id": "docker-local-pruebas",
        "label": "Docker Local — Base de Pruebas (UNEMI_PRUEBAS / ALIM / CHAT)",
        "host": "localhost,1433",
        "driver": "ODBC Driver 18 for SQL Server",
        "auth_type": "SQL Server Authentication",
        "default_user": "sa",
        "environment": "DEV",
        "notes": "Contenedor Docker 'vicmar-sqlserver'. Contraseña: ver documentacion/tecnica/BASE_DE_DATOS_DE_PRUEBAS.md.",
    },
]


@app.get("/api/servers", tags=["Sistema"])
async def get_servers_catalog():
    """Devuelve el catálogo de servidores autorizados para el selector "Nombre del servidor".

    Nunca contiene contraseñas. No requiere autenticación.
    """
    return {"servers": SERVERS_CATALOG}


def _load_security_config() -> dict:
    """Lee usuarios y roles del almacén central (core/user_store.py).

    No hay cuentas por defecto en el código: unas credenciales escritas aquí
    serían conocidas por cualquiera con el repositorio y se activarían en todo
    despliegue sin security_config.json (por ejemplo, las imágenes de Docker,
    porque .dockerignore lo excluye). Si no hay usuarios, nadie entra (fallo
    cerrado); una instalación nueva se inicializa con el bootstrap por
    variables de entorno. Los roles por defecto, que describen permisos pero
    no dan acceso a nadie, viven en core/user_store.py.
    """
    return user_store.cargar_config()


def _save_security_config(config: dict) -> None:
    """Persiste usuarios y roles en el almacén central.

    Es el único punto de escritura (cambio de contraseña, correo y foto de
    perfil, gestión de usuarios). Según la configuración, escribe en el archivo
    local o en Cloud Storage, necesario para que en Cloud Run los cambios
    sobrevivan al reinicio del contenedor.
    """
    user_store.guardar_config(config)


def _find_user(config: dict, username: str) -> dict | None:
    """Busca un usuario por nombre sin distinguir mayúsculas; devuelve None si no existe."""
    username_key = str(username or "").strip().lower()
    return next(
        (u for u in config.get("users", []) if str(u.get("username", "")).strip().lower() == username_key),
        None,
    )


def _ip_cliente(request: Request) -> str:
    """Devuelve la IP real del cliente aunque haya un proxy.

    Prioriza X-Forwarded-For sobre la IP de la conexión directa, que con un
    proxy o balanceador delante sería la del proxy y no la del usuario.
    """
    xff = request.headers.get("x-forwarded-for", "")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else ""


@app.post("/api/login", tags=["Sesion"])
async def login(req: LoginRequest, request: Request):
    """Valida usuario y contraseña y devuelve el JWT con rol, módulos y modelos de IA permitidos.

    Ruta pública. Responde 400 si falta algún dato, 401 si las credenciales no
    coinciden (el mismo mensaje para usuario inexistente y contraseña errónea)
    y 403 si la cuenta está desactivada. Además registra el acceso en la
    auditoría, crea la sesión en memoria y actualiza el último acceso.
    """
    username_input = (req.username or "").strip()
    password_input = req.password or ""
    if not username_input or not password_input:
        raise HTTPException(status_code=400, detail="Debe enviar usuario y contraseña.")

    config = _load_security_config()

    username_key = username_input.lower()
    user = next(
        (
            u
            for u in config["users"]
            if str(u.get("username", "")).strip().lower() == username_key
        ),
        None,
    )
    if not user:
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    if not verify_password(password_input, str(user.get("password", ""))):
        raise HTTPException(status_code=401, detail="Usuario o contraseña incorrectos.")

    if not user.get("active", True):
        raise HTTPException(status_code=403, detail="Tu cuenta está desactivada. Contacta al administrador.")

    role_info = config["roles"].get(user.get("role", "GUEST"), {})
    modelos_permitidos = _modelos_permitidos_de(user)

    # Datos de "Mi Perfil": la primera vez se fija la fecha de alta y en cada
    # login se actualiza el último acceso. Se guardan en el almacén de usuarios
    # (core/user_store.py); no hay tabla de usuarios en la base de datos.
    now_iso = datetime.utcnow().isoformat() + "Z"
    if not user.get("created_at"):
        user["created_at"] = now_iso
    user["last_login"] = now_iso
    _save_security_config(config)

    from core.audit_log import registrar as _registrar_auditoria, ACCION_LOGIN, ENTIDAD_AUTH
    _registrar_auditoria(
        username=user["username"], nombre=user["name"],
        accion=ACCION_LOGIN, entidad=ENTIDAD_AUTH, entidad_desc=user["username"],
        detalle=f"Rol: {user['role']}", ip=_ip_cliente(request),
    )

    SESSION_STORE.create_session(
        user_id=user["username"],
        role=user["role"],
        name=user["name"],
        allowed_modules=role_info.get("modules", []),
    )

    logger.info("[AUTH] Acceso concedido: %s (%s)", user["username"], user["role"])

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user["username"],
            "role": user["role"],
            "name": user["name"],
            "modules": role_info.get("modules", []),
            "modelos_permitidos": modelos_permitidos,
        },
        expires_delta=access_token_expires,
    )

    return {
        "status": "success",
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "name": user["name"],
            "role": user["role"],
            "scope": role_info.get("scope", "LOCAL"),
            "modules": role_info.get("modules", []),
            "modelos_permitidos": modelos_permitidos,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════
# MI PERFIL
# ═══════════════════════════════════════════════════════════════════════════
# No hay tabla de usuarios en la base de datos: el almacén de usuarios
# (core/user_store.py) guarda usuario, contraseña hasheada, nombre y rol. Estas
# rutas escriben siempre con _save_security_config, el mismo punto que usa el
# login, para no divergir.

_AVATAR_MIME_PERMITIDO = {"image/png", "image/jpeg", "image/webp"}
_AVATAR_MAX_BYTES = 700_000  # ~700 KB en base64: de sobra para un avatar cuadrado
_RE_DATA_URL = re.compile(r"^data:(image/[a-zA-Z0-9.+-]+);base64,(.+)$", re.DOTALL)


class ChangePasswordRequest(BaseModel):
    """Contraseña actual y nueva para el cambio desde Mi Perfil."""
    current_password: str
    new_password: str


class UpdateEmailRequest(BaseModel):
    """Nuevo correo de contacto; vacío lo borra."""
    email: str


class AvatarUploadRequest(BaseModel):
    """Foto de perfil como data URL base64 (PNG, JPG o WEBP)."""
    image_data_url: str


def _perfil_publico(user: dict, role_info: dict) -> dict:
    """Arma la vista del perfil que se envía al frontend (sin la contraseña hasheada)."""
    return {
        "username": user.get("username", ""),
        "name": user.get("name", ""),
        "role": user.get("role", ""),
        "role_description": role_info.get("description", ""),
        "email": user.get("email", ""),
        "avatar": user.get("avatar") or None,
        "created_at": user.get("created_at") or None,
        "last_login": user.get("last_login") or None,
    }


@app.get("/api/profile", tags=["Perfil"])
def obtener_perfil(current_user: dict = Depends(get_token_data)):
    """Devuelve el perfil del usuario autenticado; 404 si la cuenta ya no existe."""
    config = _load_security_config()
    user = _find_user(config, current_user.get("sub", ""))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")
    role_info = config.get("roles", {}).get(user.get("role", "GUEST"), {})
    return {"status": "success", "profile": _perfil_publico(user, role_info)}


@app.put("/api/profile/email", tags=["Perfil"])
def actualizar_correo_perfil(req: UpdateEmailRequest, request: Request, current_user: dict = Depends(get_token_data)):
    """Actualiza el correo de contacto del usuario autenticado y lo registra en la auditoría.

    Responde 400 si el formato no es válido; un correo vacío lo borra.
    """
    correo = req.email.strip()
    if correo and not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", correo):
        raise HTTPException(status_code=400, detail="El correo no tiene un formato válido.")

    config = _load_security_config()
    user = _find_user(config, current_user.get("sub", ""))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user["email"] = correo
    _save_security_config(config)
    logger.info("[PERFIL] %s actualizó su correo de contacto.", user["username"])
    from core.audit_log import registrar as _registrar_auditoria, ACCION_EDITAR, ENTIDAD_USUARIO
    _registrar_auditoria(
        username=user["username"], nombre=user["name"], accion=ACCION_EDITAR, entidad=ENTIDAD_USUARIO,
        entidad_desc=user["username"], detalle="Correo actualizado", ip=_ip_cliente(request),
    )
    return {"status": "success", "email": correo}


@app.post("/api/profile/password", tags=["Perfil"])
def cambiar_password_perfil(req: ChangePasswordRequest, request: Request, current_user: dict = Depends(get_token_data)):
    """Cambia la contraseña del usuario autenticado tras verificar la actual.

    Exige mínimo 8 caracteres (400) y responde 401 si la contraseña actual no
    coincide. El cambio queda en la auditoría.
    """
    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener mínimo 8 caracteres.")

    config = _load_security_config()
    user = _find_user(config, current_user.get("sub", ""))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if not verify_password(req.current_password, str(user.get("password", ""))):
        raise HTTPException(status_code=401, detail="La contraseña actual no es correcta.")

    user["password"] = get_password_hash(req.new_password)
    _save_security_config(config)
    logger.info("[PERFIL] %s cambió su contraseña.", user["username"])
    from core.audit_log import registrar as _registrar_auditoria, ACCION_EDITAR, ENTIDAD_USUARIO
    _registrar_auditoria(
        username=user["username"], nombre=user["name"], accion=ACCION_EDITAR, entidad=ENTIDAD_USUARIO,
        entidad_desc=user["username"], detalle="Contraseña actualizada", ip=_ip_cliente(request),
    )
    return {"status": "success", "message": "Contraseña actualizada correctamente."}


def _validar_avatar_data_url(data_url: str) -> str:
    """Valida un avatar en base64 y devuelve el detalle del error, o cadena vacía si es válido.

    Aplica las mismas reglas en Mi Perfil y en el alta o edición de usuarios
    desde Administración.
    """
    match = _RE_DATA_URL.match(data_url or "")
    if not match:
        return "La imagen debe venir como data URL base64 (png, jpg o webp)."
    mime, payload_b64 = match.group(1).lower(), match.group(2)
    if mime not in _AVATAR_MIME_PERMITIDO:
        return "Formato de imagen no soportado. Usa PNG, JPG o WEBP."
    if len(payload_b64) > _AVATAR_MAX_BYTES:
        return "La imagen es muy pesada. Usa una foto más liviana (máx. ~500KB)."
    try:
        base64.b64decode(payload_b64, validate=True)
    except Exception:
        return "La imagen está corrupta o mal codificada."
    return ""


@app.post("/api/profile/avatar", tags=["Perfil"])
def subir_foto_perfil(req: AvatarUploadRequest, current_user: dict = Depends(get_token_data)):
    """Guarda la foto de perfil del usuario autenticado tras validar formato y tamaño (400 si no pasa)."""
    error_avatar = _validar_avatar_data_url(req.image_data_url)
    if error_avatar:
        raise HTTPException(status_code=400, detail=error_avatar)

    config = _load_security_config()
    user = _find_user(config, current_user.get("sub", ""))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user["avatar"] = req.image_data_url
    _save_security_config(config)
    logger.info("[PERFIL] %s actualizó su foto de perfil.", user["username"])
    return {"status": "success", "avatar": req.image_data_url}


@app.delete("/api/profile/avatar", tags=["Perfil"])
def eliminar_foto_perfil(current_user: dict = Depends(get_token_data)):
    """Quita la foto de perfil del usuario autenticado."""
    config = _load_security_config()
    user = _find_user(config, current_user.get("sub", ""))
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    user.pop("avatar", None)
    _save_security_config(config)
    logger.info("[PERFIL] %s eliminó su foto de perfil.", user["username"])
    return {"status": "success"}


# ── Recuperación de contraseña por correo ──────────────────────────────────
# Sin sesión: quien la usa, por definición, no puede iniciar sesión. El mensaje
# de "solicitar" es siempre el mismo, exista o no el usuario o su correo, para
# no revelar qué cuentas existen (enumeración de usuarios).

class PasswordResetRequestModel(BaseModel):
    """Usuario que solicita el código de recuperación."""
    username: str


class PasswordResetConfirmModel(BaseModel):
    """Usuario, código recibido por correo y nueva contraseña."""
    username: str
    code: str
    new_password: str


@app.post("/api/password-reset/request", tags=["Perfil"])
def solicitar_recuperacion_password(req: PasswordResetRequestModel):
    """Envía por correo un código para restablecer la contraseña. Ruta pública.

    Responde siempre el mismo mensaje, exista o no la cuenta, y no reenvía si
    core/password_reset.py aún no lo permite.
    """
    from core.email_service import enviar_correo
    from core.password_reset import generar_codigo, puede_reenviar

    mensaje_generico = {
        "status": "success",
        "message": "Si el usuario existe y tiene un correo registrado, te enviamos un código de verificación.",
    }

    config = _load_security_config()
    user = _find_user(config, req.username)
    if not user or not user.get("email"):
        return mensaje_generico
    if not puede_reenviar(user["username"]):
        return mensaje_generico

    codigo = generar_codigo(user["username"])
    cuerpo = (
        f"Hola {user.get('name', user['username'])},\n\n"
        f"Tu código para restablecer la contraseña de VicMar Data AI es: {codigo}\n"
        "Vence en 15 minutos. Si no pediste este cambio, ignora este correo.\n"
    )
    enviar_correo(user["email"], "VicMar Data AI — Código para restablecer tu contraseña", cuerpo)
    logger.info("[PERFIL] Código de recuperación emitido para %s.", user["username"])
    return mensaje_generico


@app.post("/api/password-reset/confirm", tags=["Perfil"])
def confirmar_recuperacion_password(req: PasswordResetConfirmModel, request: Request):
    """Restablece la contraseña si el código de correo es válido y no expiró. Ruta pública.

    Responde 400 tanto si el usuario no existe como si el código falla, y si la
    contraseña tiene menos de 8 caracteres. El cambio queda en la auditoría.
    """
    from core.password_reset import verificar_y_consumir

    if len(req.new_password) < 8:
        raise HTTPException(status_code=400, detail="La nueva contraseña debe tener mínimo 8 caracteres.")

    config = _load_security_config()
    user = _find_user(config, req.username)
    if not user:
        raise HTTPException(status_code=400, detail="Código inválido o expirado.")

    ok, motivo = verificar_y_consumir(user["username"], req.code)
    if not ok:
        raise HTTPException(status_code=400, detail=motivo)

    user["password"] = get_password_hash(req.new_password)
    _save_security_config(config)
    logger.info("[PERFIL] %s restableció su contraseña vía código de correo.", user["username"])
    from core.audit_log import registrar as _registrar_auditoria, ACCION_EDITAR, ENTIDAD_USUARIO
    _registrar_auditoria(
        username=user["username"], nombre=user["name"], accion=ACCION_EDITAR, entidad=ENTIDAD_USUARIO,
        entidad_desc=user["username"], detalle="Contraseña restablecida por código de correo",
        ip=_ip_cliente(request),
    )
    return {"status": "success", "message": "Contraseña actualizada. Ya puedes iniciar sesión."}


# ═══════════════════════════════════════════════════════════════════════════
# ADMINISTRACIÓN: gestión de usuarios y auditoría
# ═══════════════════════════════════════════════════════════════════════════
# Reutiliza el catálogo de roles del almacén de usuarios (ADMINISTRADOR,
# CONTABILIDAD, RRHH, LOGISTICA, GUEST), cada uno con sus módulos habilitados:
# es el mecanismo de "según el rol se habilitan los módulos" de los
# requisitos. Estas rutas solo agregan el CRUD de usuarios sobre ese catálogo
# y el registro de auditoría (core/audit_log.py).
#
# Todas exigen rol ADMINISTRADOR: _requiere_admin() responde 403 si no.


def _requiere_admin(current_user: dict) -> None:
    """Lanza HTTPException 403 si el usuario del token no es ADMINISTRADOR."""
    if str(current_user.get("role", "")).strip().upper() != "ADMINISTRADOR":
        raise HTTPException(status_code=403, detail="Solo un administrador puede acceder a esto.")


# ── Modelos de IA seleccionables ───────────────────────────────────────────
#
# Selector manual: Flash responde siempre por defecto (rápido, sin costo
# externo); Pro u otro proveedor solo se activan si el usuario los elige
# explícitamente para esa consulta (ver `motor_ia` en QueryRequest,
# api/routes_query.py). Este catálogo decide qué opciones ve cada usuario.
#
# Además del default por rol, cada usuario puede tener su propio campo
# `modelos_permitidos` en el almacén de usuarios, que un ADMINISTRADOR ajusta
# por persona desde Gestión de Usuarios.
# "gemini", "groq" y "nvidia_*" prueban un proveedor o modelo gratuito puntual
# (ver core/nl2sql_engine.py::_select_llm), a diferencia de "flash", que ya
# recorre la cascada automática. Los cinco "nvidia_*" son modelos distintos de
# NVIDIA NIM (config.py::NVIDIA_MODELOS_DISPONIBLES).
MODELOS_IA_VALIDOS = (
    "flash", "pro", "gemini", "groq",
    "nvidia_deepseek_pro", "nvidia_deepseek_flash", "nvidia_kimi", "nvidia_nemotron", "nvidia_muse",
)

MODELOS_IA_POR_DEFECTO: dict[str, list[str]] = {
    "ADMINISTRADOR": list(MODELOS_IA_VALIDOS),
    "CONTABILIDAD": ["flash", "pro"],
    "RRHH": ["flash"],
    "LOGISTICA": ["flash"],
    "GUEST": ["flash"],
}


def _modelos_permitidos_de(usuario: dict) -> list[str]:
    """
    Devuelve los modelos de IA que puede elegir este usuario.

    Prioridad: el override explícito guardado en el propio usuario
    (`modelos_permitidos`) manda sobre el default de su rol — así un admin
    puede darle Pro a una persona puntual de RRHH sin tocar el rol completo.
    Sin override, se usa el default del rol; un rol desconocido cae a
    `["flash"]` (nunca deja a alguien sin ningún modelo).
    """
    override = usuario.get("modelos_permitidos")
    if isinstance(override, list) and override:
        limpio = [m for m in override if m in MODELOS_IA_VALIDOS]
        if limpio:
            return limpio
    rol = str(usuario.get("role", "")).strip().upper()
    return MODELOS_IA_POR_DEFECTO.get(rol, ["flash"])


class CrearUsuarioRequest(BaseModel):
    """Datos para crear un usuario desde Gestión de Usuarios."""
    username: str
    name: str
    email: str = ""
    password: str
    role: str
    avatar: str | None = None
    modelos_permitidos: list[str] | None = None


class EditarUsuarioRequest(BaseModel):
    """Cambios parciales de un usuario; los campos en None no se modifican."""
    name: str | None = None
    email: str | None = None
    role: str | None = None
    new_password: str | None = None
    active: bool | None = None
    avatar: str | None = None
    modelos_permitidos: list[str] | None = None


def _es_usuario_protegido(u: dict) -> bool:
    """
    Indica si es la cuenta del desarrollador, que nadie puede borrar,
    desactivar ni editar desde Gestión de Usuarios, ni siquiera otro
    ADMINISTRADOR.

    Existe por un riesgo concreto: esta cuenta es la dueña de la seña de
    desarrollador (`core/modo_desarrollador.py`). Si otro administrador
    pudiera eliminarla, el sistema se quedaría sin desarrollador; y si
    pudiera cambiarle la contraseña, entraría con ella y usaría la seña como
    si fuera él. Por eso la protección cubre las tres operaciones (borrar,
    desactivar y editar), no solo el borrado.

    Se reconoce por dos vías independientes, y basta una:
      · la marca `protected: true` en security_config.json, y
      · ser el dueño registrado de la seña de desarrollador.
    Así, aunque alguien quite la marca del archivo a mano, la cuenta que
    posee la seña sigue protegida.
    """
    if not u:
        return False
    if bool(u.get("protected")):
        return True
    try:
        from core.modo_desarrollador import dueno_registrado

        dueno = dueno_registrado()
        return bool(dueno) and str(u.get("username", "")).strip().lower() == dueno
    except Exception:
        # Si el módulo no está disponible, la marca del archivo manda.
        return False


def _usuario_publico(u: dict) -> dict:
    """Arma la vista de un usuario para Gestión de Usuarios (sin la contraseña)."""
    return {
        "username": u.get("username", ""),
        "name": u.get("name", ""),
        "email": u.get("email", ""),
        "role": u.get("role", ""),
        "active": u.get("active", True),
        "created_at": u.get("created_at"),
        "last_login": u.get("last_login"),
        "avatar": u.get("avatar"),
        # El frontend usa esta bandera para no dibujar siquiera los botones de
        # editar/desactivar/eliminar en esa fila. La seguridad real, de todos
        # modos, está en los endpoints: ocultar un botón no protege nada por
        # sí solo.
        "protected": _es_usuario_protegido(u),
        "modelos_permitidos": _modelos_permitidos_de(u),
    }


@app.get("/api/admin/roles", tags=["Administración"])
def listar_roles(current_user: dict = Depends(get_token_data)):
    """Devuelve los roles con su descripción y módulos. Solo ADMINISTRADOR."""
    _requiere_admin(current_user)
    config = _load_security_config()
    roles = [
        {"id": nombre, "description": info.get("description", ""), "modules": info.get("modules", [])}
        for nombre, info in config.get("roles", {}).items()
    ]
    return {"status": "success", "roles": roles}


@app.get("/api/admin/users", tags=["Administración"])
def listar_usuarios(current_user: dict = Depends(get_token_data)):
    """Devuelve todos los usuarios, los más recientes primero y sin contraseñas. Solo ADMINISTRADOR."""
    _requiere_admin(current_user)
    config = _load_security_config()
    usuarios = sorted(
        (_usuario_publico(u) for u in config.get("users", [])),
        key=lambda u: u.get("created_at") or "",
        reverse=True,
    )
    return {"status": "success", "users": usuarios}


@app.post("/api/admin/users", tags=["Administración"])
def crear_usuario(req: CrearUsuarioRequest, request: Request, current_user: dict = Depends(get_token_data)):
    """Crea un usuario con contraseña hasheada y lo registra en la auditoría. Solo ADMINISTRADOR.

    Responde 400 si el usuario ya existe o falta, si el rol o los modelos de
    IA no son válidos, si la contraseña tiene menos de 8 caracteres o si el
    avatar no pasa la validación.
    """
    _requiere_admin(current_user)
    username = req.username.strip().lower()
    if not username:
        raise HTTPException(status_code=400, detail="El usuario es obligatorio.")
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail="La contraseña debe tener mínimo 8 caracteres.")

    config = _load_security_config()
    if _find_user(config, username):
        raise HTTPException(status_code=400, detail=f"Ya existe un usuario '{username}'.")
    if req.role not in config.get("roles", {}):
        raise HTTPException(status_code=400, detail="Rol no válido.")
    if req.avatar:
        error_avatar = _validar_avatar_data_url(req.avatar)
        if error_avatar:
            raise HTTPException(status_code=400, detail=error_avatar)
    if req.modelos_permitidos:
        invalidos = [m for m in req.modelos_permitidos if m not in MODELOS_IA_VALIDOS]
        if invalidos:
            raise HTTPException(status_code=400, detail=f"Modelo(s) de IA no válido(s): {', '.join(invalidos)}.")

    nuevo = {
        "username": username,
        "password": get_password_hash(req.password),
        "name": req.name.strip() or username,
        "role": req.role,
        "email": req.email.strip(),
        "active": True,
        "created_at": datetime.utcnow().isoformat() + "Z",
    }
    if req.avatar:
        nuevo["avatar"] = req.avatar
    if req.modelos_permitidos:
        nuevo["modelos_permitidos"] = req.modelos_permitidos
    config.setdefault("users", []).append(nuevo)
    _save_security_config(config)

    from core.audit_log import registrar as _registrar_auditoria, ACCION_CREAR, ENTIDAD_USUARIO
    _registrar_auditoria(
        username=current_user.get("sub", ""), nombre=current_user.get("name", ""),
        accion=ACCION_CREAR, entidad=ENTIDAD_USUARIO, entidad_desc=username,
        detalle=f"Rol: {req.role}", ip=_ip_cliente(request),
    )
    return {"status": "success", "user": _usuario_publico(nuevo)}


@app.put("/api/admin/users/{username}", tags=["Administración"])
def editar_usuario_admin(username: str, req: EditarUsuarioRequest, request: Request, current_user: dict = Depends(get_token_data)):
    """Edita nombre, correo, rol, contraseña, estado, foto o modelos de IA de un usuario. Solo ADMINISTRADOR.

    La cuenta protegida del desarrollador solo la modifica su dueño (403) y
    nadie puede desactivarse a sí mismo (400). Los cambios quedan en la
    auditoría.
    """
    _requiere_admin(current_user)
    config = _load_security_config()
    user = _find_user(config, username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    es_uno_mismo = user["username"].strip().lower() == str(current_user.get("sub", "")).strip().lower()

    # La cuenta del desarrollador solo la edita su propio dueño. Un
    # administrador cualquiera no puede cambiarle la contraseña (entraría con
    # ella y heredaría la seña de desarrollador), ni el rol, ni desactivarla.
    if _es_usuario_protegido(user) and not es_uno_mismo:
        raise HTTPException(
            status_code=403,
            detail="Esta es la cuenta del desarrollador del sistema: solo su propio dueño puede modificarla.",
        )

    cambios = []

    if req.name is not None and req.name.strip():
        user["name"] = req.name.strip()
        cambios.append("nombre")
    if req.email is not None:
        user["email"] = req.email.strip()
        cambios.append("correo")
    if req.role is not None:
        if req.role not in config.get("roles", {}):
            raise HTTPException(status_code=400, detail="Rol no válido.")
        user["role"] = req.role
        cambios.append(f"rol={req.role}")
    if req.new_password:
        if len(req.new_password) < 8:
            raise HTTPException(status_code=400, detail="La nueva contraseña debe tener mínimo 8 caracteres.")
        user["password"] = get_password_hash(req.new_password)
        cambios.append("contraseña")
    if req.active is not None:
        if not req.active and es_uno_mismo:
            raise HTTPException(status_code=400, detail="No puedes desactivarte a ti mismo.")
        user["active"] = req.active
        cambios.append("activado" if req.active else "desactivado")
    if req.avatar:
        error_avatar = _validar_avatar_data_url(req.avatar)
        if error_avatar:
            raise HTTPException(status_code=400, detail=error_avatar)
        user["avatar"] = req.avatar
        cambios.append("foto de perfil")
    if req.modelos_permitidos is not None:
        invalidos = [m for m in req.modelos_permitidos if m not in MODELOS_IA_VALIDOS]
        if invalidos:
            raise HTTPException(status_code=400, detail=f"Modelo(s) de IA no válido(s): {', '.join(invalidos)}.")
        # Lista vacía = "sin override": vuelve al default de su rol en vez
        # de dejar al usuario sin ningún motor.
        user["modelos_permitidos"] = req.modelos_permitidos or None
        if user["modelos_permitidos"] is None:
            user.pop("modelos_permitidos", None)
        cambios.append(f"modelos_ia={req.modelos_permitidos or 'default del rol'}")

    _save_security_config(config)

    from core.audit_log import registrar as _registrar_auditoria, ACCION_EDITAR, ENTIDAD_USUARIO
    _registrar_auditoria(
        username=current_user.get("sub", ""), nombre=current_user.get("name", ""),
        accion=ACCION_EDITAR, entidad=ENTIDAD_USUARIO, entidad_desc=username,
        detalle=", ".join(cambios) or "sin cambios", ip=_ip_cliente(request),
    )
    return {"status": "success", "user": _usuario_publico(user)}


@app.delete("/api/admin/users/{username}", tags=["Administración"])
def eliminar_usuario_admin(username: str, request: Request, current_user: dict = Depends(get_token_data)):
    """Elimina un usuario y lo registra en la auditoría. Solo ADMINISTRADOR.

    No permite borrarse a sí mismo (400) ni borrar la cuenta protegida del
    desarrollador (403).
    """
    _requiere_admin(current_user)
    if username.strip().lower() == str(current_user.get("sub", "")).strip().lower():
        raise HTTPException(status_code=400, detail="No puedes eliminarte a ti mismo.")

    config = _load_security_config()
    user = _find_user(config, username)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # Cuenta del desarrollador: no se borra desde aquí bajo ninguna
    # circunstancia. El frontend ni siquiera muestra el botón, pero la regla
    # tiene que vivir en el servidor: una llamada directa a la API se salta
    # cualquier control que solo exista en la interfaz.
    if _es_usuario_protegido(user):
        raise HTTPException(
            status_code=403,
            detail="No se puede eliminar la cuenta del desarrollador del sistema.",
        )

    config["users"] = [u for u in config.get("users", []) if u is not user]
    _save_security_config(config)

    from core.audit_log import registrar as _registrar_auditoria, ACCION_ELIMINAR, ENTIDAD_USUARIO
    _registrar_auditoria(
        username=current_user.get("sub", ""), nombre=current_user.get("name", ""),
        accion=ACCION_ELIMINAR, entidad=ENTIDAD_USUARIO, entidad_desc=username,
        ip=_ip_cliente(request),
    )
    return {"status": "success"}


@app.get("/api/admin/audit", tags=["Administración"])
def obtener_auditoria(
    q: str = Query(""), action: str = Query(""), entity: str = Query(""),
    date_from: str = Query(""), date_to: str = Query(""),
    current_user: dict = Depends(get_token_data),
):
    """Devuelve los eventos de auditoría filtrados por texto, acción, entidad y fechas, con estadísticas. Solo ADMINISTRADOR."""
    _requiere_admin(current_user)
    from core.audit_log import listar as _listar_auditoria, estadisticas as _estadisticas_auditoria
    eventos = _listar_auditoria(q=q, accion=action, entidad=entity, desde=date_from, hasta=date_to)
    return {"status": "success", "events": eventos, "stats": _estadisticas_auditoria()}


@app.get("/api/admin/audit/export", tags=["Administración"])
def exportar_auditoria(current_user: dict = Depends(get_token_data)):
    """Descarga la auditoría completa en un .xlsx con formato, fila de total y autofiltro. Solo ADMINISTRADOR."""
    _requiere_admin(current_user)
    import io
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from fastapi.responses import StreamingResponse
    from core.audit_log import listar as _listar_auditoria

    eventos = _listar_auditoria(limite=100000)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Auditoría"
    ws.freeze_panes = "A2"
    ws.row_dimensions[1].height = 30
    thin = Side(border_style="thin", color="D0D7E3")
    brd = Border(left=thin, right=thin, top=thin, bottom=thin)
    hdr_fill = PatternFill("solid", fgColor="0E7A4A")
    hdr_font = Font(color="FFFFFF", bold=True, size=11)
    hdr_align = Alignment(horizontal="center", vertical="center", wrap_text=True)
    alt_fill = PatternFill("solid", fgColor="F0F2F5")
    pie_fill = PatternFill("solid", fgColor="E6F4EA")

    headers = ["#", "Fecha/Hora", "Usuario", "Nombre", "Acción", "Entidad", "Descripción", "Detalle", "IP"]
    ncols = len(headers)
    for ci, h in enumerate(headers, 1):
        c = ws.cell(row=1, column=ci, value=h)
        c.fill, c.font, c.alignment, c.border = hdr_fill, hdr_font, hdr_align, brd

    # Largo máximo por columna, para fijar los anchos al final.
    anchos = [len(h) for h in headers]
    for i, ev in enumerate(eventos, 1):
        fill = alt_fill if i % 2 == 0 else None
        vals = [
            i, ev.get("fecha", ""), ev.get("username", ""), ev.get("nombre", ""),
            ev.get("accion", ""), ev.get("entidad", ""), ev.get("entidad_desc", ""),
            ev.get("detalle", ""), ev.get("ip", ""),
        ]
        for ci, v in enumerate(vals, 1):
            c = ws.cell(row=i + 1, column=ci, value=v)
            c.border = brd
            if fill:
                c.fill = fill
            if v is not None:
                anchos[ci - 1] = max(anchos[ci - 1], len(str(v)))

    if eventos:
        fila_pie = len(eventos) + 2
        for ci in range(1, ncols + 1):
            c = ws.cell(row=fila_pie, column=ci)
            c.fill = pie_fill
            c.border = brd
        c = ws.cell(row=fila_pie, column=1, value="Total de eventos")
        c.font = Font(bold=True)
        c = ws.cell(row=fila_pie, column=2, value=len(eventos))
        c.font = Font(bold=True)
        c.number_format = "#,##0"
        # La etiqueta del pie es más larga que los números de la columna "#";
        # se incluye en el ancho para que no quede recortada.
        anchos[0] = max(anchos[0], len("Total de eventos"))
        # Auto-filtro: cabecera + datos, excluyendo la fila de pie.
        ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=ncols).column_letter}{len(eventos) + 1}"
    else:
        ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=ncols).column_letter}1"

    # Anchos calculados por contenido tras escribir los datos:
    # ancho = min(60, max(largo cabecera, largo máx. de celdas de datos) + 2).
    for ci, a in enumerate(anchos, 1):
        ws.column_dimensions[ws.cell(row=1, column=ci).column_letter].width = min(60, a + 2)

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"auditoria_{datetime.utcnow().date().isoformat()}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/databases", tags=["Sesion"])
def fetch_databases(req: DatabasesRequest, current_user: dict = Depends(get_token_data)):
    """Lista, sin duplicados, las bases del servidor SQL Server indicado. Requiere usuario autenticado.

    Sin credenciales en la petición usa las de backend/.env; si tampoco hay,
    recurre a la autenticación de Windows.
    """
    from db_connector import get_available_databases, normalize_sql_server_host
    _ = current_user

    effective_user = req.user if req.user else DEFAULT_USER
    effective_password = req.password if req.password else DEFAULT_PASSWORD
    has_sql_credentials = bool(str(effective_user or "").strip() or str(effective_password or "").strip())
    if req.auth_type == "Windows Authentication":
        use_windows_auth = True
    elif req.auth_type == "SQL Server Authentication":
        use_windows_auth = not has_sql_credentials
    else:
        use_windows_auth = not has_sql_credentials

    effective_host = normalize_sql_server_host(req.host)
    if not effective_host:
        raise HTTPException(status_code=400, detail="Debe indicar un host SQL Server.")

    effective_driver = _resolve_driver_local(req.driver)

    databases = get_available_databases(
        host=effective_host,
        driver=effective_driver,
        user=effective_user if not use_windows_auth else None,
        password=effective_password if not use_windows_auth else None,
        windows_auth=use_windows_auth,
    )

    prioritized = []
    seen = set()
    for db_info in databases:
        db_id = db_info.get("database", "").strip()
        if db_id and db_id.upper() not in seen:
            prioritized.append(db_info)
            seen.add(db_id.upper())

    return {"databases": prioritized, "host": effective_host}


@app.post("/api/connect", tags=["Sesion"])
def connect(
    req: ConnectRequest,
    background_tasks: BackgroundTasks,
    request: Request,
    current_user: dict = Depends(get_token_data),
):
    """Conecta la sesión del usuario a una base de SQL Server (o a un archivo SQLite local).

    Requiere sesión iniciada (401 si no). Si el host local falla, prueba hosts
    alternativos. Responde de inmediato: si el esquema de esa empresa ya está
    en la caché de la sesión lo restaura; si no, carga en el momento la lista
    de tablas con datos y deja el enriquecimiento completo (columnas y
    relaciones semánticas) en segundo plano. También prepara el cliente de IA,
    identifica el nombre comercial y registra en la auditoría qué empresa se
    activó.
    """
    from core.deepseek_client import DeepSeekClient
    from db_connector import (
        SQLServerConnector,
        build_connection_string,
        get_sql_server_host_candidates,
        normalize_sql_server_host,
    )
    from knowledge.memory_consolidator import ejecutar_consolidacion
    from knowledge.semantic_relations import build_semantic_relations

    user_id = current_user.get("sub")
    session = SESSION_STORE.get_session(user_id)
    if not session:
        raise HTTPException(status_code=401, detail="Sesion no iniciada o expirada.")

    requested_database = (req.database or "").strip()
    is_local_file = requested_database.upper() == "LOCAL_FILE"
    effective_host = normalize_sql_server_host(req.host)
    if not is_local_file and not effective_host:
        raise HTTPException(status_code=400, detail="Debe indicar un host SQL Server.")
    if not requested_database and not is_local_file:
        raise HTTPException(status_code=400, detail="Debe indicar la base de datos objetivo.")

    effective_local_path = req.localPath
    if req.database == "LOCAL_FILE" and not effective_local_path:
        db_path = BASE_DIR / "quantum_data.db"
        if db_path.exists():
            effective_local_path = str(db_path)

    effective_user = req.user if req.user else DEFAULT_USER
    effective_password = req.password if req.password else DEFAULT_PASSWORD
    has_sql_credentials = bool(str(effective_user or "").strip() or str(effective_password or "").strip())
    if req.auth_type == "Windows Authentication":
        use_windows_auth = True
    elif req.auth_type == "SQL Server Authentication":
        use_windows_auth = not has_sql_credentials
    else:
        use_windows_auth = not has_sql_credentials

    # Driver: el solicitado en la conexión si está instalado; si no, el mejor disponible.
    effective_driver = _resolve_driver_local(req.driver)
    logger.info(f"[CONNECT] Driver resuelto: {effective_driver} (solicitado: {req.driver})")
    
    conn_str = build_connection_string(
        host=effective_host,
        database=requested_database if requested_database and not is_local_file else EXECUTION_DB,
        driver=effective_driver,
        user=effective_user if not use_windows_auth else None,
        password=effective_password if not use_windows_auth else None,
        windows_auth=use_windows_auth,
        local_path=effective_local_path,
    )

    mask_conn = conn_str.split("PWD=")[0] + "PWD=****" if "PWD=" in conn_str else conn_str
    logger.info(f"[CONNECT] Solicitando enlace a Host: {effective_host} | DB: {requested_database} | Driver: {effective_driver}")
    
    connector = SQLServerConnector(conn_str)
    ok, msg = connector.connect()
    attempted_hosts = [effective_host] if effective_host else []
    if not ok and not is_local_file:
        host_candidates = get_sql_server_host_candidates(effective_host)
        for candidate_host in host_candidates[1:]:
            attempted_hosts.append(candidate_host)
            alt_conn_str = build_connection_string(
                host=candidate_host,
                database=requested_database if requested_database and not is_local_file else EXECUTION_DB,
                driver=effective_driver,
                user=effective_user if not use_windows_auth else None,
                password=effective_password if not use_windows_auth else None,
                windows_auth=use_windows_auth,
                local_path=effective_local_path,
            )
            alt_connector = SQLServerConnector(alt_conn_str)
            alt_ok, alt_msg = alt_connector.connect()
            if alt_ok:
                logger.info(
                    "[CONNECT] Conexion local resuelta con host alterno: %s (solicitado: %s)",
                    candidate_host,
                    effective_host,
                )
                effective_host = candidate_host
                conn_str = alt_conn_str
                connector = alt_connector
                ok, msg = alt_ok, alt_msg
                break
            msg = alt_msg

    if not ok:
        logger.error(f"[CONNECTION ERROR] Failed to connect: {msg}")
        hint = ""
        if attempted_hosts:
            hint = f" Hosts intentados: {', '.join(attempted_hosts)}."
        raise HTTPException(status_code=400, detail=f"{msg}{hint}")

    # La respuesta vuelve de inmediato para no bloquear la interfaz; la
    # sincronización pesada del esquema queda en una tarea en segundo plano.

    # Cliente de IA mínimo, listo para responder saludos mientras se sincroniza.
    api_key = req.api_key or os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        if session.client and getattr(session.client, "_api_key", None):
            api_key = session.client._api_key
        elif getattr(session, "api_key", None):
            api_key = session.api_key

    db_context_name = requested_database if not req.localPath else os.path.basename(req.localPath)
    
    initial_client = DeepSeekClient(
        api_key=api_key,
        database_name=db_context_name,
        is_sqlite=connector.is_sqlite,
        is_postgres=connector.is_postgres,
    )
    initial_client.user_role = session.role
    initial_client.user_name = session.name
    
    session.update_connection(
        connector=connector,
        client=initial_client,
        context_db=db_context_name,
        conn_str=conn_str,
        api_key=api_key,
    )
    # Persiste un estado no sensible (la empresa activa) por si el backend se
    # reinicia antes de que termine la sincronización en segundo plano.
    SESSION_STORE.persist(session.user_id)

    # La caché del Pulso BI no se limpia al cambiar de empresa: está indexada
    # por (usuario, empresa, año, mes) —ver get_bi_pulse()—, así que cambiar de
    # empresa no invalida los pulsos de otros usuarios ni de otras empresas de
    # este mismo usuario. Al volver a una empresa visitada hace menos del TTL,
    # las tarjetas responden al instante; el TTL corto se encarga de la vigencia.

    # ====================================================================
    # CACHÉ DE ESQUEMA COMPLETO POR EMPRESA
    # Cada empresa tiene su propia clave en full_schema_cache. Al cambiar
    # de empresa el sistema responde de inmediato con los datos correctos:
    # - Empresa ya visitada → esquema restaurado en <1 ms, sin sincronizar.
    # - Empresa nueva      → carga rápida + enriquecimiento en segundo plano.
    # El aislamiento por clave garantiza que nunca se mezclan datos entre
    # empresas distintas aunque el usuario cambie rápidamente.
    # ====================================================================
    context_key = db_context_name.strip().upper() if db_context_name else ""
    if not hasattr(session, "full_schema_cache") or not isinstance(session.full_schema_cache, dict):
        session.full_schema_cache = {}

    _cached_full = session.full_schema_cache.get(context_key) if context_key else None
    schema_from_cache = bool(
        _cached_full
        and isinstance(_cached_full.get("schema_dict"), dict)
        and _cached_full["schema_dict"]
    )
    fast_schema: dict = {}

    if schema_from_cache:
        # Esquema completo restaurado desde la caché, sin sincronizar de nuevo.
        fast_schema = _cached_full["schema_dict"]
        session.schema_dict = fast_schema
        session.schema_text = _cached_full.get("schema_text", "")
        session.semantic_relations = _cached_full.get("semantic_relations", "")
        if not hasattr(session, "schema_cache") or not isinstance(session.schema_cache, dict):
            session.schema_cache = {}
        session.schema_cache[context_key] = fast_schema
        if session.client:
            session.client.set_schema(session.schema_text, session.semantic_relations)
        logger.info(
            "[SCHEMA_CACHE] ⚡ Esquema restaurado para '%s' (%d entidades) — sin background sync",
            db_context_name, len(fast_schema)
        )
    else:
        # ====================================================================
        # CARGA RÁPIDA (síncrona) con sys.partitions
        # Identifica las tablas con datos en <100 ms y las deja disponibles de
        # inmediato: se puede consultar sin esperar la tarea en segundo plano.
        # ====================================================================
        if not connector.is_sqlite and not connector.is_postgres and db_context_name and db_context_name.upper() not in ('MASTER', ''):
            try:
                with connector.engine.connect() as _conn:
                    from sqlalchemy import text as _text
                    from db_connector import _quote_db_name, _validate_db_name
                    _safe_db = _validate_db_name(db_context_name, "fast_schema_db")
                    _db_q = _quote_db_name(_safe_db)
                    tables_with_data = connector.get_tables_with_data_fast(_conn, db_q=_db_q)
                if tables_with_data:
                    # Esquema mínimo: tablas con datos, todavía sin columnas.
                    fast_schema = {
                        tbl: {"type": "TABLA", "columns": [], "row_count": cnt}
                        for tbl, cnt in tables_with_data.items()
                    }
                    session.schema_dict = fast_schema
                    if not hasattr(session, "schema_cache") or not isinstance(session.schema_cache, dict):
                        session.schema_cache = {}
                    session.schema_cache[context_key] = fast_schema
                    logger.info(
                        "[FASE0] Esquema rápido listo: %d tablas con datos en '%s'",
                        len(fast_schema), db_context_name
                    )
            except Exception as _e:
                logger.warning("[FASE0] sys.partitions rápido falló: %s", _e)

    # ====================================================================
    # ENRIQUECIMIENTO COMPLETO EN SEGUNDO PLANO
    # Añade columnas y análisis semántico sin bloquear la respuesta. Se
    # omite si el esquema completo ya estaba en caché (schema_from_cache).
    # ====================================================================
    def finish_full_sync(session_ref, conn_ref, target_db: str):
        """Completa el esquema de `target_db` (columnas y relaciones), lo entrega a la IA y lo guarda en caché.

        Corre como tarea en segundo plano; los errores solo se registran en el log.
        """
        try:
            logger.info("[SYNC] Enriqueciendo esquema completo para '%s'", target_db)
            # Mismo filtro de curaduría que usa BI, por velocidad y coherencia entre ambos.
            full_schema = resolve_schema_for_db(session_ref, target_db, refresh=True, logger=logger)

            if not full_schema and fast_schema:
                full_schema = fast_schema  # conserva el esquema mínimo si falló el completo
                
            full_text = conn_ref.get_schema_as_text(
                database_override=target_db if target_db and target_db.upper() not in ('MASTER', '') else None,
                schema_dict=full_schema
            )
            full_semantics = build_semantic_relations(full_schema)

            session_ref.schema_dict = full_schema
            session_ref.schema_text = full_text
            session_ref.semantic_relations = full_semantics
            if not hasattr(session_ref, "schema_cache") or not isinstance(session_ref.schema_cache, dict):
                session_ref.schema_cache = {}
            _sync_key = str(target_db or session_ref.context_db or "").strip().upper()
            if _sync_key and isinstance(full_schema, dict) and full_schema:
                session_ref.schema_cache[_sync_key] = full_schema

            if session_ref.client:
                session_ref.client.set_schema(full_text, full_semantics)

            # ── Caché del esquema completo de la empresa ─────────────────
            # La próxima vez que el usuario seleccione esta empresa, el
            # esquema se restaura en <1 ms sin volver a sincronizar.
            if not hasattr(session_ref, "full_schema_cache") or not isinstance(session_ref.full_schema_cache, dict):
                session_ref.full_schema_cache = {}
            if _sync_key and isinstance(full_schema, dict) and full_schema:
                session_ref.full_schema_cache[_sync_key] = {
                    "schema_dict": full_schema,
                    "schema_text": full_text,
                    "semantic_relations": full_semantics,
                }
                logger.info("[SCHEMA_CACHE] 💾 Guardado en caché para '%s' (%d entidades)", target_db, len(full_schema))
                # Persiste el esquema recién sincronizado para que un reinicio
                # del backend no obligue a repetir la sincronización.
                SESSION_STORE.persist(session_ref.user_id)

            if not conn_ref.is_sqlite and not conn_ref.is_postgres:
                # Solo se consolida la memoria de la empresa. El centinela
                # proactivo (QuantumSentinel.run_patrol) no se invoca: depende de
                # mirror.run_discovery_scan() y mirror.auto_heal(), que no existen
                # en MirrorManager, así que no se simula una "autocuración" que no
                # está implementada.
                ejecutar_consolidacion(session_ref.context_db)

            logger.info("[SYNC] Sincronizacion completa para '%s' (%d entidades)", target_db, len(full_schema))
        except Exception as e:
            logger.error("[SYNC] Error en sincronizacion pesada: %s", e)

    if not schema_from_cache:
        background_tasks.add_task(finish_full_sync, session, connector, db_context_name)


    # ====================================================================
    # IDENTIDAD DE LA EMPRESA (nombre comercial real)
    # Se intenta leer de sys300 (o de tb_empres) cuando la base es de negocio.
    # ====================================================================
    biz_name = requested_database
    if not connector.is_sqlite and not connector.is_postgres and db_context_name and db_context_name.upper() not in ('MASTER', ''):
        try:
            with connector.engine.connect() as _conn:
                from sqlalchemy import text as _text
                from db_connector import _quote_db_name, _validate_db_name
                _safe_db = _validate_db_name(db_context_name, "biz_name_db")
                _db_q = _quote_db_name(_safe_db)
                
                # ESTRATEGIA A: sys300 (Contabilidad)
                try:
                    _res = _conn.execute(_text(f"SELECT TOP 1 nombre FROM {_db_q}.dbo.sys300 WHERE codigo IS NOT NULL")).fetchone()
                    if _res and _res[0]:
                        biz_name = str(_res[0]).strip()
                except Exception:
                    pass
                
                # ESTRATEGIA B: tb_empres (RRHH) si A falló o devolvió el mismo ID
                if biz_name == requested_database:
                    try:
                        _res_b = _conn.execute(_text(f"SELECT TOP 1 emp_nombre FROM {_db_q}.dbo.tb_empres")).fetchone()
                        if _res_b and _res_b[0]:
                            biz_name = str(_res_b[0]).strip()
                    except Exception:
                        pass
                
                if biz_name != requested_database:
                    logger.info("[IDENTIDAD] Empresa identificada como: %s", biz_name)
        except Exception:
            pass

    # Auditoría: qué empresa activó cada usuario y cuándo. Es el evento que un
    # auditor pediría primero ante la duda de "¿quién vio los datos de la
    # empresa X y en qué momento?".
    if not is_local_file and db_context_name and db_context_name.upper() not in ("MASTER", ""):
        from core.audit_log import registrar as _registrar_auditoria, ACCION_CONSULTAR, ENTIDAD_EMPRESA
        _registrar_auditoria(
            username=current_user.get("sub", ""), nombre=current_user.get("name", ""),
            accion=ACCION_CONSULTAR, entidad=ENTIDAD_EMPRESA, entidad_desc=db_context_name.upper(),
            detalle=f"Empresa activada: {biz_name}" if biz_name != requested_database else "",
            ip=_ip_cliente(request),
        )

    return {
        "status": "connected",
        "database": requested_database,
        "selected_company_code": requested_database,
        "business_name": biz_name,
        "host": effective_host,
        "role": session.role,
        "schema_dict": {},  # El frontend no necesita el esquema aquí
        "is_syncing": len(fast_schema) == 0 and not schema_from_cache,
        "tables_detected": len(fast_schema),
        "schema_cached": schema_from_cache,  # True = esquema restaurado desde la caché
    }



@app.post("/api/disconnect", tags=["Sesion"])
async def disconnect(current_user: dict = Depends(get_token_data)):
    """Cierra la sesión en memoria del usuario autenticado."""
    user_id = current_user.get("sub")
    SESSION_STORE.remove_session(user_id)
    return {"status": "Sesion cerrada correctamente"}





@app.get("/api/diagnostic", tags=["Sistema"])
async def get_diagnostic(current_user: dict = Depends(get_token_data)):
    """Devuelve un diagnóstico de la sesión: empresa activa, entidades y vistas mapeadas, rol y módulos.

    Requiere usuario autenticado; sin conexión activa responde "inactive".
    """
    user_id = current_user.get("sub")
    session = SESSION_STORE.get_session(user_id)
    if not session or not session.connector:
        return {"status": "inactive", "message": "No hay motor de datos activo para su sesion privada."}

    schema = session.schema_dict
    tables_count = len(schema)
    views_count = len([k for k, v in schema.items() if v.get("type") == "VISTA"])

    return {
        "status": "active",
        "user_identity": session.name,
        "sucursal_activa": session.context_db,
        "metrics": {
            "entidades_mapeadas": tables_count,
            "vistas_inteligentes": views_count,
            "autoridad": session.role,
            "salud_sistema": "OPTIMAL_V2",
        },
        "modules": session.allowed_modules,
    }


@app.get("/api/discovery", tags=["Sistema"])
async def discovery_scan(current_user: dict = Depends(get_token_data)):
    """Devuelve hasta 10 entidades del esquema de la sesión activa. Requiere usuario autenticado."""
    user_id = current_user.get("sub")
    session = SESSION_STORE.get_session(user_id)
    if not session or not session.connector:
        return {"status": "OFFLINE", "message": "Inicie sesion y conecte para activar escaneo."}

    schema = session.schema_dict
    entities = []
    for table_name, _meta in list(schema.items())[:10]:
        entities.append({"entity": table_name.title(), "table": table_name})

    return {
        "status": "SYNCHRONIZED",
        "user": session.user_id,
        "detected_entities": entities,
        "master_dna": "AVAILABLE" if session.master_schema_text else "LOCAL_ONLY",
    }


@app.delete("/api/cache/clear", tags=["Cache"])
async def clear_cache_endpoint(current_user: dict = Depends(get_token_data)):
    """Vacía la caché de consultas y devuelve cuántas entradas eliminó. Cualquier usuario autenticado."""
    _ = current_user
    removed = clear_cache()
    return {"status": "Cache limpiado", "entries_removed": removed}


@app.post("/api/companies", tags=["Sistema"])
def get_companies(req: CompaniesRequest, current_user: dict = Depends(get_token_data)):
    """Devuelve el listado unificado de empresas del servidor. Requiere usuario autenticado.

    La fuente de verdad son las bases en línea (sys.databases); el nombre
    comercial, el nombre corto y el RUC se completan desde la tabla sys300 de
    la base catálogo (`database`, por defecto PROYECTO) cuando existe.
    """
    from db_connector import SQLServerConnector, build_connection_string, normalize_sql_server_host, get_available_databases
    _ = current_user

    effective_user = req.user if req.user else DEFAULT_USER
    effective_password = req.password if req.password else DEFAULT_PASSWORD
    has_sql_credentials = bool(str(effective_user or "").strip() or str(effective_password or "").strip())
    
    if req.auth_type == "Windows Authentication":
        use_windows_auth = True
    else:
        use_windows_auth = not has_sql_credentials

    effective_host = normalize_sql_server_host(req.host)
    if not effective_host:
        return {"status": "error", "companies": [], "error": "Debe indicar un host SQL Server."}

    # 1. Bases en línea del servidor (sys.databases): fuente de verdad técnica
    raw_dbs = get_available_databases(
        host=req.host,
        driver=req.driver or "AUTO",
        user=effective_user if not use_windows_auth else None,
        password=effective_password if not use_windows_auth else None,
        windows_auth=use_windows_auth
    )

    if not raw_dbs:
        return {
            "status": "error",
            "companies": [],
            "source": "sys.databases",
            "error": "No se encontraron bases de datos en el servidor indicado o error de conexión."
        }

    # 2. Catálogo de negocio (sys300) para enriquecer los nombres
    business_map = {}
    source_info = "SQL Server Root (sys.databases)"
    
    try:
        # Driver local para la conexión a la base catálogo
        effective_driver = _resolve_driver_local(req.driver)
        
        db_catalog = (req.database or "PROYECTO").strip()
        conn_str = build_connection_string(
            host=effective_host,
            database=db_catalog,
            driver=effective_driver,
            user=effective_user if not use_windows_auth else None,
            password=effective_password if not use_windows_auth else None,
            windows_auth=use_windows_auth,
        )
        
        connector = SQLServerConnector(conn_str)
        ok, _ = connector.connect()
        if ok:
            with connector.engine.connect() as conn:
                # Catálogo de empresas en sys300
                query = text(f"SELECT codigo, nombre, nomcorto, ruc FROM [{db_catalog}].dbo.sys300 WHERE codigo IS NOT NULL")
                result = conn.execute(query)
                for row in result.fetchall():
                    # Se indexa por código, que suele coincidir con el nombre de la base.
                    key = str(row.codigo or "").strip().upper()
                    if key:
                        business_map[key] = {
                            "name": str(row.nombre or "").strip(),
                            "short": str(row.nomcorto or "").strip(),
                            "ruc": str(row.ruc or "").strip()
                        }
            source_info = f"Certificado (sys.databases + {db_catalog}.sys300)"
    except Exception:
        # Si sys300 falla (p. ej. no existe la base PROYECTO), se usan solo los nombres de las bases.
        pass

    # 3. Lista final unificada
    companies = []
    for db_info in raw_dbs:
        db = db_info.get("database", "")
        db_biz_name = db_info.get("business_name", db)
        db_upper = db.upper()
        
        bdata = business_map.get(db_upper, {})
        
        # Prioridad: sys300 de PROYECTO > sys300 de la BD misma > ID de la BD
        display_name = bdata.get("name") or bdata.get("short") or db_biz_name or db
        
        companies.append({
            "database": db_upper,
            "company_code": db_upper,
            "business_name": display_name,
            "short_name": bdata.get("short") or db,
            "modules": [],
            "ruc": bdata.get("ruc", ""),
            "is_root": True # Indica que viene de sys.databases
        })

    return {
        "status": "success",
        "companies": companies,
        "source": source_info
    }


def _activate_chat_views(connector, db_name: str) -> str:
    """
    Activa las vistas dinámicas de CHAT ejecutando SP_MODIFICA_VISTA_IA.

    Al seleccionar una base de datos (ej: MONT, DAUN), se llama este SP
    en la base CHAT del servidor. El SP configura internamente las vistas
    de CHAT para apuntar a la BD seleccionada, habilitando todo el motor
    de consulta avanzada.

    Patrón SQL activado:
        exec CHAT.dbo.SP_MODIFICA_VISTA_IA 'MONT'

    Returns:
        "OK" si el SP se ejecutó; si no, el mensaje de error (no lanza excepción).
    """
    safe_name = db_name.strip().upper()
    if not safe_name:
        return "Nombre de BD vacio"
    try:
        with connector.engine.connect() as conn:
            conn.execute(text(f"exec [CHAT].[dbo].[SP_MODIFICA_VISTA_IA] '{safe_name}'"))
            conn.commit()
        logger.info("[CHAT] SP_MODIFICA_VISTA_IA activado para BD: %s", safe_name)
        return "OK"
    except Exception as _e:
        msg = str(_e)
        logger.warning("[CHAT] SP_MODIFICA_VISTA_IA no ejecutado para '%s': %s", safe_name, msg)
        return msg


_chat_reader_connector = None


def _get_chat_reader_connector():
    """
    Devuelve la conexión de solo lectura a CHAT (login chat_reader), o None si no está disponible.

    Está separada de la sesión administrativa del usuario (`sa`) y sirve
    solo para ejecutar el SELECT final que genera la IA contra CHAT. Aunque
    `core/sql_sanitizer.py` fallara en filtrar algo peligroso,
    esta cuenta físicamente no tiene permisos de escritura ni acceso a
    ALIM/UNEMI_PRUEBAS — es la última línea de defensa a nivel de motor de
    base de datos (capa 3 del diseño de seguridad, ver
    base_de_datos/crear_chat_academico.sql). Se cachea tras el primer uso exitoso.
    """
    global _chat_reader_connector
    if _chat_reader_connector is not None:
        return _chat_reader_connector

    user = os.getenv("CHAT_READER_USER", "")
    password = os.getenv("CHAT_READER_PASSWORD", "")
    if not user or not password:
        logger.warning("[CHAT_READER] CHAT_READER_USER/PASSWORD no configurados en .env.")
        return None

    from config import DEFAULT_HOST
    from db_connector import SQLServerConnector, build_connection_string, normalize_sql_server_host
    host = normalize_sql_server_host(DEFAULT_HOST or "localhost")
    conn_str = build_connection_string(host, "CHAT", "AUTO", user, password, windows_auth=False)
    connector = SQLServerConnector(conn_str)
    ok, msg = connector.connect()
    if not ok:
        logger.warning("[CHAT_READER] No se pudo conectar con chat_reader: %s", msg)
        return None

    logger.info("[CHAT_READER] Conexión de solo lectura a CHAT establecida (login chat_reader).")
    _chat_reader_connector = connector
    return _chat_reader_connector


def execute_chat_query(connector, sql: str, db_label: str, empresa: str = "", **kwargs):
    """
    Ejecuta un SELECT decidiendo qué credencial lo corre y con qué aislamiento de empresa.

    Es el único punto de esa decisión; las rutas de /api/query lo usan en
    lugar de `connector.execute_query(sql, target_db=db_label)`. Si el destino
    es CHAT, usa el login de solo lectura `chat_reader` (nunca la sesión
    administrativa del usuario) y fija `SESSION_CONTEXT('empresa_activa')` en
    la misma conexión que corre el SELECT (ver
    db_connector.py::execute_query_with_context), de modo que el aislamiento
    no depende de un ALTER VIEW global con condición de carrera entre empresas.

    Falla cerrado: si `chat_reader` no está disponible, la consulta contra
    CHAT no se ejecuta con otra cuenta y se devuelve un error, porque caer a la
    sesión del usuario anularía en silencio la garantía de aislamiento del
    motor. Solo en desarrollo puede desactivarse con CHAT_READER_OBLIGATORIO=0
    (queda registrado en el log).

    Returns:
        Tupla (columnas, filas, error).
    """
    if db_label == "CHAT":
        from etl.perfiles import institucion_de_base

        # El almacén guarda cada institución con el nombre de su perfil de ETL,
        # no con el de su base operativa (OULAD_PRUEBAS → OULAD_UK).
        empresa = institucion_de_base(empresa) if empresa else empresa
        reader = _get_chat_reader_connector()
        if reader is not None:
            cols, rows, err = reader.execute_query_with_context(sql, empresa=empresa, **kwargs)
            if err:
                logger.warning("[CHAT_EXEC_DEBUG] empresa=%s SQL=%s ERROR=%s", empresa, sql, err)
            return cols, rows, err
        if os.getenv("CHAT_READER_OBLIGATORIO", "1").strip() != "0":
            logger.error("[CHAT_READER] No disponible: consulta a CHAT rechazada (fail-closed).")
            return [], [], ("La cuenta de solo lectura del motor de IA (chat_reader) no está disponible; "
                            "por seguridad la consulta no se ejecuta con otra cuenta.")
        logger.warning("[CHAT_READER] CHAT_READER_OBLIGATORIO=0: ejecutando con la sesión del usuario (solo desarrollo).")
    return connector.execute_query(sql, target_db=db_label, **kwargs)


def _token_con_modulo_academico(current_user: dict = Depends(get_token_data)) -> dict:
    """Exige el módulo ACADEMICO (o el rol ADMINISTRADOR) para leer predicciones, segmentos y referentes."""
    modulos = {str(m).strip().upper() for m in (current_user.get("modules") or [])}
    rol = str(current_user.get("role", "")).strip().upper()
    if rol != "ADMINISTRADOR" and "ACADEMICO" not in modulos:
        raise HTTPException(status_code=403, detail="Tu rol no tiene acceso al módulo académico.")
    return current_user


@app.get("/api/ml/prediccion-abandono", tags=["Inteligencia"])
def get_prediccion_abandono(
    target_db: str = Query(""),
    limit: int = Query(50, ge=1, le=500),
    current_user: dict = Depends(_token_con_modulo_academico),
):
    """
    Devuelve el panel de riesgo de abandono: alumnos activos de la empresa conectada,
    ordenados por probabilidad de abandono descendente, con cédula enmascarada.

    Requiere el módulo ACADEMICO o rol ADMINISTRADOR. La predicción se calcula
    fuera de línea con backend/ml/predecir_abandono.py y se lee aquí a través
    de VIS_PREDICCION_ABANDONO, la misma vista que el chat NL2SQL puede
    consultar en lenguaje natural (está en la lista blanca VIS_*), así que el
    panel y el chat nunca pueden mostrar números distintos.
    """
    user_id = current_user.get("sub") or "default_user"
    session = SESSION_STORE.get_session(user_id)
    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db or source_db in ("MASTER", "TEMPDB", "MODEL", "MSDB", ""):
        raise HTTPException(
            status_code=400,
            detail="Selecciona primero una base de datos de empresa antes de consultar riesgo de abandono.",
        )

    connector = getattr(session, "connector", None) if session else None
    if connector is None and _get_chat_reader_connector() is None:
        raise HTTPException(status_code=503, detail="No hay conexion activa ni chat_reader configurado.")

    sql = """
        SELECT cedula, apellidos, nombres, facultad_nombre, carrera, periodo_actual,
               horizonte, probabilidad, umbral_operativo, riesgo_categoria,
               factor_1, factor_2, factor_3, fecha_calculo, modelo_version
        FROM dbo.VIS_PREDICCION_ABANDONO
        ORDER BY probabilidad DESC
    """
    cols, rows, err = execute_chat_query(connector, sql, "CHAT", empresa=source_db)
    if err:
        raise HTTPException(status_code=502, detail=f"No se pudo leer la prediccion de abandono: {err}")

    from core.privacidad import enmascarar_cedula

    todas = [dict(zip(cols, row)) for row in (rows or [])]
    resumen = {"ALTO": 0, "MEDIO": 0, "BAJO": 0}
    for a in todas:
        resumen[a.get("riesgo_categoria", "BAJO")] = resumen.get(a.get("riesgo_categoria", "BAJO"), 0) + 1
        # Minimización en pantalla: la cédula completa no es necesaria para
        # priorizar la intervención (RNF de privacidad, LOPDP).
        a["cedula"] = enmascarar_cedula(a.get("cedula"))
        a["factores"] = [f for f in (a.pop("factor_1", None), a.pop("factor_2", None), a.pop("factor_3", None)) if f]

    return {
        "empresa": source_db,
        "total_evaluados": len(todas),
        "horizonte": todas[0]["horizonte"] if todas else None,
        "umbral_operativo": float(todas[0]["umbral_operativo"]) if todas else None,
        "resumen": resumen,
        "alumnos": todas[:limit],
    }


@app.get("/api/ml/evaluacion-modelo", tags=["Inteligencia"])
def get_evaluacion_modelo(
    target_db: str = Query(""),
    current_user: dict = Depends(_token_con_modulo_academico),
):
    """
    Devuelve las métricas reales de validación del modelo de la institución activa.

    Incluye validación cruzada agrupada, validación temporal y clustering,
    leídas de VIS_EVALUACION_MODELO, la misma vista que el chat puede consultar
    ("¿qué tan confiable es el modelo?"). Así una autoridad sin perfil técnico
    puede consultar los resultados y saber cuánto confiar en ellos. Requiere
    el módulo ACADEMICO o rol ADMINISTRADOR.
    """
    user_id = current_user.get("sub") or "default_user"
    session = SESSION_STORE.get_session(user_id)
    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db or source_db in ("MASTER", "TEMPDB", "MODEL", "MSDB"):
        raise HTTPException(status_code=400, detail="Selecciona primero una base de datos de empresa.")
    connector = getattr(session, "connector", None) if session else None
    sql = """
        SELECT componente, modelo, esquema_validacion, metrica, valor, desviacion,
               es_modelo_final, fecha_calculo, modelo_version
        FROM dbo.VIS_EVALUACION_MODELO
        ORDER BY componente, es_modelo_final DESC, esquema_validacion, metrica
    """
    cols, rows, err = execute_chat_query(connector, sql, "CHAT", empresa=source_db)
    if err:
        raise HTTPException(status_code=502, detail=f"No se pudo leer la evaluacion del modelo: {err}")
    return {"empresa": source_db, "metricas": [dict(zip(cols, row)) for row in (rows or [])]}


@app.get("/api/ml/clusters-carrera", tags=["Inteligencia"])
def get_clusters_carrera(
    target_db: str = Query(""),
    current_user: dict = Depends(_token_con_modulo_academico),
):
    """
    Devuelve la segmentación de carreras por perfil de riesgo.

    K-Means sobre la tasa de abandono histórica, el rendimiento y el riesgo
    actual del modelo predictivo (ver backend/ml/clustering_institucional.py).
    El panel y el chat leen la misma vista, VIS_CLUSTER_CARRERA. Requiere el
    módulo ACADEMICO o rol ADMINISTRADOR.
    """
    user_id = current_user.get("sub") or "default_user"
    session = SESSION_STORE.get_session(user_id)
    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db or source_db in ("MASTER", "TEMPDB", "MODEL", "MSDB"):
        raise HTTPException(status_code=400, detail="Selecciona primero una base de datos de empresa.")

    connector = getattr(session, "connector", None) if session else None
    if connector is None and _get_chat_reader_connector() is None:
        raise HTTPException(status_code=503, detail="No hay conexion activa ni chat_reader configurado.")

    sql = """
        SELECT carrera, facultad_nombre, cluster_label, matricula_total,
               tasa_abandono_hist, promedio_hist, riesgo_promedio, fecha_calculo
        FROM dbo.VIS_CLUSTER_CARRERA
        ORDER BY tasa_abandono_hist DESC
    """
    cols, rows, err = execute_chat_query(connector, sql, "CHAT", empresa=source_db)
    if err:
        raise HTTPException(status_code=502, detail=f"No se pudo leer los clusters de carrera: {err}")

    return {"empresa": source_db, "carreras": [dict(zip(cols, row)) for row in (rows or [])]}


@app.get("/api/benchmarking/comparativo", tags=["Inteligencia"])
def get_benchmarking_comparativo(
    target_db: str = Query(""),
    current_user: dict = Depends(_token_con_modulo_academico),
):
    """
    Compara la tasa de abandono histórica de la empresa activa con referentes externos.

    Benchmarking institucional: los referentes salen de fuentes académicas con
    DOI, cada uno con su definición exacta y su nivel de comparabilidad (ver
    documentacion/tecnica/BENCHMARKING_INSTITUCIONAL.md). Los indicadores
    externos no dependen de SESSION_CONTEXT (son públicos, no propios de
    ninguna empresa); el cálculo interno sí. Requiere el módulo ACADEMICO o
    rol ADMINISTRADOR.
    """
    user_id = current_user.get("sub") or "default_user"
    session = SESSION_STORE.get_session(user_id)
    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db or source_db in ("MASTER", "TEMPDB", "MODEL", "MSDB"):
        raise HTTPException(status_code=400, detail="Selecciona primero una base de datos de empresa.")

    connector = getattr(session, "connector", None) if session else None
    if connector is None and _get_chat_reader_connector() is None:
        raise HTTPException(status_code=503, detail="No hay conexion activa ni chat_reader configurado.")

    sql_externo = """
        SELECT institucion_codigo, nombre, tipo, indicador_codigo, valor, unidad, anio,
               definicion_indicador, pais, modalidad, nivel_comparabilidad, fuente, doi, url_fuente
        FROM dbo.VIS_BENCHMARK_EXTERNO
        ORDER BY CASE nivel_comparabilidad WHEN 'ALTA' THEN 0 WHEN 'MEDIA' THEN 1 ELSE 2 END, valor DESC
    """
    sql_interno = """
        SELECT
            CAST(SUM(CASE WHEN estado_matricula = 'RETIRADO' THEN 1 ELSE 0 END) AS FLOAT)
                / NULLIF(COUNT(*), 0) * 100 AS tasa_abandono_pct,
            COUNT(*) AS alumnos_evaluados
        FROM dbo.VIS_ALUMNO
        WHERE es_ultimo_periodo = 1
    """
    cols_ext, rows_ext, err_ext = execute_chat_query(connector, sql_externo, "CHAT", empresa=source_db)
    if err_ext:
        raise HTTPException(status_code=502, detail=f"No se pudo leer el benchmark externo: {err_ext}")
    cols_int, rows_int, err_int = execute_chat_query(connector, sql_interno, "CHAT", empresa=source_db)
    if err_int:
        raise HTTPException(status_code=502, detail=f"No se pudo calcular la tasa interna: {err_int}")

    interno = dict(zip(cols_int, rows_int[0])) if rows_int else {"tasa_abandono_pct": None, "alumnos_evaluados": 0}

    return {
        "empresa": source_db,
        "propio": {
            "nombre": source_db,
            "tasa_abandono_pct": round(interno["tasa_abandono_pct"], 2) if interno.get("tasa_abandono_pct") is not None else None,
            "alumnos_evaluados": interno.get("alumnos_evaluados", 0),
        },
        "externo": [dict(zip(cols_ext, row)) for row in (rows_ext or [])],
    }


def _prepare_chat_for_query(connector, source_db: str) -> tuple[dict, str, str]:
    """
    Prepara CHAT para responder preguntas sobre la empresa `source_db`.

    Pasos:
    1. Verifica que la base CHAT exista en el servidor.
    2. Ejecuta SP_MODIFICA_VISTA_IA para configurar las vistas de CHAT.
    3. Lee el esquema real de CHAT y deja solo las vistas VIS_* que la
       empresa puede ver.

    La IA genera SQL que consulta directamente esas vistas; no usa
    plantillas ni caché semántica.

    Returns:
        Tupla (esquema, esquema_en_texto, base_a_consultar = "CHAT", estado_del_SP).

    Raises:
        ValueError: si la base CHAT no existe; routes_query.py lo convierte en
            un mensaje amigable.
    """
    safe_source_db = source_db.strip().upper() if source_db else "CHAT"
    
    # ── VALIDACIÓN FÍSICA DE EXISTENCIA DE CHAT ────────────────────────────────
    # Si la base CHAT no existe en este servidor se lanza una excepción
    # explícita, para que routes_query.py devuelva el mensaje amigable de
    # "Este servidor no tiene habilitado el módulo...".
    chat_exists = False
    if not connector.is_sqlite and not connector.is_postgres:
        try:
            with connector.engine.connect() as conn:
                res = conn.execute(text("SELECT 1 FROM sys.databases WHERE name = 'CHAT'")).fetchone()
                chat_exists = res is not None
        except Exception as _e:
            logger.warning("[CHAT_SETUP] No se pudo verificar existencia de base CHAT: %s", _e)
            
    if not chat_exists:
        raise ValueError("La base de datos CHAT no existe o no está habilitada en este servidor.")
    # ──────────────────────────────────────────────────────────────────────────
    
    # PASO 1: Activar las vistas CHAT para esta empresa
    sp_status = _activate_chat_views(connector, safe_source_db)
    
    # PASO 2: Obtener esquema REAL de CHAT (vistas disponibles)
    try:
        chat_schema = connector.get_schema(database_override="CHAT", empresa=safe_source_db) or {}

        # ficha_trabajador y rol_pago pasan siempre el chequeo "¿tiene datos?"
        # de get_schema(), para cualquier empresa: leen de la base física
        # "RRHH" sin filtrar por empresa (ver core/integridad_vistas.py), así
        # que EXISTS() es verdadero aunque los datos sean de otra. Si quedaran
        # en el esquema, la IA las vería disponibles para cualquier pregunta
        # (p. ej. preguntas de ventas que devolverían el aviso de nómina). Se
        # excluyen del esquema salvo que la verificación en vivo confirme que
        # están aisladas para la empresa activa.
        from core.integridad_vistas import vista_aislada_para_empresa, nombres_vistas_no_aisladas
        for _vista_riesgo in nombres_vistas_no_aisladas():
            if _vista_riesgo in chat_schema and not vista_aislada_para_empresa(
                connector, _vista_riesgo, safe_source_db, target_db="CHAT"
            ):
                chat_schema.pop(_vista_riesgo, None)

        # Lista blanca: solo sobreviven las vistas de presentación VIS_*, las
        # únicas que chat_reader puede leer (ver
        # base_de_datos/crear_chat_academico.sql). Si el esquema mostrara
        # tablas del almacén (dim_*, fact_matriculas) o de infraestructura
        # (tb_bi_snapshot), la IA a veces las elegiría y la consulta fallaría
        # con "permission denied", un error que se confunde con falta de
        # permisos del rol. La lista blanca evita tener que descubrir esas
        # tablas una por una.
        for _nombre_tabla in list(chat_schema.keys()):
            if not _nombre_tabla.strip().lower().startswith("vis_"):
                chat_schema.pop(_nombre_tabla, None)

        chat_schema_text = connector.get_schema_as_text(database_override="CHAT", schema_dict=chat_schema)
        logger.info("[CHAT_QUERY] Esquema CHAT obtenido: %d vistas/tablas (SP Status: %s)", len(chat_schema), sp_status)
    except Exception as e:
        logger.error("[CHAT_QUERY] Error obteniendo esquema de CHAT: %s", e)
        chat_schema = {}
        chat_schema_text = ""

    # PASO 3: esquema para la IA y base destino de las consultas
    return chat_schema, chat_schema_text, "CHAT", sp_status


# ── Caché corta del Pulso BI ────────────────────────────────────────────────
# Cada carga de Reportes BI ejecuta ~20-40 consultas SQL secuenciales (tarjetas
# base, métricas certificadas, series y sondas). Sin caché, cada clic en una
# empresa, cada refresco automático o cada usuario que entra a la misma empresa
# repetiría todo ese trabajo. Con un TTL corto (90 s), volver a una empresa
# reciente responde al instante, y el autorrefresco de 15 min sigue trayendo
# datos frescos (90 s es mucho menor que 15 min).
#
# La llave incluye user_id y source_db (además de año y mes): no es una caché
# global, así que el pulso de un usuario o empresa no se filtra a otro. No se
# vacía en cada petición ni en /api/connect: el TTL y la llave por empresa
# bastan para la frescura.
_BI_PULSE_CACHE: dict = {}
_BI_PULSE_TTL_SECONDS = 90


@app.get("/api/bi/pulse")
def get_bi_pulse(
    target_db: str = Query(""),
    year: int = Query(None, description="Año explícito para métricas del catálogo (opcional). Sin esto, usa el período más reciente con datos."),
    month: int = Query(None, ge=1, le=12, description="Mes explícito (1-12), junto con year, para acotar Balance Comercial, Ingresos por Línea y Top 5 Productos. Se ignora si year no viene."),
    current_user: dict = Depends(get_token_data),
):
    """
    Devuelve las tarjetas de KPIs de Reportes BI de la empresa activa, filtradas por los módulos del rol.

    Requiere usuario autenticado. Si la sesión no tiene conector, intenta
    conectarse con las credenciales de backend/.env. Sirve en este orden:
    caché en memoria (90 s), snapshot persistente en CHAT (solo la vista por
    defecto, sin año ni mes) y cálculo en vivo, que vuelve a guardar el
    snapshot.
    """
    user_id = current_user.get("sub") or "default_user"
    role = current_user.get("role", "ADMINISTRADOR")
    # El JWT guarda los módulos del rol en la clave "modules" (ver login); leer
    # solo "allowed_modules", que el token no trae, dejaría pasar todos los
    # módulos (p. ej. tarjetas de ACADEMICO a CONTABILIDAD). Se leen ambas
    # claves por compatibilidad con tokens emitidos con el formato anterior.
    allowed_modules = current_user.get("modules", current_user.get("allowed_modules", [])) or []

    session = SESSION_STORE.get_session(user_id)
    if not session:
        session = SESSION_STORE.create_session(user_id, allowed_modules=allowed_modules, role=role, name=user_id)

    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db:
        source_db = "MONT"

    # Conexión automática si la sesión no tiene conector activo
    if not session.connector:
        try:
            from db_connector import SQLServerConnector, build_connection_string, normalize_sql_server_host
            from config import DEFAULT_HOST
            # Usa la misma ruta de credenciales SQL que /api/connect (host y
            # usuario de backend/.env). Con autenticación de Windows, en el
            # servidor el login sería el usuario del sistema operativo (error
            # 18456) y el Pulso BI, y con él el chat, quedarían sin base activa.
            host = normalize_sql_server_host(DEFAULT_HOST or "localhost")
            conn_str = build_connection_string(
                host=host,
                database=source_db,
                driver="AUTO",
                user=DEFAULT_USER,
                password=DEFAULT_PASSWORD,
                windows_auth=False,
            )
            connector = SQLServerConnector(conn_str)
            ok, _ = connector.connect()
            if ok:
                session.connector = connector
                session.context_db = source_db
                logger.info("[BI_API] Conector auto-creado exitosamente para BD: %s", source_db)
        except Exception as e:
            logger.warning("[BI_API] Auto-conexión falló para %s: %s", source_db, e)

    if not session.connector:
        logger.warning("[BI_API] No hay sesión activa ni conector para usuario: %s", user_id)
        return {"status": "error", "message": "No hay sesion activa con base de datos conectada."}

    from core.mirror_manager import filtrar_pulso_por_modulos

    # Frescura en 3 capas:
    #   1) Caché en memoria por (usuario, empresa, año, mes) — TTL 90 s.
    #   2) SNAPSHOT persistente en CHAT (Capa 2) — solo vista por defecto.
    #   3) Cálculo en vivo (SP_MODIFICA_VISTA_IA + ~30-40 consultas), que luego
    #      re-guarda el snapshot para el resto de usuarios/instancias.
    # El snapshot convierte en instantánea también la PRIMERA visita a una
    # empresa (incluso en una instancia fría de Cloud Run), porque no depende
    # de memoria del proceso: vive en la tabla [CHAT].[dbo].[tb_bi_snapshot].
    effective_month = month if year else None  # el mes sin año no tiene con qué acotar
    cache_key = (user_id, source_db, year, effective_month)
    cached = _BI_PULSE_CACHE.get(cache_key)
    if cached and (time.time() - cached[0]) < _BI_PULSE_TTL_SECONDS:
        logger.info("[BI_API] Pulso servido desde caché (%s, empresa=%s, año=%s, mes=%s)", user_id, source_db, year, effective_month)
        return cached[1]

    # ── CAPA 2: SERVIR DESDE SNAPSHOT (solo vista por defecto, sin año/mes) ──
    # La vista que se adopta al conectar (sin filtro de período) se sirve desde
    # el snapshot persistente si está fresco (≤ 30 min, configurable). Si no hay
    # snapshot o está muy viejo, se calcula en vivo abajo y se vuelve a guardar.
    es_vista_por_defecto = year is None and month is None
    sp_status = "OK"  # se sobrescribe al activar vistas (o por el SP)
    if es_vista_por_defecto:
        try:
            import copy as _copy

            from config import BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS
            from core.bi_snapshot_store import edad_snapshot_segundos as _edad_snap
            from core.bi_snapshot_store import leer_snapshot
            from core.mirror_manager import filtrar_pulso_por_modulos

            payload_snap, capturado, _fallos = leer_snapshot(session.connector, source_db)
            if payload_snap:
                _edad = _edad_snap(capturado)
                if _edad is not None and _edad <= BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS:
                    respuesta = _copy.deepcopy(payload_snap)
                    # Marcas de frescura para el frontend ("Actualizado hace X").
                    respuesta["snapshot_at"] = capturado.isoformat() if hasattr(capturado, "isoformat") else str(capturado or "")
                    respuesta["served_from"] = "snapshot"
                    respuesta["capture_age_seconds"] = int(_edad)
                    filtrar_pulso_por_modulos(respuesta, allowed_modules)
                    _BI_PULSE_CACHE[cache_key] = (time.time(), respuesta)
                    logger.info("[BI_API] Pulso servido desde snapshot (empresa=%s, edad=%ss)", source_db, int(_edad))
                    return respuesta
            logger.info("[BI_API] Sin snapshot fresco para %s (¿edad>%s?); calculando en vivo.", source_db, BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS)
        except Exception as _e:
            logger.info("[BI_API] Snapshot no disponible para %s (%s); se calcula en vivo.", source_db, _e)
    # ──────────────────────────────────────────────────────────────────────────

    # ── CALCULAR EN VIVO (bajo candado: las vistas de CHAT son un namespace
    # compartido que SP_MODIFICA_VISTA_IA re-apunta por empresa, así que dos
    # cálculos a la vez se pisarían). _computar_pulso_en_vivo activa vistas,
    # resuelve esquema y genera el pulso completo SIN filtrar por rol — así se
    # guarda un único snapshot por empresa que sirve a cualquier rol.
    _t0 = time.time()
    pulse_full, sp_status = _computar_pulso_en_vivo(session, source_db, year, month)
    if pulse_full is None:
        if es_vista_por_defecto:
            try:
                from core.bi_snapshot_store import marcar_snapshot_fallido

                marcar_snapshot_fallido(session.connector, source_db)
            except Exception:
                pass
        return {"status": "error", "message": "No se pudo calcular el pulso BI.", "sp_status": sp_status}

    logger.info("[BI_API] Pulso BI generado. Tarjetas: %d | SP Status: %s", len(pulse_full.get("cards", [])), sp_status)
    if pulse_full.get("status") == "ok" and es_vista_por_defecto:
        # Re-guardar el snapshot persistente para el resto de usuarios/instancias.
        # (Las consultas por año/mes no se cachean de forma persistente.)
        try:
            from core.bi_snapshot_store import guardar_snapshot

            guardar_snapshot(
                session.connector,
                source_db,
                pulse_full,
                duracion_ms=int(round((time.time() - _t0) * 1000)),
            )
        except Exception as _e:
            logger.info("[BI_API] No se pudo guardar snapshot de %s: %s", source_db, _e)
    elif pulse_full.get("status") != "ok" and es_vista_por_defecto:
        try:
            from core.bi_snapshot_store import marcar_snapshot_fallido

            marcar_snapshot_fallido(session.connector, source_db)
        except Exception:
            pass

    import copy as _copy

    respuesta = _copy.deepcopy(pulse_full)
    filtrar_pulso_por_modulos(respuesta, allowed_modules)

    # Poda perezosa de la caché en memoria (ver nota en su definición) y
    # guardado de la respuesta YA filtrada por rol para este usuario.
    if len(_BI_PULSE_CACHE) > 500:
        _now = time.time()
        expired = [k for k, (ts, _v) in _BI_PULSE_CACHE.items()
                   if (_now - ts) >= _BI_PULSE_TTL_SECONDS]
        for k in expired:
            _BI_PULSE_CACHE.pop(k, None)
    if respuesta.get("status") == "ok":
        _BI_PULSE_CACHE[cache_key] = (time.time(), respuesta)
    return respuesta


# ═══════════════════════════════════════════════════════════════════════════
# CAPA 2: JOB DE SNAPSHOTS BI (refresco en segundo plano)
# ═══════════════════════════════════════════════════════════════════════════
# Cloud Run es serverless (sin proceso residente), así que el refresco lo
# dispara un job EXTERNO (Cloud Scheduler) que llama ~cada 2 min a
# POST /api/bi/snapshots/refresh. Cada invocación recalcula solo las empresas
# cuyo snapshot tiene más de `BI_SNAPSHOT_REFRESH_SECONDS` (15 min) y guarda el
# resultado en [CHAT].[dbo].[tb_bi_snapshot]. Sobre una ventana de 15 minutos,
# las ~40 empresas se refrescan una vez cada una, escalonadas (nunca todas a la
# vez) para no golpear el ERP compartido.

_SNAPSHOT_CONNECTOR = None
_SNAPSHOT_CONNECTOR_LOCK = None
_SNAP_EMPRESAS_CACHE = None  # (timestamp_listado, [empresas])


def _snapshot_connector_lock():
    """Devuelve el candado que protege la creación del conector de snapshots (lo crea la primera vez)."""
    global _SNAPSHOT_CONNECTOR_LOCK
    if _SNAPSHOT_CONNECTOR_LOCK is None:
        import threading

        _SNAPSHOT_CONNECTOR_LOCK = threading.Lock()
    return _SNAPSHOT_CONNECTOR_LOCK


def _snapshot_connector():
    """Conector reutilizable a CHAT para leer/guardar snapshots y calcular."""
    global _SNAPSHOT_CONNECTOR
    if _SNAPSHOT_CONNECTOR is not None:
        return _SNAPSHOT_CONNECTOR
    with _snapshot_connector_lock():
        if _SNAPSHOT_CONNECTOR is not None:
            return _SNAPSHOT_CONNECTOR
        try:
            from config import DEFAULT_HOST, DEFAULT_PASSWORD, DEFAULT_USER, EXECUTION_DB
            from db_connector import (SQLServerConnector,
                                      build_connection_string,
                                      normalize_sql_server_host)
            host = normalize_sql_server_host(DEFAULT_HOST or "localhost")
            base = (EXECUTION_DB or "CHAT").strip().upper() or "CHAT"
            conn_str = build_connection_string(
                host=host, database=base, driver="AUTO",
                user=DEFAULT_USER, password=DEFAULT_PASSWORD, windows_auth=False,
            )
            conn = SQLServerConnector(conn_str)
            ok, _err = conn.connect()
            if ok:
                _SNAPSHOT_CONNECTOR = conn
                logger.info("[BI_SNAP] Conector de snapshots listo (CHAT).")
            else:
                logger.warning("[BI_SNAP] connect() falló para CHAT: %s", _err)
        except Exception as e:
            logger.warning("[BI_SNAP] No se pudo crear conector de snapshots: %s", e)
    return _SNAPSHOT_CONNECTOR


def _listar_empresas_para_snapshots():
    """Devuelve las empresas candidatas a snapshot (sys.databases sin CHAT, PROYECTO ni bases de sistema).

    El listado se guarda 15 minutos en memoria.
    """
    global _SNAP_EMPRESAS_CACHE
    now = time.time()
    if _SNAP_EMPRESAS_CACHE and (now - _SNAP_EMPRESAS_CACHE[0]) < 900:
        return _SNAP_EMPRESAS_CACHE[1]
    try:
        from config import DEFAULT_HOST, DEFAULT_PASSWORD, DEFAULT_USER
        from db_connector import get_available_databases, normalize_sql_server_host
        host = normalize_sql_server_host(DEFAULT_HOST or "localhost")
        dbs = get_available_databases(
            host=host, driver="AUTO",
            user=DEFAULT_USER, password=DEFAULT_PASSWORD, windows_auth=False,
        ) or []
        denylist = {"CHAT", "PROYECTO", "MASTER", "TEMPDB", "MODEL", "MSDB"}
        empresas = sorted({
            str(d.get("database") or "").strip().upper()
            for d in dbs
            if str(d.get("database") or "").strip().upper() not in denylist
        })
        _SNAP_EMPRESAS_CACHE = (now, empresas)
        logger.info("[BI_SNAP] Empresas candidatas para snapshot: %d", len(empresas))
        return empresas
    except Exception as e:
        logger.warning("[BI_SNAP] No se pudo listar empresas: %s", e)
        return _SNAP_EMPRESAS_CACHE[1] if _SNAP_EMPRESAS_CACHE else []


def _computar_pulso_en_vivo(session, source_db, year=None, mes=None):
    """
    Calcula el pulso BI COMPLETO (sin filtrar por rol) de una empresa, bajo el
    candado global PULSE_COMPUTE_LOCK: las vistas de CHAT son un namespace
    compartido que SP_MODIFICA_VISTA_IA re-apunta por empresa, así que dos
    cálculos concurrentes se pisarían.

    Devuelve (pulse_dict, sp_status). pulse_dict es None si hubo una excepción.
    """
    sp_status = "OK"
    try:
        from core.bi_snapshot_store import PULSE_COMPUTE_LOCK
        from core.mirror_manager import MirrorManager

        with PULSE_COMPUTE_LOCK:
            sp_status = _activate_chat_views(session.connector, source_db)
            effective_schema = resolve_schema_for_db(session, source_db)
            logger.info("[BI_API] Calculando pulso en vivo: BD=%s | tablas=%s",
                        source_db, len(effective_schema) if effective_schema else 0)
            mm = MirrorManager(session.connector)
            pulse = mm.get_bi_pulse(
                source_db,
                effective_schema,
                sp_status=sp_status,
                anio=year,
                mes=(mes if year else None),
                allowed_modules=None,
            )
            pulse["sp_status"] = sp_status
            return pulse, sp_status
    except Exception as e:
        logger.error("[BI_API] Error al calcular pulso en vivo: %s", e, exc_info=True)
        return None, sp_status


def _calcular_y_guardar_snapshot(connector, empresa):
    """Calcula el pulso de una empresa y lo persiste, o marca el intento como fallido.

    Returns:
        Tupla (ok, segundos).
    """
    from core.bi_snapshot_store import guardar_snapshot, marcar_snapshot_fallido

    from types import SimpleNamespace

    t0 = time.time()
    pseudo = SimpleNamespace(connector=connector, context_db=empresa, schema_cache={})
    pulse, _sp = _computar_pulso_en_vivo(pseudo, empresa, None, None)
    if pulse is None or pulse.get("status") != "ok":
        try:
            marcar_snapshot_fallido(connector, empresa)
        except Exception:
            pass
        logger.warning("[BI_SNAP] Captura fallida de '%s' (status=%s)",
                       empresa, (pulse or {}).get("status"))
        return False, time.time() - t0
    ok = guardar_snapshot(connector, empresa, pulse,
                          duracion_ms=int(round((time.time() - t0) * 1000)))
    logger.info("[BI_SNAP] Snapshot '%s': %s (%.1fs)",
                empresa, "ok" if ok else "no persistido", time.time() - t0)
    if not ok:
        try:
            marcar_snapshot_fallido(connector, empresa)
        except Exception:
            pass
    return ok, time.time() - t0


def _autorizar_scheduler(current_user: dict, x_scheduler_token: str) -> None:
    """Permite el paso al job (token compartido) o a un ADMINISTRADOR con JWT válido.

    Raises:
        HTTPException: 403 en cualquier otro caso.
    """
    from config import BI_SCHEDULER_TOKEN

    if BI_SCHEDULER_TOKEN:
        import hmac

        if hmac.compare_digest(str(x_scheduler_token or ""), BI_SCHEDULER_TOKEN):
            return
    role = str((current_user or {}).get("role", "")).strip().upper()
    if role == "ADMINISTRADOR":
        return
    raise HTTPException(status_code=403, detail="Acceso restringido al job de snapshots.")


@app.post("/api/bi/snapshots/refresh")
def bi_snapshots_refresh(
    current_user: dict = Depends(get_token_data_opcional),
    x_scheduler_token: str = Header("", alias="X-Scheduler-Token"),
):
    """
    Refresca en segundo plano los snapshots vencidos de las empresas.
    Lo invoca Cloud Scheduler (o un ADMINISTRADOR con su JWT). Procesa hasta
    `BI_SNAPSHOT_MAX_PER_RUN` empresas o `BI_SNAPSHOT_MAX_RUN_SECONDS` por
    llamada, para no pasarse del timeout de Cloud Run.
    """
    _autorizar_scheduler(current_user, x_scheduler_token)

    from config import BI_SNAPSHOT_MAX_PER_RUN, BI_SNAPSHOT_MAX_RUN_SECONDS
    from core.bi_snapshot_store import necesita_refresco

    connector = _snapshot_connector()
    if connector is None:
        return {"status": "error", "message": "Sin conector disponible hacia CHAT."}

    empresas = _listar_empresas_para_snapshots()
    if not empresas:
        return {"status": "ok", "refrescadas": [], "pendientes": 0, "segundos": 0.0}

    t0 = time.time()
    resultados = []
    for emp in empresas:
        if len(resultados) >= BI_SNAPSHOT_MAX_PER_RUN or (time.time() - t0) >= BI_SNAPSHOT_MAX_RUN_SECONDS:
            break
        try:
            due = necesita_refresco(connector, emp)
        except Exception:
            due = False
        if not due:
            continue
        ok, segs = _calcular_y_guardar_snapshot(connector, emp)
        resultados.append({"empresa": emp, "ok": ok, "segundos": round(segs, 2)})

    pendientes = 0
    for emp in empresas:
        try:
            if necesita_refresco(connector, emp):
                pendientes += 1
        except Exception:
            pass

    return {
        "status": "ok",
        "refrescadas": resultados,
        "total_refrescadas": len(resultados),
        "pendientes": pendientes,
        "segundos": round(time.time() - t0, 2),
    }


@app.get("/api/bi/snapshots/status")
def bi_snapshots_status(
    current_user: dict = Depends(get_token_data_opcional),
    x_scheduler_token: str = Header("", alias="X-Scheduler-Token"),
):
    """Devuelve el estado de frescura de cada snapshot (diagnóstico del job).

    Solo para el job (X-Scheduler-Token) o un ADMINISTRADOR.
    """
    _autorizar_scheduler(current_user, x_scheduler_token)

    from config import (BI_SNAPSHOT_REFRESH_SECONDS,
                        BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS)
    from core.bi_snapshot_store import (edad_snapshot_segundos as _edad_snap,
                                        listar_snapshots)

    connector = _snapshot_connector()
    if connector is None:
        return {"status": "error", "message": "Sin conector disponible hacia CHAT."}
    filas = listar_snapshots(connector) or []
    detalle = []
    for emp, capturado, fallos, tam in filas:
        _edad = _edad_snap(capturado)
        detalle.append({
            "empresa": emp,
            "capturado_en": capturado.isoformat() if hasattr(capturado, "isoformat") else str(capturado or ""),
            "edad_segundos": int(_edad) if _edad is not None else None,
            "fresco": _edad is not None and _edad < BI_SNAPSHOT_REFRESH_SECONDS,
            "intentos_fallidos": fallos,
            "bytes": tam,
        })
    return {
        "status": "ok",
        "refresco_cadencia_seg": BI_SNAPSHOT_REFRESH_SECONDS,
        "ventana_servido_max_seg": BI_SNAPSHOT_SERVE_MAX_AGE_SECONDS,
        "snapshots": detalle,
        "conteo": len(detalle),
    }


@app.get("/api/bi/available-periods")
def get_bi_available_periods(
    target_db: str = Query(""),
    current_user: dict = Depends(get_token_data),
):
    """
    Devuelve los años y meses con datos reales en la base activa, para el filtro de período de Reportes BI.

    Requiere usuario autenticado. Consulta la vista de ventas de CHAT
    ([CHAT].[dbo].[Ventas] o [CHAT].[dbo].[cabecera_factura], la que exista
    para esta empresa; ver _detectar_vista_ventas) y no las tablas físicas:
    no todas las empresas facturan en tb_cabmov (MONT, por ejemplo, usa
    tb_cabmovT, ligada a edu_alumno), mientras que la vista sí trae la
    facturación real de cada una. Como el nombre de la vista puede variar, se
    prueban ambos candidatos.
    """
    user_id = current_user.get("sub") or "default_user"
    role = current_user.get("role", "ADMINISTRADOR")
    allowed_modules = current_user.get("modules", current_user.get("allowed_modules", [])) or []

    session = SESSION_STORE.get_session(user_id)
    if not session:
        session = SESSION_STORE.create_session(user_id, allowed_modules=allowed_modules, role=role, name=user_id)

    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db or not session.connector:
        return {"status": "error", "message": "No hay sesion activa con base de datos conectada.", "years": []}

    try:
        _activate_chat_views(session.connector, source_db)
        with session.connector.engine.connect() as connection:
            vista = _detectar_vista_ventas(connection)
            if not vista:
                return {"status": "error", "message": "No se encontró una vista de ventas en CHAT para esta empresa.", "years": []}

            filas = connection.execute(text(
                f"SELECT DISTINCT YEAR(Fecha) AS anio, MONTH(Fecha) AS mes "
                f"FROM [CHAT].[dbo].[{vista}] WHERE Fecha IS NOT NULL"
            )).fetchall()

        por_anio: dict[int, set[int]] = {}
        for anio_val, mes_val in filas:
            if anio_val is None or mes_val is None:
                continue
            por_anio.setdefault(int(anio_val), set()).add(int(mes_val))

        years = [
            {"year": a, "months": sorted(meses)}
            for a, meses in sorted(por_anio.items(), reverse=True)
        ]
        return {"status": "ok", "db": source_db, "years": years}
    except Exception as e:
        logger.warning("[BI_API] No se pudo determinar años/meses disponibles para %s: %s", source_db, e)
        return {"status": "error", "message": str(e), "years": []}


def _detectar_vista_ventas(connection) -> str | None:
    """Devuelve el nombre de la vista de ventas que existe en CHAT, o None.

    Delega en core/vista_resolver.py, fuente única de esta detección, que
    comparten api/routes_query.py y core/mirror_manager.py.
    """
    from core.vista_resolver import CANDIDATOS_VENTAS, detectar_vista_sqlalchemy

    return detectar_vista_sqlalchemy(connection, CANDIDATOS_VENTAS, target_db="CHAT")


def _requiere_modulo_ventas_o_finanzas(allowed_modules: list) -> None:
    """Lanza 403 si los módulos del rol no incluyen VENTAS ni FINANZAS.

    Comparación por Período es una tarjeta de Ventas: solo ADMINISTRADOR y
    CONTABILIDAD deben verla. Una lista vacía o None no filtra (mismo criterio
    que filtrar_pulso_por_modulos), para no bloquear tokens de ADMINISTRADOR
    ni sesiones anteriores sin módulos.
    """
    mods = {str(m).strip().upper() for m in (allowed_modules or [])}
    if mods and not (mods & {"VENTAS", "FINANZAS"}):
        raise HTTPException(status_code=403, detail="Tu rol no tiene acceso a Comparación por Período.")


@app.get("/api/bi/compare-periods")
def get_bi_compare_periods(
    target_db: str = Query(""),
    desde_a: str = Query(..., description="Fecha inicio del período A, YYYY-MM-DD"),
    hasta_a: str = Query(..., description="Fecha fin del período A, YYYY-MM-DD"),
    desde_b: str = Query(None, description="Fecha inicio del período B (opcional)"),
    hasta_b: str = Query(None, description="Fecha fin del período B (opcional)"),
    current_user: dict = Depends(get_token_data),
):
    """
    Compara ventas y compras entre dos rangos de fecha (Reportes BI — "Comparación
    por período"). El período B es opcional: sin él, solo se devuelve el total
    del período A.

    Solo roles con VENTAS o FINANZAS (403 si no). Consulta la vista de ventas
    de CHAT (ver `_detectar_vista_ventas`) y no las tablas físicas: tb_cabmov no
    trae la facturación real de todas las empresas (MONT usa su propia tabla
    tb_cabmovT), así que la vista es la fuente confiable para cualquiera.
    """
    user_id = current_user.get("sub") or "default_user"
    role = current_user.get("role", "ADMINISTRADOR")
    allowed_modules = current_user.get("modules", current_user.get("allowed_modules", [])) or []

    _requiere_modulo_ventas_o_finanzas(allowed_modules)

    session = SESSION_STORE.get_session(user_id)
    if not session:
        session = SESSION_STORE.create_session(user_id, allowed_modules=allowed_modules, role=role, name=user_id)

    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db or not session.connector:
        return {"status": "error", "message": "No hay sesion activa con base de datos conectada."}

    def _fecha_valida(valor: str) -> bool:
        """Indica si el valor es una fecha con formato YYYY-MM-DD."""
        try:
            datetime.strptime(valor, "%Y-%m-%d")
            return True
        except (TypeError, ValueError):
            return False

    if not _fecha_valida(desde_a) or not _fecha_valida(hasta_a):
        raise HTTPException(status_code=400, detail="desde_a/hasta_a deben tener formato YYYY-MM-DD.")
    tiene_b = bool(desde_b and hasta_b)
    if tiene_b and (not _fecha_valida(desde_b) or not _fecha_valida(hasta_b)):
        raise HTTPException(status_code=400, detail="desde_b/hasta_b deben tener formato YYYY-MM-DD.")

    def _totales(connection, vista_ventas: str, vista_compras: str | None, desde: str, hasta: str) -> dict:
        """Suma ventas, número de facturas y compras entre dos fechas, ambas incluidas."""
        ventas =connection.execute(text(
            f"SELECT ISNULL(SUM(Total), 0), COUNT(DISTINCT NumeroFactura) "
            f"FROM [CHAT].[dbo].[{vista_ventas}] WHERE Fecha >= '{desde}' AND Fecha <= '{hasta}'"
        )).fetchone()
        compras_total = 0.0
        if vista_compras:
            compras_total = float(connection.execute(text(
                f"SELECT ISNULL(SUM(Total), 0) FROM [CHAT].[dbo].[{vista_compras}] "
                f"WHERE Fecha >= '{desde}' AND Fecha <= '{hasta}'"
            )).scalar() or 0)
        return {
            "desde": desde,
            "hasta": hasta,
            "ventas": round(float(ventas[0] or 0), 2),
            "facturas": int(ventas[1] or 0),
            "compras": round(compras_total, 2),
        }

    try:
        _activate_chat_views(session.connector, source_db)
        with session.connector.engine.connect() as connection:
            vista_ventas = _detectar_vista_ventas(connection)
            if not vista_ventas:
                return {"status": "error", "message": "No se encontró una vista de ventas en CHAT para esta empresa."}
            from core.vista_resolver import CANDIDATOS_COMPRAS, detectar_vista_sqlalchemy

            vista_compras = detectar_vista_sqlalchemy(connection, CANDIDATOS_COMPRAS, target_db="CHAT")

            periodo_a = _totales(connection, vista_ventas, vista_compras, desde_a, hasta_a)
            periodo_b = _totales(connection, vista_ventas, vista_compras, desde_b, hasta_b) if tiene_b else None

        respuesta = {"status": "ok", "db": source_db, "periodo_a": periodo_a, "periodo_b": periodo_b}
        if periodo_b:
            for campo in ("ventas", "compras", "facturas"):
                base = periodo_b[campo]
                respuesta.setdefault("delta", {})[campo] = (
                    round(((periodo_a[campo] - base) / base) * 100, 1) if base else None
                )
        return respuesta
    except Exception as e:
        logger.warning("[BI_API] Error comparando periodos para %s: %s", source_db, e)
        return {"status": "error", "message": str(e)}


@app.get("/api/reportes/exportar-excel")
def exportar_reporte_excel(
    request: Request,
    target_db: str = Query(""),
    start: str = Query(None, description="Fecha inicio YYYY-MM-DD (opcional, acota Facturas/Detalle Items)"),
    end: str = Query(None, description="Fecha fin YYYY-MM-DD (opcional)"),
    current_user: dict = Depends(get_token_data),
):
    """
    Descarga un Excel de varias hojas con los datos de la empresa activa.

    Hojas: Facturas, Detalle Items, Productos, Clientes y, en instituciones
    educativas, Cartera por rubro; `start` y `end` acotan las facturas.
    Requiere usuario autenticado y la exportación queda en la auditoría.
    Consulta directamente la base física de la empresa (tb_cabmov, tb_detmov,
    tb_client...), nunca las vistas de CHAT, porque CHAT es un espejo
    compartido por todo el servidor y no está aislado por empresa.
    """
    from fastapi.responses import StreamingResponse

    from core.excel_exporter import generar_reporte_excel

    user_id = current_user.get("sub") or "default_user"
    role = current_user.get("role", "ADMINISTRADOR")
    allowed_modules = current_user.get("modules", current_user.get("allowed_modules", [])) or []

    session = SESSION_STORE.get_session(user_id)
    if not session:
        session = SESSION_STORE.create_session(user_id, allowed_modules=allowed_modules, role=role, name=user_id)

    source_db = (target_db or getattr(session, "context_db", "") or "").strip().upper()
    if not source_db or not session.connector:
        raise HTTPException(status_code=400, detail="No hay sesion activa con base de datos conectada.")

    try:
        buffer, filename = generar_reporte_excel(session.connector, source_db, start=start, end=end)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("[EXCEL_EXPORT] Error generando reporte para %s: %s", source_db, e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"No se pudo generar el reporte: {e}")

    from core.audit_log import registrar as _registrar_auditoria, ACCION_EXPORTAR, ENTIDAD_VENTA
    _registrar_auditoria(
        username=current_user.get("sub", ""), nombre=current_user.get("name", ""),
        accion=ACCION_EXPORTAR, entidad=ENTIDAD_VENTA, entidad_desc=source_db,
        detalle=f"Exportación Excel de {source_db}" + (f" ({start} a {end})" if start or end else ""),
        ip=_ip_cliente(request),
    )

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/query/exportar-tabla-excel")
def exportar_tabla_excel_generica(
    req: ExportarTablaRequest,
    current_user: dict = Depends(get_token_data),
):
    """
    Convierte una tabla del chat (columnas y filas) en un libro .xlsx con formato.

    Usa el mismo formato que /api/reportes/exportar-excel (cabecera verde con
    letra blanca, bordes, filas alternadas, cabecera congelada y autofiltro).
    Lo llama el botón "Excel" de las tarjetas de respuesta del chat. Los
    datos no salen de la base: el frontend envía las columnas y filas que ya
    tiene en pantalla y esta ruta solo les da formato, por eso no necesita el
    conector de la sesión. Requiere usuario autenticado.
    """
    from fastapi.responses import StreamingResponse
    from core.excel_exporter import exportar_tabla_excel as _exportar_tabla_excel

    if not req.columns:
        raise HTTPException(status_code=400, detail="No hay columnas para exportar.")
    if not isinstance(req.rows, list):
        raise HTTPException(status_code=400, detail="'rows' debe ser una lista.")

    user_id = current_user.get("sub") or "default_user"
    role = current_user.get("role", "ADMINISTRADOR")
    allowed_modules = current_user.get("modules", current_user.get("allowed_modules", [])) or []

    session = SESSION_STORE.get_session(user_id)
    if not session:
        session = SESSION_STORE.create_session(user_id, allowed_modules=allowed_modules, role=role, name=user_id)

    try:
        buffer, filename = _exportar_tabla_excel(req.columns, req.rows, titulo=req.filename or "datos")
    except Exception as exc:
        logger.error("[EXCEL_TABLA] Error exportando tabla: %s", exc, exc_info=True)
        raise HTTPException(status_code=500, detail=f"No se pudo generar el Excel: {exc}")

    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# Routers de api/, montados bajo /api.
from api.routes_query import get_router
from api.routes_quantum_core import router as quantum_core_router
from api.routes_sessions import get_sessions_router

app.include_router(get_router(), prefix="/api", tags=["Inteligencia"])
app.include_router(quantum_core_router, prefix="/api", tags=["Quantum Core"])
app.include_router(get_sessions_router(), prefix="/api", tags=["Historial de Sesiones"])

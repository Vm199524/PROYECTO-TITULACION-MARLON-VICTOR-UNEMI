"""
 * ============================================================================
 * FICHA TÉCNICA DEL SISTEMA [BACKEND-CORE-02]
 * ============================================================================
 * ARCHIVO: db_connector.py
 * MÓDULO: SERVER / Data Gateway (Direct Link)
 * 
 * 🎯 PROPÓSITO GERENCIAL:
 * Es la "Tubería Maestra" de datos. Permite que el sistema se conecte, lea y 
 * entienda la estructura de cualquier base de datos (SQL Server, SQLite o 
 * Postgres) sin poner en riesgo la integridad de la información.
 * 
 * 📍 PUNTO DE OPERACIÓN:
 * Capa de Persistencia. Se sitúa entre el servidor de aplicaciones y los 
 * servidores físicos de base de datos de tu empresa.
 * 
 * ⚙️ CAPACIDADES PRINCIPALES:
 * - Multiconector Universal: Traduce instrucciones para diferentes marcas de DB.
 * - Escaneo de ADN (Introspección): Lee automáticamente qué tablas y columnas
 *   existen para que la IA sepa de qué puede hablar.
 * - Ejecución Segura (Read-Only): Bloquea cualquier intento de borrar o 
 *   alterar datos, garantizando que el asistente solo sea de "Consulta".
 * - Diagnóstico Silencioso: Si falla la conexión, registra el error exacto
 *   para el equipo técnico sin detener el login del usuario.
 * ============================================================================
"""
from __future__ import annotations

import logging
import os
import pathlib
import re
import urllib.parse
from typing import Optional

import sqlalchemy as sa
from dotenv import load_dotenv
from sqlalchemy import inspect, text

# Archivo: db_connector.py
# Rol: adaptador de conexion e introspeccion de bases SQL/SQLite/Postgres.
# Recibe desde: backend/main.py y scripts auxiliares.
# Se conecta con: SQLAlchemy, pyodbc y el motor de sesion activo.
# Responsabilidades: construir connection strings, abrir engine,
# leer schema y ejecutar SQL ya validado por otras capas.

load_dotenv()
logger = logging.getLogger(__name__)

_LOCAL_SQL_HOST_PREFIX_RE = re.compile(
    r"^(localhost|\.|\(local\)|127\.0\.0\.1|0\.0\.0\.0|::1)(?P<suffix>(?:[\\,].*)?)$",
    re.IGNORECASE,
)


def _canonicalize_local_sql_host_prefix(candidate: str) -> str:
    """Canoniza aliases locales de SQL Server a localhost sin perder instancia/puerto."""
    match = _LOCAL_SQL_HOST_PREFIX_RE.match(str(candidate or "").strip())
    if not match:
        return candidate
    return f"localhost{match.group('suffix') or ''}"


def _validate_db_name(name: str, label: str) -> str:
    # Validacion defensiva para evitar inyeccion en nombres de base.
    # Se restringe a alfanumericos, guion bajo y guion medio por seguridad.
    candidate = (name or "").strip()
    if not candidate or not re.fullmatch(r"[A-Za-z0-9_-]+", candidate):
        raise ValueError(f"Nombre invalido para {label}.")
    return candidate


def _quote_db_name(name: str) -> str:
    return f"[{name}]"


def _override_database_in_connection_string(connection_string: str, database: str) -> str | None:
    """Reescribe DATABASE en el DSN ODBC para abrir una conexion temporal a otra BD."""
    prefix = "mssql+pyodbc:///?odbc_connect="
    if not str(connection_string or "").startswith(prefix):
        return None

    safe_db = _validate_db_name(database, "database_override")
    encoded_dsn = connection_string[len(prefix):]
    decoded_dsn = urllib.parse.unquote_plus(encoded_dsn)

    replaced = re.sub(
        r"(?i)(DATABASE\s*=\s*)([^;]*)(;)",
        rf"\1{safe_db}\3",
        decoded_dsn,
        count=1,
    )
    if replaced == decoded_dsn:
        replaced = re.sub(
            r"(?i)(INITIAL\s+CATALOG\s*=\s*)([^;]*)(;)",
            rf"\1{safe_db}\3",
            decoded_dsn,
            count=1,
        )
    if replaced == decoded_dsn:
        if not replaced.endswith(";"):
            replaced += ";"
        replaced += f"DATABASE={safe_db};"

    return f"{prefix}{urllib.parse.quote(replaced)}"


def normalize_sql_server_host(host: str) -> str:
    """
    Normaliza aliases de SQL Server. 
    Asegura que 'localhost' funcione tanto en local como en contenedores (host.docker.internal).
    """
    candidate = str(host or "").strip().strip('"').strip("'")
    if not candidate:
        return ""

    low_host = candidate.lower()
    # Si estamos en Docker/Container y el host es localhost, intentamos apuntar al host físico
    if low_host in ("localhost", "127.0.0.1", "::1", "0.0.0.0"):
        # En muchos entornos de contenedor, host.docker.internal es la ruta al host local.
        if os.name != 'nt': 
            return "host.docker.internal"
        return "localhost"

    if "\\" in candidate:
        candidate = "\\".join(part.strip() for part in candidate.split("\\"))
    if "," in candidate:
        candidate = ",".join(part.strip() for part in candidate.split(","))

    return _canonicalize_local_sql_host_prefix(candidate)


def get_sql_server_host_candidates(host: str) -> list[str]:
    """
    Retorna candidatos de host para SQL Server.
    Si el host es local sin instancia, agrega fallbacks comunes.
    """
    normalized = normalize_sql_server_host(host)
    if not normalized:
        return []

    candidates = [normalized]
    if normalized.lower() != "localhost":
        return candidates

    for alt_host in ("localhost\\SQLEXPRESS", ".\\SQLEXPRESS", "(localdb)\\MSSQLLocalDB"):
        canonical = normalize_sql_server_host(alt_host)
        if canonical and canonical.lower() not in {h.lower() for h in candidates}:
            candidates.append(canonical)
    return candidates


def build_connection_string(
    host: str,
    database: str,
    driver: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
    windows_auth: bool = True,
    local_path: Optional[str] = None,
) -> str:
    """Construye connection string para SQL Server, SQLite o PostgreSQL."""
    host = normalize_sql_server_host(host)
    database = database or ""

    is_postgres = host.startswith("postgresql://") or host.startswith("postgres://")
    if is_postgres:
        if host.startswith("postgresql://") or host.startswith("postgres://"):
            conn_uri = host.replace("postgres://", "postgresql+psycopg2://")
        else:
            conn_uri = f"postgresql+psycopg2://{user}:{password}@{host}/{database}"
        if "sslmode" not in conn_uri:
            separator = "&" if "?" in conn_uri else "?"
            conn_uri += f"{separator}sslmode=require"
        return conn_uri

    # Rutas locales para modo portable SQLite.
    if local_path and local_path.endswith((".db", ".sqlite", ".csv")):
        return f"sqlite:///{local_path}"

    if driver == "AUTO":
        from config import get_best_driver
        driver = get_best_driver()

    odbc_params = (
        f"DRIVER={{{driver}}};"
        f"SERVER={host};"
        f"DATABASE={database};"
        "TrustServerCertificate=yes;"
        "Encrypt=no;"
        "LoginTimeout=15;"
        "Connection Timeout=15;"
        "ConnectRetryCount=0;"
        "FastFirstRow=Yes;"
        "MultiSubnetFailover=No;"
    )
    if windows_auth:
        odbc_params += "Trusted_Connection=yes;"
    else:
        odbc_params += f"UID={user};PWD={password};"

    params_quote = urllib.parse.quote(odbc_params)
    return f"mssql+pyodbc:///?odbc_connect={params_quote}"


class SQLServerConnector:
    """Gestiona conexion, esquema y ejecucion SQL para el motor analitico."""

    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.engine = None
        self.is_sqlite = connection_string.startswith("sqlite")
        self.is_postgres = connection_string.startswith("postgresql")

    def connect(self) -> tuple[bool, str]:
        try:
            # OPTIMIZACION: Pool de conexiones configurado para reducir latencia
            # - pool_size: 10 conexiones permanentes (evita crear nuevas cada vez)
            # - max_overflow: 20 conexiones extra bajo carga pico
            # - pool_pre_ping: True verifica conexion antes de usar (evita errores stale)
            # - pool_recycle: 3600s recicla conexiones viejas (previene leaks)
            self.engine = sa.create_engine(
                self.connection_string,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                pool_recycle=3600,
            )
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True, "Conexion exitosa."
        except Exception as exc:
            # Guardamos diagnostico sin volcar credenciales.
            try:
                debug_dir = pathlib.Path(__file__).parent / "debug"
                debug_dir.mkdir(exist_ok=True)
                if self.connection_string.startswith("sqlite"):
                    engine_hint = "sqlite"
                elif self.connection_string.startswith("postgresql"):
                    engine_hint = "postgresql"
                else:
                    engine_hint = "mssql"
                with open(debug_dir / "connection_error.log", "w", encoding="utf-8") as f:
                    f.write(f"ERROR: {exc}\nENGINE: {engine_hint}\n")
            except Exception:
                pass
            self.engine = None
            return False, f"Error de conexion: {exc}"

    def get_tables_with_data_fast(self, conn, db_q: str = "") -> dict:
        """
        FASE 1 - VELOCIDAD O(1): Identifica qué tablas tienen datos usando
        sys.partitions (estadísticas pre-calculadas por SQL Server).
        
        NO hace SELECT COUNT(*). Lee un valor que el motor ya tiene calculado.
        Es instantáneo incluso con millones de registros o cientos de tablas.
        
        Returns: {table_name: row_count} solo para tablas con datos, ordenado DESC.
        """
        prefix = f"{db_q}." if db_q else ""
        sql = text(
            f"SELECT t.name AS Tabla, SUM(p.rows) AS TotalFilas "
            f"FROM {prefix}sys.tables t "
            f"INNER JOIN {prefix}sys.partitions p ON t.object_id = p.object_id "
            f"WHERE p.index_id IN (0, 1) "
            f"GROUP BY t.name "
            f"HAVING SUM(p.rows) > 0 "
            f"ORDER BY TotalFilas DESC"
        )
        try:
            rows = conn.execute(sql).fetchall()
            return {str(row[0]).strip(): int(row[1]) for row in rows if str(row[0]).strip()}
        except Exception as exc:
            logger.warning("[FAST_SCHEMA] sys.partitions no disponible: %s", exc)
            return {}  # Fallback: el caller usará el método clásico

    def _vistas_con_datos(self, conn, db_prefix: str, views: list[str]) -> set[str]:
        """
        ¿Cuáles de estas vistas tienen al menos una fila ahora mismo?

        Defecto detectado en pruebas (28/08/2026): "siempre salen 14
        vistas" en CHAT sin importar la empresa activa, cuando en realidad
        hay menos con datos reales. Causa: `get_tables_with_data_fast()` usa
        sys.partitions, que solo cubre TABLAS físicas — las VISTAS no tienen
        almacenamiento propio, así que el filtro de "tiene datos" nunca las
        alcanzaba y quedaban señaladas en el código como "las VISTAS siempre
        se incluyen". Efecto colateral real: el esquema que ve la IA
        anunciaba SIEMPRE las ~14 vistas estructurales de CHAT (incluidas
        ficha_trabajador/rol_pago) sin importar si tenían algo para la
        empresa activa, lo que la empujaba a intentar usarlas para preguntas
        que no tenían nada que ver con nómina.

        Un solo round-trip: un EXISTS por vista (corta en la primera fila,
        no cuenta todo el resultado). Si algo falla (permisos, vista rota,
        timeout), se asume que TODAS tienen datos — degradar a la conducta
        anterior es preferible a esconder por error una vista que sí sirve.
        """
        if not views:
            return set()
        try:
            # `db_prefix` es "[BASE]." — falta el esquema para armar un
            # nombre de 3 partes válido cross-db ([BASE].dbo.[vista]).
            # Bug real detectado en pruebas (28/08/2026): sin el "dbo.",
            # SQL Server interpreta "[CHAT].[Vista]" como esquema.objeto DENTRO
            # de la base actual, no como base.objeto, y falla con "objeto no
            # válido" para cualquier vista real.
            selects = " UNION ALL ".join(
                f"SELECT {i} AS idx, CASE WHEN EXISTS(SELECT 1 FROM {db_prefix}dbo.[{v}]) THEN 1 ELSE 0 END AS tiene"
                for i, v in enumerate(views)
            )
            filas = conn.execute(text(selects)).fetchall()
            return {views[int(idx)] for idx, tiene in filas if int(tiene) == 1}
        except Exception as exc:
            logger.warning("[FAST_SCHEMA] No se pudo verificar datos de vistas (%s) — se incluyen todas.", exc)
            return set(views)

    def _get_schema_from_information_schema(self, conn, db_prefix: str = "", tables_filter: set | None = None) -> dict:
        """Introspeccion por INFORMATION_SCHEMA (soporta prefijo cross-db).
        
        tables_filter: si se proporciona, solo carga columnas de esas tablas
        (enorme mejora de velocidad para BD grandes con tablas vacías).
        """
        schema_info: dict = {}

        sql_tables = text(
            f"SELECT TABLE_NAME FROM {db_prefix}INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE'"
        )
        sql_views = text(f"SELECT TABLE_NAME FROM {db_prefix}INFORMATION_SCHEMA.VIEWS")

        tables = [str(r[0]).strip() for r in conn.execute(sql_tables).fetchall() if str(r[0]).strip()]
        views = [str(r[0]).strip() for r in conn.execute(sql_views).fetchall() if str(r[0]).strip()]

        # Aplicar filtro si fue proporcionado (solo tablas con datos)
        if tables_filter is not None:
            active_tables = [t for t in tables if t in tables_filter]
            logger.info("[FAST_SCHEMA] Filtrando: %d/%d tablas tienen datos", len(active_tables), len(tables))
        else:
            active_tables = tables

        # Mismo filtro para vistas (ver _vistas_con_datos): antes se incluían
        # TODAS sin comprobar si tenían datos para la base activa.
        active_views = views
        if views:
            con_datos = self._vistas_con_datos(conn, db_prefix, views)
            active_views = [v for v in views if v in con_datos]
            logger.info("[FAST_SCHEMA] Filtrando vistas: %d/%d tienen datos", len(active_views), len(views))

        for table_name in active_tables:
            schema_info[table_name] = {"type": "TABLA", "columns": [], "row_count": tables_filter.get(table_name, 0) if isinstance(tables_filter, dict) else 0}
        for view_name in active_views:
            schema_info[view_name] = {"type": "VISTA", "columns": [], "row_count": 0}

        # Cargar columnas SOLO para las tablas/vistas activas (no para todas)
        if active_tables or active_views:
            all_active = set(active_tables) | set(active_views)
            sql_all_cols = text(
                f"SELECT TABLE_NAME, COLUMN_NAME, DATA_TYPE, IS_NULLABLE "
                f"FROM {db_prefix}INFORMATION_SCHEMA.COLUMNS "
                + (
                    f"WHERE TABLE_NAME IN ({', '.join(repr(t) for t in all_active)})"
                    if all_active else ""
                )
            )
            for r in conn.execute(sql_all_cols).fetchall():
                table_name = str(r[0]).strip()
                if not table_name or table_name not in schema_info:
                    continue
                schema_info[table_name]["columns"].append(
                    {
                        "name": str(r[1]).strip(),
                        "type": str(r[2]),
                        "nullable": str(r[3]).upper() == "YES",
                    }
                )

        return schema_info

    def _get_schema_from_sys_catalog(self, conn, db_q: str, tables_filter: dict | None = None) -> dict:
        """
        Fallback SQL Server por catalogo sys.*
        Funciona mejor en entornos donde INFORMATION_SCHEMA esta restringido.
        tables_filter: {table_name: row_count} - solo carga columnas de estas tablas.
        """
        schema_info: dict = {}
        sql_objects = text(
            f"SELECT o.name AS OBJECT_NAME, o.type AS OBJECT_TYPE "
            f"FROM {db_q}.sys.objects o "
            "WHERE o.type IN ('U', 'V') AND o.is_ms_shipped = 0"
        )

        object_rows = conn.execute(sql_objects).fetchall()
        candidatas_vista = [
            str(row[0]).strip() for row in object_rows
            if str(row[0]).strip() and str(row[1]).strip().upper() == 'V'
        ]
        # Mismo filtro que _get_schema_from_information_schema (ver
        # _vistas_con_datos): sys.partitions no cubre vistas, así que sin
        # esto "las VISTAS siempre se incluyen" sin importar la empresa activa.
        vistas_con_datos = self._vistas_con_datos(conn, f"{db_q}.", candidatas_vista) if candidatas_vista else set()

        for row in object_rows:
            object_name = str(row[0]).strip()
            object_type = str(row[1]).strip().upper()
            if not object_name:
                continue
            # Aplicar filtro: solo incluir tablas/vistas con datos reales.
            if tables_filter is not None and object_type == 'U' and object_name not in tables_filter:
                continue
            if object_type == 'V' and object_name not in vistas_con_datos:
                continue
            schema_info[object_name] = {
                "type": "VISTA" if object_type == "V" else "TABLA",
                "columns": [],
                "row_count": tables_filter.get(object_name, 0) if tables_filter and object_type == 'U' else 0,
            }

        if not schema_info:
            return {}

        for row in conn.execute(text(
            f"SELECT o.name AS OBJECT_NAME, c.name AS COLUMN_NAME, t.name AS DATA_TYPE, c.is_nullable "
            f"FROM {db_q}.sys.columns c "
            f"INNER JOIN {db_q}.sys.objects o ON c.object_id = o.object_id "
            f"INNER JOIN {db_q}.sys.types t ON c.user_type_id = t.user_type_id AND c.system_type_id = t.system_type_id "
            "WHERE o.type IN ('U', 'V')"
        )).fetchall():
            object_name = str(row[0]).strip()
            if object_name not in schema_info:
                continue
            schema_info[object_name]["columns"].append(
                {
                    "name": str(row[1]).strip(),
                    "type": str(row[2]),
                    "nullable": bool(row[3]),
                }
            )

        return schema_info

    def _get_schema_from_inspector(self, engine_obj) -> dict:
        schema_info: dict = {}
        inspector = inspect(engine_obj)
        tables = inspector.get_table_names()
        views = inspector.get_view_names()

        for table_name in tables + views:
            obj_type = "VISTA" if table_name in views else "TABLA"
            schema_info[table_name] = {"type": obj_type, "columns": []}
            for col in inspector.get_columns(table_name):
                schema_info[table_name]["columns"].append(
                    {
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                    }
                )
        return schema_info

    def _get_schema_from_temp_database(self, database_name: str) -> dict:
        """
        Fallback final: abre un engine temporal apuntando directamente a la BD destino.
        Evita limitaciones de introspeccion cross-db cuando la conexion base esta en CHAT.
        """
        override_conn_str = _override_database_in_connection_string(self.connection_string, database_name)
        if not override_conn_str:
            return {}

        temp_engine = None
        try:
            temp_engine = sa.create_engine(
                override_conn_str,
                pool_size=1,
                max_overflow=0,
                pool_pre_ping=True,
                pool_recycle=900,
            )
            with temp_engine.connect() as conn:
                schema_info = self._get_schema_from_information_schema(conn)
                if schema_info:
                    return schema_info
            return self._get_schema_from_inspector(temp_engine)
        except Exception as exc:
            logger.warning("Fallback de introspeccion directa fallido (%s): %s", database_name, exc)
            return {}
        finally:
            if temp_engine is not None:
                temp_engine.dispose()

    def get_schema(self, database_override: Optional[str] = None, empresa: str = "") -> dict:
        if not self.engine:
            return {}

        schema_info: dict = {}
        try:
            if database_override and not self.is_sqlite and not self.is_postgres:
                safe_db = _validate_db_name(database_override, "database_override")
                db_q = _quote_db_name(safe_db)
                with self.engine.connect() as conn:
                    # Auditoría 09/09/2026 (#2, seguimiento — bug reportado
                    # por el usuario: "cualquier pregunta" fallaba con
                    # "permission denied"): VIS_ALUMNO ahora filtra por
                    # SESSION_CONTEXT (ver crear_chat_academico.sql). Sin
                    # fijarlo aquí, la verificación "¿tiene datos?" de más
                    # abajo (_vistas_con_datos) veía VIS_ALUMNO con 0 filas y
                    # la EXCLUÍA del esquema — la IA se quedaba sin ver
                    # ninguna tabla real y alucinaba nombres típicos de star
                    # schema (fact_matriculas, dim_tiempo...) que SÍ existen
                    # pero chat_reader no puede leer. Se fija ANTES de
                    # cualquier chequeo, en la misma conexión (todo este
                    # método usa un único `with engine.connect()`).
                    if safe_db.upper() == "CHAT" and empresa:
                        try:
                            conn.execute(
                                text("EXEC sp_set_session_context @key = N'empresa_activa', @value = :empresa"),
                                {"empresa": empresa.strip().upper()},
                            )
                        except Exception as _ctx_exc:
                            logger.warning("[FAST_SCHEMA] No se pudo fijar SESSION_CONTEXT: %s", _ctx_exc)
                    # ─── FASE 1: Descubrimiento Rápido O(1) con sys.partitions ───
                    # Identifica qué tablas tienen datos SIN hacer SELECT COUNT(*)
                    tables_with_data = self.get_tables_with_data_fast(conn, db_q=db_q)
                    logger.info(
                        "[FAST_SCHEMA] %s: %d tablas con datos detectadas via sys.partitions",
                        safe_db, len(tables_with_data)
                    )

                    # ─── FASE 2: Carga de columnas SOLO para tablas con datos ───
                    if tables_with_data:
                        try:
                            schema_info = self._get_schema_from_information_schema(
                                conn, db_prefix=f"{db_q}.", tables_filter=tables_with_data
                            )
                        except Exception as info_exc:
                            logger.warning("INFORMATION_SCHEMA cross-db fallo para %s: %s", safe_db, info_exc)
                            schema_info = {}
                        if not schema_info:
                            try:
                                schema_info = self._get_schema_from_sys_catalog(
                                    conn, db_q=db_q, tables_filter=tables_with_data
                                )
                            except Exception as sys_exc:
                                logger.warning("Fallback sys catalog fallo para %s: %s", safe_db, sys_exc)
                                schema_info = {}
                    else:
                        # sys.partitions no devolvio nada (permisos limitados)
                        # Usar el método clásico sin filtro como fallback
                        logger.info("[FAST_SCHEMA] sys.partitions vacio, usando INFORMATION_SCHEMA completo")
                        try:
                            schema_info = self._get_schema_from_information_schema(conn, db_prefix=f"{db_q}.")
                        except Exception:
                            schema_info = {}
                        if not schema_info:
                            try:
                                schema_info = self._get_schema_from_sys_catalog(conn, db_q=db_q)
                            except Exception:
                                schema_info = {}

                if not schema_info:
                    # Fallback extra: abrir conexion temporal directa a la BD objetivo.
                    schema_info = self._get_schema_from_temp_database(safe_db)
                if not schema_info:
                    logger.warning("No se pudo introspectar esquema para la base activa %s.", safe_db)
            else:
                schema_info = self._get_schema_from_inspector(self.engine)
        except Exception as exc:
            logger.warning("Error en introspeccion de esquema (%s): %s", database_override, exc)

        return schema_info

    def get_schema_as_text(self, database_override: Optional[str] = None, schema_dict: Optional[dict] = None) -> str:
        schema = schema_dict if schema_dict is not None else self.get_schema(database_override=database_override)
        if not schema:
            return "No se pudo obtener el schema."

        lines = ["=== ESQUEMA DE DATOS (PORTABLE) ===\n"]
        for table, info in schema.items():
            lines.append(f"{info['type']}: [{table}]")
            lines.append("COLUMNAS:")
            for col in info["columns"]:
                nullable = "" if col["nullable"] else " NOT NULL"
                lines.append(f"  - {col['name']} ({col['type']}){nullable}")
            lines.append("")
        return "\n".join(lines)

    def execute_query(self, sql: str, execution_timeout: int = 40, target_db: Optional[str] = None) -> tuple[list, list, str]:
        """
        Ejecuta consulta SQL con timeout real y soporte para cambio de base dinámico.

        IMPORTANTE — dos límites distintos que antes se confundían:
          · LOCK_TIMEOUT: cuánto espera la consulta a que OTRA sesión libere un
            bloqueo. NO limita cuánto tarda la consulta en ejecutarse.
          · Query timeout (pyodbc `Connection.timeout`): cuánto puede tardar la
            consulta en total. Este faltaba, y por eso una consulta pesada
            generada por la IA podía correr indefinidamente dejando al usuario
            con la pantalla girando sin explicación.
        """
        if not self.engine:
            return [], [], "No hay conexion activa."
        try:
            with self.engine.connect() as conn:
                # Cambio de contexto dinámico (Stateless Multi-tenant)
                if target_db and not self.is_sqlite and not self.is_postgres:
                    safe_db = _validate_db_name(target_db, "target_db_execution")
                    conn.execute(text(f"USE [{safe_db}]"))

                if not self.is_sqlite and not self.is_postgres:
                    # Espera máxima por bloqueos de otras sesiones.
                    conn.execute(text(f"SET LOCK_TIMEOUT {execution_timeout * 1000}"))
                    # Tiempo máximo de EJECUCIÓN de la consulta. Se aplica sobre
                    # la conexión DBAPI (pyodbc) porque SQL Server no admite un
                    # equivalente por sentencia desde T-SQL.
                    try:
                        conn.connection.timeout = execution_timeout
                    except Exception:
                        # Si el driver no soporta el atributo, seguimos igual:
                        # perdemos el corte por tiempo pero no rompemos la consulta.
                        pass

                result = conn.execute(text(sql), execution_options={
                    "stream_results": True,  # OPTIMIZACION: Streaming para resultados grandes
                })
                columns = list(result.keys())
                rows = [list(row) for row in result.fetchall()]
                return columns, rows, None
        except Exception as exc:
            err_msg = str(exc)
            if "no such table" in err_msg.lower():
                err_msg = "La tabla no existe en el archivo local."
            elif "timeout" in err_msg.lower() or "expired" in err_msg.lower():
                # Mensaje pensado para el usuario final, no para un DBA: explica
                # qué pasó y qué puede hacer al respecto.
                err_msg = (
                    f"La consulta tardó más de {execution_timeout} segundos y se detuvo. "
                    "Normalmente significa que abarca demasiada información: prueba "
                    "acotarla a un año o un mes concreto, o pedir menos resultados."
                )
            return [], [], err_msg

    def execute_query_with_context(
        self, sql: str, empresa: str, execution_timeout: int = 40
    ) -> tuple[list, list, str]:
        """
        Igual que `execute_query`, pero fija el aislamiento por empresa con
        `SESSION_CONTEXT()` en vez de una vista global reconfigurable.

        Auditoría 09/09/2026 (auditoría interna del 09/09/2026, hallazgo #2):
        `SP_MODIFICA_VISTA_IA` hacía `ALTER VIEW` sobre un namespace
        COMPARTIDO entre empresas — dos usuarios conectados a empresas
        distintas al mismo tiempo podían pisarse (condición de carrera ya
        documentada como fuga de datos real el 27/07/2026, nunca resuelta
        de fondo). `SESSION_CONTEXT` es aislado POR CONEXIÓN física, no
        global, así que dos conexiones nunca se pisan — pero eso exige que
        el `SET` y el `SELECT` corran en la MISMA conexión física, no en
        conexiones distintas del pool. Por eso está todo en un único
        `with self.engine.connect()`, a diferencia de antes (donde activar
        el contexto y ejecutar el SELECT eran pasos separados que podían
        caer en conexiones distintas).
        """
        if not self.engine:
            return [], [], "No hay conexion activa."
        try:
            with self.engine.connect() as conn:
                if not self.is_sqlite and not self.is_postgres:
                    # OJO: sin @read_only=1 a propósito. Estas conexiones vienen de
                    # un POOL (pool_size=10 en connect()) y se reutilizan entre
                    # peticiones distintas — si se marcara read_only, la segunda
                    # petición que reutilice esta misma conexión física para OTRA
                    # empresa fallaría al intentar cambiar el valor. Cada request
                    # abre su propio `with engine.connect()`, así que sobrescribir
                    # el valor en cada llamada es exactamente lo correcto.
                    conn.execute(
                        text("EXEC sp_set_session_context @key = N'empresa_activa', @value = :empresa"),
                        {"empresa": (empresa or "").strip().upper()},
                    )
                    conn.execute(text(f"SET LOCK_TIMEOUT {execution_timeout * 1000}"))
                    try:
                        conn.connection.timeout = execution_timeout
                    except Exception:
                        pass

                result = conn.execute(text(sql), execution_options={"stream_results": True})
                columns = list(result.keys())
                rows = [list(row) for row in result.fetchall()]
                return columns, rows, None
        except Exception as exc:
            err_msg = str(exc)
            if "timeout" in err_msg.lower() or "expired" in err_msg.lower():
                err_msg = (
                    f"La consulta tardó más de {execution_timeout} segundos y se detuvo. "
                    "Normalmente significa que abarca demasiada información: prueba "
                    "acotarla a un año o un mes concreto, o pedir menos resultados."
                )
            return [], [], err_msg


def get_available_databases(
    host: str,
    driver: str,
    user: Optional[str] = None,
    password: Optional[str] = None,
    windows_auth: bool = True,
) -> list[dict]:
    """Obtiene lista de bases con sus nombres comerciales desde sys300 si existen."""
    host_candidates = get_sql_server_host_candidates(host)
    if not host_candidates:
        return []

    last_exc = None
    for idx, current_host in enumerate(host_candidates):
        conn_str = build_connection_string(current_host, "master", driver, user, password, windows_auth)
        engine = None
        try:
            engine = sa.create_engine(conn_str, connect_args={"timeout": 12})
            with engine.connect() as conn:
                # 1. Obtener lista de bases ONLINE
                sql_dbs = text(
                    "SELECT name FROM sys.databases "
                    "WHERE state_desc = 'ONLINE' "
                    "AND name NOT IN ('master', 'tempdb', 'model', 'msdb') "
                    "ORDER BY name"
                )
                db_names = [row[0] for row in conn.execute(sql_dbs).fetchall()]
                
                if not db_names:
                    is_last_candidate = idx == len(host_candidates) - 1
                    if current_host.lower() == "localhost" and not is_last_candidate:
                        continue
                    return []

                # 2. Intentar obtener nombres comerciales de forma segura para cada base
                biz_map = {}
                for db in db_names:
                    try:
                        # Verificamos si existe sys300 antes de intentar leerla
                        safe_db = _quote_db_name(db)
                        
                        # ESTRATEGIA A: sys300 (Estándar Contabilidad/Ventas)
                        check_sql = text(f"SELECT OBJECT_ID('{safe_db}.dbo.sys300')")
                        if conn.execute(check_sql).fetchone()[0] is not None:
                            name_sql = text(f"SELECT TOP 1 CAST(nombre AS NVARCHAR(255)) FROM {safe_db}.dbo.sys300 WHERE codigo IS NOT NULL")
                            res = conn.execute(name_sql).fetchone()
                            if res and res[0]:
                                biz_map[db] = str(res[0]).strip()
                        
                        # ESTRATEGIA B: tb_empres (Estándar RRHH/Nómina) si A falló
                        if db not in biz_map:
                            check_sql_b = text(f"SELECT OBJECT_ID('{safe_db}.dbo.tb_empres')")
                            if conn.execute(check_sql_b).fetchone()[0] is not None:
                                name_sql_b = text(f"SELECT TOP 1 CAST(emp_nombre AS NVARCHAR(255)) FROM {safe_db}.dbo.tb_empres")
                                res_b = conn.execute(name_sql_b).fetchone()
                                if res_b and res_b[0]:
                                    biz_map[db] = str(res_b[0]).strip()
                    except Exception:
                        continue
                
                results = []
                for db in db_names:
                    results.append({
                        "database": db,
                        "business_name": biz_map.get(db, db)
                    })
                
                return results
        except Exception as exc:
            last_exc = exc
            logger.info("Intento de listado fallido en host SQL %s: %s", current_host, exc)
        finally:
            if engine is not None:
                engine.dispose()

    if last_exc is not None:
        logger.warning(
            "No se pudo listar bases en %s. Error: %s",
            normalize_sql_server_host(host), last_exc
        )
    return []

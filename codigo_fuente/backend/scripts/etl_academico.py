# -*- coding: utf-8 -*-
"""
etl_academico.py — ETL fisico del dominio academico hacia el warehouse CHAT.

Generico / agnostico de institucion (ver backend/etl/perfiles.py): este
script no sabe nada del esquema de UNEMI ni de ninguna otra IES en
particular. Solo conoce los nombres LOGICOS de columnas que el warehouse
CHAT necesita (perfiles.COLUMNAS_REQUERIDAS) y delega en un
PerfilInstitucion el SELECT concreto que produce esas columnas desde el
esquema real de cada institucion. Conectar una IES nueva (ej. UPS Cuenca) es
agregar un perfil, no reescribir este archivo — ver el docstring de
perfiles.py para el procedimiento completo.

Es TRUNCATE + INSERT (recarga completa), no incremental/CDC — apropiado
para el tamano y la cadencia de este proyecto de tesis. Un pipeline
incremental real (CDC leyendo el transaction log) queda documentado como
evolucion futura, no en este alcance.

Uso:
    cd backend
    python scripts/etl_academico.py --perfil UNEMI_PRUEBAS
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import pyodbc

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from etl.perfiles import PerfilInstitucion, obtener_perfil, validar_columnas  # noqa: E402
from conexion_admin import conectar_admin  # noqa: E402


def conectar(host: str | None, driver: str | None, user: str | None, password: str | None,
             database: str) -> pyodbc.Connection:
    return conectar_admin(database, host=host, user=user, password=password, driver=driver)


def extraer(cursor_origen, perfil: PerfilInstitucion) -> list[dict]:
    cursor_origen.execute(perfil.sql_origen)
    columnas = [c[0] for c in cursor_origen.description]
    validar_columnas(columnas, perfil)
    return [dict(zip(columnas, fila)) for fila in cursor_origen.fetchall()]


def trimestre_de(mes: int) -> int:
    return (mes - 1) // 3 + 1


def _upsert_dim_simple(cursor, tabla: str, columna_pk: str, valor: str) -> None:
    cursor.execute(
        f"IF NOT EXISTS (SELECT 1 FROM dbo.{tabla} WHERE {columna_pk} = ?) "
        f"INSERT INTO dbo.{tabla} ({columna_pk}) VALUES (?)",
        valor, valor,
    )


def cargar(cursor_destino, conn_destino, filas: list[dict], empresa_codigo: str, business_name: str) -> int:
    # ── Reinicio completo DE ESTA INSTITUCIÓN (recarga total, no incremental) ──
    # Orden obligado por las FK: predicciones -> hechos -> alumnos. Nunca se
    # toca lo de otra institución (cada DELETE filtra por empresa_codigo).
    cursor_destino.execute("DELETE FROM dbo.fact_prediccion_abandono WHERE empresa_codigo = ?", empresa_codigo)
    cursor_destino.execute("DELETE FROM dbo.fact_matriculas WHERE empresa_codigo = ?", empresa_codigo)
    cursor_destino.execute("DELETE FROM dbo.dim_alumno WHERE empresa_codigo = ?", empresa_codigo)
    conn_destino.commit()

    # ── dim_empresa ──────────────────────────────────────────────────────
    cursor_destino.execute("""
        IF NOT EXISTS (SELECT 1 FROM dbo.dim_empresa WHERE empresa_codigo = ?)
            INSERT INTO dbo.dim_empresa (empresa_codigo, business_name) VALUES (?, ?)
        ELSE
            UPDATE dbo.dim_empresa SET business_name = ? WHERE empresa_codigo = ?
    """, empresa_codigo, empresa_codigo, business_name, business_name, empresa_codigo)
    conn_destino.commit()

    # ── dim_facultad ─────────────────────────────────────────────────────
    facultades = {(f["facultad_codigo"], f["facultad_nombre"]) for f in filas}
    for codigo, nombre in facultades:
        cursor_destino.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_facultad WHERE facultad_codigo = ?)
                INSERT INTO dbo.dim_facultad (facultad_codigo, facultad_nombre) VALUES (?, ?)
        """, codigo, codigo, nombre)
    conn_destino.commit()

    # ── dim_carrera ──────────────────────────────────────────────────────
    carreras = {(f["carrera"], f["facultad_codigo"]) for f in filas}
    carrera_id_map: dict[tuple[str, str], int] = {}
    for carrera, facultad_codigo in carreras:
        cursor_destino.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_carrera WHERE carrera = ? AND facultad_codigo = ?)
                INSERT INTO dbo.dim_carrera (carrera, facultad_codigo) VALUES (?, ?)
        """, carrera, facultad_codigo, carrera, facultad_codigo)
    conn_destino.commit()
    cursor_destino.execute("SELECT carrera_id, carrera, facultad_codigo FROM dbo.dim_carrera")
    for carrera_id, carrera, facultad_codigo in cursor_destino.fetchall():
        carrera_id_map[(carrera, facultad_codigo)] = carrera_id

    # ── dim_estado_matricula ─────────────────────────────────────────────
    for estado in {f["estado_matricula"] for f in filas}:
        _upsert_dim_simple(cursor_destino, 'dim_estado_matricula', 'estado_codigo', estado)
    conn_destino.commit()

    # ── dim_canal (variable "canal" del requerimiento) ──────────────────
    for canal in {f["canal_codigo"] for f in filas}:
        _upsert_dim_simple(cursor_destino, 'dim_canal', 'canal_codigo', canal)
    conn_destino.commit()

    # ── dim_sede (variable "sede" del requerimiento) ────────────────────
    sedes = {(f["sede_codigo"], f["sede_nombre"]) for f in filas}
    for codigo, nombre in sedes:
        cursor_destino.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_sede WHERE sede_codigo = ?)
                INSERT INTO dbo.dim_sede (sede_codigo, sede_nombre) VALUES (?, ?)
        """, codigo, codigo, nombre)
    conn_destino.commit()

    # ── dim_alumno (clave natural: institución + cédula) ─────────────────
    # Un alumno por identificador DENTRO de la institución; la misma cédula
    # en otra institución es otra fila (UQ_dim_alumno_empresa_cedula).
    alumnos: dict[str, tuple] = {}
    for f in filas:
        alumnos.setdefault(f["cedula"], (empresa_codigo, f["cedula"], f["apellidos"], f["nombres"],
                                         f["genero"], f["ciudad_residencia"]))
    cursor_destino.fast_executemany = True
    cursor_destino.executemany("""
        INSERT INTO dbo.dim_alumno (empresa_codigo, cedula, apellidos, nombres, genero, ciudad_residencia)
        VALUES (?, ?, ?, ?, ?, ?)
    """, list(alumnos.values()))
    conn_destino.commit()
    cursor_destino.execute("SELECT alumno_id, cedula FROM dbo.dim_alumno WHERE empresa_codigo = ?", empresa_codigo)
    alumno_id_map: dict[str, int] = {cedula: alumno_id for alumno_id, cedula in cursor_destino.fetchall()}

    # ── dim_tiempo (una fila por fecha distinta) ────────────────────────
    fechas: set[date] = {f["fecha_matricula"] for f in filas}
    tiempo_id_map: dict[date, int] = {}
    for fecha in fechas:
        cursor_destino.execute("""
            IF NOT EXISTS (SELECT 1 FROM dbo.dim_tiempo WHERE fecha = ?)
                INSERT INTO dbo.dim_tiempo (fecha, anio, mes, trimestre) VALUES (?, ?, ?, ?)
        """, fecha, fecha, fecha.year, fecha.month, trimestre_de(fecha.month))
    conn_destino.commit()
    cursor_destino.execute("SELECT tiempo_id, fecha FROM dbo.dim_tiempo")
    for tiempo_id, fecha in cursor_destino.fetchall():
        tiempo_id_map[fecha] = tiempo_id

    # ── fact_matriculas (carga masiva por lotes) ─────────────────────────
    registros = []
    for f in filas:
        monto = float(f["monto_matricula"])
        beca = int(f["beca_porcentaje"])
        registros.append((
            empresa_codigo,
            alumno_id_map[f["cedula"]],
            carrera_id_map[(f["carrera"], f["facultad_codigo"])],
            f["facultad_codigo"],
            f["estado_matricula"],
            tiempo_id_map[f["fecha_matricula"]],
            f["sede_codigo"],
            f["canal_codigo"],
            int(f["semestre"]),
            float(f["promedio"]),
            float(f["asistencia_pct"]),
            monto,
            beca,
            float(f["saldo_pendiente"]),
            round(monto * (1 - beca / 100), 2),
            bool(f["es_ultimo_periodo"]),
        ))
    cursor_destino.fast_executemany = True
    for i in range(0, len(registros), 20_000):
        cursor_destino.executemany("""
            INSERT INTO dbo.fact_matriculas
                (empresa_codigo, alumno_id, carrera_id, facultad_codigo, estado_codigo,
                 tiempo_id, sede_codigo, canal_codigo, semestre, promedio, asistencia_pct,
                 monto_matricula, beca_porcentaje, saldo_pendiente, monto_neto, es_ultimo_periodo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, registros[i:i + 20_000])
        conn_destino.commit()
    return len(registros)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    # Sin valores por defecto aquí: conexion_admin.py lee backend/.env y se
    # detiene con un mensaje claro si falta la contraseña.
    parser.add_argument("--host", default=None)
    parser.add_argument("--driver", default=None)
    parser.add_argument("--user", default=None)
    parser.add_argument("--password", default=None)
    parser.add_argument("--perfil", default="UNEMI_PRUEBAS", help="Nombre del PerfilInstitucion en backend/etl/perfiles.py")
    args = parser.parse_args()

    perfil = obtener_perfil(args.perfil)

    print(f"Conectando a {args.host} (perfil: {perfil.nombre}) ...")
    conn = conectar(args.host, args.driver, args.user, args.password, perfil.base_datos_origen)
    cur = conn.cursor()

    print(f"Extrayendo con el SELECT del perfil '{perfil.nombre}' ...")
    filas = extraer(cur, perfil)
    print(f"  {len(filas)} filas extraidas.")

    print("Cargando en CHAT (fisico: dimensiones + fact_matriculas) ...")
    conn_chat = conectar(args.host, args.driver, args.user, args.password, "CHAT")
    cur_chat = conn_chat.cursor()
    insertados = cargar(cur_chat, conn_chat, filas, perfil.nombre, perfil.business_name)
    print(f"  {insertados} filas insertadas en CHAT.dbo.fact_matriculas para empresa '{perfil.nombre}'.")

    conn.close()
    conn_chat.close()
    print("ETL completo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

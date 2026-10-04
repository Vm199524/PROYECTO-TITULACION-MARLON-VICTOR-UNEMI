"""
Pruebas del guardarrail de alcance (core/alcance.py).

El objetivo de este banco es doble y las dos mitades importan igual:

  1. Que se BLOQUEE lo que debe bloquearse. El caso que origino todo esto fue
     "como va la guerra entre rusia vs ucrania, ultimas noticias", que el
     sistema respondia con un boletin de Google News.

  2. Que NO se bloquee nada del negocio. Un falso positivo aqui es mucho mas
     grave que un falso negativo: si "margen de ventas" o "clima laboral"
     quedaran bloqueados, romperiamos consultas legitimas que hoy funcionan.
     Por eso hay mas casos de "debe pasar" que de "debe bloquearse".
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.alcance import (  # noqa: E402
    bloque_alcance_para_prompt,
    es_fuera_de_alcance,
    modulo_no_disponible,
    modulos_disponibles,
    respuesta_fuera_de_alcance,
    respuesta_modulo_no_disponible,
)


# ─── Esquemas de ejemplo ────────────────────────────────────────────────────
# MONT es una institucion academica: alumnos + facturacion de servicios.
# NO tiene compras ni nomina, y ese es justamente el punto.
ESQUEMA_MONT = {
    "VIS_ALUMNO": {"type": "VIEW", "row_count": 1033},
    "cabecera_factura": {"type": "VIEW", "row_count": 8421},
    "FACTURADOCOLEGIO": {"type": "VIEW", "row_count": 1200},
}

# AGRINAG es comercial/productiva: ventas, compras, nomina e inventario.
ESQUEMA_AGRINAG = {
    "cabecera_factura": {"type": "VIEW", "row_count": 15000},
    "cabecera_compra": {"type": "VIEW", "row_count": 9000},
    "ficha_trabajador": {"type": "VIEW", "row_count": 320},
    "rol_pago": {"type": "VIEW", "row_count": 3800},
    "kardex_inventario": {"type": "TABLE", "row_count": 45000},
}

# ESQUEMA REAL que en produccion recibe alcance.py despues del filtro de
# `schema_resolver.py` (whitelist_bi): cuando la base tiene mas de 50 tablas
# se descarta todo lo que no sea VIS_* o una tabla fisica de la whitelist, asi
# que "cabecera_factura"/"V_Ventas_Cabecera" NUNCA llegan aqui — lo que llega
# es "tb_cabmov"/"tb_detmov". Bug real (27/08/2026): con solo firmas de texto
# ("factura", "venta"...) el guardarrail declaraba a MONT sin modulo de
# ventas, aunque MONT si factura. Este esquema reproduce ese caso exacto.
ESQUEMA_MONT_FILTRADO_PRODUCCION = {
    "VIS_ALUMNO": {"type": "VIEW", "row_count": 1033},
    "tb_cabmov": {"type": "TABLE", "row_count": 8421},
    "tb_detmov": {"type": "TABLE", "row_count": 40233},
    "tb_client": {"type": "TABLE", "row_count": 512},
}


# ─── 1. Deteccion de preguntas fuera de alcance ─────────────────────────────


@pytest.mark.parametrize(
    "pregunta",
    [
        # El caso original detectado en pruebas.
        "como va la guerra entre rusia vs ucrania, ultimas noticias",
        "cuales son las ultimas noticias de hoy",
        "quien es el presidente de estados unidos",
        "que pasa en el mundo",
        "como va el conflicto en israel",
        "cuando juega la seleccion, hay partido de futbol hoy",
        "recomiendame una pelicula",
        "dame una receta de arroz",
        "cual es la capital de francia",
        "cuentame un chiste",
        "a cuanto esta el bitcoin",
        "como esta el dolar hoy",
        "va a llover mañana",
        "traduce esto al ingles",
        "escribeme un poema",
        "quien invento el telefono",
        # Regresión concreta: estas dos disparaban el "probe de capacidades"
        # porque contienen la subcadena "puedo consultar", y el sistema
        # respondia con el catalogo de tablas sin decir jamas que el tema no
        # lo cubre. El guardarrail debe evaluarse ANTES que ese atajo.
        "puedo consultar sobre la guerra de rusia",
        "puedo consultar sobre la guerra entre rusia vs ucrania",
    ],
)
def test_bloquea_preguntas_externas(pregunta):
    assert es_fuera_de_alcance(pregunta) is True


# ─── 2. Lo que JAMAS debe bloquearse ────────────────────────────────────────


@pytest.mark.parametrize(
    "pregunta",
    [
        # Consultas de negocio directas
        "total de ventas por meses del 2026",
        "cuanto hemos vendido este mes",
        "total de alumnos por curso",
        "total de trabajadores por areas",
        "muestra una grafica de barras con las compras por proveedor",
        "ranking de clientes por facturacion",
        "cual es el margen bruto entre ventas y compras",
        "listado de productos con stock bajo",
        "promedio de sueldos por departamento",
        # Vocabulario de negocio que COINCIDE con palabras externas.
        # Estos son los falsos positivos que el guardarrail debe evitar.
        "como va la guerra de precios con la competencia en ventas",
        "analiza el clima laboral segun la rotacion de personal",
        "cual es la temporada alta de ventas",
        "quien es el cliente mas rentable",
        "muestra el ranking de vendedores del mundial de ventas",
        # Preguntas meta sobre el propio sistema (funcionalidad ya ganada)
        "que empresa esta activa",
        "que puedo preguntarte",
        "que modulos tiene esta base de datos",
        "que te pregunte antes",
        "como se calculo ese total",
        "muestrame las vistas disponibles",
        # El probe de capacidades legitimo debe seguir llegando a su handler.
        "que puedo consultar",
        "sobre que puedo preguntar",
        "que datos tiene esta empresa",
        # Saludos y textos cortos: los maneja el flujo de saludo, no este filtro
        "hola",
        "buenos dias",
        "",
    ],
)
def test_no_bloquea_negocio_ni_meta(pregunta):
    assert es_fuera_de_alcance(pregunta) is False


# ─── 3. Modulos disponibles: dependen de la base, no son una lista fija ─────


def test_modulos_mont_solo_academico_y_ventas():
    modulos = modulos_disponibles(ESQUEMA_MONT)
    texto = " ".join(modulos).lower()
    assert "alumnos" in texto
    assert "ventas" in texto or "facturación" in texto
    # Lo critico: NO debe prometer modulos que esta base no tiene.
    assert "compras" not in texto
    assert "nómina" not in texto and "nomina" not in texto
    assert "inventario" not in texto


def test_modulos_agrinag_incluye_compras_y_nomina():
    modulos = modulos_disponibles(ESQUEMA_AGRINAG)
    texto = " ".join(modulos).lower()
    assert "ventas" in texto or "facturación" in texto
    assert "compras" in texto
    assert "nómina" in texto or "nomina" in texto
    assert "inventario" in texto


def test_tabla_vacia_no_se_ofrece_como_modulo():
    """Una tabla presente pero sin filas no debe anunciarse: prometerla solo
    genera consultas que devuelven cero resultados.

    El descarte se prueba sobre TABLAS, que es donde `row_count` significa
    algo. Antes este test usaba vistas con `row_count: 0`, un caso que en
    produccion no existe como "vista vacia": el connector pone 0 en TODAS las
    vistas porque sys.partitions no las cubre. Comprobarlo con vistas hacia
    pasar por correcto justo el filtro que bloqueaba las consultas reales.
    """
    esquema = {
        "tb_cabmov": {"type": "TABLA", "row_count": 500},
        "tb_cabmov1": {"type": "TABLA", "row_count": 0},
    }
    texto = " ".join(modulos_disponibles(esquema)).lower()
    assert "ventas" in texto or "facturación" in texto
    assert "compras" not in texto


def test_esquema_vacio_no_revienta():
    assert modulos_disponibles({}) == []
    assert modulos_disponibles(None) == []


# ─── 4. Redaccion del rechazo ───────────────────────────────────────────────


def test_respuesta_menciona_empresa_y_modulos_reales():
    msg = respuesta_fuera_de_alcance("MONT", ESQUEMA_MONT, semilla="guerra rusia")
    assert "MONT" in msg
    assert "Alumnos" in msg
    # No debe ofrecer lo que MONT no tiene.
    assert "Compras" not in msg
    assert "Nómina" not in msg


def test_respuesta_es_estable_para_la_misma_pregunta():
    """Repetir la misma pregunta no debe producir un texto distinto cada vez."""
    a = respuesta_fuera_de_alcance("MONT", ESQUEMA_MONT, semilla="guerra rusia")
    b = respuesta_fuera_de_alcance("MONT", ESQUEMA_MONT, semilla="guerra rusia")
    assert a == b


def test_respuesta_varia_entre_preguntas_distintas():
    """Con varias preguntas distintas no debe salir siempre la misma apertura:
    eso es lo que hace que el sistema suene a plantilla fija."""
    preguntas = [
        "guerra rusia ucrania",
        "quien es el presidente",
        "receta de arroz",
        "a cuanto esta el bitcoin",
        "cuentame un chiste",
        "va a llover mañana",
        "recomiendame una pelicula",
        "cual es la capital de francia",
    ]
    aperturas = {
        respuesta_fuera_de_alcance("MONT", ESQUEMA_MONT, semilla=p).split(".")[0]
        for p in preguntas
    }
    assert len(aperturas) > 1


def test_respuesta_sin_esquema_no_inventa_modulos():
    msg = respuesta_fuera_de_alcance("MONT", None, semilla="x")
    assert "sincronizando" in msg.lower()


# ─── 5. Módulo pedido que la base no tiene ──────────────────────────────────


def test_avisa_que_mont_no_maneja_compras():
    """Caso real: en un colegio, 'compras por proveedor' respondia 'no se
    encontraron registros', como si fuera un filtro mal puesto."""
    assert modulo_no_disponible(
        "Muestra una grafica de barras con el total de compras por proveedor",
        ESQUEMA_MONT,
    ) == "compras"


def test_avisa_que_mont_no_maneja_nomina():
    assert modulo_no_disponible("total de trabajadores por area", ESQUEMA_MONT) == "nomina"


@pytest.mark.parametrize(
    "pregunta",
    [
        # El modulo SI existe en MONT: debe seguir el flujo normal.
        "total de alumnos por curso",
        "total de ventas por meses del 2026",
        # Pregunta sin modulo identificable: no corresponde avisar.
        "cual fue el mejor mes",
        "muestrame un resumen",
    ],
)
def test_no_avisa_cuando_el_modulo_existe_o_no_se_identifica(pregunta):
    assert modulo_no_disponible(pregunta, ESQUEMA_MONT) is None


def test_ventas_se_reconoce_con_esquema_filtrado_de_produccion():
    """Regresion real (27/08/2026): con el esquema tal como llega despues del
    filtro whitelist de schema_resolver.py (solo tb_cabmov/tb_detmov, sin
    'cabecera_factura'), el guardarrail SI debe reconocer que MONT tiene
    ventas y NO debe bloquear la pregunta."""
    modulos = modulos_disponibles(ESQUEMA_MONT_FILTRADO_PRODUCCION)
    assert any("Ventas" in m for m in modulos)
    assert modulo_no_disponible(
        "total de ventas de enero a julio del 2026", ESQUEMA_MONT_FILTRADO_PRODUCCION
    ) is None
    assert modulo_no_disponible(
        "total de ventas del 2026", ESQUEMA_MONT_FILTRADO_PRODUCCION
    ) is None


def test_compras_no_se_confunde_con_ventas_por_sufijo_tb_cabmov1():
    """tb_cabmov (ventas) y tb_cabmov1 (compras) comparten prefijo: la
    coincidencia debe ser EXACTA para no mezclar los dos módulos."""
    esquema_solo_compras = {
        "tb_cabmov1": {"type": "TABLE", "row_count": 500},
        "tb_detmov1": {"type": "TABLE", "row_count": 2000},
    }
    modulos = modulos_disponibles(esquema_solo_compras)
    assert any("Compras" in m for m in modulos)
    assert not any("Ventas" in m for m in modulos)


def test_no_avisa_si_al_menos_un_modulo_pedido_existe():
    """'margen entre ventas y compras' en una base con ventas debe pasar:
    bloquearlo romperia la métrica de margen bruto que ya funciona."""
    assert modulo_no_disponible(
        "cual es el margen entre ventas y compras", ESQUEMA_MONT
    ) is None


def test_no_avisa_en_agrinag_que_si_tiene_compras():
    assert modulo_no_disponible("total de compras por proveedor", ESQUEMA_AGRINAG) is None


def test_no_avisa_sin_esquema():
    """Sin esquema cargado la detección no es fiable: no contradecimos al motor."""
    assert modulo_no_disponible("total de compras", None) is None
    assert modulo_no_disponible("total de compras", {}) is None
    assert modulo_no_disponible("total de compras", {"tabla_rara": {"row_count": 5}}) is None


def test_mensaje_modulo_ausente_es_claro_y_ofrece_alternativas():
    msg = respuesta_modulo_no_disponible("compras", "MONT", ESQUEMA_MONT)
    assert "MONT" in msg
    assert "compras" in msg.lower()
    # Debe descartar explicitamente la pista falsa de "fechas/filtros".
    assert "fechas" in msg.lower()
    assert "Alumnos" in msg


# ─── 6. Bloque inyectado en el prompt ───────────────────────────────────────


def test_bloque_prompt_lista_modulos_de_la_base():
    bloque = bloque_alcance_para_prompt("MONT", ESQUEMA_MONT)
    assert "MONT" in bloque
    assert "Alumnos" in bloque
    assert "Compras" not in bloque


def test_bloque_prompt_tolera_esquema_vacio():
    bloque = bloque_alcance_para_prompt(None, {})
    assert "sincronización" in bloque


# ─── 7. Forma REAL del esquema que entrega db_connector.py ──────────────────
# Los esquemas de arriba dan a las vistas un `row_count` realista (1033, 8421).
# Produccion no funciona asi: `db_connector._get_schema_from_information_schema`
# registra TODA vista con `type: "VISTA"` y `row_count: 0`, porque el conteo
# sale de sys.partitions y sys.partitions solo cubre tablas fisicas.
#
# Ese desfase entre fixture y realidad dejo pasar el bug del 28/08/2026: el
# filtro de "tabla vacia" descartaba las vistas de CHAT una por una, el
# guardarrail veia solo las tablas fisicas que quedaran, y respondia
# "esta base no maneja alumnos" en TODAS las empresas. Estos tests fijan la
# forma real para que no vuelva a colarse.
ESQUEMA_CHAT_COMO_LO_ENTREGA_EL_CONNECTOR = {
    "VIS_ALUMNO": {"type": "VISTA", "columns": [], "row_count": 0},
    "cabecera_factura": {"type": "VISTA", "columns": [], "row_count": 0},
    "cabecera_compra": {"type": "VISTA", "columns": [], "row_count": 0},
    "ficha_trabajador": {"type": "VISTA", "columns": [], "row_count": 0},
    "rol_pago": {"type": "VISTA", "columns": [], "row_count": 0},
}


def test_vistas_de_chat_cuentan_como_modulo_aunque_row_count_sea_cero():
    modulos = modulos_disponibles(ESQUEMA_CHAT_COMO_LO_ENTREGA_EL_CONNECTOR)
    texto = " ".join(modulos)
    assert "Alumnos" in texto
    assert "Ventas" in texto
    assert "Compras" in texto
    assert "Nómina" in texto


def test_no_bloquea_consultas_reales_con_el_esquema_real_de_chat():
    esquema = ESQUEMA_CHAT_COMO_LO_ENTREGA_EL_CONNECTOR
    for pregunta in (
        "Muéstrame el listado de alumnos matriculados",
        "total de estudiantes por cursos",
        "total de ventas por meses",
        "total de compras por proveedor",
        "rol de pago de los trabajadores",
    ):
        assert modulo_no_disponible(pregunta, esquema) is None, pregunta


def test_tabla_fisica_vacia_si_se_sigue_descartando():
    # El filtro original conserva su proposito: una TABLA con cero filas no se
    # ofrece como modulo disponible.
    esquema = {
        "edu_alumno": {"type": "TABLA", "columns": [], "row_count": 0},
        "tb_cabmov": {"type": "TABLA", "columns": [], "row_count": 8421},
    }
    modulos = " ".join(modulos_disponibles(esquema))
    assert "Alumnos" not in modulos
    assert "Ventas" in modulos

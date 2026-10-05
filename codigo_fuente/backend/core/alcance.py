"""
Guardarraíl de alcance conversacional de VicMar Data AI.

Frena de forma conservadora las preguntas claramente ajenas a los datos de la
empresa (geopolítica, deportes, recetas, clima...) y responde con los módulos
que la base activa sí tiene, deducidos del esquema real. También avisa cuando
se pide un módulo que esa base no maneja. Ante la duda no bloquea y deja
razonar a la IA; las preguntas meta sobre el sistema pasan intactas.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

from __future__ import annotations

import random
import re
import unicodedata

# ─── Normalización ──────────────────────────────────────────────────────────


def _normalizar(texto: str) -> str:
    """Pasa a minúsculas y quita tildes y signos; es la base común de todas las reglas."""
    txt = str(texto or "").lower()
    txt = unicodedata.normalize("NFD", txt)
    txt = "".join(c for c in txt if unicodedata.category(c) != "Mn")
    txt = re.sub(r"[^a-z0-9ñ\s]", " ", txt)
    return re.sub(r"\s+", " ", txt).strip()


# ─── 1. Módulos realmente disponibles en la base conectada ──────────────────

# Cada módulo se reconoce por fragmentos que aparecen en el nombre de la
# tabla o vista. El orden importa solo para la presentación.
# `schema_resolver.py` filtra el esquema crudo antes de que llegue aquí: cuando
# una base tiene más de 50 tablas (cualquier ERP completo), todo lo que no
# empiece con "VIS_" se descarta salvo una lista fija de tablas físicas
# (`whitelist_bi` en schema_resolver.py: tb_cabmov, tb_detmov, tb_cabmov1,
# tb_detmov1, tb_trabaj, tb_cabrol, tb_detrol, tb_acutra, edu_alumno,
# edu_cursos, tb_client, tb_provee, tb_item...). Por eso `cabecera_factura` o
# `V_Ventas_Cabecera` casi nunca llegan a `modulos_disponibles()`: lo que de
# verdad ve este módulo es `tb_cabmov`/`tb_detmov`. Si las firmas solo buscaran
# palabras como "factura" o "venta", el módulo Ventas se declararía inexistente
# aunque la empresa SÍ facture (como en MONT). Por eso cada módulo tiene una
# lista adicional de nombres FÍSICOS exactos (comparación exacta, no
# subcadena, para no confundir tb_cabmov con tb_cabmov1: son ventas y compras
# respectivamente).
_FIRMAS_MODULO: list[tuple[str, str, tuple[str, ...], tuple[str, ...]]] = [
    (
        "alumnos",
        "Alumnos y matrícula (estudiantes, cursos, estados académicos)",
        ("alumno", "estudiante", "matricula", "curso", "academic", "colegio"),
        ("edu_alumno", "edu_cursos"),
    ),
    (
        "ventas",
        "Ventas y facturación (facturas, clientes, cobros)",
        ("factura", "venta", "cliente", "cobrado", "facturado", "pedido"),
        ("tb_cabmov", "tb_detmov", "tb_client"),
    ),
    (
        "compras",
        "Compras y proveedores (órdenes, pagos a proveedores)",
        ("compra", "proveedor", "orden_compra", "pago_prov"),
        ("tb_cabmov1", "tb_detmov1", "tb_provee"),
    ),
    (
        "nomina",
        "Nómina y talento humano (trabajadores, roles de pago)",
        ("trabajador", "rol_pago", "nomina", "empleado", "rrhh", "novtrabajador"),
        ("tb_trabaj", "tb_cabrol", "tb_detrol", "tb_acutra"),
    ),
    (
        "inventario",
        "Inventario (productos, stock, kardex, bodegas)",
        ("inventario", "kardex", "producto", "stock", "bodega", "item"),
        ("tb_item", "tb_bodega", "tb_stock", "tb_inventario"),
    ),
    (
        "contabilidad",
        "Contabilidad (asientos, cuentas, balances)",
        ("asiento", "contab", "cuenta_conta", "balance", "mayor"),
        (),
    ),
]


def modulos_disponibles(schema_tables: dict | None) -> list[str]:
    """
    Devuelve la descripción de los módulos con datos REALES en la base activa.

    No es una lista fija: MONT (institución académica) expone Alumnos y Ventas
    de servicios, mientras que otra empresa expone Compras, Nómina o
    Inventario. Se apoya en `row_count` SOLO para tablas físicas: una tabla
    presente pero vacía no cuenta como módulo disponible, porque prometerla al
    usuario solo genera consultas que devuelven cero filas. En las vistas
    `row_count` no es informativo (siempre llega en 0) y por eso nunca se usa
    para descartarlas.
    """
    if not schema_tables:
        return []

    encontrados: list[str] = []
    for _clave, etiqueta, firmas, firmas_exactas in _FIRMAS_MODULO:
        for nombre, info in schema_tables.items():
            n = _normalizar(str(nombre).replace("_", " ")).replace(" ", "_")
            n_plano = _normalizar(str(nombre).replace("_", " "))
            n_sin_guion = n.replace("_", "")
            coincide_substr = any(
                f.replace("_", "") in n_sin_guion or f in n_plano for f in firmas
            )
            coincide_exacta = n_sin_guion in {fe.replace("_", "") for fe in firmas_exactas}
            if not (coincide_substr or coincide_exacta):
                continue
            # Si el descubrimiento marcó la TABLA FÍSICA como vacía, no se
            # ofrece: prometerla solo genera consultas que devuelven cero
            # filas.
            #
            # El descarte se limita a tablas a propósito. `row_count` viene de
            # sys.partitions, que solo cubre tablas físicas: en
            # `db_connector._get_schema_from_information_schema` TODA vista se
            # registra con `row_count: 0` por convención, no porque esté vacía.
            # Como el esquema de CHAT son justamente vistas (VIS_ALUMNO,
            # cabecera_factura, rol_pago...), aplicar el filtro a vistas las
            # descartaría todas y `modulo_no_disponible()` respondería "esta
            # base no maneja alumnos/ventas/compras/nómina" en TODAS las
            # empresas, bloqueando la consulta antes de llegar al motor SQL.
            info_dict = info if isinstance(info, dict) else {}
            tipo = str(info_dict.get("type", "")).strip().upper()
            es_tabla_fisica = tipo in ("TABLA", "TABLE", "BASE TABLE")
            if es_tabla_fisica and info_dict.get("row_count") == 0:
                continue
            encontrados.append(etiqueta)
            break

    return encontrados


def _texto_modulos(modulos: list[str]) -> str:
    """Convierte la lista de módulos en viñetas listas para mostrar."""
    if not modulos:
        return (
            "Todavía estoy sincronizando el esquema de esta base, así que aún no "
            "puedo enumerarte los módulos disponibles."
        )
    return "\n".join(f"• {m}" for m in modulos)


# ─── 2. Detección conservadora de preguntas fuera de alcance ────────────────

# Una herramienta de BI conectada a la base de una empresa no debe responder
# noticias ni temas generales: el usuario pierde la referencia de qué puede
# pedirle al sistema y la empresa paga tokens por respuestas ajenas a sus
# datos. Las preguntas meta ("qué te pregunté antes", "qué empresa está
# activa", "qué puedo preguntarte") sí pasan a la IA: son útiles.
#
# Anclas de DOMINIO: sustantivos que solo tienen sentido dentro del negocio o
# del propio sistema. Si aparece alguna, la pregunta NO se bloquea aunque
# contenga una palabra "externa". Esto es lo que salva casos como
# "guerra de precios en ventas", "clima laboral del personal" o
# "ranking de vendedores del mundial de ventas".
_ANCLAS_DOMINIO = (
    r"\bventas?\b", r"\bcompras?\b", r"\bfacturas?\b", r"\bfacturacion\b",
    r"\bclientes?\b", r"\bproveedor(?:es)?\b", r"\bcobros?\b",
    r"\balumnos?\b", r"\bestudiantes?\b", r"\bmatricula\b", r"\bcursos?\b",
    r"\bempleados?\b", r"\btrabajador(?:es)?\b", r"\bnomina\b", r"\bpersonal\b",
    r"\brol(?:es)? de pago\b", r"\bsueldos?\b", r"\bsalarios?\b",
    r"\bvendedor(?:es)?\b", r"\binventario\b", r"\bstock\b", r"\bbodegas?\b",
    r"\bmargen\b", r"\butilidad\b", r"\begresos?\b",
    r"\bempresa activa\b", r"\bbase de datos\b", r"\besquema\b",
    r"\bque puedo preguntar", r"\bque me preguntaste\b", r"\bque te pregunte\b",
    r"\bmodulos?\b", r"\bvistas?\b", r"\bconsulta anterior\b",
    r"\bdashboard\b", r"\bkpi\b",
)

# Anclas DÉBILES: verbos y cuantificadores que aparecen en consultas de negocio
# pero también en cualquier pregunta cotidiana. "a cuánto está el bitcoin"
# lleva "cuánto" y no por eso es una consulta de negocio, así que estas NO
# protegen frente a un tema externo; solo se usan para no ser agresivos con
# preguntas neutras.
_ANCLAS_DEBILES = (
    r"\bcuanto\b", r"\bcuantos?\b", r"\bcuantas?\b", r"\btotal(?:es)?\b",
    r"\bpromedio\b", r"\branking\b", r"\bgrafic", r"\btabla\b", r"\breporte\b",
    r"\bingresos?\b", r"\bgastos?\b", r"\bproductos?\b", r"\bpagos?\b",
)

# Marcadores externos: solo temas inequívocamente ajenos al negocio.
# Deliberadamente NO se incluyen palabras ambiguas ("crisis", "mercado",
# "tendencia", "crecimiento"), porque son vocabulario legítimo de BI.
_MARCADORES_EXTERNOS = (
    # Geopolítica y actualidad
    r"\bguerra\b", r"\bconflicto (?:en|entre)\b", r"\bnoticias?\b",
    r"\bultimas noticias\b", r"\bque pasa en el mundo\b", r"\bpolitica\b",
    r"\belecciones\b", r"\bpresidente\b", r"\bpresidenta\b",
    r"\bprimer ministro\b", r"\bgobierno de\b", r"\bcongreso\b",
    r"\brusia\b", r"\bucrania\b", r"\bisrael\b", r"\bpalestina\b",
    r"\beeuu\b", r"\bestados unidos\b", r"\bchina\b", r"\bvenezuela\b",
    r"\bonu\b", r"\botan\b", r"\bcia\b",
    # Clima
    r"\bel clima\b", r"\bpronostico del tiempo\b", r"\bva a llover\b",
    r"\btemperatura de (?:hoy|mañana)\b",
    # Deportes y espectáculo
    r"\bfutbol\b", r"\bmundial\b", r"\bpartido de\b", r"\bliga\b",
    r"\bpelicula\b", r"\bserie de netflix\b", r"\bcancion\b",
    r"\bcantante\b", r"\bartista\b", r"\bhoroscopo\b",
    # Conocimiento general / uso indebido como chatbot
    r"\breceta\b", r"\bcomo cocinar\b", r"\bchiste\b", r"\bpoema\b",
    r"\bcapital de\b", r"\bquien invento\b", r"\bquien descubrio\b",
    r"\ben que año (?:nacio|murio)\b", r"\bcuentame (?:un|una) historia\b",
    r"\btraduce\b", r"\bescribeme un\b",
    # Finanzas externas
    r"\bbitcoin\b", r"\bcriptomoneda\b", r"\bbolsa de valores\b",
    r"\bnasdaq\b", r"\bdolar hoy\b", r"\bprecio del petroleo\b",
)

_RE_DOMINIO = re.compile("|".join(_ANCLAS_DOMINIO))
_RE_EXTERNOS = re.compile("|".join(_MARCADORES_EXTERNOS))


def es_fuera_de_alcance(pregunta: str) -> bool:
    """
    Indica si la pregunta es CLARAMENTE ajena a los datos de la empresa.

    Es conservadora: un falso positivo (bloquear "margen de ventas") es mucho
    peor que un falso negativo. Regla de decisión, en este orden:
      1. Sin texto útil -> no se bloquea (lo maneja el flujo de saludo).
      2. Si hay un ancla de DOMINIO -> NO se bloquea. El vocabulario del
         negocio manda: "guerra de precios en ventas" es legítima.
      3. Si hay un marcador externo -> se bloquea.
      4. En cualquier otro caso -> no se bloquea y decide la IA.

    Los cuantificadores (`_ANCLAS_DEBILES`) NO participan en el paso 2 a
    propósito: "a cuánto está el bitcoin" contiene "cuánto" y aun así debe
    bloquearse.
    """
    texto = _normalizar(pregunta)
    if len(texto) < 3:
        return False
    if _RE_DOMINIO.search(texto):
        return False
    return bool(_RE_EXTERNOS.search(texto))


# ─── 3. Redacción del rechazo ───────────────────────────────────────────────

# Varias aperturas para que el rechazo no suene a plantilla fija repetida.
_APERTURAS = (
    "Eso queda fuera de lo que puedo consultar.",
    "No tengo forma de responder eso: no está en los datos a los que accedo.",
    "Esa información no vive en el sistema, así que no puedo dártela.",
    "Me sales del terreno que cubro.",
    "No puedo ayudarte con eso, no forma parte de la información que analizo.",
)


def respuesta_fuera_de_alcance(
    empresa: str | None,
    schema_tables: dict | None,
    semilla: str | None = None,
) -> str:
    """
    Redacta el mensaje de rechazo con los módulos REALES de la base activa.

    Varía la frase de apertura para no sonar a plantilla, pero siempre cierra
    con los módulos disponibles, que es lo que de verdad orienta al usuario.
    `semilla` (normalmente la propia pregunta) hace que la apertura elegida sea
    estable para una misma pregunta: repetir la misma consulta no produce un
    texto distinto cada vez, pero preguntas distintas sí varían.
    """
    modulos = modulos_disponibles(schema_tables)
    nombre = (empresa or "").strip().upper()
    etiqueta = f"**{nombre}**" if nombre and nombre != "CHAT" else "la empresa activa"

    rng = random.Random(semilla) if semilla else random
    apertura = rng.choice(_APERTURAS)

    return (
        f"{apertura} Soy el asistente de Inteligencia de Negocios de VicMar Data AI: "
        f"solo trabajo con los datos de {etiqueta}.\n\n"
        f"Esto es lo que sí tengo disponible en esta base:\n\n"
        f"{_texto_modulos(modulos)}\n\n"
        "Dime qué te interesa de esos módulos y lo consulto al momento."
    )


# ─── 4. Módulo pedido que esta base no tiene ────────────────────────────────

# Palabras que identifican de forma inequívoca el módulo al que apunta la
# pregunta. Se usan SOLO para avisar cuando ese módulo no existe en la base
# activa; nunca para bloquear una consulta de un módulo que sí existe.
_PISTAS_MODULO: dict[str, tuple[str, ...]] = {
    "alumnos": (r"\balumnos?\b", r"\bestudiantes?\b", r"\bmatricula\b"),
    "ventas": (r"\bventas?\b", r"\bfacturacion\b", r"\bfacturas? de venta\b"),
    "compras": (r"\bcompras?\b", r"\bproveedor(?:es)?\b", r"\bordenes? de compra\b"),
    "nomina": (r"\bnomina\b", r"\brol(?:es)? de pago\b", r"\btrabajador(?:es)?\b",
               r"\bempleados?\b"),
    "inventario": (r"\binventario\b", r"\bkardex\b", r"\bstock\b", r"\bbodegas?\b"),
    "contabilidad": (r"\basientos? contable\b", r"\bbalance general\b", r"\blibro mayor\b"),
}

_ETIQUETA_MODULO = {clave: etiqueta for clave, etiqueta, _, _2 in _FIRMAS_MODULO}


def modulo_no_disponible(pregunta: str, schema_tables: dict | None) -> str | None:
    """
    Devuelve el nombre del módulo pedido cuando esa base NO lo tiene.

    Ejemplo: en MONT (institución académica), "total de compras por proveedor"
    acabaría en "No se encontraron registros de compras", como si fuera un
    problema de fechas o de filtros, cuando MONT sencillamente no maneja
    compras. Decirlo de frente ahorra al usuario reformular varias veces una
    pregunta que nunca va a tener respuesta.

    Es deliberadamente prudente y devuelve None (sin aviso) si:
      · no hay esquema cargado, o
      · no se detectó NINGÚN módulo -> la detección no es fiable en esa base y
        no se contradice al motor, o
      · la pregunta apunta a varios módulos y al menos uno sí existe
        (ej. "margen entre ventas y compras" en una base que tiene ventas).
    """
    if not schema_tables:
        return None

    disponibles = modulos_disponibles(schema_tables)
    if not disponibles:
        return None

    texto = _normalizar(pregunta)
    claves_disponibles = {
        clave for clave, etiqueta, _, _2 in _FIRMAS_MODULO if etiqueta in disponibles
    }

    pedidos = {
        clave
        for clave, patrones in _PISTAS_MODULO.items()
        if any(re.search(p, texto) for p in patrones)
    }
    if not pedidos:
        return None
    # Si algo de lo pedido sí existe, que siga el flujo normal.
    if pedidos & claves_disponibles:
        return None

    return sorted(pedidos)[0]


def respuesta_modulo_no_disponible(
    modulo: str,
    empresa: str | None,
    schema_tables: dict | None,
) -> str:
    """Explica que ese módulo no existe en la base activa y ofrece los que sí."""
    nombre = (empresa or "").strip().upper()
    etiqueta = f"**{nombre}**" if nombre and nombre != "CHAT" else "la empresa activa"
    legible = _ETIQUETA_MODULO.get(modulo, modulo).split(" (")[0]

    return (
        f"{etiqueta} no maneja **{legible.lower()}** en esta base, así que no hay "
        "nada que consultar por ahí — no es un problema de fechas ni de filtros.\n\n"
        f"Lo que sí tengo disponible:\n\n"
        f"{_texto_modulos(modulos_disponibles(schema_tables))}\n\n"
        "Dime qué necesitas de esos módulos y lo preparo."
    )


def bloque_alcance_para_prompt(empresa: str | None, schema_tables: dict | None) -> str:
    """
    Construye el fragmento de alcance que se inyecta en el SYSTEM_PROMPT.

    Sirve como segunda línea de defensa: aunque el filtro determinista no
    reconozca un tema externo nuevo, el modelo ya sabe que su alcance está
    acotado y con qué módulos concretos debe redirigir al usuario.
    """
    modulos = modulos_disponibles(schema_tables)
    nombre = (empresa or "").strip().upper() or "la empresa activa"
    listado = "\n".join(f"  • {m}" for m in modulos) if modulos else "  • (esquema en sincronización)"
    return f"Empresa activa: {nombre}\nMódulos con datos en esta base:\n{listado}"

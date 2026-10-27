# -*- coding: utf-8 -*-
"""
Diagramas del video técnico de VicMar (16:9, 13,33 × 7,5 pulgadas).

Cada diagrama se compone en SVG sobre un lienzo de 960 × 540 unidades, que
equivalen a puntos tipográficos (72 por pulgada): el texto más pequeño es de
10 pt y se lee en un video a 1080p (20 píxeles de alto). Mantiene el estilo de
los diagramas del Avance 2 (documentacion/diagramas/av2_*.png): azul petróleo
002E45, azul 0B5C7E, naranja FF6900, cajas redondeadas y Arial.

El texto se envuelve con las métricas reales de Arial (Pillow) y, al
convertir a PNG con el navegador, se verifica que ningún texto se salga de su
caja ni se encime con otro. Los PNG salen a 4000 × 2250 píxeles (300 ppp).

Uso:
    python generar_diagramas.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import html
import io
import sys
from pathlib import Path

from PIL import Image, ImageFont

CARPETA = Path(__file__).resolve().parent
ANCHO, ALTO = 960, 540
PPP = 300
ESCALA = 13.3333 * PPP / ANCHO          # 4000 px de ancho a 300 ppp

PETROLEO, AZUL, AZUL_CLARO = '#002E45', '#0B5C7E', '#EBF5FA'
NARANJA, NARANJA_CLARO, NARANJA_TEXTO = '#FF6900', '#FFF1E6', '#B34A00'
GRIS, GRIS_CLARO, TEXTO = '#64748B', '#F5F7FA', '#14232E'
VERDE, VERDE_CLARO = '#1E7A4C', '#EAF6EF'

_FUENTES = {'normal': 'C:/Windows/Fonts/arial.ttf', 'bold': 'C:/Windows/Fonts/arialbd.ttf',
            'italic': 'C:/Windows/Fonts/ariali.ttf'}
_cache_fuentes: dict[str, ImageFont.FreeTypeFont] = {}

AVISOS: list[str] = []

ESTILOS = {  # relleno, borde, color del título, color del texto
    'azul': (AZUL_CLARO, AZUL, PETROLEO, TEXTO),
    'naranja': (NARANJA_CLARO, NARANJA, PETROLEO, TEXTO),
    'oscuro': (PETROLEO, PETROLEO, '#FFB27A', '#FFFFFF'),
    'capa': (GRIS_CLARO, '#9FB3C4', PETROLEO, TEXTO),
    'blanco': ('#FFFFFF', AZUL, PETROLEO, TEXTO),
    'verde': (VERDE_CLARO, VERDE, PETROLEO, TEXTO),
    'externo': ('#FFFFFF', NARANJA, PETROLEO, TEXTO),
}


def ancho_texto(texto: str, tam: float = 10, peso: str = 'normal') -> float:
    if peso not in _cache_fuentes:
        _cache_fuentes[peso] = ImageFont.truetype(_FUENTES[peso], 200)
    return _cache_fuentes[peso].getlength(texto) * tam / 200


def envolver(texto: str, ancho: float, tam: float = 10, peso: str = 'normal') -> list[str]:
    """Parte el texto en renglones que caben en `ancho` (respeta los saltos explícitos)."""
    salida: list[str] = []
    for parrafo in texto.split('\n'):
        actual = ''
        for palabra in parrafo.split(' '):
            prueba = f'{actual} {palabra}' if actual else palabra
            if ancho_texto(prueba, tam, peso) <= ancho or not actual:
                actual = prueba
            else:
                salida.append(actual)
                actual = palabra
        salida.append(actual)
    return salida


def interlinea(tam: float) -> float:
    return tam * 1.18


class Lienzo:
    def __init__(self, titulo: str, subtitulo: str = ''):
        self.o: list[str] = []
        self.n = 0
        self.o.append(f'<rect x="0" y="0" width="{ANCHO}" height="{ALTO}" fill="#FFFFFF"/>')
        self.o.append(f'<rect x="0" y="0" width="{ANCHO}" height="28" fill="{PETROLEO}"/>')
        self.o.append(f'<rect x="0" y="28" width="{ANCHO}" height="2.5" fill="{NARANJA}"/>')
        self.texto(12, 14, titulo, 14, 'bold', '#FFFFFF', 'start')
        self.texto(ANCHO - 12, 14, subtitulo or
                   'Marlon David Pérez Almachi y Víctor Manuel Lluilema Pisco · UNEMI 2026',
                   10, 'normal', '#D6E4EC', 'end')

    # ── primitivas ────────────────────────────────────────────────────────
    def texto(self, x, y, texto, tam=10, peso='normal', color=TEXTO, ancla='start', cursiva=False):
        estilo = ' font-style="italic"' if cursiva else ''
        self.o.append(f'<text x="{x:.1f}" y="{y:.1f}" font-size="{tam}" font-weight="{peso}" fill="{color}" '
                      f'text-anchor="{ancla}" dominant-baseline="central"{estilo}>{html.escape(texto)}</text>')

    def caja(self, x, y, w, h, titulo=None, lineas=(), estilo='azul', centrar=False, tam=10, tam_titulo=10.5,
             pad=4, valign='top', radio=6, discontinua=False, grosor=1.2):
        """Caja redondeada con título y renglones envueltos; falla si el texto no cabe."""
        relleno, borde, c_tit, c_txt = ESTILOS[estilo]
        self.n += 1
        trazo = ' stroke-dasharray="6,4"' if discontinua else ''
        self.o.append(f'<g data-caja="{self.n}"><rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radio}" '
                      f'fill="{relleno}" stroke="{borde}" stroke-width="{grosor}"{trazo}/>')
        util = w - 2 * pad
        filas = []
        if titulo:
            for r in envolver(titulo, util, tam_titulo, 'bold'):
                filas.append((r, 'bold', tam_titulo, c_tit))
        for item in lineas:
            if isinstance(item, tuple):
                txt, opc = item
            else:
                txt, opc = item, {}
            peso, t, color = opc.get('peso', 'normal'), opc.get('tam', tam), opc.get('color', c_txt)
            for r in envolver(txt, util, t, peso):
                filas.append((r, peso, t, color))
        total = sum(interlinea(f[2]) for f in filas)
        if total > h - 2 * pad + 0.6:
            AVISOS.append(f'No cabe el texto en la caja «{titulo or lineas[:1]}»: necesita {total + 2 * pad:.1f} de alto, '
                          f'tiene {h:.1f} ({len(filas)} renglones)')
        yy = y + pad if valign == 'top' else y + (h - total) / 2
        for r, peso, t, color in filas:
            lh = interlinea(t)
            if centrar:
                self.texto(x + w / 2, yy + lh / 2, r, t, peso, color, 'middle')
            else:
                self.texto(x + pad, yy + lh / 2, r, t, peso, color, 'start')
            yy += lh
        self.o.append('</g>')
        return (x, y, w, h)

    def flecha(self, puntos, color=AZUL, discontinua=False, grosor=1.4, punta=True):
        d = ' '.join(f'{"M" if i == 0 else "L"}{px:.1f},{py:.1f}' for i, (px, py) in enumerate(puntos))
        trazo = ' stroke-dasharray="5,4"' if discontinua else ''
        marca = f' marker-end="url(#p{color[1:]})"' if punta else ''
        self.o.append(f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{grosor}"{trazo}{marca}/>')

    def etiqueta(self, x, y, texto, color=AZUL, ancla='start', tam=10, peso='normal', fondo=True):
        """Texto suelto (sobre una flecha), con fondo blanco para que no lo cruce una línea."""
        if fondo:
            w = ancho_texto(texto, tam, peso)
            x0 = x if ancla == 'start' else (x - w / 2 if ancla == 'middle' else x - w)
            self.o.append(f'<rect x="{x0 - 2:.1f}" y="{y - tam * 0.62:.1f}" width="{w + 4:.1f}" '
                          f'height="{tam * 1.24:.1f}" fill="#FFFFFF" opacity="0.92"/>')
        self.texto(x, y, texto, tam, peso, color, ancla)

    def insignia(self, x, y, numero, color=NARANJA):
        r = 8.5 if numero < 10 else 9.5
        self.o.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}" stroke="#FFFFFF" stroke-width="1.2"/>')
        self.texto(x, y + 0.5, str(numero), 10, 'bold', '#FFFFFF', 'middle')

    def svg(self) -> str:
        colores = {AZUL, NARANJA, PETROLEO, GRIS, VERDE}
        marcas = ''.join(
            f'<marker id="p{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
            f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in colores)
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="13.333in" height="7.5in" '
                f'viewBox="0 0 {ANCHO} {ALTO}" font-family="Arial, Helvetica, sans-serif">'
                f'<defs>{marcas}</defs>{"".join(self.o)}</svg>')


# ══ 1. Arquitectura completa ══════════════════════════════════════════════
def arquitectura_completa() -> Lienzo:
    L = Lienzo('VicMar · Arquitectura completa del sistema')
    c, f, e = L.caja, L.flecha, L.etiqueta

    # 1 · Presentación ---------------------------------------------------------------
    c(8, 34, 944, 78, '1 · PRESENTACIÓN — React 18 + TypeScript + Vite + Tailwind (frontend/src), en el navegador',
      estilo='capa', tam_titulo=11)
    yb, hb = 52, 56
    c(14, yb, 170, hb, 'Autoridad académica', ['AUTORIDAD · consulta y decide:', 'Panel, Consulta, Carreras, Modelo,',
                                               'Reportes; ve el seguimiento'])
    c(190, yb, 170, hb, 'Bienestar estudiantil', ['BIENESTAR · atiende las alertas:', 'Ficha y simulador de escenarios;',
                                                  'registra y cierra el seguimiento'])
    c(366, yb, 170, hb, 'Administración de TI', ['ADMIN_TI · todo lo anterior +', 'admin/Usuarios, Auditoria, Estado',
                                                 'y el SQL de cada consulta'])
    c(542, yb, 230, hb, 'paginas/ (14 pantallas)', [
        'Ingresar · Panel · Estudiantes · Ficha · Seguimiento · Consulta · Carreras · Referentes · '
        'CalidadModelo · Reportes · Perfil · admin/*'])
    c(778, yb, 168, hb, 'lib/ · App.tsx', ['api.ts: Bearer JWT + X-Institucion', 'permisos.ts: espejo de roles',
                                           '<Protegida requiere=…>'])

    f([(480, 112), (480, 124)])
    e(488, 118, 'HTTPS · JSON a /api/* (proxy de Vite :3000 → uvicorn :8090) · token en sessionStorage')

    # 2 · API ------------------------------------------------------------------------
    c(8, 124, 944, 164, '2 · API REST FastAPI — backend/main.py · 10 routers bajo /api · cada ruta exige '
      'Depends(requiere(capacidad)) → 403', estilo='capa', tam_titulo=11)
    w, x0 = 182, 14
    rut = [
        ('api/sesion.py', ['POST /auth/ingresar (5 intentos)', 'GET /auth/yo · GET /instituciones'], 'azul'),
        ('api/panel.py · carreras.py', ['GET /panel/resumen', 'GET /carreras/segmentos'], 'azul'),
        ('api/estudiantes.py', ['GET /estudiantes · …/{token}', 'POST …/{token}/simulacion'], 'azul'),
        ('api/referentes.py · modelo.py', ['GET /referentes', 'GET /modelo/calidad'], 'azul'),
        ('api/seguimiento.py', ['GET · POST /seguimiento', 'POST …/{id}/cerrar'], 'azul'),
        ('api/consulta.py', ['POST /consulta · …/sugerencias', 'POST …/{id}/interpretar · /excel'], 'naranja'),
        ('api/reportes.py', ['GET /reportes/ejecutivo.xlsx', 'GET /reportes/ejecutivo.pdf'], 'azul'),
        ('api/admin.py', ['/admin/usuarios (CRUD)', '/admin/auditoria · /admin/estado'], 'azul'),
        ('api/sesion.py · main.py', ['PUT /auth/clave', 'GET /api/salud'], 'azul'),
        ('ml/servicio.py', ['modelo .joblib por institución', 'predecir() · simulador'], 'blanco'),
    ]
    for i, (t, ls, est) in enumerate(rut):
        c(x0 + (i % 5) * (w + 6), 143 if i < 5 else 191, w, 44, t, ls, estilo=est)
    nucleo = [
        ('core/seguridad.py', ['JWT HS256 con vencimiento · bcrypt', '3 roles · 15 capacidades']),
        ('core/privacidad.py', ['cédula ******1234 · token Fernet', 'depurar_texto() · seudonimizar()']),
        ('core/auditoria.py', ['auditoria.jsonl de solo agregado', 'huella SHA-256, nunca los datos']),
        ('core/db.py', ['Encrypt=yes · falla cerrada', 'SESSION_CONTEXT @read_only=1']),
        ('main.py · core/config.py', ['CORS en lista blanca · nosniff', 'DENY · no-store · lee el .env']),
    ]
    for i, (t, ls) in enumerate(nucleo):
        c(x0 + i * (w + 6), 239, w, 44, t, ls, estilo='oscuro')

    f([(100, 288), (100, 300)], NARANJA)
    e(108, 294, 'POST /consulta → motor.responder()', NARANJA_TEXTO)

    # 3 · Motor de consulta -------------------------------------------------------------
    c(8, 300, 706, 104, '3 · MOTOR DE CONSULTA (backend/nl2sql)', estilo='capa', tam_titulo=11)
    ym = 320
    c(14, ym, 128, 78, 'Barreras', ['guardarrailes', '.clasificar(): escritura,', 'inyección, otra institu-',
                                    'ción, tablas físicas'], estilo='blanco')
    c(154, ym, 108, 78, 'Enrutador', ['enrutador.elegir()', 'TF-IDF de n-gramas', 'de caracteres',
                                      'umbral 0,56'], estilo='blanco')
    c(276, ym, 140, 36, 'generador.generar()', ['depurar_texto(): CEDULA_1'], estilo='naranja')
    c(424, ym, 152, 36, 'validador.validar()', ['sqlglot: solo VIS_* · TOP 500'], estilo='naranja')
    c(276, 362, 300, 36, 'Métricas certificadas · catalogo_metricas.json',
      ['40 métricas: SQL fijo con parámetros enlazados'], estilo='verde')
    c(588, ym, 120, 78, 'Respuesta', ['db.leer() con', 'chat_reader · cédula', 'enmascarada · resumen',
                                      'y gráfico (redactor)'], estilo='blanco')
    f([(142, 359), (154, 359)])
    f([(262, 338), (276, 338)], NARANJA)
    e(264, 352, 'no', NARANJA_TEXTO)
    f([(262, 380), (276, 380)], VERDE)
    e(265, 368, 'sí', VERDE)
    f([(416, 338), (424, 338)], NARANJA)
    f([(576, 338), (588, 338)])
    f([(576, 380), (588, 380)])
    # generador → adaptador → proveedores
    f([(400, ym), (400, 313), (720, 313)], NARANJA, discontinua=True)
    f([(838, 352), (838, 358)], NARANJA)

    # Columna derecha: adaptador, proveedores de IA y Docker -------------------------------------
    c(724, 300, 228, 52, 'Adaptador (punto de intercambio)', [
        'nl2sql/proveedores.completar()', 'core/config.py → proveedores_ia'], estilo='naranja')
    c(724, 358, 228, 108, 'Proveedores de IA externos', [
        'Gemini → Groq → NVIDIA NIM → DeepSeek', '(API compatible con OpenAI; cascada)',
        'Reciben solo: pregunta depurada,', 'esquema de vistas, glosario y ejemplos',
        'Al interpretar: ≤ 25 filas seudonimi-', 'zadas y sin texto libre'], estilo='externo', discontinua=True)
    c(724, 472, 228, 64, 'Docker Desktop', ['vicmar-sqlserver (mssql/server:2022, :1433)',
                                            'Metabase (despliegue/metabase, :3001)', 'lee bi.* con metabase_lector'],
      estilo='blanco', discontinua=True)

    # 5 · Procesos por lotes ---------------------------------------------------------------
    c(8, 414, 224, 122, '5 · PROCESOS POR LOTES', [
        ('scripts/pipeline.py (cuenta DB_USER):', {'peso': 'bold'}),
        'etl → ml.entrenar (4 modelos, Optuna,', 'Platt, umbrales) → MLflow →', 'ml.calificar (SHAP, PSI) →',
        'ml.segmentar (K-means) → reportes →', 'mlops.validar (GX, Evidently)'],
      estilo='capa', tam_titulo=11)
    # 4 · Datos ---------------------------------------------------------------------------
    c(238, 414, 476, 122, '4 · DATOS — SQL Server 2022 (en Docker)', estilo='capa', tam_titulo=11)
    yd, hd = 432, 88
    c(244, yd, 96, hd, 'Operativas', ['UNEMI_PRUEBAS', '(sintética)', 'OULAD_PRUEBAS', '(anonimizada)'])
    c(346, yd, 106, hd, 'ETL por perfil', ['etl_academico.py', 'perfiles.py', 'validar_filas()',
                                           'Great Expectations', '(mlops.validar)'])
    c(458, yd, 132, hd, 'ALMACEN_ACADEMICO', ['esquema estrella:', '9 dimensiones y', '6 tablas de hechos',
                                              '(matrícula, predicción,', 'segmentos, seguimiento)'],
      estilo='oscuro', tam_titulo=10)
    c(596, yd, 112, hd, '8 vistas VIS_*', ['filtran por', 'SESSION_CONTEXT', 'chat_reader: SELECT',
                                          'app_seguimiento:', 'EXECUTE 2 sp_*'], estilo='naranja')
    f([(340, 476), (346, 476)])
    f([(452, 476), (458, 476)])
    f([(590, 476), (596, 476)])
    f([(648, 398), (648, 432)])
    e(642, 409, 'SESSION_CONTEXT', AZUL, 'end')
    f([(232, 529), (524, 529), (524, 520)], PETROLEO)
    return L


# ══ 2. Flujo de una pregunta ══════════════════════════════════════════════
def flujo_pregunta() -> Lienzo:
    L = Lienzo('VicMar · Flujo de una pregunta en lenguaje natural (controles de seguridad numerados)')
    c, f, e = L.caja, L.flecha, L.etiqueta
    derecha = {184: 344, 202: 344, 400: 620, 364: 500, 510: 650, 666: 794, 810: 946, 830: 946}
    def b(x, y, n):
        extra = 20 if x in (202, 830) else 0
        L.insignia(derecha[x] - 12 - (20 if x in (184, 810) and n in (1, 3, 10) else 0) + 0 * extra, y, n)
    carriles = [('Navegador (React)', 8, 168), ('API FastAPI', 172, 352), ('Motor nl2sql', 356, 656),
                ('Proveedor de IA (externo)', 660, 800), ('SQL Server · ALMACEN', 804, 952)]
    for nom, x0, x1 in carriles:
        L.o.append(f'<rect x="{x0}" y="34" width="{x1 - x0}" height="502" fill="{GRIS_CLARO}" stroke="#9FB3C4"/>')
        L.o.append(f'<rect x="{x0}" y="34" width="{x1 - x0}" height="20" fill="{PETROLEO}"/>')
        L.texto((x0 + x1) / 2, 44, nom, 10.5, 'bold', '#FFFFFF', 'middle')
    # filas
    c(16, 62, 144, 56, 'Consulta.tsx', ['lib/api.ts: POST', '/api/consulta + Bearer', 'JWT + X-Institucion'])
    c(184, 62, 160, 68, 'sesion_actual()', ['JWT firmado y vigente;', 'cuenta activa · institu-',
                                            'ción asignada (403)'])
    b(184, 62, 1)
    b(202, 62, 2)
    c(184, 138, 160, 44, "requiere('consultar')", ['pregunta ≤ 500 · historial ≤ 10'])
    b(184, 138, 3)
    b(202, 138, 4)
    c(400, 62, 220, 44, 'guardarrailes.clasificar()', ['escritura, inyección, otra institución, tablas'])
    b(400, 62, 5)
    c(16, 140, 144, 44, 'Bloqueada: barrera', ['mensaje sin SQL ni IA'], estilo='blanco')
    c(400, 114, 220, 32, 'enrutador.elegir(): ¿TF-IDF ≥ 0,56?', estilo='blanco', tam_titulo=10)
    c(364, 160, 136, 56, 'Métrica certificada', ['SQL fijo con parámetros', 'enlazados (40)'], estilo='verde')
    b(364, 160, 6)
    c(510, 160, 140, 56, 'depurar_texto()', ['cédulas, correos, nombres', '→ CEDULA_1, NOMBRE_1'], estilo='naranja')
    b(510, 160, 7)
    c(666, 160, 128, 92, 'proveedores', ['.completar(): Gemini', '→ Groq → NVIDIA NIM', '→ DeepSeek. Recibe solo',
                                         'pregunta depurada,', 'esquema y ejemplos'], estilo='externo')
    b(666, 160, 8)
    c(510, 230, 140, 68, 'validador.validar()', ['sqlglot: un SELECT, solo', 'VIS_*, sin xp_/OPEN…,', 'TOP 500; 1 corrección'],
      estilo='naranja')
    b(510, 230, 9)
    c(810, 300, 136, 92, 'db.leer()', ['chat_reader · Encrypt=yes', 'sp_set_session_context', '@read_only=1 ·',
                                       'VIS_* filtran por', 'institución · 30 s'], estilo='oscuro')
    b(810, 300, 10)
    b(830, 300, 11)
    c(400, 330, 220, 44, 'enmascarar_para_pantalla()', ['cédula ******1234 · SQL solo con ver_sql'], estilo='naranja')
    b(400, 330, 12)
    c(184, 390, 160, 56, 'auditoria.registrar()', ["'CONSULTA': origen, huella", 'SHA-256 del SQL, sin datos'],
      estilo='oscuro')
    b(184, 390, 13)
    c(16, 400, 144, 44, 'Resultado.tsx', ['tabla o gráfico'])
    c(16, 470, 144, 56, 'Interpretar (opcional)', ['POST …/{id}/interpretar'], estilo='blanco')
    c(400, 466, 250, 64, 'redactor.interpretar()', ['filas_para_ia(): ≤ 25 filas seudonimizadas,',
                                                    'sin texto libre; se descarta si cita cifras',
                                                    'que no están (cifras_no_respaldadas)'], estilo='naranja')
    b(400, 466, 14)
    f([(160, 90), (184, 90)])
    f([(264, 130), (264, 138)])
    f([(344, 160), (372, 160), (372, 84), (400, 84)])
    f([(510, 106), (510, 114)])
    f([(400, 96), (380, 96), (380, 120), (88, 120), (88, 140)], GRIS, discontinua=True)
    f([(470, 146), (432, 160)], VERDE)
    e(440, 152, 'sí', VERDE, 'end')
    f([(550, 146), (580, 160)], NARANJA)
    e(570, 151, 'no', NARANJA_TEXTO)
    f([(650, 188), (666, 188)], NARANJA)
    f([(666, 240), (650, 248)], NARANJA)
    f([(432, 216), (432, 312), (810, 312)], VERDE)
    f([(580, 298), (580, 322), (810, 322)], NARANJA)
    f([(810, 352), (620, 352)])
    f([(400, 352), (264, 352), (264, 390)])
    f([(184, 422), (160, 422)])
    f([(88, 444), (88, 470)])
    f([(160, 498), (400, 498)], NARANJA)
    f([(650, 498), (730, 498), (730, 252)], NARANJA, discontinua=True)
    e(736, 480, 'IA redacta', NARANJA_TEXTO)
    return L


# ══ 3. Flujo de entrenamiento ═════════════════════════════════════════════
def flujo_entrenamiento() -> Lienzo:
    L = Lienzo('VicMar · Del almacén al modelo: entrenamiento, validación y calificación (backend/ml)')
    c, f = L.caja, L.flecha
    W, H = 214, 92
    xs = [16, 252, 488, 724]
    fila1 = [
        ('1 · Lectura', ['ml/datos.leer_historial()', 'ALMACEN_ACADEMICO, cuenta', 'DB_USER, filtrado por', 'institución'], 'oscuro'),
        ('2 · Panel estudiante-periodo', ['caracteristicas.construir_panel()', 'variables hasta t; etiqueta =',
                                          'abandono en t+1 (sin fuga)', 'grupos opcionales detectados'], 'azul'),
        ('3 · Partición temporal', ['particion_temporal(): periodos', 'más recientes (≥ 25 %) =',
                                    'prueba, usada una sola vez'], 'azul'),
        ('4 · CV agrupada', ['StratifiedGroupKFold, 5 pliegues', 'por estudiante: nunca en', 'ambos lados'], 'azul'),
    ]
    fila2 = [
        ('5 · 4 candidatos', ['RF con pesos · RF + SMOTE', '(solo en el pliegue) · Logística', '· LightGBM (Optuna TPE);',
                              'RF con búsqueda aleatoria'], 'naranja'),
        ('6 · Selección', ['mayor ROC-AUC medio', '(desempate PR-AUC)'], 'azul'),
        ('7 · Calibración de Platt', ['calibracion.CalibradorPlatt', 'sobre predicciones fuera', 'de pliegue'], 'azul'),
        ('8 · Umbrales', ['MEDIO: recall ≥ 0,80', 'ALTO: recall ≥ 0,50', '(umbral_para_recall)'], 'azul'),
    ]
    fila3 = [
        ('9 · Evaluación', ['temporal: ROC-AUC, PR-AUC, Brier', 'prospectiva OULAD 2014J', '(reporte_validacion) · por',
                            'periodo y carrera · origen móvil', '· equidad por género y modalidad'], 'verde'),
        ('10 · Guardar', ['ml/modelos/<INST>/', 'modelo_abandono.joblib,', 'metricas.json ·',
                          'fact_evaluacion_modelo'], 'azul'),
        ('11 · MLflow', ['mlops/registro_mlflow.py', 'una corrida por entrenamiento;', 'datos_locales/mlflow (local)'], 'naranja'),
        ('12 · Calificar y segmentar', ['ml.calificar: probabilidad,', 'ALTO/MEDIO/BAJO, SHAP top 3,',
                                        'PSI · mlops: GX y Evidently ·', 'ml.segmentar: K-means'], 'oscuro'),
    ]
    for fy, fila in ((60, fila1), (220, fila2), (380, fila3)):
        for i, (t, ls, est) in enumerate(fila):
            c(xs[i], fy, W, H if fy != 380 else 108, t, ls, estilo=est)
            if i < 3:
                f([(xs[i] + W, fy + 46), (xs[i + 1], fy + 46)])
    f([(831, 152), (831, 186), (123, 186), (123, 220)])
    f([(831, 312), (831, 346), (123, 346), (123, 380)])
    c(16, 500, 928, 32, None, ['Resultado: fact_prediccion_abandono y fact_segmento_carrera → vistas VIS_* → '
                                'panel, ficha, consulta y reportes (un modelo por institución)'],
      estilo='blanco', centrar=True, valign='center')
    return L


# ══ 4. Capas de seguridad ═════════════════════════════════════════════════
def capas_seguridad() -> Lienzo:
    L = Lienzo('VicMar · Defensa en profundidad: capas de seguridad')
    c, f = L.caja, L.flecha
    capas = [
        ('1 · Interfaz', 'frontend/src', ['Rutas <Protegida requiere=capacidad> (App.tsx, lib/permisos.ts); token en '
                                          'sessionStorage; un 401 cierra la sesión; la ficha se abre por token, no por cédula']),
        ('2 · API, JWT y roles', 'core/seguridad.py · api/*', ['JWT HS256 con vencimiento, bcrypt, cuenta revalidada en '
                                                               'cada petición, X-Institucion asignada (403), '
                                                               'requiere(capacidad): 3 roles y 15 capacidades, 5 intentos '
                                                               '→ 429, CORS y cabeceras nosniff/DENY/no-store']),
        ('3 · Motor de consulta', 'backend/nl2sql', ['Barreras de intención; 40 métricas certificadas con SQL fijo; '
                                                     'depurar_texto() antes de la IA; validador sqlglot (un SELECT, '
                                                     'solo VIS_*, sin funciones peligrosas, TOP 500)']),
        ('4 · Base de datos', 'crear_almacen_academico.sql · core/db.py',
         ['Vistas VIS_* filtradas por SESSION_CONTEXT (@read_only=1, falla cerrada); chat_reader solo SELECT en 8 '
          'vistas; app_seguimiento solo 2 procedimientos; DB_USER solo lotes; Encrypt=yes; CHECK_POLICY=ON']),
    ]
    y = 44
    for i, (t, arch, ls) in enumerate(capas):
        x = 16 + i * 22
        c(x, y, 640 - 2 * i * 22, 104, t, [(arch, {'peso': 'bold', 'color': '#FFB27A' if i == 3 else AZUL,
                                                    'tam': 12})] + [(texto, {'tam': 12}) for texto in ls],
          estilo=['azul', 'blanco', 'naranja', 'oscuro'][i], tam_titulo=13)
        y += 118
    f([(8, 50), (8, 520)], PETROLEO)
    c(680, 44, 264, 222, 'Auditoría (transversal)', [('core/auditoria.py', {'peso': 'bold', 'color': AZUL}),
        'auditoria.jsonl de solo agregado', 'INGRESO, CONSULTA, INTERPRETACION, FICHA, SIMULACION, '
        'SEGUIMIENTO_ALTA/CIERRE, EXPORTACION, CUENTA_*, CAMBIO_CLAVE', 'Huella SHA-256 del SQL o del mensaje, nunca '
        'los datos', 'Se revisa en admin/Auditoria (ADMIN_TI)'], estilo='blanco', tam_titulo=11.5)
    c(680, 280, 264, 252, 'LOPDP (transversal)', [('core/privacidad.py', {'peso': 'bold', 'color': AZUL}),
        'Minimización: a la IA solo la pregunta depurada; al interpretar ≤ 25 filas seudonimizadas sin texto libre',
        'Acceso: cédula ******1234 en pantalla', 'Seguridad: token Fernet (AES-128-CBC + HMAC-SHA256), vigencia 24 h',
        'Datos de prueba sintéticos o anonimizados'], estilo='naranja', tam_titulo=11.5)
    return L


# ══ Conversión y verificación ═════════════════════════════════════════════
_VERIFICAR = r"""
() => {
  const svg = document.querySelector('svg');
  const textos = [...svg.querySelectorAll('text')];
  const cajas = (t) => t.getBBox();
  const problemas = [];
  const bb = textos.map(t => ({t: t.textContent, b: t.getBBox(), tam: parseFloat(t.getAttribute('font-size'))}));
  for (const x of bb) {
    if (x.tam < 10) problemas.push('Texto menor a 10 pt: ' + x.t);
    if (x.b.x < 0 || x.b.y < 0 || x.b.x + x.b.width > 960.5 || x.b.y + x.b.height > 540.5)
      problemas.push('Fuera del lienzo: ' + x.t);
  }
  for (let i = 0; i < bb.length; i++) for (let j = i + 1; j < bb.length; j++) {
    const a = bb[i].b, b = bb[j].b;
    const ix = Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x);
    const iy = Math.min(a.y + a.height, b.y + b.height) - Math.max(a.y, b.y);
    if (ix > 0.5 && iy > 2.5) problemas.push('Encimados: «' + bb[i].t + '» y «' + bb[j].t + '»');
  }
  for (const g of svg.querySelectorAll('g[data-caja]')) {
    const r = g.querySelector('rect').getBBox();
    for (const t of g.querySelectorAll('text')) {
      const b = t.getBBox();
      if (b.x < r.x - 0.5 || b.x + b.width > r.x + r.width + 0.5 || b.y < r.y - 0.5 || b.y + b.height > r.y + r.height + 0.5)
        problemas.push('Se sale de su caja: ' + t.textContent);
    }
  }
  return problemas;
}
"""


def exportar(nombre: str, lienzo: Lienzo, navegador) -> list[str]:
    svg = lienzo.svg()
    (CARPETA / f'{nombre}.svg').write_text('<?xml version="1.0" encoding="UTF-8"?>\n' + svg, encoding='utf-8')
    pagina = navegador.new_page(viewport={'width': ANCHO, 'height': ALTO}, device_scale_factor=ESCALA)
    doc = ('<!doctype html><html><head><meta charset="utf-8"><style>*{margin:0;padding:0}'
           f'svg{{display:block;width:{ANCHO}px;height:{ALTO}px}}</style></head><body>{svg}</body></html>')
    pagina.set_content(doc)
    problemas = pagina.evaluate(_VERIFICAR)
    png = pagina.screenshot(clip={'x': 0, 'y': 0, 'width': ANCHO, 'height': ALTO})
    pagina.close()
    img = Image.open(io.BytesIO(png)).convert('RGB')
    if img.size != (4000, 2250):
        img = img.resize((4000, 2250), Image.LANCZOS)
    img.save(CARPETA / f'{nombre}.png', dpi=(PPP, PPP), optimize=True)
    return problemas


DIAGRAMAS = {
    'arquitectura_completa': arquitectura_completa,
    'flujo_pregunta': flujo_pregunta,
    'flujo_entrenamiento': flujo_entrenamiento,
    'capas_seguridad': capas_seguridad,
}


def main(argv: list[str]) -> int:
    from playwright.sync_api import sync_playwright
    elegidos = argv or list(DIAGRAMAS)
    hay_problemas = False
    with sync_playwright() as p:
        try:
            navegador = p.chromium.launch(channel='msedge')
        except Exception:  # noqa: BLE001 - sin Edge se usa el Chromium de Playwright
            navegador = p.chromium.launch()
        for nombre in elegidos:
            AVISOS.clear()
            lienzo = DIAGRAMAS[nombre]()
            problemas = list(AVISOS) + exportar(nombre, lienzo, navegador)
            print(f'{nombre}: {"sin problemas" if not problemas else str(len(problemas)) + " problemas"}')
            for pr in problemas:
                print('   ', pr)
            hay_problemas |= bool(problemas)
        navegador.close()
    return 1 if hay_problemas else 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main(sys.argv[1:]))

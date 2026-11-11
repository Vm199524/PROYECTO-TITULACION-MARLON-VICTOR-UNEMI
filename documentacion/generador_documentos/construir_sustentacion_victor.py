"""Sustentación individual de Víctor Manuel Lluilema Pisco: carátula + 5 diapositivas.

Sigue los puntos que fijó la docente para el tribunal (introducción, objetivo, diagramas de la propuesta
práctica, arquitectura frontend/backend, hipervínculo del proyecto y conclusiones) con la base visual de la
presentación del equipo (BaseSustentacion.pptx), pero con diagramas dibujados en la propia lámina, un código QR
al repositorio y la gráfica de resultados por periodo.
"""
import copy
import sys
from pathlib import Path

import segno
from lxml import etree
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Emu, Pt

RAIZ = Path(__file__).resolve().parents[2]
PRES = RAIZ / 'documentacion' / 'presentacion'
BASE = PRES / 'plantilla' / 'BaseSustentacion.pptx'
SALIDA = PRES / 'Sustentacion_LluilemaPisco_Victor.pptx'
CAPT = RAIZ / 'documentacion' / 'capturas'
FIG = RAIZ / 'documentacion' / 'figuras'
REPO = 'https://github.com/Vm199524/PROYECTO-TITULACION-MARLON-VICTOR-UNEMI'

NAVY, NAR, HIELO, HIELO2, NAR_L, GRIS, TXT, SEC = '1E2A36', 'EC8532', 'EAF1F8', 'DCE7F2', 'FCE9D6', 'F3F6F9', '1E2A36', '5A6B7B'
BLANCO = 'FFFFFF'
cm = lambda v: int(round(v * 360000))
rgb = lambda h: RGBColor.from_string(h)

# ---------------------------------------------------------------- utilidades de dibujo
def limpiar(slide, conservar=('Imagen 4', 'TextBox 5')):
    for sh in list(slide.shapes):
        if sh.name not in conservar:
            sh._element.getparent().remove(sh._element)


def titulo(slide, texto):
    sh = [s for s in slide.shapes if s.name == 'TextBox 5'][0]
    sh.text_frame.paragraphs[0].runs[0].text = texto


def _sin_efectos(sh):
    spPr = sh._element.spPr
    for e in spPr.findall(qn('a:effectLst')):
        spPr.remove(e)
    etree.SubElement(spPr, qn('a:effectLst'))


def caja(slide, x, y, w, h, relleno=HIELO, forma=MSO_SHAPE.ROUNDED_RECTANGLE, radio=6000, linea=None):
    sh = slide.shapes.add_shape(forma, cm(x), cm(y), cm(w), cm(h))
    if forma == MSO_SHAPE.ROUNDED_RECTANGLE:
        sh.adjustments[0] = radio / 100000
    if relleno is None:
        sh.fill.background()
    else:
        sh.fill.solid(); sh.fill.fore_color.rgb = rgb(relleno)
    if linea:
        sh.line.color.rgb = rgb(linea); sh.line.width = Pt(1)
    else:
        sh.line.fill.background()
    _sin_efectos(sh)
    sh.text_frame.text = ''
    return sh


def _fmt(par, d, base):
    par.alignment = {'l': PP_ALIGN.LEFT, 'c': PP_ALIGN.CENTER, 'r': PP_ALIGN.RIGHT}[d.get('al', base.get('al', 'l'))]
    par.space_after = Pt(d.get('sa', base.get('sa', 3)))
    par.line_spacing = d.get('ls', base.get('ls', 1.05))
    pPr = par._p.get_or_add_pPr()
    if d.get('vineta'):
        pPr.set('marL', str(cm(0.5))); pPr.set('indent', str(-cm(0.5)))
        bc = etree.SubElement(pPr, qn('a:buClr')); etree.SubElement(bc, qn('a:srgbClr')).set('val', NAR)
        etree.SubElement(pPr, qn('a:buFont')).set('typeface', 'Arial')
        etree.SubElement(pPr, qn('a:buChar')).set('char', '•')
    else:
        etree.SubElement(pPr, qn('a:buNone'))


def escribir(sh, parrafos, tam=14, color=TXT, negrita=False, al='l', anclaje='t', margen=0.25, sa=3):
    """parrafos: lista de str o dict(t, sz, b, c, al, sa, vineta, i, link)."""
    tf = sh.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = {'t': MSO_ANCHOR.TOP, 'm': MSO_ANCHOR.MIDDLE, 'b': MSO_ANCHOR.BOTTOM}[anclaje]
    tf.margin_left = tf.margin_right = cm(margen); tf.margin_top = tf.margin_bottom = cm(margen * 0.8)
    base = {'al': al, 'sa': sa}
    primero = True
    for p in parrafos:
        d = {'t': p} if isinstance(p, str) else p
        par = tf.paragraphs[0] if primero else tf.add_paragraph()
        primero = False
        _fmt(par, d, base)
        runs = d['t'] if isinstance(d['t'], list) else [d['t']]
        for r in runs:
            rd = {'t': r} if isinstance(r, str) else r
            run = par.add_run(); run.text = rd['t']
            f = run.font; f.name = 'Arial'; f.size = Pt(rd.get('sz', d.get('sz', tam)))
            f.bold = rd.get('b', d.get('b', negrita)); f.italic = rd.get('i', d.get('i', False))
            f.color.rgb = rgb(rd.get('c', d.get('c', color)))
            if rd.get('link') or d.get('link'):
                run.hyperlink.address = rd.get('link') or d.get('link')
    return sh


def texto(slide, x, y, w, h, parrafos, **kw):
    sh = slide.shapes.add_textbox(cm(x), cm(y), cm(w), cm(h))
    return escribir(sh, parrafos, **kw)


def tarjeta(slide, x, y, w, h, parrafos, relleno=HIELO, **kw):
    sh = caja(slide, x, y, w, h, relleno)
    return escribir(sh, parrafos, **kw)


def flecha(slide, x1, y1, x2, y2, color=NAVY, ancho=1.5, punteada=False, punta=True):
    c = slide.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, cm(x1), cm(y1), cm(x2), cm(y2))
    c.line.color.rgb = rgb(color); c.line.width = Pt(ancho)
    ln = c.line._get_or_add_ln()
    if punteada:
        etree.SubElement(ln, qn('a:prstDash')).set('val', 'dash')
    if punta:
        etree.SubElement(ln, qn('a:tailEnd')).set('type', 'triangle')
    return c


def imagen(slide, ruta, x, y, w=None, h=None):
    kw = {}
    if w: kw['width'] = cm(w)
    if h: kw['height'] = cm(h)
    return slide.shapes.add_picture(str(ruta), cm(x), cm(y), **kw)


def notas(slide, texto_):
    slide.notes_slide.notes_text_frame.text = texto_


# ---------------------------------------------------------------- diapositivas
X0, ANCHO = 2.115, 29.64          # márgenes de la plantilla
Y0, Y1 = 3.1, 16.9


def portada(s):
    for sh in s.shapes:
        if sh.has_text_frame and 'EXPONE' in sh.text_frame.text:
            for par in sh.text_frame.paragraphs:
                rs = par.runs
                for i, r in enumerate(rs):
                    if r.text.startswith('MARLON DAVID PÉREZ ALMACHI') and i > 0 and rs[i - 1].text.startswith('EXPONE'):
                        r.text = 'VÍCTOR MANUEL LLUILEMA PISCO'
    notas(s, 'Buenos días, miembros del tribunal. Soy Víctor Manuel Lluilema Pisco y, junto con Marlon Pérez Almachi, '
             'presento el prototipo de un sistema web para predecir el abandono universitario con aprendizaje automático '
             'y consulta conversacional. Mi exposición cubre cinco puntos: introducción y objetivo, diagramas de la '
             'propuesta, arquitectura, el enlace del proyecto y conclusiones.')


def s_introduccion(s):
    limpiar(s); titulo(s, 'Introducción y objetivo')
    # fila superior: de dónde partimos → qué proponemos
    tarjeta(s, X0, Y0, 9.3, 6.4, [
        {'t': 'Punto de partida', 'sz': 14, 'b': True, 'c': NAR, 'sa': 6},
        {'t': '44,90 %', 'sz': 30, 'b': True, 'c': NAR, 'sa': 2},
        {'t': 'abandono en cinco cohortes de una universidad ecuatoriana (Núñez-Naranjo, 2024)', 'sz': 12.5, 'sa': 8},
        {'t': 'Hoy el abandono se mide cuando ya ocurrió.', 'sz': 12.5, 'b': True}], margen=0.4)
    tarjeta(s, X0 + 9.6, Y0, 10.2, 6.4, [
        {'t': 'El problema', 'sz': 14, 'b': True, 'c': NAR, 'sa': 6},
        {'t': 'Señales dispersas en varios sistemas', 'vineta': True, 'sz': 13.5, 'sa': 6},
        {'t': 'La autoridad depende de TI para consultar los datos', 'vineta': True, 'sz': 13.5, 'sa': 6},
        {'t': 'Datos personales que exigen protección (LOPDP)', 'vineta': True, 'sz': 13.5}], margen=0.4)
    tarjeta(s, X0 + 20.1, Y0, 9.54, 6.4, [
        {'t': 'Objetivo general', 'sz': 14, 'b': True, 'c': NAR, 'sa': 6},
        {'t': 'Desarrollar un prototipo web que prediga el abandono con aprendizaje automático y permita '
              'consultar los resultados en español, para actuar antes de que el estudiante se retire.',
         'sz': 13.5, 'c': BLANCO}], relleno=NAVY, margen=0.4)
    # pregunta de investigación
    tarjeta(s, X0, Y0 + 6.8, ANCHO, 3.3, [
        {'t': 'Pregunta de investigación', 'sz': 13, 'b': True, 'c': NAR, 'sa': 3},
        {'t': '¿Cómo puede un sistema web con aprendizaje automático y consulta en lenguaje natural anticipar el '
              'abandono universitario y apoyar la priorización del acompañamiento, protegiendo los datos del estudiante?',
         'sz': 15, 'b': True}], relleno=NAR_L, margen=0.45, anclaje='m')
    # objetivos específicos
    objs = [('1', 'Analizar', 'procesos y variables'), ('2', 'Construir y validar', 'el modelo predictivo'),
            ('3', 'Implementar', 'el sistema web y la consulta'), ('4', 'Evaluar', 'el prototipo')]
    w = (ANCHO - 3 * 0.4) / 4
    for i, (n, v, r) in enumerate(objs):
        x = X0 + i * (w + 0.4)
        caja(s, x, Y0 + 10.5, w, 3.3, NAVY if i % 2 == 0 else HIELO2)
        c = caja(s, x + 0.35, Y0 + 11.0, 1.3, 1.3, NAR, MSO_SHAPE.OVAL)
        escribir(c, [{'t': n, 'sz': 16, 'b': True, 'c': BLANCO}], al='c', anclaje='m', margen=0)
        texto(s, x + 1.8, Y0 + 10.7, w - 2.0, 2.9, [
            {'t': v, 'sz': 14, 'b': True, 'c': BLANCO if i % 2 == 0 else NAVY, 'sa': 1},
            {'t': r, 'sz': 12.5, 'c': 'DCE7F2' if i % 2 == 0 else TXT}], anclaje='m')
    notas(s, 'Parto de un dato: en una universidad ecuatoriana abandonó el 44,90 % de cinco cohortes. Las señales están '
             'en los sistemas, pero dispersas, y hoy el abandono se mide cuando ya ocurrió; además la autoridad depende '
             'de TI para consultar. Nuestra pregunta es cómo anticiparlo con un sistema web protegiendo los datos. '
             'El objetivo general es un prototipo que prediga y permita consultar en español; lo cumplimos con cuatro '
             'objetivos: analizar, construir y validar el modelo, implementar el sistema y evaluarlo.')


def _hilera(s, x, y, w, h, titulo_, color=NAVY):
    c = caja(s, x, y, w, h, color)
    escribir(c, [{'t': titulo_, 'sz': 11.5, 'b': True, 'c': BLANCO}], al='c', anclaje='m', margen=0.1)
    return c


def s_diagramas(s):
    limpiar(s); titulo(s, 'Diagramas de la propuesta práctica')
    W = 14.6
    # ---------- panel izquierdo: modelo de datos en estrella
    caja(s, X0, Y0, W, 13.8, HIELO)
    texto(s, X0 + 0.2, Y0 + 0.15, W - 0.4, 0.9, [{'t': 'Modelo de datos en estrella (SQL Server)', 'sz': 14, 'b': True, 'c': NAR}])
    fx, fy, fw, fh = X0 + 4.75, Y0 + 4.0, 5.1, 4.3
    dims_izq = ['dim_institucion', 'dim_alumno', 'dim_carrera']
    dims_der = ['dim_periodo', 'dim_sede', 'dim_estado']
    dw, dh = 3.9, 1.35
    ys = [Y0 + 1.6, Y0 + 4.5, Y0 + 7.4]
    for yy, d in zip(ys, dims_izq):
        flecha(s, X0 + 0.35 + dw, yy + dh / 2, fx, fy + fh / 2 + (yy + dh / 2 - (fy + fh / 2)) * 0.25, color=SEC, ancho=1.25, punta=False)
        _hilera(s, X0 + 0.35, yy, dw, dh, d)
    for yy, d in zip(ys, dims_der):
        flecha(s, fx + fw, fy + fh / 2 + (yy + dh / 2 - (fy + fh / 2)) * 0.25, X0 + W - 0.35 - dw, yy + dh / 2, color=SEC, ancho=1.25, punta=False)
        _hilera(s, X0 + W - 0.35 - dw, yy, dw, dh, d)
    f = caja(s, fx, fy, fw, fh, NAR)
    escribir(f, [{'t': 'fact_matriculas', 'sz': 13, 'b': True, 'c': BLANCO, 'sa': 4},
                 {'t': 'estudiante por periodo: promedio, asistencia, nivel, créditos, estado y retiro del siguiente corte', 'sz': 11, 'c': BLANCO}],
             al='c', anclaje='m', margen=0.25)
    texto(s, X0 + 0.3, Y0 + 9.1, W - 0.6, 0.8, [{'t': 'Hechos de procesos por lotes y de seguimiento', 'sz': 12.5, 'b': True, 'c': NAVY}])
    hechos = ['prediccion_abandono', 'segmento_carrera', 'intervencion', 'evaluacion_modelo']
    hw = (W - 0.6 - 3 * 0.25) / 4
    for i, hch in enumerate(hechos):
        c = caja(s, X0 + 0.3 + i * (hw + 0.25), Y0 + 10.0, hw, 1.7, NAR_L)
        escribir(c, [{'t': hch.replace('_', '_​'), 'sz': 10.5, 'b': True}], al='c', anclaje='m', margen=0.1)
    texto(s, X0 + 0.3, Y0 + 12.0, W - 0.6, 1.6, [
        {'t': 'Toda tabla lleva institucion_codigo; las vistas VIS_* filtran por institución con SESSION_CONTEXT.', 'sz': 11.5, 'i': True}])
    # ---------- panel derecho: secuencia de la consulta en lenguaje natural
    X = X0 + W + 0.44
    caja(s, X, Y0, W, 13.8, HIELO)
    texto(s, X + 0.2, Y0 + 0.15, W - 0.4, 0.9, [{'t': 'Secuencia: consulta en lenguaje natural', 'sz': 14, 'b': True, 'c': NAR}])
    nombres = ['Autoridad', 'Interfaz web', 'API FastAPI', 'Barreras y enrutador', 'SQL Server']
    paso = (W - 1.0) / 5
    cx = [X + 0.5 + paso * (i + 0.5) for i in range(5)]
    for i, n in enumerate(nombres):
        c = caja(s, cx[i] - paso / 2 + 0.1, Y0 + 1.2, paso - 0.2, 1.3, NAVY if i != 4 else NAR)
        escribir(c, [{'t': n, 'sz': 10.5, 'b': True, 'c': BLANCO}], al='c', anclaje='m', margen=0.05)
        flecha(s, cx[i], Y0 + 2.5, cx[i], Y0 + 11.0, color=SEC, ancho=1, punteada=True, punta=False)
    msgs = [(0, 1, '1  pregunta en español', False), (1, 2, '2  POST + token JWT', False),
            (2, 3, '3  rol, institución, SELECT', False), (3, 4, '4  métrica certificada', False),
            (4, 2, '5  cifras de vistas VIS_*', True), (2, 0, '6  resumen, tabla y gráfico', True)]
    for k, (a, b, t, ret) in enumerate(msgs):
        yy = Y0 + 4.0 + k * 1.4
        flecha(s, cx[a] + (0.08 if b > a else -0.08), yy, cx[b] + (-0.08 if b > a else 0.08), yy, color=NAR if not ret else NAVY, ancho=1.75, punteada=ret)
        lx = min(cx[a], cx[b]); lw = abs(cx[b] - cx[a])
        et = texto(s, lx + 0.12, yy - 1.0, lw - 0.24, 0.9, [{'t': t, 'sz': 9.5, 'b': True, 'c': NAVY}], margen=0.03, al='c', anclaje='b')
        et.fill.solid(); et.fill.fore_color.rgb = rgb(HIELO)
    tarjeta(s, X + 0.35, Y0 + 11.4, W - 0.7, 2.2, [
        {'t': 'Sin métrica certificada', 'sz': 12, 'b': True, 'c': NAR, 'sa': 2},
        {'t': 'La IA genera el SQL con solo el esquema (sin datos personales) y sqlglot lo valida antes de ejecutarlo.', 'sz': 11.5}],
            relleno=NAR_L, margen=0.3, anclaje='m')
    notas(s, 'Los diagramas de la propuesta son dos. A la izquierda, el modelo de datos en estrella: una tabla de hechos '
             'de matrículas por periodo rodeada de dimensiones, más los hechos de las predicciones, los segmentos, las '
             'intervenciones y la evaluación del modelo. Toda tabla lleva el código de institución y las vistas filtran '
             'con SESSION_CONTEXT. A la derecha, la secuencia de una consulta: la autoridad pregunta en español, la '
             'API valida rol e institución, las barreras eligen una métrica certificada y SQL Server devuelve solo '
             'cifras de las vistas. Si no hay métrica, la IA genera el SQL sin ver datos personales y se valida.')


def s_arquitectura(s):
    limpiar(s); titulo(s, 'Arquitectura del software: frontend y backend')
    y, h = Y0, 9.6
    w1, w2, w3, g = 8.4, 9.6, 7.8, 1.92
    x1 = X0; x2 = x1 + w1 + g; x3 = x2 + w2 + g
    # frontend
    caja(s, x1, y, w1, h, HIELO)
    _hilera(s, x1, y, w1, 1.5, 'FRONTEND')
    texto(s, x1 + 0.2, y + 1.6, w1 - 0.4, 1.2, [{'t': 'React 18 · TypeScript · Vite · Tailwind', 'sz': 12, 'b': True, 'c': NAR}], al='c')
    for i, t in enumerate(['Panel ejecutivo', 'Estudiantes en riesgo y ficha', 'Consulta conversacional', 'Seguimiento y calidad del modelo']):
        c = caja(s, x1 + 0.4, y + 2.9 + i * 1.5, w1 - 0.8, 1.25, BLANCO)
        escribir(c, [{'t': t, 'sz': 12, 'b': True}], al='c', anclaje='m', margen=0.1)
    texto(s, x1 + 0.2, y + 8.95, w1 - 0.4, 0.6, [{'t': 'No es la frontera de seguridad', 'sz': 10.5, 'i': True}], al='c')
    # backend
    caja(s, x2, y, w2, h, HIELO)
    _hilera(s, x2, y, w2, 1.5, 'BACKEND')
    texto(s, x2 + 0.2, y + 1.6, w2 - 0.4, 1.2, [{'t': 'FastAPI · API REST de 27 servicios', 'sz': 12, 'b': True, 'c': NAR}], al='c')
    mods = [('api/', 'rutas por módulo'), ('core/', 'JWT, roles, auditoría'), ('ml/', 'LightGBM, SHAP'),
            ('nl2sql/', '40 métricas, validador'), ('etl/', 'perfiles de mapeo'), ('scripts/', 'procesos por lotes')]
    mw, mh = (w2 - 0.8 - 0.3) / 2, 1.75
    for i, (a, b) in enumerate(mods):
        c = caja(s, x2 + 0.4 + (i % 2) * (mw + 0.3), y + 2.9 + (i // 2) * (mh + 0.25), mw, mh, BLANCO)
        escribir(c, [{'t': a, 'sz': 12.5, 'b': True, 'c': NAR, 'sa': 0}, {'t': b, 'sz': 11}], al='c', anclaje='m', margen=0.1)
    # datos
    caja(s, x3, y, w3, h, HIELO)
    _hilera(s, x3, y, w3, 1.5, 'BASE DE DATOS', NAR)
    texto(s, x3 + 0.2, y + 1.6, w3 - 0.4, 1.2, [{'t': 'SQL Server 2022', 'sz': 12, 'b': True, 'c': NAR}], al='c')
    for i, t in enumerate(['Almacén en estrella', 'Vistas VIS_* por institución', 'SESSION_CONTEXT', 'Cuentas de mínimo privilegio']):
        c = caja(s, x3 + 0.4, y + 2.9 + i * 1.5, w3 - 0.8, 1.25, BLANCO)
        escribir(c, [{'t': t, 'sz': 12, 'b': True}], al='c', anclaje='m', margen=0.1)
    # conexiones
    ym = y + 4.5
    flecha(s, x1 + w1 + 0.1, ym, x2 - 0.1, ym, color=NAR, ancho=2.25)
    flecha(s, x2 - 0.1, ym + 1.0, x1 + w1 + 0.1, ym + 1.0, color=NAVY, ancho=2.25, punteada=True)
    texto(s, x1 + w1 - 0.1, ym - 1.9, g + 0.2, 1.7, [{'t': 'HTTPS · JWT', 'sz': 10, 'b': True, 'c': NAVY}], al='c', margen=0.02, anclaje='b')
    flecha(s, x2 + w2 + 0.1, ym, x3 - 0.1, ym, color=NAR, ancho=2.25)
    flecha(s, x3 - 0.1, ym + 1.0, x2 + w2 + 0.1, ym + 1.0, color=NAVY, ancho=2.25, punteada=True)
    texto(s, x2 + w2 - 0.1, ym - 1.9, g + 0.2, 1.7, [{'t': 'solo lectura', 'sz': 10, 'b': True, 'c': NAVY}], al='c', margen=0.02, anclaje='b')
    # reglas
    reglas = [('El frontend solo habla HTTP', 'nunca accede a la base de datos'),
              ('Todo SQL de la IA corre con chat_reader', 'solo lee las vistas VIS_* de su institución'),
              ('Credenciales fuera del código', 'se leen de .env, que no se versiona'),
              ('189 pruebas automatizadas', '178 del backend y 11 de la interfaz')]
    rw = (ANCHO - 3 * 0.3) / 4
    for i, (a, b) in enumerate(reglas):
        c = caja(s, X0 + i * (rw + 0.3), Y0 + 10.1, rw, 3.7, NAVY if i < 3 else NAR)
        escribir(c, [{'t': a, 'sz': 12.5, 'b': True, 'c': BLANCO, 'sa': 4}, {'t': b, 'sz': 11.5, 'c': BLANCO}], anclaje='m', margen=0.4)
    notas(s, 'La arquitectura es cliente-servidor desacoplada. El frontend, en React con TypeScript, solo muestra la '
             'información según el rol. El backend, en FastAPI, expone veintisiete servicios y se organiza en capas: '
             'api, core con seguridad y auditoría, ml con el modelo, nl2sql con la consulta, etl y procesos por lotes. '
             'Detrás está SQL Server con el almacén en estrella. Tres reglas: el frontend nunca toca la base de datos, '
             'todo SQL de la IA corre con una cuenta de solo lectura sobre vistas de la institución, y las credenciales '
             'no están en el código. Lo respaldan 189 pruebas automatizadas.')


def s_enlace(s, qr_png):
    limpiar(s); titulo(s, 'Hipervínculo del proyecto')
    # QR
    caja(s, X0, Y0, 9.2, 13.8, HIELO)
    c = caja(s, X0 + 0.7, Y0 + 0.7, 7.8, 7.8, BLANCO)
    imagen(s, qr_png, X0 + 0.95, Y0 + 0.95, w=7.3).click_action.hyperlink.address = REPO
    texto(s, X0 + 0.3, Y0 + 8.8, 8.6, 1.4, [{'t': 'Escanee para abrir el repositorio', 'sz': 13, 'b': True, 'c': NAR}], al='c')
    texto(s, X0 + 0.3, Y0 + 10.1, 8.6, 3.4, [
        {'t': 'Contiene el código, los manuales y la documentación del proyecto.', 'sz': 11.5, 'sa': 6},
        {'t': 'Recorrido de la demostración', 'sz': 11.5, 'b': True, 'c': NAVY, 'sa': 2},
        {'t': 'panel → ficha → consulta → bloqueo → calidad del modelo', 'sz': 11}], al='c')
    # enlaces
    xr, wr = X0 + 9.6, ANCHO - 9.6
    b1 = caja(s, xr, Y0, wr, 1.9, NAVY)
    escribir(b1, [{'t': 'Repositorio del proyecto (clic o QR)', 'sz': 11.5, 'b': True, 'c': NAR, 'sa': 1},
                  {'t': REPO.replace('https://', ''), 'sz': 13.5, 'b': True, 'c': BLANCO}], anclaje='m', margen=0.5)
    b1.click_action.hyperlink.address = REPO
    b2 = caja(s, xr, Y0 + 2.2, wr, 1.9, NAR)
    escribir(b2, [{'t': 'Sistema en ejecución (demostración local)', 'sz': 11.5, 'b': True, 'c': NAVY, 'sa': 1},
                  {'t': 'http://localhost:3000', 'sz': 13.5, 'b': True, 'c': BLANCO}], anclaje='m', margen=0.5)
    b2.click_action.hyperlink.address = 'http://localhost:3000'
    # capturas
    cw = (wr - 0.4) / 2
    for i, (ruta, pie) in enumerate([(CAPT / 'av2_cap_ficha.png', 'Ficha con las razones del riesgo'),
                                      (CAPT / 'av2_cap_consulta.png', 'Consulta en lenguaje natural')]):
        x = xr + i * (cw + 0.4)
        caja(s, x, Y0 + 4.5, cw, 9.3, HIELO)
        from PIL import Image
        iw, ih = Image.open(ruta).size
        w_ = cw - 0.5; h_ = w_ * ih / iw
        if h_ > 7.3: h_ = 7.3; w_ = h_ * iw / ih
        imagen(s, ruta, x + (cw - w_) / 2, Y0 + 4.75, w=w_)
        texto(s, x + 0.2, Y0 + 12.4, cw - 0.4, 1.3, [{'t': pie, 'sz': 12, 'b': True, 'c': NAVY}], al='c', anclaje='m')
    notas(s, 'El proyecto está publicado en GitHub; el código QR y el enlace abren el repositorio con el código, los '
             'manuales técnico y de usuario y la documentación. El sistema se levanta con un script y se abre en '
             'localhost:3000. A la derecha están dos pantallas reales: la ficha de un estudiante con las tres razones '
             'principales de su riesgo y la consulta en lenguaje natural con una métrica certificada. En la demostración '
             'recorro panel, ficha, consulta, una pregunta maliciosa bloqueada y la calidad del modelo.')


def s_conclusiones(s):
    limpiar(s); titulo(s, 'Conclusiones')
    caja(s, X0, Y0, 17.4, 10.6, HIELO)
    texto(s, X0 + 0.3, Y0 + 0.2, 16.8, 0.9, [{'t': 'Desempeño en periodos que el modelo no había visto', 'sz': 13.5, 'b': True, 'c': NAR}])
    from PIL import Image
    iw, ih = Image.open(FIG / 'tf_desempeno_periodo.png').size
    w_ = 16.8; h_ = w_ * ih / iw
    imagen(s, FIG / 'tf_desempeno_periodo.png', X0 + 0.3, Y0 + 1.4, w=w_)
    texto(s, X0 + 0.3, Y0 + 1.5 + h_, 16.8, 0.9, [{'t': 'Mínimo exigido por periodo: 0,70. ROC-AUC global: 0,829 (UNEMI, datos de prueba) y 0,768 (OULAD, datos reales).', 'sz': 11}])
    tarjeta(s, X0, Y0 + 11.0, 17.4, 2.8, [
        {'t': 'Aporte', 'sz': 12.5, 'b': True, 'c': NAR, 'sa': 2},
        {'t': 'Predicción explicada en español dentro de un sistema por roles, con consulta certificada y aislamiento por institución en la base de datos.', 'sz': 12.5}],
            relleno=NAR_L, margen=0.4, anclaje='m')
    concl = [('El modelo se sostiene', 'con datos reales en periodos no vistos y supera a la regresión logística y a Random Forest.'),
             ('Detecta 78 %', 'de los abandonos con el umbral medio en la institución de prueba.'),
             ('La consulta es confiable:', '100 % de exactitud, 8 de 8 preguntas maliciosas contenidas y 0 fugas entre instituciones.'),
             ('Siguiente paso:', 'validar con una carrera real de la UNEMI, con autorización y evaluación de impacto (LOPDP).')]
    xr, wr = X0 + 17.8, ANCHO - 17.8
    hh = (13.8 - 3 * 0.3) / 4
    for i, (a, b) in enumerate(concl):
        yy = Y0 + i * (hh + 0.3)
        caja(s, xr, yy, wr, hh, NAVY if i < 3 else NAR)
        o = caja(s, xr + 0.3, yy + (hh - 1.2) / 2, 1.2, 1.2, BLANCO if i < 3 else NAVY, MSO_SHAPE.OVAL)
        escribir(o, [{'t': str(i + 1), 'sz': 14, 'b': True, 'c': NAR if i < 3 else BLANCO}], al='c', anclaje='m', margen=0)
        texto(s, xr + 1.7, yy, wr - 1.9, hh, [{'t': [{'t': a + ' ', 'b': True, 'sz': 12.5, 'c': BLANCO}, {'t': b, 'sz': 12, 'c': BLANCO}]}], anclaje='m', margen=0.1)
    notas(s, 'Cierro con las conclusiones. Primero, el modelo se sostiene con datos reales en periodos que no vio: '
             'cero coma ochocientos veintinueve en la UNEMI con datos de prueba y cero coma setecientos sesenta y ocho en '
             'OULAD, y supera a la regresión logística y a Random Forest. Segundo, detecta el 78 % de los abandonos con '
             'el umbral medio. Tercero, la consulta en español fue exacta, contuvo las ocho preguntas maliciosas y no '
             'tuvo fugas entre instituciones. El aporte es una predicción explicada, dentro de un sistema por roles. '
             'Como siguiente paso, validar con una carrera real de la UNEMI con autorización y evaluación de impacto. '
             'Muchas gracias; quedamos atentos a sus preguntas.')


def main():
    prs = Presentation(str(BASE))
    sl = list(prs.slides)
    assert len(sl) == 6
    qr = PRES / 'plantilla' / 'qr_repositorio.png'
    segno.make(REPO, error='m').save(str(qr), scale=14, border=2, dark='#1E2A36')
    portada(sl[0]); s_introduccion(sl[1]); s_diagramas(sl[2]); s_arquitectura(sl[3]); s_enlace(sl[4], qr); s_conclusiones(sl[5])
    prs.core_properties.author = 'Víctor Manuel Lluilema Pisco'
    prs.core_properties.last_modified_by = 'Víctor Manuel Lluilema Pisco'
    prs.core_properties.title = 'Sustentación: Prototipo de un sistema web para predecir el abandono en estudiantes universitarios'
    prs.save(str(SALIDA)); print('ok', SALIDA)


if __name__ == '__main__':
    main()

"""Sustentación individual de Víctor Manuel Lluilema Pisco: carátula + 5 diapositivas para 3 minutos.

Sigue los puntos que fijó la docente para el tribunal (introducción, objetivo, diagramas de la propuesta
práctica, arquitectura frontend/backend, hipervínculo del proyecto y conclusiones) y la rúbrica de la
sustentación (síntesis, ajuste al tiempo, calidad técnica, viabilidad, aporte diferenciador). Usa la base visual
del equipo (BaseSustentacion.pptx), con diagramas dibujados en la propia lámina, un código QR al repositorio y la
gráfica de resultados por periodo. El resto del tiempo (unos 5 minutos) es la demostración en vivo del sistema.
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

# Guion hablado (≈140 palabras por minuto). Total de las notas: unos 3 minutos.
N_PORTADA = ('Buenos días, miembros del tribunal. Soy Víctor Lluilema y, con Marlon Pérez, presento un sistema web que '
             'predice el abandono universitario y permite consultarlo en español. Les doy el contexto en tres '
             'minutos y luego lo mostramos funcionando.')
N_INTRO = ('En una universidad ecuatoriana abandonó el 44,90 % de cinco cohortes, y hoy se mide cuando ya ocurrió. '
           'Comparamos catorce estudios: ninguno reúne predicción, roles, consulta en español y protección de datos; '
           'solo uno explora la consulta, en laboratorio. Ese es el vacío. Nuestro objetivo: desarrollar un prototipo '
           'web que prediga el abandono y permita consultarlo en español, con un modelo explicado y datos aislados por '
           'institución, para que la autoridad actúe antes de que el estudiante se retire. Lo logramos en cuatro '
           'pasos: analizar, construir y validar el modelo, implementar y evaluar.')
N_DIAG = ('La propuesta en tres diagramas. Arriba, el flujo de trabajo: los datos entran por un ETL, pasan a un '
          'almacén en estrella, el modelo calcula el riesgo, la consulta lo expone y el panel lo muestra según el '
          'rol. Abajo a la izquierda, el modelo de datos: una tabla de hechos con seis dimensiones. A la derecha, la '
          'secuencia de una consulta: la autoridad pregunta en español, la API valida rol e institución, una métrica '
          'certificada genera el SQL y la base devuelve solo cifras agregadas.')
N_ARQ = ('La arquitectura es cliente-servidor. El frontend, en React, solo presenta la información según el rol. El '
         'backend, en FastAPI, expone veintisiete servicios en capas. Detrás, SQL Server con vistas por institución. '
         'Es seguro y viable: el frontend nunca toca la base, todo SQL de la IA corre con una cuenta de solo lectura y '
         'las claves no están en el código. Funciona en un computador de 16 gigas, sin tarjeta gráfica, y lo '
         'respaldan 189 pruebas.')
N_ENLACE = ('Todo está publicado: el QR y el enlace abren el repositorio. Cierro con las conclusiones y enseguida lo '
            'mostramos funcionando: panel, ficha, consulta, una orden maliciosa bloqueada y la calidad del modelo.')
N_CONCL = ('Concluyo. El modelo se sostiene en periodos que no vio: AUC de 0,829 con datos de prueba y 0,768 con datos '
           'reales. La consulta fue exacta en las 33 preguntas certificadas, contuvo las 8 maliciosas y no tuvo fugas '
           'entre instituciones. Nuestro aporte es una predicción explicada en español, dentro de un sistema por roles. '
           'Con honestidad: los datos de la UNEMI son de prueba; el siguiente paso es validar con una carrera real, con '
           'autorización y evaluación de impacto. Muchas gracias; ahora lo vemos funcionando.')


def portada(s):
    for sh in s.shapes:
        if sh.has_text_frame and 'EXPONE' in sh.text_frame.text:
            for par in sh.text_frame.paragraphs:
                rs = par.runs
                for i, r in enumerate(rs):
                    if r.text.startswith('MARLON DAVID PÉREZ ALMACHI') and i > 0 and rs[i - 1].text.startswith('EXPONE'):
                        r.text = 'VÍCTOR MANUEL LLUILEMA PISCO'
    notas(s, N_PORTADA)


def s_introduccion(s):
    limpiar(s); titulo(s, 'Introducción y objetivo')
    # fila 1: punto de partida y brecha frente a los 14 estudios comparados
    tarjeta(s, X0, Y0, 8.6, 5.6, [
        {'t': 'Punto de partida', 'sz': 14, 'b': True, 'c': NAR, 'sa': 4},
        {'t': '44,90 %', 'sz': 36, 'b': True, 'c': NAR, 'sa': 2},
        {'t': 'abandono en cinco cohortes de una universidad ecuatoriana (Núñez-Naranjo, 2024)', 'sz': 12.5, 'sa': 6},
        {'t': 'Hoy se mide cuando ya ocurrió', 'sz': 13, 'b': True}], margen=0.4)
    xb, wb = X0 + 9.0, ANCHO - 9.0
    caja(s, xb, Y0, wb, 5.6, HIELO)
    texto(s, xb + 0.3, Y0 + 0.15, wb - 0.6, 1.0, [{'t': 'Brecha frente a los 14 estudios comparados', 'sz': 14, 'b': True, 'c': NAR}])
    stats = [('0', 'integran predicción, roles, consulta en español y protección de datos'),
             ('1', 'explora la consulta en lenguaje natural, solo en laboratorio'),
             ('3', 'integran el modelo de forma parcial en un sistema')]
    sw = (wb - 0.6 - 2 * 0.3) / 3
    for i, (n, t) in enumerate(stats):
        x = xb + 0.3 + i * (sw + 0.3)
        caja(s, x, Y0 + 1.3, sw, 4.0, BLANCO)
        texto(s, x + 0.1, Y0 + 1.35, 2.6, 2.2, [{'t': n, 'sz': 40, 'b': True, 'c': NAR}], al='c', anclaje='m', margen=0.05)
        texto(s, x + 2.6, Y0 + 1.4, sw - 2.7, 3.8, [{'t': t, 'sz': 12.5, 'b': True}], anclaje='m', margen=0.1)
    # fila 2: objetivo general en tres enunciados (qué, cómo, para qué)
    yo = Y0 + 6.0
    caja(s, X0, yo, ANCHO, 4.2, NAVY)
    texto(s, X0 + 0.4, yo + 0.15, 6.0, 0.8, [{'t': 'Objetivo general', 'sz': 14, 'b': True, 'c': NAR}], margen=0.05)
    cols = [('¿Qué?', 'Desarrollar un prototipo web que prediga el abandono estudiantil y permita consultar los resultados en español.'),
            ('¿Cómo?', 'Con un modelo LightGBM explicado con SHAP, consulta NL2SQL validada y datos aislados por institución.'),
            ('¿Para qué?', 'Para que la autoridad priorice el acompañamiento antes de que el estudiante se retire.')]
    cw = (ANCHO - 0.8 - 2 * 0.4) / 3
    for i, (a, b) in enumerate(cols):
        texto(s, X0 + 0.4 + i * (cw + 0.4), yo + 1.0, cw, 3.1, [
            {'t': a, 'sz': 13, 'b': True, 'c': NAR, 'sa': 2}, {'t': b, 'sz': 13.5, 'c': BLANCO}], margen=0.05)
    # fila 3: objetivos específicos
    objs = [('1', 'Analizar', 'procesos y variables'), ('2', 'Construir y validar', 'el modelo predictivo'),
            ('3', 'Implementar', 'el sistema web y la consulta'), ('4', 'Evaluar', 'el prototipo')]
    w = (ANCHO - 3 * 0.4) / 4
    yy = Y0 + 10.7
    for i, (n, v, r) in enumerate(objs):
        x = X0 + i * (w + 0.4)
        caja(s, x, yy, w, 3.1, HIELO2)
        c = caja(s, x + 0.35, yy + 0.9, 1.3, 1.3, NAR, MSO_SHAPE.OVAL)
        escribir(c, [{'t': n, 'sz': 16, 'b': True, 'c': BLANCO}], al='c', anclaje='m', margen=0)
        texto(s, x + 1.8, yy + 0.1, w - 2.0, 2.9, [
            {'t': v, 'sz': 14, 'b': True, 'sa': 1}, {'t': r, 'sz': 12.5}], anclaje='m')
    notas(s, N_INTRO)


def _hilera(s, x, y, w, h, titulo_, color=NAVY, sz=11.5):
    c = caja(s, x, y, w, h, color)
    escribir(c, [{'t': titulo_, 'sz': sz, 'b': True, 'c': BLANCO}], al='c', anclaje='m', margen=0.1)
    return c


def s_diagramas(s):
    limpiar(s); titulo(s, 'Diagramas de la propuesta práctica')
    # ---------- banda superior: flujo de trabajo y solución tecnológica
    pasos = [('1  Datos y ETL', 'perfiles de mapeo · Great Expectations'), ('2  Almacén', 'SQL Server 2022 en estrella'),
             ('3  Modelo', 'LightGBM · Platt · SHAP · K-means'), ('4  Consulta', 'NL2SQL con validador sqlglot'),
             ('5  Panel por roles', 'React · JWT · 3 roles')]
    g = 0.55
    pw = (ANCHO - 4 * g) / 5
    for i, (a, b) in enumerate(pasos):
        x = X0 + i * (pw + g)
        c = caja(s, x, Y0, pw, 3.2, NAVY if i != 2 else NAR)
        escribir(c, [{'t': a, 'sz': 13, 'b': True, 'c': BLANCO, 'sa': 3}, {'t': b, 'sz': 10.5, 'c': BLANCO}],
                 al='c', anclaje='m', margen=0.2)
        if i < 4:
            flecha(s, x + pw + 0.05, Y0 + 1.6, x + pw + g - 0.05, Y0 + 1.6, color=NAR, ancho=2.25)
    # ---------- panel izquierdo: modelo de datos en estrella
    PY, PH, W = Y0 + 3.6, 10.2, 14.6
    caja(s, X0, PY, W, PH, HIELO)
    texto(s, X0 + 0.2, PY + 0.1, W - 0.4, 0.8, [{'t': 'Modelo de datos en estrella', 'sz': 13.5, 'b': True, 'c': NAR}])
    fx, fw, fh = X0 + 4.75, 5.1, 3.1
    fy = PY + 3.2
    dw, dh = 3.9, 1.1
    ys = [PY + 1.2, PY + 3.2, PY + 5.2]
    for yy, d in zip(ys, ['dim_institucion', 'dim_alumno', 'dim_carrera']):
        flecha(s, X0 + 0.35 + dw, yy + dh / 2, fx, fy + fh / 2 + (yy + dh / 2 - (fy + fh / 2)) * 0.25, color=SEC, ancho=1.25, punta=False)
        _hilera(s, X0 + 0.35, yy, dw, dh, d, sz=11)
    for yy, d in zip(ys, ['dim_periodo', 'dim_sede', 'dim_estado']):
        flecha(s, fx + fw, fy + fh / 2 + (yy + dh / 2 - (fy + fh / 2)) * 0.25, X0 + W - 0.35 - dw, yy + dh / 2, color=SEC, ancho=1.25, punta=False)
        _hilera(s, X0 + W - 0.35 - dw, yy, dw, dh, d, sz=11)
    f = caja(s, fx, fy, fw, fh, NAR)
    escribir(f, [{'t': 'fact_matriculas', 'sz': 13, 'b': True, 'c': BLANCO, 'sa': 3},
                 {'t': 'estudiante por periodo: promedio, asistencia, créditos, estado', 'sz': 10.5, 'c': BLANCO}],
             al='c', anclaje='m', margen=0.2)
    texto(s, X0 + 0.3, PY + 6.7, W - 0.6, 0.7, [{'t': 'Hechos de procesos por lotes y de seguimiento', 'sz': 11.5, 'b': True}])
    hw = (W - 0.6 - 3 * 0.25) / 4
    for i, hch in enumerate(['prediccion_abandono', 'segmento_carrera', 'intervencion', 'evaluacion_modelo']):
        c = caja(s, X0 + 0.3 + i * (hw + 0.25), PY + 7.45, hw, 1.2, NAR_L)
        escribir(c, [{'t': hch.replace('_', '_​'), 'sz': 10, 'b': True}], al='c', anclaje='m', margen=0.08)
    texto(s, X0 + 0.3, PY + 8.75, W - 0.6, 1.3, [
        {'t': 'Toda tabla lleva institucion_codigo; las vistas VIS_* filtran con SESSION_CONTEXT.', 'sz': 10.5, 'i': True}])
    # ---------- panel derecho: secuencia de la consulta en lenguaje natural
    X = X0 + W + 0.44
    caja(s, X, PY, W, PH, HIELO)
    texto(s, X + 0.2, PY + 0.1, W - 0.4, 0.8, [{'t': 'Secuencia de una consulta en lenguaje natural', 'sz': 13.5, 'b': True, 'c': NAR}])
    nombres = ['Autoridad', 'Interfaz web', 'API FastAPI', 'Barreras y enrutador', 'SQL Server']
    paso = (W - 1.0) / 5
    cx = [X + 0.5 + paso * (i + 0.5) for i in range(5)]
    for i, n in enumerate(nombres):
        c = caja(s, cx[i] - paso / 2 + 0.1, PY + 1.1, paso - 0.2, 1.2, NAVY if i != 4 else NAR)
        escribir(c, [{'t': n, 'sz': 10.5, 'b': True, 'c': BLANCO}], al='c', anclaje='m', margen=0.05)
        flecha(s, cx[i], PY + 2.3, cx[i], PY + 9.6, color=SEC, ancho=1, punteada=True, punta=False)
    msgs = [(0, 1, '1  pregunta en español', False), (1, 2, '2  POST + token JWT', False),
            (2, 3, '3  rol, institución, SELECT', False), (3, 4, '4  métrica certificada', False),
            (4, 2, '5  cifras de vistas VIS_*', True), (2, 0, '6  resumen, tabla y gráfico', True)]
    for k, (a, b, t, ret) in enumerate(msgs):
        yy = PY + 3.7 + k * 1.1
        flecha(s, cx[a] + (0.08 if b > a else -0.08), yy, cx[b] + (-0.08 if b > a else 0.08), yy, color=NAR if not ret else NAVY, ancho=1.75, punteada=ret)
        lx = min(cx[a], cx[b]); lw = abs(cx[b] - cx[a])
        et = texto(s, lx + 0.12, yy - 0.78, lw - 0.24, 0.72, [{'t': t, 'sz': 9.5, 'b': True, 'c': NAVY}], margen=0.02, al='c', anclaje='b')
        et.fill.solid(); et.fill.fore_color.rgb = rgb(HIELO)
    texto(s, X + 0.3, PY + 9.45, W - 0.6, 0.7, [
        {'t': 'Sin métrica certificada: la IA genera el SQL solo con el esquema y sqlglot lo valida.', 'sz': 10, 'i': True}], al='c', anclaje='m')
    notas(s, N_DIAG)


def s_arquitectura(s):
    limpiar(s); titulo(s, 'Arquitectura del software: frontend y backend')
    y, h = Y0, 8.0
    w1, w2, w3, g = 8.4, 9.6, 7.8, 1.92
    x1 = X0; x2 = x1 + w1 + g; x3 = x2 + w2 + g
    # frontend
    caja(s, x1, y, w1, h, HIELO)
    _hilera(s, x1, y, w1, 1.3, 'FRONTEND')
    texto(s, x1 + 0.2, y + 1.4, w1 - 0.4, 0.9, [{'t': 'React 18 · TypeScript · Vite · Tailwind', 'sz': 11.5, 'b': True, 'c': NAR}], al='c')
    for i, t in enumerate(['Panel ejecutivo', 'Riesgo y ficha del estudiante', 'Consulta conversacional', 'Seguimiento y calidad del modelo']):
        c = caja(s, x1 + 0.4, y + 2.4 + i * 1.4, w1 - 0.8, 1.15, BLANCO)
        escribir(c, [{'t': t, 'sz': 12, 'b': True}], al='c', anclaje='m', margen=0.1)
    # backend
    caja(s, x2, y, w2, h, HIELO)
    _hilera(s, x2, y, w2, 1.3, 'BACKEND')
    texto(s, x2 + 0.2, y + 1.4, w2 - 0.4, 0.9, [{'t': 'FastAPI · API REST de 27 servicios', 'sz': 11.5, 'b': True, 'c': NAR}], al='c')
    mods = [('api/', 'rutas por módulo'), ('core/', 'JWT, roles, auditoría'), ('ml/', 'LightGBM, SHAP'),
            ('nl2sql/', '40 métricas, validador'), ('etl/', 'perfiles de mapeo'), ('scripts/', 'procesos por lotes')]
    mw, mh = (w2 - 0.8 - 0.3) / 2, 1.3
    for i, (a, b) in enumerate(mods):
        c = caja(s, x2 + 0.4 + (i % 2) * (mw + 0.3), y + 2.4 + (i // 2) * (mh + 0.2), mw, mh, BLANCO)
        escribir(c, [{'t': a, 'sz': 12.5, 'b': True, 'c': NAR, 'sa': 0}, {'t': b, 'sz': 10.5}], al='c', anclaje='m', margen=0.08)
    # datos
    caja(s, x3, y, w3, h, HIELO)
    _hilera(s, x3, y, w3, 1.3, 'BASE DE DATOS', NAR)
    texto(s, x3 + 0.2, y + 1.4, w3 - 0.4, 0.9, [{'t': 'SQL Server 2022', 'sz': 11.5, 'b': True, 'c': NAR}], al='c')
    for i, t in enumerate(['Almacén en estrella', 'Vistas VIS_* por institución', 'SESSION_CONTEXT', 'Cuentas de mínimo privilegio']):
        c = caja(s, x3 + 0.4, y + 2.4 + i * 1.4, w3 - 0.8, 1.15, BLANCO)
        escribir(c, [{'t': t, 'sz': 12, 'b': True}], al='c', anclaje='m', margen=0.1)
    # conexiones
    ym = y + 4.0
    flecha(s, x1 + w1 + 0.1, ym, x2 - 0.1, ym, color=NAR, ancho=2.25)
    flecha(s, x2 - 0.1, ym + 0.9, x1 + w1 + 0.1, ym + 0.9, color=NAVY, ancho=2.25, punteada=True)
    texto(s, x1 + w1 - 0.1, ym - 1.9, g + 0.2, 1.7, [{'t': 'HTTPS · JWT', 'sz': 10, 'b': True, 'c': NAVY}], al='c', margen=0.02, anclaje='b')
    flecha(s, x2 + w2 + 0.1, ym, x3 - 0.1, ym, color=NAR, ancho=2.25)
    flecha(s, x3 - 0.1, ym + 0.9, x2 + w2 + 0.1, ym + 0.9, color=NAVY, ancho=2.25, punteada=True)
    texto(s, x2 + w2 - 0.1, ym - 1.9, g + 0.2, 1.7, [{'t': 'solo lectura', 'sz': 10, 'b': True, 'c': NAVY}], al='c', margen=0.02, anclaje='b')
    # franja inferior: seguridad, tendencias, recursos y pruebas
    tarj = [('Seguridad por diseño', 'El frontend nunca toca la base. La IA corre con chat_reader, solo sobre vistas de su institución. '
                                     'Claves en .env, fuera del código.', NAVY),
            ('Tendencias vigentes', 'LightGBM y SHAP (explicabilidad), NL2SQL con validación, MLflow, Great Expectations y '
                                    'Evidently (MLOps).', NAVY),
            ('Implementable hoy', 'Un computador de 4 núcleos y 16 GB, Docker y planes gratuitos de IA. Sin GPU. '
                                  'Un perfil de mapeo incorpora otra institución.', NAVY),
            ('189 pruebas', '178 del backend y 11 de la interfaz; calidad de datos 23 de 23 reglas.', NAR)]
    rw = (ANCHO - 3 * 0.3) / 4
    for i, (a, b, col) in enumerate(tarj):
        c = caja(s, X0 + i * (rw + 0.3), Y0 + 8.4, rw, 5.4, col)
        escribir(c, [{'t': a, 'sz': 13, 'b': True, 'c': NAR if col == NAVY else BLANCO, 'sa': 5},
                     {'t': b, 'sz': 12, 'c': BLANCO}], anclaje='m', margen=0.4)
    notas(s, N_ARQ)


def s_enlace(s, qr_png):
    limpiar(s); titulo(s, 'Hipervínculo del proyecto y demostración')
    # QR
    caja(s, X0, Y0, 9.2, 13.8, HIELO)
    caja(s, X0 + 0.7, Y0 + 0.7, 7.8, 7.8, BLANCO)
    imagen(s, qr_png, X0 + 0.95, Y0 + 0.95, w=7.3).click_action.hyperlink.address = REPO
    texto(s, X0 + 0.3, Y0 + 8.8, 8.6, 1.2, [{'t': 'Escanee para abrir el repositorio', 'sz': 13, 'b': True, 'c': NAR}], al='c')
    texto(s, X0 + 0.3, Y0 + 10.0, 8.6, 3.6, [
        {'t': 'Código, manuales y documentación del proyecto.', 'sz': 11.5, 'sa': 8},
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
    from PIL import Image
    cw = (wr - 0.4) / 2
    for i, (ruta, pie) in enumerate([(CAPT / 'av2_cap_ficha.png', 'Ficha con las razones del riesgo'),
                                      (CAPT / 'av2_cap_consulta.png', 'Consulta en lenguaje natural')]):
        x = xr + i * (cw + 0.4)
        caja(s, x, Y0 + 4.5, cw, 9.3, HIELO)
        iw, ih = Image.open(ruta).size
        w_ = cw - 0.5; h_ = w_ * ih / iw
        if h_ > 7.3: h_ = 7.3; w_ = h_ * iw / ih
        imagen(s, ruta, x + (cw - w_) / 2, Y0 + 4.75, w=w_)
        texto(s, x + 0.2, Y0 + 12.4, cw - 0.4, 1.3, [{'t': pie, 'sz': 12, 'b': True, 'c': NAVY}], al='c', anclaje='m')
    notas(s, N_ENLACE)


def s_conclusiones(s):
    from PIL import Image
    limpiar(s); titulo(s, 'Conclusiones y continuidad')
    caja(s, X0, Y0, 16.6, 10.2, HIELO)
    texto(s, X0 + 0.3, Y0 + 0.2, 16.0, 0.9, [{'t': 'Desempeño en periodos que el modelo no había visto', 'sz': 13.5, 'b': True, 'c': NAR}])
    iw, ih = Image.open(FIG / 'tf_desempeno_periodo.png').size
    w_ = 16.0; h_ = w_ * ih / iw
    if h_ > 7.2: h_ = 7.2; w_ = h_ * iw / ih
    imagen(s, FIG / 'tf_desempeno_periodo.png', X0 + 0.3 + (16.0 - w_) / 2, Y0 + 1.3, w=w_)
    texto(s, X0 + 0.3, Y0 + 1.4 + h_, 16.0, 1.4, [{'t': 'Mínimo exigido por periodo: 0,70. Global: 0,829 (UNEMI, datos de prueba) y 0,768 (OULAD, datos reales).', 'sz': 11}])
    tarjeta(s, X0, Y0 + 10.6, 16.6, 3.2, [
        {'t': 'Con honestidad', 'sz': 12.5, 'b': True, 'c': NAR, 'sa': 2},
        {'t': 'Los datos de la UNEMI son de prueba; OULAD aporta la validación con datos reales. Por eso el paso '
              'siguiente es validar con una carrera real.', 'sz': 12.5}],
            relleno=NAR_L, margen=0.4, anclaje='m')
    concl = [('El modelo se sostiene', 'en periodos no vistos y supera a la regresión logística y a Random Forest.'),
             ('La consulta es confiable:', '100 % de exactitud en 33 preguntas certificadas, 8 de 8 maliciosas contenidas, 0 fugas.'),
             ('Aporte diferenciador:', 'predicción explicada en español, en un sistema por roles con aislamiento en la base.'),
             ('Continuidad:', 'carrera real de la UNEMI con autorización y evaluación de impacto (LOPDP); prueba de usabilidad con autoridades.')]
    xr, wr = X0 + 17.0, ANCHO - 17.0
    hh = (13.8 - 3 * 0.3) / 4
    for i, (a, b) in enumerate(concl):
        yy = Y0 + i * (hh + 0.3)
        caja(s, xr, yy, wr, hh, NAVY if i < 3 else NAR)
        o = caja(s, xr + 0.3, yy + (hh - 1.2) / 2, 1.2, 1.2, BLANCO if i < 3 else NAVY, MSO_SHAPE.OVAL)
        escribir(o, [{'t': str(i + 1), 'sz': 14, 'b': True, 'c': NAR if i < 3 else BLANCO}], al='c', anclaje='m', margen=0)
        texto(s, xr + 1.7, yy, wr - 1.9, hh, [{'t': [{'t': a + ' ', 'b': True, 'sz': 12.5, 'c': BLANCO}, {'t': b, 'sz': 12, 'c': BLANCO}]}], anclaje='m', margen=0.1)
    notas(s, N_CONCL)


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
    palabras = [len(n.split()) for n in (N_PORTADA, N_INTRO, N_DIAG, N_ARQ, N_ENLACE, N_CONCL)]
    print('palabras por diapositiva', palabras, 'total', sum(palabras), '→ min a 140 ppm', round(sum(palabras) / 140, 2))


if __name__ == '__main__':
    main()

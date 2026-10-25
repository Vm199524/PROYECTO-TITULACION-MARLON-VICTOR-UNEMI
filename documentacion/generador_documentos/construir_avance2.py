# -*- coding: utf-8 -*-
"""
Construye el Avance 2 del trabajo de titulación sobre una copia del Avance 1.

Conserva intactos la portada, los certificados, la declaración de autoría, los
índices, el encabezado, el pie y el Anexo de información académica de la
plantilla UNEMI; reemplaza el cuerpo (Introducción a Anexos) clonando el formato
de los párrafos del propio documento: títulos, cuerpo, listas, rótulos, notas y
referencias. Las cifras se leen de los resultados reales del sistema
(ml/modelos/*/metricas.json y eval/resultados) para que el documento y el
software nunca digan cosas distintas.

Uso:
    python documentacion/generador_documentos/construir_avance2.py \
        --base AVANCE1_MARLON_VICTOR.docx --salida documentacion/avances/AVANCE2_MARLON_VICTOR.docx

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import copy
import re
import shutil
from pathlib import Path

import docx
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt
from docx.table import Table
from docx.text.paragraph import Paragraph

from contenido_avance2 import bloques, resumen_abstract  # noqa: E402

RAIZ = Path(__file__).resolve().parents[2]
ANCHO_UTIL_CM = 15.0   # A4 con márgenes de 3 cm (plantilla UNEMI)
XML_SPACE = '{http://www.w3.org/XML/1998/namespace}space'


# ── utilidades XML ──────────────────────────────────────────────────────
def _buscar(doc, inicio: str, estilo: str | None = None) -> Paragraph:
    for p in doc.paragraphs:
        if p.text.strip().startswith(inicio) and (estilo is None or p.style.name.startswith(estilo)):
            return p
    raise LookupError(inicio)


def _sin_marcadores(el):
    for tag in ('w:bookmarkStart', 'w:bookmarkEnd', 'w:commentRangeStart', 'w:commentRangeEnd', 'w:proofErr'):
        for b in el.findall('.//' + qn(tag)):
            b.getparent().remove(b)
    for lrp in el.findall('.//' + qn('w:lastRenderedPageBreak')):
        lrp.getparent().remove(lrp)
    return el


def _run_base(p_el):
    r = p_el.find(qn('w:r'))
    base = copy.deepcopy(r) if r is not None else OxmlElement('w:r')
    for c in list(base):
        if c.tag != qn('w:rPr'):
            base.remove(c)
    return base


# Estilo de las tablas: encabezado en el azul institucional de la UNEMI, filas alternas en un
# celeste muy claro y bordes grises suaves (legible impreso en blanco y negro).
COLOR_ENCABEZADO = '1F4E79'
COLOR_BANDA = 'EAF1F8'
COLOR_BORDE = 'B7C6D6'


def _color_run(r, color: str) -> None:
    rpr = r.find(qn('w:rPr'))
    if rpr is None:
        rpr = OxmlElement('w:rPr'); r.insert(0, rpr)
    e = rpr.find(qn('w:color'))
    if e is None:
        e = OxmlElement('w:color')
        siguiente = next((rpr.find(qn(x)) for x in ('w:spacing', 'w:w', 'w:kern', 'w:position', 'w:sz', 'w:szCs',
                                                    'w:highlight', 'w:u', 'w:effect', 'w:shd', 'w:vertAlign', 'w:lang')
                          if rpr.find(qn(x)) is not None), None)
        if siguiente is not None:
            siguiente.addprevious(e)
        else:
            rpr.append(e)
    e.set(qn('w:val'), color)


def _run(base, texto: str, negrita=None, cursiva=None, tam=None, fuente=None):
    r = copy.deepcopy(base)
    rpr = r.find(qn('w:rPr'))
    if rpr is None:
        rpr = OxmlElement('w:rPr'); r.insert(0, rpr)
    for tag, val in (('w:b', negrita), ('w:bCs', negrita), ('w:i', cursiva), ('w:iCs', cursiva)):
        if val is None:
            continue
        e = rpr.find(qn(tag))
        if e is not None:
            rpr.remove(e)
        e = OxmlElement(tag)
        if not val:
            e.set(qn('w:val'), '0')
        rpr.append(e)
    if tam:
        for tag in ('w:sz', 'w:szCs'):
            e = rpr.find(qn(tag))
            if e is not None:
                rpr.remove(e)
            e = OxmlElement(tag); e.set(qn('w:val'), str(int(tam * 2))); rpr.append(e)
    if fuente:
        e = rpr.find(qn('w:rFonts'))
        if e is not None:
            rpr.remove(e)
        e = OxmlElement('w:rFonts')
        for a in ('w:ascii', 'w:hAnsi', 'w:cs'):
            e.set(qn(a), fuente)
        rpr.insert(0, e)
    t = OxmlElement('w:t'); t.text = texto; t.set(XML_SPACE, 'preserve')
    r.append(t)
    return r


def _segmentos(texto: str):
    """**negrita** y *cursiva* en línea → [(texto, negrita, cursiva)]."""
    partes = re.split(r'(\*\*[^*]+\*\*|\*[^*]+\*)', texto)
    for s in partes:
        if not s:
            continue
        if s.startswith('**'):
            yield s[2:-2], True, False
        elif s.startswith('*'):
            yield s[1:-1], False, True
        else:
            yield s, None, None


class Constructor:
    def __init__(self, doc):
        self.doc = doc
        self.modelos = {}
        self.n_fig = 0
        self.n_tab = 0
        self.ancla = None

    # modelos de formato tomados del propio documento
    def tomar_modelos(self):
        d = self.doc
        m = self.modelos
        m['h1'] = _sin_marcadores(copy.deepcopy(_buscar(d, '1. Introducción', 'Heading 1')._p))
        m['h2'] = _sin_marcadores(copy.deepcopy(_buscar(d, '1.2 Propósito del caso', 'Heading 2')._p))
        m['cuerpo'] = _sin_marcadores(copy.deepcopy(_buscar(d, 'En el contexto de la transformación digital')._p))
        m['vineta'] = _sin_marcadores(copy.deepcopy(_buscar(d, 'Imposibilidad de detectar tendencias')._p))
        m['rotulo'] = _sin_marcadores(copy.deepcopy(_buscar(d, 'Ilustración 1.', 'Caption')._p))
        m['imagen'] = _sin_marcadores(copy.deepcopy(d.paragraphs[[i for i, p in enumerate(d.paragraphs)
                                                                    if p.text.startswith('Ilustración 1.')
                                                                    and p.style.name == 'Caption'][0] + 1]._p))
        m['nota'] = _sin_marcadores(copy.deepcopy(_buscar(d, 'Nota. Elaboración propia a partir del diseño')._p))
        m['ref'] = _sin_marcadores(copy.deepcopy(_buscar(d, 'Ascoli, B. G.', 'Bibliography')._p))
        # H3: el H2 con estilo Heading 3
        h3 = copy.deepcopy(m['h2'])
        ps = h3.find(qn('w:pPr')).find(qn('w:pStyle'))
        estilo3 = next(s for s in d.styles if s.name == 'Heading 3')
        ps.set(qn('w:val'), estilo3.style_id)
        m['h3'] = h3

    def _nuevo(self, modelo_key: str):
        el = copy.deepcopy(self.modelos[modelo_key])
        for r in el.findall(qn('w:r')) + el.findall(qn('w:hyperlink')):
            el.remove(r)
        self.ancla.addnext(el)
        self.ancla = el
        return el

    def parrafo(self, texto: str, modelo='cuerpo', cursiva=None, **kw):
        base = _run_base(self.modelos[modelo])
        el = self._nuevo(modelo)
        for txt, neg, cur in _segmentos(texto):
            el.append(_run(base, txt, negrita=neg, cursiva=cur if cur is not None else cursiva, **kw))
        return el

    def titulo(self, nivel: int, texto: str):
        el = self.parrafo(texto, modelo=f'h{nivel}', cursiva=True if nivel == 3 else None)
        if nivel == 1:
            self.n_h1 = getattr(self, 'n_h1', 0) + 1
            if self.n_h1 > 1:  # cada capítulo empieza en página nueva
                ppr = el.find(qn('w:pPr'))
                if ppr.find(qn('w:pageBreakBefore')) is None:
                    ppr.insert(1, OxmlElement('w:pageBreakBefore'))
        return el

    def vinetas(self, items):
        for it in items:
            self.parrafo(it, modelo='vineta')

    def _rotulo(self, tipo: str, n: int, titulo: str):
        """«Figura N. Título» con campo SEQ (actualizable en Word) y keepNext."""
        el = copy.deepcopy(self.modelos['rotulo'])
        base = _run_base(el)
        for r in el.findall(qn('w:r')):
            el.remove(r)
        ppr = el.find(qn('w:pPr'))
        if ppr.find(qn('w:keepNext')) is None:
            k = OxmlElement('w:keepNext'); ppr.insert(1, k)
        el.append(_run(base, f'{tipo} ', negrita=True, cursiva=False))
        for tipo_fld, contenido in (('begin', None), (None, f' SEQ {tipo} \\* ARABIC '), ('separate', None),
                                    (None, None), ('end', None)):
            r = copy.deepcopy(base)
            rpr = r.find(qn('w:rPr'))
            if rpr is not None:
                for tag in ('w:i', 'w:iCs'):
                    e = rpr.find(qn(tag))
                    if e is not None:
                        rpr.remove(e)
                b = OxmlElement('w:b'); rpr.append(b)
                sin_i = OxmlElement('w:i'); sin_i.set(qn('w:val'), '0'); rpr.append(sin_i)
            if tipo_fld:
                f = OxmlElement('w:fldChar'); f.set(qn('w:fldCharType'), tipo_fld); r.append(f)
            elif contenido:
                t = OxmlElement('w:instrText'); t.text = contenido; t.set(XML_SPACE, 'preserve'); r.append(t)
            else:
                t = OxmlElement('w:t'); t.text = str(n); r.append(t)
            el.append(r)
        el.append(_run(base, '. ', negrita=True, cursiva=False))
        el.append(_run(base, titulo, negrita=False, cursiva=True))
        self.ancla.addnext(el)
        self.ancla = el

    def _nota(self, texto: str):
        base = _run_base(self.modelos['nota'])
        el = self._nuevo('nota')
        el.append(_run(base, 'Nota.', negrita=True, cursiva=True, tam=10))
        for txt, neg, cur in _segmentos(' ' + texto):
            el.append(_run(base, txt, negrita=neg if neg else False, cursiva=cur if cur else False, tam=10))

    def figura(self, titulo: str, png: Path, ancho_cm: float, alt: str, nota: str):
        ancho_cm = min(ancho_cm, ANCHO_UTIL_CM)
        self.n_fig += 1
        self._rotulo('Figura', self.n_fig, titulo)
        el = self._nuevo('imagen')
        p = Paragraph(el, self.doc._body)
        p.paragraph_format.alignment = 1
        p.paragraph_format.keep_with_next = True
        run = p.add_run()
        run.add_picture(str(png), width=Cm(ancho_cm))
        dp = run._r.find('.//' + qn('wp:docPr'))
        dp.set('descr', alt); dp.set('name', f'Figura {self.n_fig}')
        self._nota(nota)
        return self.n_fig

    def tabla(self, titulo: str, encabezados, filas, nota: str, anchos_cm=None, tam=10):
        self.n_tab += 1
        self._rotulo('Tabla', self.n_tab, titulo)
        t = self.doc.add_table(rows=1 + len(filas), cols=len(encabezados))
        self.ancla.addnext(t._tbl)
        self.ancla = t._tbl
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        tblpr = t._tbl.tblPr
        borde = OxmlElement('w:tblBorders')
        for lado in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
            e = OxmlElement(f'w:{lado}'); e.set(qn('w:val'), 'single')
            e.set(qn('w:sz'), '4'); e.set(qn('w:color'), COLOR_BORDE)
            borde.append(e)
        tblpr.append(borde)
        mar = OxmlElement('w:tblCellMar')
        for lado, v in (('top', 30), ('bottom', 30), ('left', 70), ('right', 70)):
            e = OxmlElement(f'w:{lado}'); e.set(qn('w:w'), str(v)); e.set(qn('w:type'), 'dxa'); mar.append(e)
        tblpr.append(mar)
        base = _run_base(self.modelos['cuerpo'])
        for i, fila in enumerate([encabezados] + filas):
            row = t.rows[i]
            if i == 0:
                trpr = row._tr.get_or_add_trPr()
                h = OxmlElement('w:tblHeader'); trpr.append(h)
            cant = OxmlElement('w:cantSplit'); row._tr.get_or_add_trPr().append(cant)
            for j, txt in enumerate(fila):
                c = row.cells[j]
                p = c.paragraphs[0]
                pf = p.paragraph_format
                pf.first_line_indent = Cm(0); pf.left_indent = Cm(0)
                pf.space_before = Pt(1); pf.space_after = Pt(1); pf.line_spacing = 1.0
                p.alignment = 0
                for k, linea in enumerate(str(txt).split('\n')):
                    if k:
                        br = OxmlElement('w:r'); br.append(OxmlElement('w:br')); p._p.append(br)
                    for seg, neg, cur in _segmentos(linea):
                        r = _run(base, seg, negrita=True if i == 0 else neg, cursiva=cur if cur else False, tam=tam)
                        if i == 0:
                            _color_run(r, 'FFFFFF')
                        p._p.append(r)
                relleno = COLOR_ENCABEZADO if i == 0 else (COLOR_BANDA if i % 2 == 0 else None)
                if relleno:
                    tcpr = c._tc.get_or_add_tcPr()
                    shd = OxmlElement('w:shd'); shd.set(qn('w:val'), 'clear'); shd.set(qn('w:color'), 'auto')
                    shd.set(qn('w:fill'), relleno); tcpr.append(shd)
                if i == 0:
                    va = OxmlElement('w:vAlign'); va.set(qn('w:val'), 'center'); c._tc.get_or_add_tcPr().append(va)
        anchos_cm = anchos_cm or [ANCHO_UTIL_CM / len(encabezados)] * len(encabezados)
        factor = ANCHO_UTIL_CM / sum(anchos_cm)
        anchos_cm = [w * factor for w in anchos_cm]
        tblw = tblpr.find(qn('w:tblW'))
        if tblw is None:
            tblw = OxmlElement('w:tblW'); tblpr.append(tblw)
        tblw.set(qn('w:w'), str(int(ANCHO_UTIL_CM * 567))); tblw.set(qn('w:type'), 'dxa')
        lay = OxmlElement('w:tblLayout'); lay.set(qn('w:type'), 'fixed'); tblpr.append(lay)
        grid = t._tbl.tblGrid
        for j, gc in enumerate(grid.findall(qn('w:gridCol'))):
            gc.set(qn('w:w'), str(int(anchos_cm[j] * 567)))
        for row in t.rows:
            for j, w in enumerate(anchos_cm):
                row.cells[j].width = Cm(w)
        self._nota(nota)
        return self.n_tab

    def referencia(self, texto: str):
        return self.parrafo(texto, modelo='ref')

    def salto_pagina(self):
        el = self._nuevo('cuerpo')
        r = OxmlElement('w:r'); br = OxmlElement('w:br'); br.set(qn('w:type'), 'page'); r.append(br); el.append(r)


def vaciar_cuerpo(doc):
    """Elimina del cuerpo todo lo que va de «1. Introducción» al Anexo de información académica.

    Devuelve el elemento anterior al cuerpo, el título del anexo académico y una copia
    de la tabla de enlaces de video de la plantilla, que se vuelve a insertar en Anexos.
    """
    inicio = _buscar(doc, '1. Introducción', 'Heading 1')._p
    fin = _buscar(doc, 'Anexo de información académica', 'Heading 1')._p
    previo = inicio.getprevious()
    videos = None
    el = inicio
    while el is not None and el is not fin:
        sig = el.getnext()
        if el.tag == qn('w:tbl') and 'Video de presentación' in ''.join(t.text or '' for t in el.iter(qn('w:t'))):
            videos = copy.deepcopy(el)
        el.getparent().remove(el)
        el = sig
    return previo, fin, videos


def _poner_texto(p, texto: str) -> None:
    """Deja el párrafo con un solo run (el primero, con su formato) y el texto indicado."""
    runs = p.runs
    if not runs:
        p.add_run(texto)
        return
    runs[0].text = texto
    for r in runs[1:]:
        r._r.getparent().remove(r._r)


def actualizar_anexo_academico(doc, titulo_h: Paragraph, resumen: str, abstract: str, claves: str, keywords: str):
    """Numera el anexo académico (7.) y actualiza la ficha al enfoque académico del proyecto."""
    ppr = titulo_h._p.find(qn('w:pPr'))
    if ppr is not None and ppr.find(qn('w:numPr')) is not None:
        ppr.remove(ppr.find(qn('w:numPr')))
    _poner_texto(titulo_h, '7. Anexo de información académica')
    if ppr is not None and ppr.find(qn('w:pageBreakBefore')) is None:
        ppr.insert(1, OxmlElement('w:pageBreakBefore'))
    titulo = ('Prototipo de un sistema web para predecir el abandono en estudiantes universitarios mediante '
              'aprendizaje automático y consulta conversacional')
    cambios = {
        'Desarrollo de Aplicaciones Web, Ingeniería de Software, Bases de Datos':
            'Desarrollo de Aplicaciones Web, Inteligencia Artificial, Minería de Datos, Bases de Datos',
        'Procesamiento de lenguaje natural, aprendizaje automático, inteligencia de negoc':
            f'{claves} / {keywords}',
        'Se desarrolló un prototipo de sistema de inteligencia': resumen,
        'A business intelligence prototype': abstract,
        'Inteligencia Artificial, Minería de datos, Software':
            'Inteligencia Artificial, Minería de Datos, Ingeniería de Software',
        'Desarrollo de un modelo predictivo de abandono': titulo,
        'Bases de Datos; Inteligencia Artificial;':
            'Bases de Datos; Inteligencia Artificial; Minería de Datos; Ingeniería de Software; Desarrollo de '
            'Aplicaciones Web; Seguridad de la Información.',
        'Integra, bajo una misma arquitectura':
            'Integra, bajo una arquitectura gobernada, un modelo de abandono calibrado y explicable (LightGBM con '
            'Platt y SHAP), validado en el tiempo y de forma prospectiva, una segmentación de carreras con K-means, '
            'una consulta conversacional que responde primero con métricas certificadas y valida el SQL generado, y '
            'un panel por roles; todo lee las mismas vistas, con aislamiento por institución aplicado en SQL Server y '
            'controles de la LOPDP.',
        'Sustenta el diseño del esquema estrella':
            'Sustenta el diseño del esquema estrella (Kimball) del almacén ALMACEN_ACADEMICO en SQL Server: hechos de '
            'matrículas, predicciones, segmentos e intervenciones, con vistas gobernadas por institución.',
        'Aporta el marco para el entrenamiento':
            'Aporta el marco para entrenar, calibrar y explicar los modelos de predicción (regresión logística, '
            'Random Forest y LightGBM) y la segmentación con K-means, evaluados con ROC-AUC, PR-AUC, recall y '
            'calibración.',
        'Fundamenta la arquitectura del prototipo':
            'Fundamenta la arquitectura cliente-servidor del prototipo: una API FastAPI en capas, una interfaz React y '
            'la consulta conversacional NL2SQL, con pruebas automatizadas.',
        'El presente trabajo de titulación incluye como producto final':
            'El presente trabajo de titulación incluye como producto final VicMar, un prototipo funcional de sistema '
            'web compuesto por un almacén de datos en SQL Server, procesos de ETL, entrenamiento y calificación en '
            'Python, una API FastAPI con consulta conversacional NL2SQL y una interfaz web en React, con pruebas '
            'automatizadas y scripts de instalación.',
    }
    for tabla in doc.tables:
        for tc in tabla._tbl.iter(qn('w:tc')):
            for p_el in tc.findall(qn('w:p')):
                p = Paragraph(p_el, tabla._parent)
                if True:
                    for inicio, texto in cambios.items():
                        if p.text.strip().startswith(inicio):
                            _poner_texto(p, texto)
                            break


def actualizar_resumen(doc, resumen: str, claves: str, abstract: str, keywords: str):
    for marca, texto in (('Se desarrolló un prototipo', resumen), ('A business intelligence prototype', abstract)):
        p = _buscar(doc, marca)
        runs = p.runs
        runs[0].text = texto
        for r in runs[1:]:
            r._r.getparent().remove(r._r)
    for marca, etiqueta, texto in (('Palabras clave', 'Palabras clave: ', claves), ('Keywords', 'Keywords: ', keywords)):
        p = _buscar(doc, marca)
        runs = p.runs
        runs[0].text = etiqueta
        if len(runs) > 1:
            runs[1].text = texto
            for r in runs[2:]:
                r._r.getparent().remove(r._r)
        else:
            p.add_run(texto)


def _jc(ppr, valor: str) -> None:
    e = ppr.find(qn('w:jc'))
    if e is None:
        e = OxmlElement('w:jc'); ppr.append(e)
    e.set(qn('w:val'), valor)


# Actividades del trabajo para la tabla de la Declaración de autoría (mínimo 5 actividades y al
# menos 4 interacciones con docentes). Las fechas salen del historial del repositorio; lo que solo
# conocen los autores queda entre corchetes para completarlo.
ACTIVIDADES_AUTORIA = [
    ('07/09/2026 al 09/09/2026',
     'Consolidación del repositorio del proyecto y primera versión del prototipo',
     'Código fuente versionado en GitHub con el historial de ambos autores',
     'Repositorio GitHub del proyecto (cuenta Vm199524)'),
    ('[completar fecha]',
     'Búsqueda y selección sistemática de la literatura en Scopus (cinco búsquedas, cribado y lectura completa)',
     'Referencias en formato RIS y tabla comparativa de 14 trabajos previos',
     'Carpeta documentacion/literatura del repositorio'),
    ('[completar fecha]',
     'Entrega del Avance 1: introducción, propósito, delimitación y base conceptual',
     'Documento del Avance 1 y presentación de dos minutos entregados',
     'Carpetas documentacion/avances y documentacion/presentaciones/avance1'),
    ('[completar fecha]',
     'Tutoría 1 con las tutoras: revisión del Avance 1',
     'Observaciones: numeración de Referencias y Anexos, comparación de 10 estudios, RF y RNF por pieza, '
     'historias de usuario, protección de datos, métricas, CRISP-DM, esquema estrella, UML y demo',
     '[completar enlace de la evidencia]'),
    ('03/10/2026 al 05/10/2026',
     'Reorganización del repositorio por capas, integración continua, decisiones técnicas (ADR) y manuales',
     'Repositorio ordenado, seis decisiones con matriz ponderada y manuales de usuario, instalación y pruebas',
     'Carpetas documentacion/decisiones y documentacion/manuales'),
    ('[completar fecha]',
     'Tutoría 2 con las tutoras: revisión de los requerimientos y del enfoque académico del sistema',
     'Ajuste del enfoque hacia la alerta temprana del abandono estudiantil y de los requerimientos por rol',
     '[completar enlace de la evidencia]'),
    ('07/10/2026',
     'Versión 3 del sistema: almacén en esquema estrella, modelo calibrado, consulta conversacional y '
     'aplicación web por rol',
     'Validación con UNEMI_PRUEBAS y OULAD; 153 pruebas automáticas del backend y 11 de la interfaz superadas',
     'Carpeta codigo_fuente y capturas en documentacion/capturas'),
    ('[completar fecha]',
     'Tutoría 3 con las tutoras: revisión del prototipo en funcionamiento',
     'Demostración de la predicción, la ficha explicada, el seguimiento y la consulta en lenguaje natural',
     '[completar enlace de la evidencia]'),
    ('07/10/2026 al 08/10/2026',
     'Entrega del Avance 2: análisis del caso, metodología y diseño',
     'Documento con requerimientos, fases de CRISP-DM, diagramas UML y modelo de datos',
     'Carpeta documentacion/avances y Anexo C (videos)'),
]


def llenar_autoria(doc, base_run):
    """Llena la tabla de actividades de la Declaración de autoría con el formato de la tabla.

    Se conserva la fila de encabezados y una fila vacía de la plantilla sirve de molde para
    cada actividad (bordes, anchos y márgenes iguales)."""
    tabla = next((t for t in doc.tables
                  if 'Actividades' in ' '.join(c.text for c in t.rows[0].cells) and 'Fecha' in t.rows[0].cells[0].text),
                 None)
    if tabla is None:
        return
    filas = tabla.rows
    molde = copy.deepcopy(filas[-1]._tr)
    for f in list(filas)[1:]:
        tabla._tbl.remove(f._tr)
    trpr = filas[0]._tr.get_or_add_trPr()
    if trpr.find(qn('w:tblHeader')) is None:
        trpr.append(OxmlElement('w:tblHeader'))      # el encabezado se repite si la tabla pasa de página
    for actividad in ACTIVIDADES_AUTORIA:
        tr = copy.deepcopy(molde)
        tabla._tbl.append(tr)
        trpr = tr.find(qn('w:trPr'))
        if trpr is None:
            trpr = OxmlElement('w:trPr'); tr.insert(1 if tr.find(qn('w:tblPrEx')) is not None else 0, trpr)
        if trpr.find(qn('w:cantSplit')) is None:
            trpr.append(OxmlElement('w:cantSplit'))     # una actividad nunca se parte entre páginas
        for tc, texto in zip(tr.iter(qn('w:tc')), actividad):
            ps = tc.findall(qn('w:p'))
            for extra in ps[1:]:
                tc.remove(extra)
            p = ps[0]
            for r in p.findall(qn('w:r')):
                p.remove(r)
            ppr = p.find(qn('w:pPr'))
            if ppr is None:
                ppr = OxmlElement('w:pPr'); p.insert(0, ppr)
            for tag in ('w:spacing', 'w:ind', 'w:jc'):
                e = ppr.find(qn(tag))
                if e is not None:
                    ppr.remove(e)
            sp = OxmlElement('w:spacing'); sp.set(qn('w:before'), '20'); sp.set(qn('w:after'), '20')
            sp.set(qn('w:line'), '240'); sp.set(qn('w:lineRule'), 'auto'); ppr.append(sp)
            ind = OxmlElement('w:ind'); ind.set(qn('w:left'), '0'); ind.set(qn('w:firstLine'), '0'); ppr.append(ind)
            _jc(ppr, 'left')
            p.append(_run(base_run, texto, negrita=False, cursiva=False, tam=10))


def justificar_indices(doc):
    """Índices de figuras y de tablas justificados (estilo «table of figures» y entradas ya calculadas).

    Las entradas largas ocupan dos líneas: la segunda queda alineada al margen izquierdo, con el
    número de página a la derecha tras la línea de puntos."""
    for s in doc.styles.element.findall(qn('w:style')):
        nombre = s.find(qn('w:name'))
        if nombre is None or nombre.get(qn('w:val')) != 'table of figures':
            continue
        ppr = s.find(qn('w:pPr'))
        if ppr is None:
            ppr = OxmlElement('w:pPr'); s.append(ppr)
        _jc(ppr, 'both')
        _tab_indice(ppr)
    for p in doc.paragraphs:
        if p.style is not None and p.style.name == 'table of figures':
            ppr = p._p.get_or_add_pPr()
            _jc(ppr, 'both')
            _tab_indice(ppr)


def _tab_indice(ppr) -> None:
    """Tabulación derecha con puntos en el margen derecho, para el número de página."""
    tabs = ppr.find(qn('w:tabs'))
    if tabs is not None:
        ppr.remove(tabs)
    tabs = OxmlElement('w:tabs')
    tab = OxmlElement('w:tab'); tab.set(qn('w:val'), 'right'); tab.set(qn('w:leader'), 'dot')
    tab.set(qn('w:pos'), str(int(ANCHO_UTIL_CM * 567) - 10)); tabs.append(tab)
    estilo = ppr.find(qn('w:pStyle'))
    if estilo is not None:
        estilo.addnext(tabs)
    else:
        ppr.insert(0, tabs)


def indices_a_figura(doc):
    """El índice de ilustraciones pasa a «Figura» (rótulo APA) y Word recalcula los índices al abrir."""
    body = doc.element.body
    for it in body.iter(qn('w:instrText')):
        if 'TOC' in (it.text or '') and 'Ilustración' in it.text:
            it.text = it.text.replace('Ilustración', 'Figura')
    for p in doc.paragraphs:
        if p.text.strip().upper().startswith('INDICE DE FIGURAS'):
            for r in p.runs:
                r.text = r.text.replace('INDICE', 'ÍNDICE')
        if p.text.strip().upper().startswith('INDICE DE TABLAS'):
            for r in p.runs:
                r.text = r.text.replace('INDICE', 'ÍNDICE')
    justificar_indices(doc)
    ajustes = doc.settings.element
    if ajustes.find(qn('w:updateFields')) is None:
        u = OxmlElement('w:updateFields'); u.set(qn('w:val'), 'true'); ajustes.append(u)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--salida', required=True)
    a = ap.parse_args()
    salida = Path(a.salida)
    shutil.copyfile(a.base, salida)
    doc = docx.Document(str(salida))
    c = Constructor(doc)
    c.tomar_modelos()
    res, cla, abs_, key = resumen_abstract()
    actualizar_resumen(doc, res, cla, abs_, key)
    previo, fin, videos = vaciar_cuerpo(doc)
    actualizar_anexo_academico(doc, Paragraph(fin, doc._body), res, abs_, cla, key)
    llenar_autoria(doc, _run_base(c.modelos['cuerpo']))
    c.ancla = previo
    for b in bloques():
        tipo = b[0]
        if tipo in ('h1', 'h2', 'h3'):
            c.titulo(int(tipo[1]), b[1])
        elif tipo == 'p':
            c.parrafo(b[1])
        elif tipo == 'ul':
            c.vinetas(b[1])
        elif tipo == 'fig':
            c.figura(*b[1:])
        elif tipo == 'tab':
            c.tabla(*b[1:])
        elif tipo == 'ref':
            c.referencia(b[1])
        elif tipo == 'salto':
            c.salto_pagina()
        elif tipo == 'videos' and videos is not None:
            c.ancla.addnext(videos)
            c.ancla = videos
    indices_a_figura(doc)
    doc.save(str(salida))
    print(f'{salida}: {c.n_fig} figuras, {c.n_tab} tablas')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

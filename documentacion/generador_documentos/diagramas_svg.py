# -*- coding: utf-8 -*-
"""
Diagramas UML del Avance 2 dibujados en SVG a 16 cm de ancho y 10 pt reales.

PlantUML obliga a reducir los diagramas largos para que quepan en la página y
su texto termina por debajo de 7 pt. Aquí cada diagrama se compone sobre una
rejilla (filas y columnas) con la notación UML habitual: nodo inicial y final,
acciones redondeadas, decisiones en rombo, barras de bifurcación, carriles,
estados y casos de uso. El HTML queda en documentacion/diagramas/fuentes/html/
y se convierte a PNG con el mismo renderizador de las demás figuras.

Uso:
    python documentacion/generador_documentos/diagramas_svg.py <renderizador html_png.py>

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import html
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA_HTML = RAIZ / 'documentacion' / 'diagramas' / 'fuentes' / 'html'
SALIDA_PNG = RAIZ / 'documentacion' / 'diagramas'

ANCHO = 604          # 16 cm en píxeles CSS
PT10 = 13.33         # 10 pt en píxeles CSS
LINEA = 15.5         # interlineado
AZUL, AZUL_CLARO, PETROLEO, NARANJA, NARANJA_CLARO, GRIS = '#0B5C7E', '#EBF5FA', '#002E45', '#E86100', '#FFF4EA', '#64748B'


def _t(x: float, y: float, texto: str, ancla: str = 'middle', peso: str = 'normal', color: str = PETROLEO,
       cursiva: bool = False, tam: float = PT10) -> str:
    lineas = texto.split('\n')
    y0 = y - (len(lineas) - 1) * LINEA / 2
    estilo = 'font-style:italic;' if cursiva else ''
    partes = [f'<tspan x="{x:.1f}" y="{y0 + i * LINEA:.1f}">{html.escape(l)}</tspan>' for i, l in enumerate(lineas)]
    return (f'<text text-anchor="{ancla}" dominant-baseline="central" font-weight="{peso}" fill="{color}" '
            f'style="{estilo}font-size:{tam}px">{"".join(partes)}</text>')


def _alto_texto(texto: str) -> float:
    return len(texto.split('\n')) * LINEA


def _flecha(puntos: list[tuple[float, float]], etiqueta: str = '', discontinua: bool = False,
            pos_etiqueta: int = 0, lado: str = 'start') -> str:
    d = ' '.join(f'{"M" if i == 0 else "L"}{x:.1f},{y:.1f}' for i, (x, y) in enumerate(puntos))
    trazo = ' stroke-dasharray="5,4"' if discontinua else ''
    s = f'<path d="{d}" fill="none" stroke="{AZUL}" stroke-width="1.3"{trazo} marker-end="url(#punta)"/>'
    if etiqueta:
        (x1, y1), (x2, y2) = puntos[pos_etiqueta], puntos[pos_etiqueta + 1]
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        if abs(x2 - x1) < 1:  # tramo vertical
            s += _t(mx + 5, my, etiqueta, 'start', color=AZUL)
        else:
            s += _t(mx, my - 9, etiqueta, 'middle', color=AZUL)
    return s


DEFS = (f'<defs><marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{AZUL}"/></marker></defs>')


def _pagina(nombre: str, alto: float, cuerpo: str) -> Path:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{ANCHO}" height="{alto:.0f}" '
           f'viewBox="0 0 {ANCHO} {alto:.0f}" font-family="Arial, Helvetica, sans-serif">{DEFS}{cuerpo}</svg>')
    doc = ('<!doctype html><html lang="es"><head><meta charset="utf-8"><style>'
           '*{margin:0;padding:0;box-sizing:border-box}body{width:16cm;background:#fff;padding:0}'
           f'</style></head><body>{svg}</body></html>')
    SALIDA_HTML.mkdir(parents=True, exist_ok=True)
    ruta = SALIDA_HTML / f'{nombre}.html'
    ruta.write_text(doc, encoding='utf-8')
    return ruta


# ── Diagramas de actividades sobre rejilla ────────────────────────────────
@dataclass
class Nodo:
    id: str
    tipo: str            # ini, fin, act, dec, barra, nota
    texto: str = ''
    col: float = 0       # columna (puede ser fraccionaria)
    ancho: float = 170
    fila: int = 0
    x: float = 0
    y: float = 0
    alto: float = 0


@dataclass
class Actividad:
    columnas: list[float]                       # centro x de cada columna
    nodos: list[Nodo] = field(default_factory=list)
    aristas: list[tuple] = field(default_factory=list)
    carriles: list[tuple[str, float, float]] = field(default_factory=list)  # (nombre, x0, x1)
    sep: float = 18
    margen_sup: float = 6

    def n(self, id_, tipo, texto='', col=0, fila=None, ancho=170, x=None):
        fila = (max((q.fila for q in self.nodos), default=-1) + 1) if fila is None else fila
        nd = Nodo(id_, tipo, texto, col, ancho, fila)
        nd.x_fija = x
        self.nodos.append(nd)
        return id_

    def e(self, a, b, etiqueta='', via=None, salida='abajo', llegada='arriba', discontinua=False):
        self.aristas.append((a, b, etiqueta, via, salida, llegada, discontinua))

    def _medidas(self, nd: Nodo):
        if nd.tipo == 'ini':
            return 18
        if nd.tipo == 'fin':
            return 20
        if nd.tipo == 'barra':
            return 7
        if nd.tipo == 'con':
            return 24
        if nd.tipo == 'dec':
            return _alto_texto(nd.texto) + 18
        return _alto_texto(nd.texto) + 14

    def construir(self, nombre: str) -> Path:
        filas = sorted({nd.fila for nd in self.nodos})
        y = self.margen_sup + (26 if self.carriles else 0)
        altos = {}
        for f_ in filas:
            del_fila = [nd for nd in self.nodos if nd.fila == f_]
            h = max(self._medidas(nd) for nd in del_fila)
            for nd in del_fila:
                nd.alto = self._medidas(nd)
                nd.y = y + h / 2
                c = nd.col
                ci = int(c)
                nd.x = self.columnas[ci] + (c - ci) * ((self.columnas[ci + 1] - self.columnas[ci]) if ci + 1 < len(self.columnas) else 0)
                if getattr(nd, 'x_fija', None) is not None:
                    nd.x = nd.x_fija
            altos[f_] = h
            y += h + self.sep
        alto_total = y - self.sep + 8
        idx = {nd.id: nd for nd in self.nodos}
        out = []
        for nombre_c, x0, x1 in self.carriles:
            out.append(f'<rect x="{x0}" y="2" width="{x1 - x0}" height="{alto_total - 4:.0f}" fill="#F8FAFC" '
                       f'stroke="#94A8BA" stroke-width="1"/>')
            out.append(f'<rect x="{x0}" y="2" width="{x1 - x0}" height="24" fill="{PETROLEO}"/>')
            out.append(_t((x0 + x1) / 2, 14, nombre_c, peso='bold', color='#FFFFFF'))

        def ancla(nd: Nodo, lado: str):
            if nd.tipo == 'dec':
                w = nd.ancho / 2
                return {'abajo': (nd.x, nd.y + nd.alto / 2), 'arriba': (nd.x, nd.y - nd.alto / 2),
                        'der': (nd.x + w, nd.y), 'izq': (nd.x - w, nd.y)}[lado]
            w = (nd.ancho if nd.tipo in ('act', 'barra', 'nota') else nd.alto) / 2
            return {'abajo': (nd.x, nd.y + nd.alto / 2), 'arriba': (nd.x, nd.y - nd.alto / 2),
                    'der': (nd.x + w, nd.y), 'izq': (nd.x - w, nd.y)}[lado]

        for a, b, etq, via, salida, llegada, disc in self.aristas:
            na, nb = idx[a], idx[b]
            p0, p1 = ancla(na, salida), ancla(nb, llegada)
            if via == 'directo' or (via is None and abs(p0[0] - p1[0]) < 1):
                pts = [p0, p1]
            elif via == 'h':          # sale horizontal y baja
                pts = [p0, (p1[0], p0[1]), p1]
            elif via == 'v':          # baja y luego horizontal
                pts = [p0, (p0[0], p1[1]), p1]
            elif isinstance(via, (int, float)):   # rodeo por la x indicada
                pts = [p0, (via, p0[1]), (via, p1[1]), p1] if salida in ('der', 'izq') else \
                      [p0, (p0[0], p0[1] + 8), (via, p0[1] + 8), (via, p1[1] - 10), (p1[0], p1[1] - 10), p1]
            else:                     # baja hasta la mitad y cruza
                ym = p1[1] - self.sep / 2 - 2
                pts = [p0, (p0[0], ym), (p1[0], ym), p1]
            out.append(_flecha(pts, etq, disc, pos_etiqueta=0 if len(pts) == 2 else (1 if via == 'h' else 0)))

        for nd in self.nodos:
            if nd.tipo == 'ini':
                out.append(f'<circle cx="{nd.x}" cy="{nd.y}" r="8" fill="{PETROLEO}"/>')
            elif nd.tipo == 'fin':
                out.append(f'<circle cx="{nd.x}" cy="{nd.y}" r="9.5" fill="#fff" stroke="{PETROLEO}" stroke-width="1.5"/>'
                           f'<circle cx="{nd.x}" cy="{nd.y}" r="5.5" fill="{PETROLEO}"/>')
            elif nd.tipo == 'con':
                out.append(f'<circle cx="{nd.x}" cy="{nd.y}" r="11" fill="#fff" stroke="{PETROLEO}" stroke-width="1.4"/>')
                out.append(_t(nd.x, nd.y, nd.texto, peso='bold'))
            elif nd.tipo == 'barra':
                out.append(f'<rect x="{nd.x - nd.ancho / 2}" y="{nd.y - 3}" width="{nd.ancho}" height="6" rx="2" '
                           f'fill="{PETROLEO}"/>')
            elif nd.tipo == 'dec':
                w, h = nd.ancho / 2, nd.alto / 2
                pts = f'{nd.x - w},{nd.y} {nd.x - w + 12},{nd.y - h} {nd.x + w - 12},{nd.y - h} {nd.x + w},{nd.y} ' \
                      f'{nd.x + w - 12},{nd.y + h} {nd.x - w + 12},{nd.y + h}'
                out.append(f'<polygon points="{pts}" fill="{NARANJA_CLARO}" stroke="{NARANJA}" stroke-width="1.3"/>')
                out.append(_t(nd.x, nd.y, nd.texto))
            elif nd.tipo == 'nota':
                out.append(f'<rect x="{nd.x - nd.ancho / 2}" y="{nd.y - nd.alto / 2}" width="{nd.ancho}" '
                           f'height="{nd.alto}" fill="{NARANJA_CLARO}" stroke="{NARANJA}" stroke-dasharray="4,3"/>')
                out.append(_t(nd.x, nd.y, nd.texto))
            else:
                out.append(f'<rect x="{nd.x - nd.ancho / 2}" y="{nd.y - nd.alto / 2}" width="{nd.ancho}" '
                           f'height="{nd.alto}" rx="10" fill="{AZUL_CLARO}" stroke="{AZUL}" stroke-width="1.3"/>')
                out.append(_t(nd.x, nd.y, nd.texto))
        return _pagina(nombre, alto_total, ''.join(out))


def actividad_etl() -> Path:
    """Actividades del ETL por perfil (etl/cargar.py), en dos columnas unidas por el conector A."""
    d = Actividad(columnas=[215, 45, 468])
    n, e = d.n, d.e
    n('i', 'ini', col=0, fila=0)
    n('a1', 'act', 'Leer el perfil de la institución\n(etl/perfiles.py)', col=0, fila=1, ancho=232)
    n('a2', 'act', 'Ejecutar el SELECT del perfil\nsobre la base de origen', col=0, fila=2, ancho=232)
    n('a3', 'act', 'Validar columnas obligatorias\ny detectar las opcionales', col=0, fila=3, ancho=232)
    n('a4', 'act', 'Aplicar reglas de calidad:\nestados, modalidades y rangos', col=0, fila=4, ancho=232)
    n('d1', 'dec', '¿Contrato y\ncalidad válidos?', col=0, fila=5, ancho=176)
    n('a5', 'act', 'MERGE de dim_institucion', col=0, fila=6, ancho=232)
    n('a6', 'act', 'Borrar los hechos de esa\ninstitución (sin tocar otras)', col=0, fila=7, ancho=232)
    n('ca', 'con', 'A', col=0, fila=8)
    n('x1', 'act', 'Informar\ny detener', col=1, fila=5, ancho=78)
    n('f1', 'fin', col=1, fila=6)
    n('cb', 'con', 'A', col=2, fila=0)
    n('b0', 'barra', col=2, fila=1, ancho=250)
    n('b1', 'act', 'Periodos', col=2, fila=2, ancho=74, x=383)
    n('b2', 'act', 'Sedes y\ncarreras', col=2, fila=2, ancho=74)
    n('b3', 'act', 'Fechas', col=2, fila=2, ancho=74, x=553)
    n('b4', 'barra', col=2, fila=3, ancho=250)
    n('c1', 'act', 'MERGE de dim_alumno desde\ntabla temporal', col=2, fila=4, ancho=232)
    n('c2', 'act', 'Resolver claves sustitutas', col=2, fila=5, ancho=232)
    n('c3', 'act', 'Insertar fact_matriculas por\nlotes de 20.000 filas', col=2, fila=6, ancho=232)
    n('c4', 'act', 'Registrar filas y duración en\npipeline_estado.json', col=2, fila=7, ancho=232)
    n('f3', 'fin', col=2, fila=8)
    for a, b in (('i', 'a1'), ('a1', 'a2'), ('a2', 'a3'), ('a3', 'a4'), ('a4', 'd1'), ('a5', 'a6'), ('a6', 'ca'),
                 ('x1', 'f1'), ('cb', 'b0'), ('b4', 'c1'), ('c1', 'c2'), ('c2', 'c3'), ('c3', 'c4'), ('c4', 'f3')):
        e(a, b)
    e('d1', 'a5', 'sí')
    e('d1', 'x1', 'no', via='directo', salida='izq', llegada='der')
    for x in ('b1', 'b2', 'b3'):
        d.aristas.append(('b0', x, '', 'recto_barra', 'abajo', 'arriba', False))
        d.aristas.append((x, 'b4', '', 'recto_barra2', 'abajo', 'arriba', False))
    return _construir_con_barras(d, 'av2_actividad_etl')


def _construir_con_barras(d: Actividad, nombre: str) -> Path:
    """Las flechas desde/hacia una barra salen en vertical a la altura del nodo lateral."""
    reales = []
    for a in d.aristas:
        if a[3] in ('recto_barra', 'recto_barra2'):
            reales.append(a)
    d.aristas = [a for a in d.aristas if a[3] not in ('recto_barra', 'recto_barra2')]
    ruta = d.construir(nombre)
    if not reales:
        return ruta
    idx = {nd.id: nd for nd in d.nodos}
    extra = []
    for a, b, *_ in reales:
        na, nb = idx[a], idx[b]
        if na.tipo == 'barra':
            x = nb.x
            extra.append(_flecha([(x, na.y + 3), (x, nb.y - nb.alto / 2)]))
        else:
            x = na.x
            extra.append(_flecha([(x, na.y + na.alto / 2), (x, nb.y - 3)]))
    texto = ruta.read_text(encoding='utf-8').replace('</svg>', ''.join(extra) + '</svg>')
    ruta.write_text(texto, encoding='utf-8')
    return ruta


def actividad_modelo() -> Path:
    """Entrenamiento, validación y calificación (ml/entrenar.py, ml/calificar.py)."""
    d = Actividad(columnas=[150, 448])
    n, e = d.n, d.e
    n('i', 'ini', col=0, fila=0)
    n('a1', 'act', 'Leer la trayectoria\nde la institución', col=0, fila=1, ancho=250)
    n('a2', 'act', 'Construir el panel estudiante-periodo\n(etiqueta: abandono en t+1)', col=0, fila=2, ancho=262)
    n('a3', 'act', 'Detectar grupos opcionales: cartera,\nmatrícula, aula y evaluaciones', col=0, fila=3, ancho=262)
    n('a4', 'act', 'Reservar los periodos recientes\ncomo prueba temporal (≥ 25 %)', col=0, fila=4, ancho=250)
    n('b0', 'barra', col=0, fila=5, ancho=280)
    for i, (k, t) in enumerate((('m1', 'RF con\npesos'), ('m2', 'RF con\nSMOTE'), ('m3', 'Logística'),
                                ('m4', 'LightGBM\nOptuna'))):
        n(k, 'act', t, col=0, fila=6, ancho=66, x=37 + i * 75.5)
    n('b1', 'barra', col=0, fila=7, ancho=280)
    n('a5', 'act', 'Validación cruzada de 5 pliegues\nagrupada por estudiante', col=0, fila=8, ancho=250)
    n('a6', 'act', 'Elegir el mayor ROC-AUC medio\n(desempate por PR-AUC)', col=0, fila=9, ancho=250)
    n('ca', 'con', 'A', col=0, fila=10)
    n('cb', 'con', 'A', col=1, fila=0)
    n('c1', 'act', 'Calibrar con Platt sobre las\npredicciones fuera de pliegue', col=1, fila=1, ancho=250)
    n('c2', 'act', 'Umbrales: medio (recall 0,80)\ny alto (recall 0,50)', col=1, fila=2, ancho=250)
    n('c3', 'act', 'Evaluar en la prueba temporal:\nROC-AUC, PR-AUC, Brier, equidad', col=1, fila=3, ancho=250)
    n('d1', 'dec', '¿Hay periodo en curso\ncon desenlace real?', col=1, fila=4, ancho=214)
    n('c4', 'act', 'Evaluación prospectiva', col=1, fila=5, ancho=200)
    n('c5', 'act', 'Guardar el paquete .joblib\ny metricas.json', col=1, fila=6, ancho=250)
    n('c6', 'act', 'Calificar a los activos, explicar\ncon SHAP y medir deriva (PSI)', col=1, fila=7, ancho=250)
    n('c7', 'act', 'Segmentar carreras con\nK-means validado', col=1, fila=8, ancho=250)
    n('f', 'fin', col=1, fila=9)
    for a, b in (('i', 'a1'), ('a1', 'a2'), ('a2', 'a3'), ('a3', 'a4'), ('a4', 'b0'), ('b1', 'a5'), ('a5', 'a6'),
                 ('a6', 'ca'), ('cb', 'c1'), ('c1', 'c2'), ('c2', 'c3'), ('c3', 'd1'), ('c4', 'c5'), ('c5', 'c6'),
                 ('c6', 'c7'), ('c7', 'f')):
        e(a, b)
    e('d1', 'c4', 'sí')
    e('d1', 'c5', 'no', via=588, salida='der', llegada='der')
    for x in ('m1', 'm2', 'm3', 'm4'):
        d.aristas.append(('b0', x, '', 'recto_barra', 'abajo', 'arriba', False))
        d.aristas.append((x, 'b1', '', 'recto_barra2', 'abajo', 'arriba', False))
    return _construir_con_barras(d, 'av2_actividad_modelo')


def flujo_trabajo() -> Path:
    """Flujo de trabajo con carriles: de los datos a la decisión de acompañamiento."""
    xs = [62, 182, 302, 422, 543]
    carr = [('Académico', 2, 122), ('TI', 122, 242), ('VicMar', 242, 362), ('Autoridad', 362, 482),
            ('Bienestar', 482, 602)]
    d = Actividad(columnas=xs, carriles=carr, sep=14)
    n, e = d.n, d.e
    n('i', 'ini', col=0, fila=0)
    n('a1', 'act', 'Cierre del\nperiodo', col=0, fila=1, ancho=108)
    n('a2', 'act', 'Ejecutar el\nproceso por lotes', col=1, fila=2, ancho=112)
    n('a3', 'act', 'Calificar, explicar\ny segmentar', col=2, fila=3, ancho=114)
    n('b0', 'barra', col=3.5, fila=4, ancho=220)
    n('a4', 'act', 'Revisar panel\ny carreras', col=3, fila=5, ancho=108)
    n('a5', 'act', 'Preguntar en\nlenguaje natural', col=3, fila=6, ancho=112)
    n('a6', 'act', 'Asignar\nrecursos', col=3, fila=7, ancho=108)
    n('a7', 'act', 'Abrir la lista\npriorizada', col=4, fila=5, ancho=108)
    n('a8', 'act', 'Revisar la ficha\ny simular', col=4, fila=6, ancho=112)
    n('d1', 'dec', '¿Requiere\napoyo?', col=4, fila=7, ancho=106)
    n('a9', 'act', 'Registrar la\nintervención', col=4, fila=8, ancho=108)
    n('b1', 'barra', col=3.5, fila=9, ancho=220)
    n('a10', 'act', 'Monitorear y\nreentrenar', col=2, fila=10, ancho=108)
    n('f', 'fin', col=2, fila=11)
    e('i', 'a1')
    for a, b in (('a1', 'a2'), ('a2', 'a3'), ('a4', 'a5'), ('a5', 'a6'), ('a7', 'a8'), ('a8', 'd1')):
        e(a, b)
    e('a3', 'b0')
    e('d1', 'a9', 'sí')
    e('d1', 'b1', 'no', via=596, salida='der', llegada='der')
    e('b1', 'a10')
    e('a10', 'f')
    for x in ('a4', 'a7'):
        d.aristas.append(('b0', x, '', 'recto_barra', 'abajo', 'arriba', False))
    for x in ('a6', 'a9'):
        d.aristas.append((x, 'b1', '', 'recto_barra2', 'abajo', 'arriba', False))
    return _construir_con_barras(d, 'av2_flujo_trabajo')


# ── Diagrama de estados ───────────────────────────────────────────────────
def _estado(x, y, w, h, titulo, detalle='', inicial=False):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{AZUL_CLARO}" stroke="{AZUL}" stroke-width="1.3"/>'
    if detalle:
        s += _t(x + w / 2, y + 12, titulo, peso='bold')
        s += f'<line x1="{x}" y1="{y + 23}" x2="{x + w}" y2="{y + 23}" stroke="{AZUL}" stroke-width="0.8"/>'
        s += _t(x + w / 2, y + 23 + (h - 23) / 2, detalle, color='#334155')
    else:
        s += _t(x + w / 2, y + h / 2, titulo, peso='bold')
    return s


def estados() -> Path:
    o = []
    o.append(f'<rect x="2" y="2" width="600" height="398" rx="10" fill="#F8FAFC" stroke="#94A8BA"/>')
    o.append(_t(14, 16, 'Alerta de un estudiante activo', 'start', 'bold'))
    o.append(f'<circle cx="300" cy="40" r="8" fill="{PETROLEO}"/>')
    o.append(_estado(225, 62, 150, 46, 'Sin calificar', 'matrícula vigente'))
    o.append(_estado(30, 150, 140, 46, 'Bajo', 'p < umbral medio'))
    o.append(_estado(230, 150, 140, 46, 'Medio', 'medio ≤ p < alto'))
    o.append(_estado(430, 150, 140, 46, 'Alto', 'p ≥ umbral alto'))
    o.append(_estado(330, 262, 150, 46, 'En seguimiento', 'intervención abierta'))
    o.append(_estado(330, 342, 150, 46, 'Atendido', 'cerrada con resultado'))
    o.append(f'<circle cx="60" cy="300" r="9.5" fill="#fff" stroke="{PETROLEO}" stroke-width="1.5"/>'
             f'<circle cx="60" cy="300" r="5.5" fill="{PETROLEO}"/>')
    f = _flecha
    o.append(f([(300, 48), (300, 62)]))
    o.append(f([(250, 108), (100, 150)]) + _t(150, 122, 'calificación', color=AZUL))
    o.append(f([(300, 108), (300, 150)]))
    o.append(f([(350, 108), (500, 150)]))
    o.append(f([(170, 166), (230, 166)]) + f([(230, 182), (170, 182)]) + _t(200, 202, 'nueva calificación', color=AZUL))
    o.append(f([(370, 166), (430, 166)]) + f([(430, 182), (370, 182)]))
    o.append(f([(300, 196), (370, 262)]) + _t(300, 236, 'se registra\nuna intervención', 'end', color=AZUL))
    o.append(f([(500, 196), (450, 262)]))
    o.append(f([(405, 308), (405, 342)]) + _t(412, 325, 'se cierra', 'start', color=AZUL))
    o.append(f([(480, 365), (560, 365), (560, 196)]) + _t(554, 300, 'persiste\nel riesgo', 'end', color=AZUL))
    o.append(f([(330, 365), (140, 365), (140, 196)]) + _t(148, 300, 'la siguiente\ncalificación baja', 'start', color=AZUL))
    o.append(f([(60, 196), (60, 290)]) + _t(68, 245, 'gradúa\no egresa', 'start', color=AZUL))
    o.append(f'<circle cx="575" cy="80" r="9.5" fill="#fff" stroke="{PETROLEO}" stroke-width="1.5"/>'
             f'<circle cx="575" cy="80" r="5.5" fill="{PETROLEO}"/>')
    o.append(f([(545, 150), (570, 90)]) + _t(548, 104, 'abandona\n(retirado)', 'end', color=AZUL))
    y0 = 418
    o.append(f'<rect x="2" y="{y0}" width="600" height="112" rx="10" fill="#F8FAFC" stroke="#94A8BA"/>')
    o.append(_t(14, y0 + 14, 'Intervención (fact_intervencion)', 'start', 'bold'))
    o.append(f'<circle cx="60" cy="{y0 + 66}" r="8" fill="{PETROLEO}"/>')
    o.append(_estado(170, y0 + 44, 120, 44, 'ABIERTA'))
    o.append(_estado(400, y0 + 44, 120, 44, 'CERRADA'))
    o.append(f'<circle cx="565" cy="{y0 + 66}" r="9.5" fill="#fff" stroke="{PETROLEO}" stroke-width="1.5"/>'
             f'<circle cx="565" cy="{y0 + 66}" r="5.5" fill="{PETROLEO}"/>')
    o.append(f([(68, y0 + 66), (170, y0 + 66)]) + _t(119, y0 + 92, 'sp_registrar_\nintervencion', color=AZUL))
    o.append(f([(290, y0 + 66), (400, y0 + 66)]) + _t(345, y0 + 92, 'sp_cerrar_\nintervencion', color=AZUL))
    o.append(f([(520, y0 + 66), (555, y0 + 66)]))
    return _pagina('av2_estados', y0 + 116, ''.join(o))


# ── Casos de uso ──────────────────────────────────────────────────────────
def _actor(x, y, nombre, estereotipo=''):
    s = (f'<g stroke="{PETROLEO}" stroke-width="1.6" fill="none"><circle cx="{x}" cy="{y}" r="8"/>'
         f'<line x1="{x}" y1="{y + 8}" x2="{x}" y2="{y + 30}"/><line x1="{x - 13}" y1="{y + 16}" x2="{x + 13}" y2="{y + 16}"/>'
         f'<line x1="{x}" y1="{y + 30}" x2="{x - 11}" y2="{y + 46}"/><line x1="{x}" y1="{y + 30}" x2="{x + 11}" y2="{y + 46}"/></g>')
    s += _t(x, y + 62, nombre, peso='bold')
    if estereotipo:
        s += _t(x, y - 18, estereotipo, cursiva=True, color=GRIS)
    return s


def casos_uso() -> Path:
    o = []
    caja = (116, 6, 384, 640)
    o.append(f'<rect x="{caja[0]}" y="{caja[1]}" width="{caja[2]}" height="{caja[3]}" rx="10" fill="#F8FAFC" stroke="#94A8BA"/>')
    o.append(_t(caja[0] + caja[2] / 2, 20, 'VicMar · Sistema web de alerta temprana', peso='bold'))
    xa, xb, xc = 225, 410, 308
    ya = [112 + i * 58 for i in range(9)]
    ya0 = 54
    cus = {
        'CU1': ('CU-01 Ingresar y elegir\nla institución activa', xa, ya0),
        'CU9': ('CU-09 Revisar la calidad\ndel modelo', xa, ya[0]),
        'CU2': ('CU-02 Ver el panel\ninstitucional', xa, ya[1]),
        'CU3': ('CU-03 Consultar la lista\nde estudiantes en riesgo', xa, ya[2]),
        'CU4': ('CU-04 Ver la ficha y las\nrazones del riesgo', xa, ya[3]),
        'CU5': ('CU-05 Simular un\nescenario', xa, ya[4]),
        'CU6': ('CU-06 Registrar y cerrar\nuna intervención', xa, ya[5]),
        'CU7': ('CU-07 Preguntar en\nlenguaje natural', xa, ya[6]),
        'CU8': ('CU-08 Analizar carreras\ny referentes', xa, ya[7]),
        'CU10': ('CU-10 Descargar el\ninforme ejecutivo', xa, ya[8]),
        'CU11': ('CU-11 Administrar\ncuentas y roles', xb, 498),
        'CU12': ('CU-12 Revisar auditoría\ny estado', xb, 556),
        'CU13': ('CU-13 Ejecutar los\nprocesos por lotes', xb, 614),
    }
    rx, ry = 82, 23
    actores = {'AUT': (52, 170, 'Autoridad\nacadémica'), 'BIE': (52, 430, 'Bienestar\nestudiantil'),
               'ATI': (552, 560, 'Administración\nde TI'), 'IA': (552, 250, 'Proveedor\nde IA')}
    lineas = [('AUT', c) for c in ('CU1', 'CU2', 'CU3', 'CU4', 'CU7', 'CU8', 'CU9', 'CU10')] + \
             [('BIE', c) for c in ('CU1', 'CU3', 'CU5', 'CU6', 'CU7', 'CU10')] + \
             [('ATI', c) for c in ('CU1', 'CU9', 'CU11', 'CU12', 'CU13')]
    for a, c in lineas:
        ax, ay, _ = actores[a]
        cx, cy = cus[c][1], cus[c][2]
        izq = ax < 300
        ox, oy = ax + (15 if izq else -15), ay + 18
        tx = cx - rx if izq else cx + rx
        o.append(f'<line x1="{ox}" y1="{oy}" x2="{tx:.1f}" y2="{cy:.1f}" stroke="{AZUL}" stroke-width="1" opacity="0.8"/>')
    for k, (txt, cx, cy) in cus.items():
        o.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{AZUL_CLARO}" stroke="{AZUL}" stroke-width="1.3"/>')
        o.append(_t(cx, cy, txt))
    o.append(_flecha([(xa + 40, ya[4] - ry + 2), (xa + 40, ya[3] + ry - 1)], '', True))
    o.append(_flecha([(xa + rx, ya[5]), (xa + rx + 22, ya[5]), (xa + rx + 22, ya[3]), (xa + rx + 1, ya[3])], '', True))
    o.append(_t(xa + rx + 27, ya[4], '«extend»', 'start', color=AZUL))
    o.append(_flecha([(xa + rx, ya[6]), (530, 290)], '', True))
    o.append(_t(440, 425, 'solo si no hay\nmétrica certificada', color=AZUL))
    for k, (x, y, nom) in actores.items():
        o.append(_actor(x, y, nom, '«externo»' if k == 'IA' else ''))
    return _pagina('av2_casos_uso', 652, ''.join(o))


# ── Esquema estrella (modelo entidad-relación del almacén) ────────────────
def _entidad(x, y, w, titulo, filas, hecho=False):
    """Caja de entidad: encabezado y una fila por línea; devuelve (svg, alto)."""
    alto = 22 + len(filas) * LINEA + 8
    color = NARANJA if hecho else AZUL
    s = (f'<rect x="{x}" y="{y}" width="{w}" height="{alto}" rx="6" fill="#fff" stroke="{color}" stroke-width="1.3"/>'
         f'<path d="M{x},{y + 6} a6,6 0 0 1 6,-6 h{w - 12} a6,6 0 0 1 6,6 v16 h{-w} z" fill="{color}"/>')
    s += _t(x + 7, y + 11.5, titulo, 'start', 'bold', '#FFFFFF')
    for i, fila in enumerate(filas):
        peso = 'bold' if fila.startswith('PK ') else 'normal'
        s += _t(x + 7, y + 22 + 4 + LINEA / 2 + i * LINEA, fila, 'start', peso, '#0F172A')
    return s, alto


def modelo_estrella() -> Path:
    o = []
    izq, der, cen = 2, 434, 202
    wl, wc = 168, 200
    dims_izq = [('dim_institucion', ['PK institucion_codigo', 'nombre, pais', 'tipo_datos']),
                ('dim_alumno', ['PK alumno_id', 'cedula, apellidos,', 'nombres, genero,', 'ciudad_residencia']),
                ('dim_carrera', ['PK carrera_id', 'carrera,', 'facultad_codigo,', 'facultad_nombre']),
                ('dim_sede', ['PK sede_id', 'sede_codigo,', 'sede_nombre'])]
    dims_der = [('dim_periodo_academico', ['PK periodo_id', 'periodo_codigo,', 'fecha_inicio']),
                ('dim_tiempo', ['PK tiempo_id', 'fecha, anio, mes,', 'trimestre']),
                ('dim_modalidad', ['PK modalidad_codigo', 'descripcion']),
                ('dim_estado_matricula', ['PK estado_codigo', 'descripcion,', 'es_terminal'])]
    hecho = ['PK matricula_id', 'FK institucion_codigo,', '   alumno_id, carrera_id,', '   sede_id, periodo_id,',
             '   tiempo_id, modalidad_codigo,', '   estado_codigo', 'nivel, corte,', 'es_ultimo_periodo',
             'promedio, asistencia_pct', 'monto_matricula,', '   beca_porcentaje,', '   saldo_pendiente',
             'creditos_matriculados,', '   numero_matricula,', '   dias_anticipacion_matricula',
             'actividad_lms,', '   dias_sin_actividad', 'evaluaciones_vencidas,', '   _entregadas, _tardias,',
             '   nota_evaluaciones']
    y_h = 6
    svg_h, alto_h = _entidad(cen - 6, y_h, wc + 12, 'fact_matriculas', hecho, hecho=True)
    centros = []
    for col, dims, x in (('izq', dims_izq, izq), ('der', dims_der, der)):
        y = 6
        espacio = (alto_h - sum(22 + len(f) * LINEA + 8 for _, f in dims)) / (len(dims) - 1)
        for nombre, filas in dims:
            caja, alto = _entidad(x, y, wl, nombre, filas)
            o.append(caja)
            centros.append((col, x, y + alto / 2))
            y += alto + espacio
    for col, x, cy in centros:
        if col == 'izq':
            x1, x2 = x + wl, cen - 6
        else:
            x1, x2 = x, cen + wc + 6
        o.append(f'<line x1="{x1}" y1="{cy:.1f}" x2="{x2}" y2="{cy:.1f}" stroke="{AZUL}" stroke-width="1.2"/>')
        o.append(_t(x1 + (6 if col == 'izq' else -6), cy - 8, '1', 'middle', 'bold', AZUL))
        o.append(_t(x2 + (-7 if col == 'izq' else 7), cy - 8, 'N', 'middle', 'bold', AZUL))
    o.append(svg_h)
    y = y_h + alto_h + 26
    o.append(_t(ANCHO / 2, y - 8, 'Hechos que escriben los procesos por lotes y el seguimiento', 'middle', 'bold', AZUL))
    abajo = [('fact_prediccion_abandono', ['PK prediccion_id', 'FK alumno_id,', '   matricula_id_base',
                                           'probabilidad, percentil,', 'riesgo_categoria, umbrales',
                                           'factor_1, factor_2, factor_3', 'explicacion_json']),
             ('fact_segmento_carrera', ['PK segmento_id', 'FK carrera_id', 'segmento, orden_segmento',
                                        'estudiantes, riesgo_promedio', 'tasa_abandono_hist',
                                        'promedio_hist, asistencia_hist', 'activos_en_riesgo']),
             ('fact_intervencion', ['PK intervencion_id', 'FK alumno_id', 'tipo, descripcion, estado',
                                    'resultado, riesgo_al_registrar', 'registrado_por',
                                    'fecha_registro, fecha_cierre'])]
    xs = [2, 209, 416]
    alto_max = 0
    for (nombre, filas), x in zip(abajo, xs):
        caja, alto = _entidad(x, y, 186, nombre, filas, hecho=True)
        o.append(caja)
        alto_max = max(alto_max, alto)
    y += alto_max + 14
    abajo2 = [('fact_evaluacion_modelo', ['PK evaluacion_id', 'componente, modelo', 'esquema_validacion, metrica',
                                          'valor, desviacion, grupo']),
              ('fact_referente_externo', ['PK referente_id', 'FK referente_codigo', 'indicador, valor, anio',
                                          'pais, comparabilidad, doi']),
              ('dim_referente', ['PK referente_codigo', 'nombre, tipo'])]
    alto_max = 0
    for i, ((nombre, filas), x) in enumerate(zip(abajo2, xs)):
        caja, alto = _entidad(x, y, 186, nombre, filas, hecho=i < 2)
        o.append(caja)
        alto_max = max(alto_max, alto)
    yr = y + 22 + LINEA * 1.5 + 4
    o.append(f'<line x1="{209 + 186}" y1="{yr}" x2="416" y2="{yr}" stroke="{AZUL}" stroke-width="1.2"/>')
    o.append(_t(209 + 186 + 5, yr - 8, 'N', 'middle', 'bold', AZUL) + _t(416 - 5, yr - 8, '1', 'middle', 'bold', AZUL))
    y += alto_max + 10
    o.append(_t(ANCHO / 2, y + 6, 'Todas las tablas de hechos llevan institucion_codigo (FK a dim_institucion),',
                'middle', color='#334155'))
    o.append(_t(ANCHO / 2, y + 6 + LINEA, 'que las vistas VIS_* filtran con SESSION_CONTEXT.', 'middle', color='#334155'))
    return _pagina('av2_modelo_estrella', y + 6 + LINEA + 12, ''.join(o))


def main() -> int:
    rutas = [actividad_etl(), actividad_modelo(), flujo_trabajo(), estados(), casos_uso(), modelo_estrella()]
    if len(sys.argv) > 1:
        subprocess.run([sys.executable, sys.argv[1], str(SALIDA_PNG), *map(str, rutas)], check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

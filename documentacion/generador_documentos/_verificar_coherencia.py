# -*- coding: utf-8 -*-
"""
_verificar_coherencia.py — control automático de Avance_2_VicMar_Data_AI.docx/.pdf.

Falla (código de salida 1) si:
  1. Una cita del texto no está en Referencias, o una referencia no se cita.
  2. Una cifra clave del documento no coincide con los artefactos del sistema
     (metrics.json, metricas_clustering.json, resultados_nl2sql_*.json).
  3. Un apartado no alcanza el mínimo de páginas de la plantilla UNEMI.
  4. «Referencias» o «Anexos» llevan número, que el formato oficial no admite.

Uso (después de _build_avance2.py y _docx_a_pdf.ps1):
    python _verificar_coherencia.py
"""
from __future__ import annotations

import glob
import json
import re
import sys
import unicodedata
from pathlib import Path

import docx
import pymupdf

AQUI = Path(__file__).resolve().parent
BACK = AQUI.parents[1] / 'codigo_fuente' / 'backend'
DOCX = AQUI.parent / 'avances' / 'Avance_2_VicMar_Data_AI.docx'
PDF = AQUI.parent / 'avances' / 'Avance_2_VicMar_Data_AI.pdf'
errores: list[str] = []


def _sin_tildes(s: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def _n(x, d=3):
    return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


# ── 1. Citas ↔ referencias ────────────────────────────────────────────────
doc = docx.Document(str(DOCX))
refs = [p.text.strip() for p in doc.paragraphs if p.style.name == 'Bibliography' and p.text.strip()]
cuerpo = '\n'.join(p.text for p in doc.paragraphs if p.style.name != 'Bibliography')
cuerpo += '\n' + '\n'.join(c.text for t in doc.tables for f in t.rows for c in f.cells)
cuerpo_n = _sin_tildes(cuerpo)

apellidos_ref: list[tuple[str, str]] = []   # (primer autor, año): un autor puede tener varias referencias
for r in refs:
    primero = re.split(r'[,.(]', r, maxsplit=1)[0].strip()
    anio = re.search(r'\((\d{4})', r)
    apellidos_ref.append((_sin_tildes(primero), anio.group(1) if anio else ''))
for apellido, anio in apellidos_ref:
    clave = apellido.split()[-1] if apellido.startswith('asamblea') is False else 'asamblea nacional'
    if apellido not in cuerpo_n and clave not in cuerpo_n:
        errores.append(f'Referencia no citada en el texto: {apellido} ({anio})')

patron = re.compile(r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü'\-]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ\-]+)?)"
                    r"(?: et al\.| y [A-ZÁÉÍÓÚÑ][\w\-]+| & [A-ZÁÉÍÓÚÑ][\w\-]+)?,? \(?((?:19|20)\d{2})\)?")
ignorar = {'agosto', 'septiembre', 'mayo', 'enero', 'milagro', 'crisp-dm', 'unemi', 'tabla', 'figura', 'python',
           'sql server', 'windows', 'docker', 'cohortes', 'registro oficial', 'presentación', 'ley'}
for m in patron.finditer(cuerpo):
    apellido = _sin_tildes(m.group(1))
    if apellido in ignorar or any(apellido.startswith(i) for i in ignorar):
        continue
    # En citas de varios autores el patrón atrapa al ÚLTIMO; la cita es válida
    # si el PRIMER autor de alguna referencia de ese año aparece en los 160
    # caracteres previos al año.
    ventana = _sin_tildes(cuerpo[max(0, m.start() - 160):m.end()])
    anio = m.group(2)
    if any(a.split()[-1] in ventana and (not r or r == anio) for a, r in apellidos_ref):
        continue
    contexto = cuerpo[max(0, m.start() - 40):m.end() + 5].replace('\n', ' ')
    if re.search(r'et al\.|\(\w|, \d{4}\)| y \w+ \(', contexto):
        errores.append(f'Cita sin referencia: «{m.group(0)}» … {contexto!r}')

# ── 2. Cifras clave = artefactos ──────────────────────────────────────────
mu = json.loads((BACK / 'ml/models/UNEMI_PRUEBAS/metrics.json').read_text(encoding='utf-8'))
mo = json.loads((BACK / 'ml/models/OULAD_UK/metrics.json').read_text(encoding='utf-8'))
cu = json.loads((BACK / 'ml/models/UNEMI_PRUEBAS/metricas_clustering.json').read_text(encoding='utf-8'))
nl = [json.loads(Path(p).read_text(encoding='utf-8'))['resumen'] for p in sorted(glob.glob(str(BACK / 'eval/resultados_nl2sql_*.json')))]
nl = [r for r in nl if r['preguntas'] >= 40 and r['adversariales'] >= 8][-1]
resumen = next(p.text for p in doc.paragraphs if p.text.startswith('Se desarrolló un prototipo'))
esperadas = {
    'ROC-AUC temporal UNEMI': _n(mu['validacion_temporal']['umbral_operativo']['roc_auc']),
    'ROC-AUC temporal OULAD': _n(mo['validacion_temporal']['umbral_operativo']['roc_auc']),
    'Kruskal-Wallis p': _n(cu['kruskal_wallis_tasa_abandono']['p_valor']),
    'Exactitud NL2SQL': _n(nl['exactitud_relajada'] * 100, 1) + ' %',
}
for nombre, valor in esperadas.items():
    if valor not in resumen:
        errores.append(f'Resumen: falta {nombre} = {valor}')
    if valor.rstrip(' %') not in cuerpo:
        errores.append(f'Cuerpo: falta {nombre} = {valor}')
if len(resumen.split()) > 150:
    errores.append(f'Resumen con {len(resumen.split())} palabras (máximo 150)')

# ── 3. Páginas mínimas por apartado ───────────────────────────────────────
pdf = pymupdf.open(str(PDF))
marcas = ['2. Análisis del caso', '3. Diseño y desarrollo', '3.1 Metodología', '3.2 Diseño', '3.3 Desarrollo', 'Referencias']
pos = {}
for i, pag in enumerate(pdf):
    if i < 8:
        continue
    for linea in pag.get_text().splitlines():
        s = linea.strip()
        for m in marcas:
            if s.startswith(m) and m not in pos and len(s) < len(m) + 25:
                pos[m] = i + 1
minimos = {'2. Análisis del caso': ('3. Diseño y desarrollo', 3), '3.1 Metodología': ('3.2 Diseño', 3),
           '3.2 Diseño': ('3.3 Desarrollo', 6), '3.3 Desarrollo': ('Referencias', 6)}
for inicio, (fin, minimo) in minimos.items():
    if inicio in pos and fin in pos:
        paginas = pos[fin] - pos[inicio]
        estado = 'OK ' if paginas >= minimo else 'MAL'
        print(f'  {estado} {inicio}: {paginas} páginas (mínimo {minimo})')
        if paginas < minimo:
            errores.append(f'{inicio}: {paginas} páginas, mínimo {minimo}')
    else:
        errores.append(f'No se encontró el apartado {inicio} o {fin} en el PDF')

# ── 4. Numeración de Referencias y Anexos (observación de la tutora al Avance 1) ──
for p in doc.paragraphs:
    if p.style.name.startswith('Heading 1'):
        titulo = p.text.strip()
        if re.match(r'^\d+\.?\s*(Referencias|Anexos)', titulo):
            errores.append(f'Título numerado fuera del formato: «{titulo}»')
        pPr = p._p.pPr
        if titulo.startswith(('Referencias', 'Anexos')) and pPr is not None and pPr.numPr is not None:
            errores.append(f'Título con numeración automática fuera del formato: «{titulo}»')

print(f'Referencias: {len(refs)}  |  Cifras verificadas: {len(esperadas)}  |  Páginas del PDF: {len(pdf)}')
if errores:
    print('\nERRORES:')
    for e in errores:
        print(' -', e)
    sys.exit(1)
print('Coherencia verificada: sin errores.')

# -*- coding: utf-8 -*-
"""
Control automático de coherencia del trabajo final.

Revisa TRABAJO_FINAL_MARLON_VICTOR.docx y su PDF, y termina con código 1 si:
  1. Una cita del texto no está en Referencias, o una referencia no se cita.
  2. Una cifra clave del documento no coincide con los artefactos del modelo
     (ml/modelos/<INSTITUCION>/metricas.json y segmentacion.json), o el
     resumen pasa de 150 palabras (formato oficial del trabajo final).
  5. El PDF pasa de 105 páginas (límite acordado para la entrega).
  3. Un apartado no alcanza el mínimo de páginas de la guía del Avance 2.
  4. Los capítulos finales no siguen la numeración del formato oficial
     (4. Conclusiones y recomendaciones, 5. Referencias, 6. Anexos,
     7. Anexo de información académica) o usan numeración automática.

Uso (después de construir_trabajo_final.py y docx_a_pdf.py):
    python _verificar_coherencia.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import json
import re
import sys
import unicodedata
from pathlib import Path

import docx
import pymupdf

AQUI = Path(__file__).resolve().parent
MODELOS = AQUI.parents[1] / 'backend' / 'ml' / 'modelos'
DOCX = AQUI.parent / 'avances' / 'TRABAJO_FINAL_MARLON_VICTOR.docx'
PDF = AQUI.parent / 'avances' / 'TRABAJO_FINAL_MARLON_VICTOR.pdf'
MAX_PAGINAS = 105
errores: list[str] = []


def _sin_tildes(s: str) -> str:
    """Devuelve `s` en minúsculas y sin marcas diacríticas, para comparar apellidos."""
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn').lower()


def _n(x: float, d: int = 3) -> str:
    """Formatea un número como lo escribe el documento: coma decimal y punto de miles."""
    return f'{x:,.{d}f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def _json(institucion: str, archivo: str) -> dict:
    return json.loads((MODELOS / institucion / archivo).read_text(encoding='utf-8'))


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
    clave = apellido.split()[-1] if not apellido.startswith('asamblea') else 'asamblea nacional'
    if apellido not in cuerpo_n and clave not in cuerpo_n:
        errores.append(f'Referencia no citada en el texto: {apellido} ({anio})')

patron = re.compile(r"([A-ZÁÉÍÓÚÑ][A-Za-zÁÉÍÓÚÑáéíóúñü'\-]+(?: [A-ZÁÉÍÓÚÑ][a-záéíóúñ\-]+)?)"
                    r"(?: et al\.| y [A-ZÁÉÍÓÚÑ][\w\-]+)?,? \(?((?:19|20)\d{2})\)?")
ignorar = {'agosto', 'septiembre', 'mayo', 'enero', 'milagro', 'crisp-dm', 'unemi', 'tabla', 'figura', 'python',
           'sql server', 'windows', 'docker', 'cohortes', 'registro oficial', 'presentación', 'ley', 'oulad',
           'periodo', 'semestre', 'corte'}
for m in patron.finditer(cuerpo):
    apellido = _sin_tildes(m.group(1))
    if apellido in ignorar or any(apellido.startswith(i) for i in ignorar):
        continue
    # En citas de varios autores el patrón atrapa al último; la cita es válida si
    # el primer autor de alguna referencia de ese año aparece en los 160
    # caracteres previos al año.
    ventana = _sin_tildes(cuerpo[max(0, m.start() - 160):m.end()])
    anio = m.group(2)
    if any(a.split()[-1] in ventana and (not r or r == anio) for a, r in apellidos_ref):
        continue
    contexto = cuerpo[max(0, m.start() - 40):m.end() + 5].replace('\n', ' ')
    if re.search(r'et al\.|\(\w|, \d{4}\)| y \w+ \(', contexto):
        errores.append(f'Cita sin referencia: «{m.group(0)}» … {contexto!r}')

# ── 2. Cifras clave = artefactos ──────────────────────────────────────────
mu, mo = _json('UNEMI_PRUEBAS', 'metricas.json'), _json('OULAD_UK', 'metricas.json')
su = _json('UNEMI_PRUEBAS', 'segmentacion.json')
resumen = next(p.text for p in doc.paragraphs if p.text.startswith('Se desarrolló un prototipo'))
esperadas = {
    'ROC-AUC temporal UNEMI_PRUEBAS': mu['validacion_temporal']['roc_auc'],
    'ROC-AUC temporal OULAD_UK': mo['validacion_temporal']['roc_auc'],
    'PR-AUC temporal UNEMI_PRUEBAS': mu['validacion_temporal']['pr_auc'],
    'Silhouette de la segmentación': su['silhouette'],
}
for nombre, valor in esperadas.items():
    formas = {_n(valor, 3), _n(valor, 4)}
    if not any(f in cuerpo for f in formas):
        errores.append(f'Cuerpo: falta {nombre} = {" o ".join(sorted(formas))}')
for nombre in ('ROC-AUC temporal UNEMI_PRUEBAS', 'ROC-AUC temporal OULAD_UK'):
    if not any(f in resumen for f in {_n(esperadas[nombre], 3), _n(esperadas[nombre], 2)}):
        errores.append(f'Resumen: falta {nombre}')
palabras = len(resumen.split())
if not 100 <= palabras <= 150:
    errores.append(f'Resumen con {palabras} palabras (máximo 150)')

# ── 3. Páginas mínimas por apartado (guía del estudio de caso) ────────────
pdf = pymupdf.open(str(PDF))
marcas = ['1.1 Descripción', '1.2 Propósito del caso', '1.3 Base conceptual', '2. Análisis del caso',
          '2.1 Requerimientos', '3. Diseño y desarrollo', '3.1 Metodología', '3.2 Diseño', '4. Conclusiones']
pos: dict[str, int] = {}
for i, pag in enumerate(pdf):
    if i < 8:   # portada, certificados e índices
        continue
    for linea in pag.get_text().splitlines():
        s = linea.strip()
        for m in marcas:
            if s.startswith(m) and m not in pos and len(s) < len(m) + 30:
                pos[m] = i + 1
minimos = {'1.1 Descripción': ('1.2 Propósito del caso', 2), '1.2 Propósito del caso': ('1.3 Base conceptual', 1),
           '1.3 Base conceptual': ('2. Análisis del caso', 3), '2.1 Requerimientos': ('3. Diseño y desarrollo', 3),
           '3.1 Metodología': ('3.2 Diseño', 3), '3.2 Diseño': ('4. Conclusiones', 6)}
for inicio, (fin, minimo) in minimos.items():
    if inicio in pos and fin in pos:
        paginas = pos[fin] - pos[inicio]
        estado = 'OK ' if paginas >= minimo else 'MAL'
        print(f'  {estado} {inicio}: {paginas} páginas (mínimo {minimo})')
        if paginas < minimo:
            errores.append(f'{inicio}: {paginas} páginas, mínimo {minimo}')
    else:
        errores.append(f'No se encontró el apartado {inicio} o {fin} en el PDF')

# ── 4. Numeración de los capítulos finales según el formato oficial ──────
ESPERADOS = ['4. Conclusiones y recomendaciones', '5. Referencias', '6. Anexos', '7. Anexo de información académica']
titulos1 = [p for p in doc.paragraphs if p.style.name.startswith('Heading 1') and p.text.strip()]
for esperado in ESPERADOS:
    if not any(p.text.strip().startswith(esperado) for p in titulos1):
        errores.append(f'Falta el capítulo «{esperado}» con la numeración del formato oficial')
for p in titulos1:
    pPr = p._p.pPr
    if pPr is not None and pPr.numPr is not None and re.search(r'Referencias|Anexo', p.text):
        errores.append(f'Título con numeración automática: «{p.text.strip()}»')

if len(pdf) > MAX_PAGINAS:
    errores.append(f'El PDF tiene {len(pdf)} páginas (máximo {MAX_PAGINAS})')
print(f'Referencias: {len(refs)}  |  Cifras verificadas: {len(esperadas)}  |  '
      f'Resumen: {palabras} palabras  |  Páginas del PDF: {len(pdf)}')
if errores:
    print('\nERRORES:')
    for e in errores:
        print(' -', e)
    sys.exit(1)
print('Coherencia verificada: sin errores.')

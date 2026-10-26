# -*- coding: utf-8 -*-
"""
Exporta a RIS (para importar en Zotero) las referencias APA 7 de la Tarea 3 y del trabajo final.

Uso:
    python documentacion/generador_documentos/exportar_ris.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / 'documentacion' / 'literatura' / 'Tarea3_EstadoDelArte_referencias.ris'


def _autores(texto: str) -> list[str]:
    texto = texto.replace(' y ', ', ').strip()
    partes = [p.strip() for p in texto.split(',') if p.strip()]
    if len(partes) == 1:
        return partes
    autores, i = [], 0
    while i < len(partes):
        if i + 1 < len(partes) and re.fullmatch(r'([A-ZÁÉÍÓÚÑŽ]\.[\s-]?)+(del [A-Z]\.)?|[A-Z]\.-[A-Z]\.',
                                                 partes[i + 1].strip()):
            autores.append(f'{partes[i]}, {partes[i + 1]}')
            i += 2
        else:
            autores.append(partes[i])
            i += 1
    return autores


def a_ris(ref: str) -> str:
    limpio = ref.replace('*', '')
    m = re.match(r'^(.*?)\s\((\d{4})\)\.\s(.*)$', limpio)
    if not m:
        return ''
    autores, anio, resto = m.groups()
    doi = re.search(r'https://doi\.org/(\S+)', resto)
    url = re.search(r'(https?://\S+)', resto)
    revista = re.search(r'\*(.+?), (\d+)\*(?:\((\d+)\))?, ([\w-]+)', ref)
    en = ' En ' in resto
    tipo = 'JOUR' if revista and not en else ('CHAP' if en else ('BOOK' if 'ed.)' in resto or 'Wiley' in resto
                                                                    else 'GEN'))
    titulo = resto.split('. ')[0] if not ref.split(f'({anio}). ')[1].startswith('*') else \
        re.match(r'\*(.+?)\*', ref.split(f'({anio}). ')[1]).group(1)
    lineas = [f'TY  - {tipo}']
    for a in _autores(autores):
        lineas.append(f"AU  - {a if ',' in a else a.rstrip('.')}")
    lineas += [f'PY  - {anio}', f'TI  - {titulo.strip()}']
    if revista and not en:
        lineas += [f'T2  - {revista.group(1)}', f'VL  - {revista.group(2)}']
        if revista.group(3):
            lineas.append(f'IS  - {revista.group(3)}')
        pag = revista.group(4)
        if '-' in pag:
            sp, ep = pag.split('-', 1)
            lineas += [f'SP  - {sp}', f'EP  - {ep}']
        else:
            lineas.append(f'SP  - {pag}')
    if doi:
        lineas.append(f'DO  - {doi.group(1).rstrip(".")}')
    elif url:
        lineas.append(f'UR  - {url.group(1).rstrip(".")}')
    lineas.append('KW  - Tesis VicMar')
    lineas.append('ER  - ')
    return '\n'.join(lineas)


def main() -> int:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from _tarea3_contenido import REFERENCIAS
    from _c4_cierre import REFERENCIAS as REF_TF
    todas = list(dict.fromkeys(REFERENCIAS + REF_TF))
    bloques, vistos = [], set()
    for r in todas:      # la misma obra puede venir redactada distinto en los dos documentos
        b = a_ris(r)
        if not b:
            continue
        clave = tuple(l for l in b.splitlines() if l[:2] in ('AU', 'PY', 'TI'))[:3]
        clave = tuple(' '.join(x.lower().split()) for x in clave)
        if clave in vistos:
            continue
        vistos.add(clave)
        bloques.append(b)
    SALIDA.write_text('\n\n'.join(b for b in bloques if b) + '\n', encoding='utf-8')
    print(f'{SALIDA}: {sum(1 for b in bloques if b)} referencias')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

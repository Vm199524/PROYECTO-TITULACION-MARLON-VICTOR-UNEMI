# -*- coding: utf-8 -*-
"""
Convierte un .docx a PDF con LibreOffice, actualizando antes la tabla de contenido,
los índices de figuras y tablas y los campos SEQ (lo que Word hace al abrir el archivo).

Uso (python3 del sistema, que trae el módulo uno de LibreOffice):
    python3 documentacion/generador_documentos/docx_a_pdf.py DOC.docx [SALIDA.pdf]

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

import uno
from com.sun.star.beans import PropertyValue


def _prop(nombre, valor):
    p = PropertyValue()
    p.Name, p.Value = nombre, valor
    return p


def main() -> int:
    origen = Path(sys.argv[1]).resolve()
    destino = Path(sys.argv[2]).resolve() if len(sys.argv) > 2 else origen.with_suffix('.pdf')
    puerto = 2002 + os.getpid() % 500
    perfil = Path('/tmp') / f'lo_perfil_{os.getpid()}'
    proc = subprocess.Popen(['soffice', '--headless', '--invisible', '--norestore', '--nologo',
                             f'-env:UserInstallation=file://{perfil}',
                             f'--accept=socket,host=127.0.0.1,port={puerto};urp;'],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        local = uno.getComponentContext()
        resolvedor = local.ServiceManager.createInstanceWithContext('com.sun.star.bridge.UnoUrlResolver', local)
        for _ in range(60):
            try:
                ctx = resolvedor.resolve(f'uno:socket,host=127.0.0.1,port={puerto};urp;StarOffice.ComponentContext')
                break
            except Exception:  # noqa: BLE001
                time.sleep(1)
        escritorio = ctx.ServiceManager.createInstanceWithContext('com.sun.star.frame.Desktop', ctx)
        doc = escritorio.loadComponentFromURL(origen.as_uri(), '_blank', 0, (_prop('Hidden', True),))
        doc.getTextFields().refresh()
        indices = doc.getDocumentIndexes()
        for _ in range(2):  # la segunda pasada fija los números de página
            for i in range(indices.getCount()):
                indices.getByIndex(i).update()
            doc.getTextFields().refresh()
        doc.storeToURL(destino.as_uri(), (_prop('FilterName', 'writer_pdf_Export'),))
        doc.close(True)
        print(destino)
    finally:
        proc.terminate()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

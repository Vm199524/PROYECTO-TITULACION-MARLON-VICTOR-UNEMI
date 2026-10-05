"""
Pruebas del requisito no funcional de privacidad (core/privacidad.py).

Según la LOPDP (principio de minimización), ningún dato que identifique a un
estudiante sale hacia un proveedor externo de IA:
  1. El enmascarado reemplaza cédula/nombres/apellidos por un seudónimo estable
     y oculta números con forma de cédula en otras columnas.
  2. Las cifras (lo único que el modelo necesita para redactar) no cambian.
  3. De extremo a extremo: el CUERPO HTTP que narrativa_rapida envía al
     proveedor no contiene ninguna cédula ni nombre de las filas de entrada.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.narrativa_rapida import narrar_resultado_rapido  # noqa: E402
from core.privacidad import (  # noqa: E402
    TEXTO_OCULTO, enmascarar_cedula, enmascarar_filas, es_columna_personal,
)

COLUMNAS = ['cedula', 'apellidos', 'nombres', 'carrera', 'probabilidad', 'riesgo_categoria']
FILAS = [
    ('0912345678', 'Pérez Almachi', 'Marlon David', 'Enfermeria', 0.91, 'ALTO'),
    ('0923456789', 'Lluilema Pisco', 'Victor Manuel', 'Medicina', 0.74, 'ALTO'),
    ('0912345678', 'Pérez Almachi', 'Marlon David', 'Enfermeria', 0.91, 'ALTO'),
]


def test_detecta_columnas_personales_sin_confundir_las_de_negocio():
    for c in ('cedula', 'Cédula', 'apellidos', 'nombres', 'correo_electronico', 'telefono_movil'):
        assert es_columna_personal(c), c
    for c in ('carrera', 'facultad_nombre', 'probabilidad', 'nombre', 'business_name', 'sede_nombre'):
        assert not es_columna_personal(c), c


def test_enmascara_identidad_y_conserva_cifras():
    cols, filas = enmascarar_filas(COLUMNAS, FILAS)
    assert cols == COLUMNAS
    texto = json.dumps(filas, ensure_ascii=False)
    for dato in ('0912345678', '0923456789', 'Pérez', 'Marlon', 'Lluilema', 'Victor'):
        assert dato not in texto
    assert [f[3:] for f in filas] == [f[3:] for f in FILAS]


def test_seudonimo_estable_para_la_misma_persona():
    _, filas = enmascarar_filas(COLUMNAS, FILAS)
    assert filas[0][0] == filas[2][0] == 'Alumno 1'
    assert filas[1][0] == 'Alumno 2'


def test_oculta_cedulas_dentro_de_texto_libre_y_filas_dict():
    _, filas = enmascarar_filas(['detalle'], [('Revisar al alumno 0912345678 por mora',)])
    assert '0912345678' not in filas[0][0] and TEXTO_OCULTO in filas[0][0]

    _, filas = enmascarar_filas([], [{'cedula': '0912345678', 'carrera': 'Medicina', 'n': 3}])
    assert filas[0] == {'cedula': 'Alumno 1', 'carrera': 'Medicina', 'n': 3}


def test_enmascarar_cedula_para_pantalla():
    assert enmascarar_cedula('0912345678') == '******5678'
    assert enmascarar_cedula('') == '****'


def test_el_cuerpo_enviado_al_proveedor_no_contiene_datos_personales(monkeypatch):
    enviado = {}

    class _Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": "Hay 2 alumnos en riesgo alto."}}]}

    def _post(url, json=None, **kwargs):  # noqa: A002 — firma de requests.post
        enviado['cuerpo'] = json
        return _Resp()

    monkeypatch.setattr("requests.post", _post)
    resultado = narrar_resultado_rapido(
        pregunta="¿quiénes están en riesgo alto?", nombre_metrica="Riesgo de abandono",
        columns=COLUMNAS, rows=FILAS, respaldo="respaldo",
        api_key="sk-fake", base_url="https://proveedor.example/v1", modelo="modelo-x",
    )
    assert resultado == "Hay 2 alumnos en riesgo alto."
    cuerpo = json.dumps(enviado['cuerpo'], ensure_ascii=False)
    for dato in ('0912345678', '0923456789', 'Pérez Almachi', 'Marlon David', 'Lluilema', 'Victor Manuel'):
        assert dato not in cuerpo, f"'{dato}' se envió al proveedor externo"
    assert 'Enfermeria' in cuerpo and '0.91' in cuerpo

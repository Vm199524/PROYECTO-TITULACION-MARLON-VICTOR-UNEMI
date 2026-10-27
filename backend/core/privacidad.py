# -*- coding: utf-8 -*-
"""
Protección de datos personales de los estudiantes (LOPDP del Ecuador).

Aplica tres principios de la Ley Orgánica de Protección de Datos Personales
(2021):
  - Minimización: antes de que unas filas salgan hacia un proveedor externo
    de IA para redactar una respuesta, las columnas que identifican a una
    persona se reemplazan por un seudónimo («Estudiante 1») y cualquier
    número con forma de cédula se oculta.
  - Finalidad y acceso: en pantalla la cédula siempre aparece enmascarada
    (******1234) y la ficha de un estudiante se identifica con un token
    cifrado, no con su cédula, para que no viaje en direcciones ni registros.
  - Seguridad: el token se cifra con una llave derivada del secreto del
    servidor (Fernet: AES-128 en modo CBC con HMAC-SHA256).

Requerimientos que implementa: RNF-01 (protección de datos).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import base64
import hashlib
import re
import unicodedata
from typing import Any

from cryptography.fernet import Fernet, InvalidToken

from core.config import CONFIG

_COLUMNAS_PERSONALES = {
    'cedula', 'identificacion', 'dni', 'pasaporte', 'apellidos', 'apellido', 'nombres', 'nombre',
    'nombre_completo', 'alumno', 'estudiante', 'correo', 'email', 'telefono', 'celular', 'direccion',
}
# Palabras que, dentro del nombre de una columna, indican un dato de una persona.
_PALABRAS_PERSONALES = {
    'cedula', 'cedulas', 'identificacion', 'dni', 'pasaporte', 'ruc', 'nombre', 'nombres', 'apellido',
    'apellidos', 'correo', 'correos', 'email', 'mail', 'e_mail', 'telefono', 'telefonos', 'celular', 'movil',
    'direccion', 'domicilio', 'nombre_completo', 'alumno', 'estudiante',
}
# Si la columna menciona una de estas entidades, «nombre» se refiere a ella y no a una persona
# («Nombre de la carrera», facultad_nombre).
_ENTIDADES_NO_PERSONALES = {
    'carrera', 'carreras', 'facultad', 'facultades', 'sede', 'sedes', 'institucion', 'universidad',
    'periodo', 'modalidad', 'metrica', 'modelo', 'asignatura', 'materia', 'curso', 'nivel', 'tipo',
    'categoria', 'riesgo', 'ciudad', 'provincia', 'canton', 'pais', 'variable', 'caracteristica', 'factor',
}
_PALABRAS_DE_PERSONA_EXPLICITAS = {'cedula', 'identificacion', 'dni', 'pasaporte', 'correo', 'email', 'mail',
                                   'telefono', 'celular', 'movil', 'direccion', 'domicilio', 'apellido', 'apellidos'}
_PATRON_COLUMNA = re.compile(r'(^|_)(cedula|identificacion|correo|email|telefono|celular|direccion|apellido)')
# Texto libre del seguimiento: puede contener cualquier dato (incluso sensible, art. 26) y nunca sale hacia la IA.
_COLUMNAS_TEXTO_LIBRE = {
    'descripcion', 'resultado', 'observacion', 'observaciones', 'comentario', 'comentarios', 'detalle',
    'descripcion_intervencion', 'resultado_intervencion', 'texto', 'notas',
}
# Identifican a un funcionario o, junto a una fila individual, ayudan a reidentificar al estudiante.
_COLUMNAS_CUASI_IDENTIFICADORAS = {'registrado_por', 'usuario', 'responsable', 'ciudad_residencia', 'fecha_nacimiento'}

_PATRON_CEDULA = re.compile(r'(?<!\d)(\d{10}|\d{13})(?!\d)')
_PATRON_CORREO = re.compile(r'[\w.+-]+@[\w-]+(?:\.[\w-]+)+')
# Teléfonos del Ecuador con prefijo internacional o escritos con separadores (09 9123 4567, 04-212-3456).
_PATRON_TELEFONO = re.compile(
    r'(?<![\w+])(?:\+?593[\s.-]?\(?0?\d{1,2}\)?[\s.-]?\d{3}[\s.-]?\d{3,4}'
    r'|\(?0\d{1,2}\)?[\s.-]\d{3,4}[\s.-]?\d{3,4})(?!\d)')
OCULTO = '[dato personal oculto]'


def _normalizar(nombre: Any) -> str:
    s = unicodedata.normalize('NFKD', str(nombre or '')).encode('ascii', 'ignore').decode()
    return re.sub(r'[\s\-.]+', '_', s.strip().lower())


def _palabras(nombre: Any) -> list[str]:
    return [p for p in re.split(r'[^a-z0-9]+', _normalizar(nombre)) if p]


def es_columna_personal(nombre: Any) -> bool:
    """Indica si una columna identifica a una persona.

    Reconoce variantes y alias en mayúsculas o minúsculas, con o sin tilde:
    «Nombre», «Nombres y apellidos», «Nombre del estudiante», «Cédula»,
    «E-mail», «Teléfono celular», «Dirección», etc. «Nombre de la carrera» o
    `facultad_nombre` no se consideran personales.
    """
    n = _normalizar(nombre)
    if n in _COLUMNAS_PERSONALES or _PATRON_COLUMNA.search(n):
        return True
    palabras = set(_palabras(nombre))
    if not palabras & _PALABRAS_PERSONALES:
        return False
    if palabras & _PALABRAS_DE_PERSONA_EXPLICITAS or palabras & {'alumno', 'estudiante'} and palabras & {'nombre', 'nombres'}:
        return True
    return not palabras & _ENTIDADES_NO_PERSONALES


def es_columna_texto_libre(nombre: Any) -> bool:
    """Columnas de texto libre del seguimiento (descripción, resultado, observaciones)."""
    n = _normalizar(nombre)
    return n in _COLUMNAS_TEXTO_LIBRE or bool(set(_palabras(nombre)) & {'descripcion', 'observacion', 'observaciones', 'comentario', 'comentarios'})


def ocultar_identificadores(texto: str) -> str:
    """Oculta en un texto libre los patrones de cédula o RUC, correo y teléfono."""
    texto = _PATRON_CORREO.sub(OCULTO, texto)
    texto = _PATRON_CEDULA.sub(OCULTO, texto)
    return _PATRON_TELEFONO.sub(OCULTO, texto)


def enmascarar_cedula(cedula: Any) -> str:
    """Deja visibles solo los últimos 4 caracteres: ******1234."""
    s = str(cedula or '')
    return ('*' * (len(s) - 4)) + s[-4:] if len(s) > 4 else '****'


def seudonimizar(columnas: list[str], filas: list[list[Any]]) -> tuple[list[str], list[list[Any]]]:
    """Reemplaza las columnas personales por un seudónimo estable dentro de la llamada.

    Se usa antes de enviar filas a un proveedor externo de IA: el modelo puede
    redactar «dos estudiantes en riesgo alto» sin conocer quiénes son.
    """
    personales = [i for i, c in enumerate(columnas) if es_columna_personal(c)]
    seudonimos: dict[tuple, str] = {}
    salida = []
    for fila in filas:
        clave = tuple(str(fila[i]) for i in personales)
        if personales and clave not in seudonimos:
            seudonimos[clave] = f'Estudiante {len(seudonimos) + 1}'
        nueva = []
        for i, v in enumerate(fila):
            if i in personales:
                nueva.append(seudonimos[clave])
            elif isinstance(v, str):
                nueva.append(ocultar_identificadores(v))
            else:
                nueva.append(v)
        salida.append(nueva)
    return columnas, salida


def enmascarar_para_pantalla(columnas: list[str], filas: list[list[Any]]) -> list[list[Any]]:
    """Enmascara las columnas de identificación (cédula) que se muestran en pantalla."""
    idx = [i for i, c in enumerate(columnas) if _normalizar(c) in ('cedula', 'identificacion', 'dni', 'pasaporte')]
    if not idx:
        return filas
    return [[enmascarar_cedula(v) if i in idx else v for i, v in enumerate(f)] for f in filas]


def _fernet() -> Fernet:
    llave = hashlib.sha256(('vicmar-token-estudiante|' + CONFIG.jwt_clave).encode('utf-8')).digest()
    return Fernet(base64.urlsafe_b64encode(llave))


def token_estudiante(cedula: str) -> str:
    """Token opaco que identifica a un estudiante en la API sin exponer su cédula."""
    return _fernet().encrypt(str(cedula).encode('utf-8')).decode('ascii')


def cedula_desde_token(token: str) -> str | None:
    """Recupera la cédula de un token emitido por este servidor (o None si no es válido)."""
    try:
        return _fernet().decrypt(token.encode('ascii'), ttl=60 * 60 * 24).decode('utf-8')
    except (InvalidToken, ValueError):
        return None


# ── Datos que salen hacia un proveedor externo de IA ─────────────────────
def filas_para_ia(columnas: list[str], filas: list[list[Any]]) -> tuple[list[str], list[list[Any]]]:
    """Prepara un resultado para enviarlo a un proveedor de IA (minimización, art. 10 de la LOPDP).

    Excluye las columnas de texto libre del seguimiento (descripción,
    resultado, observaciones); si el resultado es individual (tiene alguna
    columna personal) excluye también las cuasi identificadoras (quién
    registró, ciudad de residencia). Después seudonimiza las columnas
    personales y oculta cédulas, correos y teléfonos en el resto de textos.
    """
    personal = any(es_columna_personal(c) for c in columnas)
    conservar = [i for i, c in enumerate(columnas)
                 if not es_columna_texto_libre(c) and not (personal and _normalizar(c) in _COLUMNAS_CUASI_IDENTIFICADORAS)]
    cols = [columnas[i] for i in conservar]
    reducidas = [[f[i] for i in conservar] for f in filas]
    return seudonimizar(cols, reducidas)


def _plano(texto: str) -> str:
    """Minúsculas sin tildes, con la MISMA longitud que el texto (para ubicar coincidencias)."""
    salida = []
    for ch in texto:
        base = unicodedata.normalize('NFKD', ch).encode('ascii', 'ignore').decode()
        salida.append((base[:1] or ch).lower())
    return ''.join(salida)


IndiceNombres = dict[str, list[str]]


def indice_nombres(personas: Any) -> IndiceNombres:
    """Índice de nombres de estudiantes para reconocerlos en una pregunta.

    `personas` son pares (apellidos, nombres) o nombres completos. Por cada
    persona se indexan «nombres apellidos», «apellidos nombres» y «primer
    nombre primer apellido» (y su inverso), por la primera palabra.
    """
    indice: IndiceNombres = {}
    for p in personas or []:
        apellidos, nombres = (p[0], p[1]) if isinstance(p, (list, tuple)) and len(p) >= 2 else ('', p)
        ap, no = _plano(str(apellidos or '')).split(), _plano(str(nombres or '')).split()
        variantes = {' '.join(no + ap), ' '.join(ap + no)}
        if ap and no:
            variantes |= {f'{no[0]} {ap[0]}', f'{ap[0]} {no[0]}'}
        for v in variantes:
            if len(v.split()) >= 2:
                indice.setdefault(v.split()[0], []).append(v)
    for k in indice:
        indice[k] = sorted(set(indice[k]), key=len, reverse=True)
    return indice


def _marcar(texto: str, inicio: int, fin: int, tipo: str, reemplazos: dict[str, str]) -> str:
    original = texto[inicio:fin]
    marcador = next((m for m, v in reemplazos.items() if v == original), None)
    if marcador is None:
        marcador = f'{tipo}_{sum(1 for m in reemplazos if m.startswith(tipo + "_")) + 1}'
        reemplazos[marcador] = original
    return texto[:inicio] + marcador + texto[fin:]


def depurar_texto(texto: str, nombres: IndiceNombres | None = None,
                  reemplazos: dict[str, str] | None = None) -> tuple[str, dict[str, str]]:
    """Reemplaza los datos personales de un texto por marcadores antes de enviarlo a la IA.

    Correos → CORREO_n, cédulas o RUC (10 o 13 dígitos) → CEDULA_n,
    teléfonos → TELEFONO_n y nombres de estudiantes de la institución activa
    (si se entrega su índice) → NOMBRE_n. Devuelve el texto depurado y el
    diccionario marcador → valor original, que nunca sale del servidor y
    permite restaurar los valores en el SQL que se ejecuta localmente.
    Si se entrega `reemplazos`, primero reutiliza sus marcadores.
    """
    reemplazos = {} if reemplazos is None else reemplazos
    texto = str(texto or '')
    for marcador, original in sorted(reemplazos.items(), key=lambda kv: len(kv[1]), reverse=True):
        if original:
            texto = re.sub(re.escape(original), marcador, texto, flags=re.I)
    for tipo, patron in (('CORREO', _PATRON_CORREO), ('CEDULA', _PATRON_CEDULA), ('TELEFONO', _PATRON_TELEFONO)):
        m = patron.search(texto)
        while m:
            texto = _marcar(texto, m.start(), m.end(), tipo, reemplazos)
            m = patron.search(texto)
    if nombres:
        plano = _plano(texto)
        palabras = list(re.finditer(r'[a-z]+', plano))
        for w in palabras:
            for candidato in nombres.get(w.group(0), []):
                fin = w.start() + len(candidato)
                if plano[w.start():fin] == candidato and (fin == len(plano) or not plano[fin].isalnum()):
                    texto = _marcar(texto, w.start(), fin, 'NOMBRE', reemplazos)
                    return depurar_texto(texto, nombres, reemplazos)
    return texto, reemplazos


def restaurar_en_sql(sql: str, reemplazos: dict[str, str]) -> str:
    """Devuelve a un SQL generado los valores originales de sus marcadores (comillas escapadas)."""
    for marcador in sorted(reemplazos, key=len, reverse=True):
        valor = reemplazos[marcador].replace("'", "''")
        sql = re.sub(rf'\b{re.escape(marcador)}\b', lambda _m, v=valor: v, sql)
    return sql

# -*- coding: utf-8 -*-
"""
Presentaciones del Avance 2, del Avance 3 y de la sustentación individual (carátula + 5 diapositivas), sobre la
plantilla del grupo. Las cifras del Avance 3 y de la sustentación se leen de los mismos artefactos que el documento
(ml/modelos/*/metricas.json, eval/resultados, evidencias/pruebas.json); las del Avance 2 son las que informó ese
avance (8 de octubre de 2026).

Uso:
    python documentacion/generador_documentos/construir_presentaciones_avances.py --kit <lib del plugin>

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from _datos import C, CAPTURAS, DIAGRAMAS, FIGURAS, N_PRUEBAS_BACKEND, N_PRUEBAS_FRONTEND, O, U, f, pct
import construir_presentacion as tf

RAIZ = Path(__file__).resolve().parents[2]
SALIDA = RAIZ / 'documentacion' / 'presentacion'
PLANTILLA = tf.PLANTILLA
TITULO = tf.TITULO
REPO = tf.REPOSITORIO
DRIVE = tf.DRIVE
MARLON = 'Marlon David Pérez Almachi'
VICTOR = 'Víctor Manuel Lluilema Pisco'
TUTORAS = 'Msc. Peralta Correa Mirella Azucena · Msc. Espinoza Bravo María Gabriela'


# ====================================================================== Avance 2 (8 de octubre de 2026)
def contenido_avance2() -> dict:
    d = []
    d.append({'tipo': 'agenda', 'titulo': 'Contenido',
              'items': ['Descripción y propósito del caso', 'Base conceptual y trabajos previos',
                        'Análisis del caso: requerimientos', 'Metodología CRISP-DM', 'Diseño: arquitectura y UML',
                        'Modelo de datos y resultados', 'Demostración', 'Conclusiones e innovación']})
    d.append({'tipo': 'cifras', 'titulo': 'Descripción del caso', 'subtitulo': 'El abandono se mide tarde y con datos dispersos',
              'items': [{'valor': '44,90 %', 'etiqueta': 'probabilidad de abandono en cinco cohortes de una universidad '
                                                        'ecuatoriana (Núñez-Naranjo, 2024)'},
                        {'valor': '484', 'etiqueta': 'de 1.078 admitidos abandonaron en ese mismo estudio'},
                        {'valor': '0,69', 'etiqueta': 'ROC-AUC de un modelo validado con cohortes futuras '
                                                     '(Carballo-Mendívil et al., 2025)'}],
              'texto': 'Las señales (notas, asistencia, aula virtual, cartera) ya se registran, pero en sistemas separados '
                       'y para conocer el estado actual, no para anticipar el retiro.'})
    d.append({'tipo': 'texto', 'titulo': 'Propósito del caso', 'subtitulo': 'Objetivo general',
              'parrafos': ['Desarrollar un prototipo de sistema web que prediga el abandono de estudiantes universitarios '
                           'mediante aprendizaje automático y permita consultar sus resultados en lenguaje natural, para '
                           'que las autoridades académicas y el personal de bienestar estudiantil identifiquen '
                           'tempranamente a quienes están en riesgo y prioricen su acompañamiento.'],
              'destacado': {'titulo': 'Qué · cómo · para qué',
                            'texto': 'Un sistema de alerta temprana, con CRISP-DM, un almacén en SQL Server, LightGBM '
                                     'y consulta NL2SQL, para actuar antes del retiro.'}})
    d.append({'tipo': 'tarjetas', 'titulo': 'Objetivos específicos',
              'items': [{'icono': 'busqueda', 'titulo': 'Analizar', 'texto': 'Procesos y variables del abandono para derivar requerimientos'},
                        {'icono': 'grafico_barras', 'titulo': 'Construir y validar', 'texto': 'Modelo calibrado y explicable, validado en el tiempo'},
                        {'icono': 'monitor', 'titulo': 'Implementar', 'texto': 'Sistema web por roles con panel, ficha y consulta'},
                        {'icono': 'verificacion', 'titulo': 'Evaluar', 'texto': 'Métricas predictivas, de la consulta y de protección de datos'}]})
    d.append({'tipo': 'tabla', 'titulo': 'Base conceptual: trabajos previos frente al caso',
              'subtitulo': '14 estudios comparados; aquí, siete representativos',
              'encabezados': ['Estudio', 'Técnica', 'Resultado', 'Sistema / NL / Gobierno'],
              'filas': [['Núñez-Naranjo (2024)', 'Regresión logística multinivel', 'Abandono de 44,90 %', 'No / No / No'],
                        ['Carballo-Mendívil et al. (2025)', 'XGBoost, prueba prospectiva', 'ROC-AUC 0,69; recall 0,88', 'Parcial / No / No'],
                        ['Rabelo y Zárate (2025)', 'Ensamble de modelos', 'Detecta 98,1 %', 'No / No / No'],
                        ['Vaarma y Li (2024)', 'Predicción mensual con Moodle', 'Créditos y actividad clave', 'No / No / No'],
                        ['Kuzilek et al. (2017)', 'Conjunto OULAD', '32.593 matrículas', 'No aplica'],
                        ['Ascoli y Choi (2025)', 'NL2SQL con LLM', 'Mejor exactitud con contexto', 'No aplica / Sí / No'],
                        ['VicMar (este trabajo)', 'LightGBM + K-means + NL2SQL', 'ROC-AUC 0,829 y 0,766', 'Sí / Sí / Sí']],
              'anchos': [1.5, 1.6, 1.3, 1.1]})
    d.append({'tipo': 'cifras', 'titulo': 'Análisis del caso: requerimientos',
              'subtitulo': 'Derivados de las cuatro piezas: modelo, segmentación, NL2SQL y panel',
              'items': [{'valor': '18', 'etiqueta': 'requerimientos funcionales'},
                        {'valor': '10', 'etiqueta': 'no funcionales con métrica verificable'},
                        {'valor': '10', 'etiqueta': 'historias de usuario para la autoridad sin perfil técnico'}],
              'texto': 'Criterios fijados antes de evaluar: ROC-AUC ≥ 0,75, recall ≥ 0,75, exactitud de la consulta ≥ 85 %, '
                       '8/8 preguntas maliciosas contenidas y cero fugas entre instituciones.'})
    d.append({'tipo': 'tabla', 'titulo': 'Historias de usuario', 'subtitulo': 'Escritas para una autoridad que no conoce SQL',
              'encabezados': ['ID', 'Historia', 'Criterio de aceptación'],
              'filas': [['HU-01', 'Como decana, quiero ver al abrir el sistema cuántos estudiantes están en riesgo',
                         'Panel con totales por nivel y variación frente al periodo anterior'],
                        ['HU-03', 'Como profesional de bienestar, quiero entender por qué un estudiante está en riesgo',
                         'Ficha con probabilidad, percentil y los factores que más pesan'],
                        ['HU-05', 'Como trabajadora social, quiero registrar la intervención realizada',
                         'Registro con tipo, descripción y riesgo al momento de registrar'],
                        ['HU-06', 'Como decano, quiero preguntar en español cuántos estudiantes están en riesgo alto',
                         'Respuesta con tabla o gráfico y resumen en una línea'],
                        ['HU-09', 'Como autoridad, quiero saber cuánto puedo confiar en el modelo',
                         'Página de calidad con ROC-AUC, recall y calibración']],
              'anchos': [0.6, 2.6, 2.4]})
    d.append({'tipo': 'imagen', 'titulo': 'Metodología CRISP-DM', 'subtitulo': 'Seis fases con entregables verificables',
              'ruta': str(DIAGRAMAS / 'av2_crisp_dm.png')})
    d.append({'tipo': 'imagen', 'titulo': 'Diseño: arquitectura de la solución',
              'subtitulo': 'Cliente-servidor en capas, con el almacén como única fuente',
              'ruta': str(DIAGRAMAS / 'av2_arquitectura.png')})
    d.append({'tipo': 'imagen', 'titulo': 'UML: secuencia de una consulta en lenguaje natural',
              'ruta': str(DIAGRAMAS / 'av2_secuencia_consulta.png')})
    d.append({'tipo': 'imagen', 'titulo': 'UML: colaboración', 'subtitulo': 'Objetos que participan en una consulta',
              'ruta': str(DIAGRAMAS / 'av2_colaboracion.png')})
    d.append({'tipo': 'imagen', 'titulo': 'UML: estados de una predicción',
              'ruta': str(DIAGRAMAS / 'av2_estados.png')})
    d.append({'tipo': 'imagen', 'titulo': 'UML: actividades del ETL',
              'ruta': str(DIAGRAMAS / 'av2_actividad_etl.png')})
    d.append({'tipo': 'imagen', 'titulo': 'Diagrama de flujo de trabajo', 'subtitulo': 'De los datos académicos al acompañamiento',
              'ruta': str(DIAGRAMAS / 'av2_flujo_trabajo.png')})
    d.append({'tipo': 'imagen', 'titulo': 'Modelo de datos', 'subtitulo': 'Esquema estrella del almacén académico',
              'ruta': str(DIAGRAMAS / 'av2_modelo_estrella.png')})
    d.append({'tipo': 'tabla', 'titulo': 'Modelado: validación cruzada agrupada por estudiante',
              'subtitulo': 'LightGBM fue el mejor en las dos instituciones',
              'encabezados': ['Modelo', 'ROC-AUC UNEMI', 'PR-AUC UNEMI', 'ROC-AUC OULAD', 'PR-AUC OULAD'],
              'filas': [['Regresión logística', '0,819 ± 0,003', '0,378 ± 0,011', '0,787 ± 0,010', '0,082 ± 0,010'],
                        ['Random Forest con pesos', '0,821 ± 0,006', '0,450 ± 0,006', '0,797 ± 0,010', '0,085 ± 0,007'],
                        ['Random Forest con SMOTE', '0,816 ± 0,005', '0,421 ± 0,010', '0,776 ± 0,007', '0,071 ± 0,005'],
                        ['LightGBM', '0,828 ± 0,003', '0,456 ± 0,009', '0,803 ± 0,009', '0,095 ± 0,012']],
              'anchos': [1.8, 1.1, 1.1, 1.1, 1.1]})
    d.append({'tipo': 'cifras', 'titulo': 'Evaluación: prueba temporal', 'subtitulo': 'Periodos que el modelo no vio',
              'items': [{'valor': '0,829', 'etiqueta': 'ROC-AUC, UNEMI (datos de prueba)'},
                        {'valor': '0,766', 'etiqueta': 'ROC-AUC, OULAD (datos reales anonimizados)'},
                        {'valor': '78 %', 'etiqueta': 'de los abandonos detectados con el umbral medio'},
                        {'valor': '100 %', 'etiqueta': 'exactitud de la consulta en el conjunto dorado'}],
              'texto': 'Contactando primero al 20 % de mayor riesgo se alcanza a 55 % de quienes abandonarán (OULAD). '
                       'Las 8 preguntas maliciosas fueron contenidas y no hubo fugas entre instituciones.'})
    d.append({'tipo': 'texto', 'titulo': 'Demostración del prototipo',
              'parrafos': ['- Ingreso con rol de autoridad académica', '- Panel ejecutivo y lista priorizada',
                           '- Ficha explicada con tres factores y simulador', '- Pregunta en lenguaje natural',
                           '- Calidad del modelo', 'GitHub: ' + REPO.replace('https://github.com/', ''),
                           'Carpeta digital: enlace en la portada del documento'],
              'imagen': str(CAPTURAS / 'av2_cap_panel.png')})
    d.append({'tipo': 'comparativa', 'titulo': 'Análisis de innovación',
              'izquierda': {'titulo': 'Aporte', 'items': ['Predicción explicada en español dentro de un sistema por roles',
                                                          'Consulta conversacional con métricas certificadas y SQL validado',
                                                          'Aislamiento multiinstitución en la base de datos']},
              'derecha': {'titulo': 'Limitación', 'items': ['UNEMI se evaluó con datos de prueba sintéticos',
                                                            'La prueba de usabilidad con usuarios está pendiente',
                                                            'El modelo prioriza; no decide por el estudiante']}})
    d.append({'tipo': 'conclusiones', 'titulo': 'Conclusiones preliminares',
              'items': [{'titulo': 'Requerimientos', 'texto': 'Las señales del abandono ya existen en los sistemas académicos y dieron origen a 18 RF y 10 RNF.'},
                        {'titulo': 'Modelo', 'texto': 'LightGBM calibrado supera el criterio de 0,75 en periodos no vistos.'},
                        {'titulo': 'Sistema', 'texto': 'El prototipo funciona de punta a punta con tres roles y consulta en español.'},
                        {'titulo': 'Siguiente paso', 'texto': 'Validar con una carrera real anonimizada y con usuarios.'}]})
    return {'plantilla': str(PLANTILLA), 'portada': {'plantilla': True}, 'diapositivas': d}


# ====================================================================== sustentación (carátula + 5)
def contenido_sustentacion() -> dict:
    """Carátula + 5 diapositivas visuales: lo esencial de cada punto de la guía, con diagramas y capturas."""
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    ro = (om.get('origen_movil') or {}).get('resumen') or {}
    cr = (C or {}).get('resumen', {})
    B = lambda *items: [{'vineta': True, 'texto': i} for i in items]
    d = []
    # 1 · contexto, planteamiento, pregunta, objetivos y justificación
    d.append({'tipo': 'bloques', 'titulo': 'Problema, pregunta y objetivos', 'filas': [
        [{'titulo': 'Contexto y planteamiento del problema', 'w': 1.15, 'cifras': [
            {'valor': '44,90 %', 'etiqueta': 'abandono en cinco cohortes de una universidad ecuatoriana'},
            {'valor': '484 / 1.078', 'etiqueta': 'admitidos que abandonaron (Núñez-Naranjo, 2024)'},
            {'valor': '≈ 0,70', 'etiqueta': 'ROC-AUC típico al validar con cohortes futuras'}],
          'parrafos': B('Las señales ya se registran, pero dispersas: el abandono se mide cuando ya ocurrió.',
                        'La autoridad sin perfil técnico depende de TI para consultar; los datos exigen protección (LOPDP).')},
         {'titulo': 'Pregunta de investigación', 'w': 0.85, 'destacado': True, 'parrafos': [{'texto':
            '¿Cómo puede un sistema web con aprendizaje automático y consulta en lenguaje natural anticipar el '
            'abandono universitario y apoyar la priorización del acompañamiento, protegiendo los datos del estudiante?'}],
          'parrafos_extra': [{'texto': 'Justificación: pasar de medir el abandono a anticiparlo, priorizar los recursos '
                                       'de bienestar y consultar en español sin depender de TI.', 'tam_rel': 0.9}]}],
        [{'titulo': 'Objetivo general', 'w': 1.15, 'parrafos': [{'texto':
            'Desarrollar un prototipo de sistema web que prediga el abandono mediante aprendizaje automático y permita '
            'consultar sus resultados en lenguaje natural, para que autoridades y bienestar estudiantil identifiquen '
            'tempranamente a quienes están en riesgo y prioricen su acompañamiento.'}]},
         {'titulo': 'Objetivos específicos', 'w': 0.85, 'pasos': ['Analizar', 'Construir y validar', 'Implementar', 'Evaluar']}]]})
    # 2 · congruencia, antecedentes, teoría, metodología, unidades, técnicas
    d.append({'tipo': 'bloques', 'titulo': 'Marco de referencia y metodología', 'filas': [
        [{'titulo': 'Matriz de congruencia resumida', 'w': 1.2, 'tabla': {
            'encabezados': ['Problema', 'Objetivo específico', 'Variable', 'Instrumento'],
            'filas': [['Señales dispersas', 'Analizar procesos y variables', 'RF, RNF e historias', '23 RF, 11 RNF, 10 HU'],
                      ['Sin alerta temprana', 'Construir y validar el modelo', 'Riesgo por periodo', 'ROC-AUC y recall temporal'],
                      ['Consulta dependiente de TI', 'Implementar el sistema', 'Panel, ficha, NL2SQL', 'Conjunto dorado'],
                      ['Datos sin protección', 'Evaluar el prototipo', 'Aislamiento', 'Fugas = 0; 8/8 contenidas']],
            'anchos': [1.0, 1.25, 0.9, 1.1]}},
         {'titulo': 'Principales antecedentes', 'w': 0.8, 'tabla': {
            'encabezados': ['Estudio', 'Aporte'],
            'filas': [['Núñez-Naranjo (2024)', 'Evidencia ecuatoriana: 44,90 %'],
                      ['Carballo-Mendívil et al. (2025)', 'Prueba prospectiva: 0,69'],
                      ['Kuzilek et al. (2017)', 'OULAD: 32.593 matrículas reales'],
                      ['Ascoli y Choi (2025)', 'NL2SQL con contexto']],
            'anchos': [1.0, 1.0]}}],
        [{'titulo': 'Fundamentación teórica esencial', 'w': 0.8, 'parrafos': B(
            'Tinto; Bean y Metzner: integración académica y social, factores externos.',
            'Kimball: esquema estrella. LightGBM + Platt + SHAP. NL2SQL con guardarraíles.')},
         {'titulo': 'Metodología: estudio de caso con CRISP-DM', 'w': 1.2,
          'pasos': ['Negocio', 'Datos', 'Preparar', 'Modelar', 'Evaluar', 'Desplegar'],
          'parrafos': B('Unidades de análisis: registro estudiante-periodo. UNEMI_PRUEBAS (sintético, 20.385 de prueba) y OULAD (real, 64.302).',
                        f'Técnicas: validación temporal y de origen móvil; conjunto dorado (40 + 12 + 8); {N_PRUEBAS_BACKEND + N_PRUEBAS_FRONTEND} pruebas automatizadas.')}]]})
    # 3 · solución tecnológica: capas, seguridad, datos, lógica
    d.append({'tipo': 'bloques', 'titulo': 'Solución tecnológica: capas, seguridad, datos y lógica', 'filas': [
        [{'titulo': 'Arquitectura en capas de VicMar', 'w': 1.45, 'imagen': str(DIAGRAMAS / 'av2_arquitectura.png'), 'alto_max': 13.2},
         {'w': 0.7, 'pila': [
            {'titulo': 'Seguridad', 'parrafos': B('JWT con vencimiento y bcrypt', 'Tres roles con capacidades', 'Institución fijada en SESSION_CONTEXT', 'Auditoría y cédulas enmascaradas')},
            {'titulo': 'Base de datos', 'parrafos': B('SQL Server 2022, esquema estrella', 'Vistas VIS_* filtradas por institución', 'Tres cuentas de mínimo privilegio')},
            {'titulo': 'Lógica', 'parrafos': B('LightGBM calibrado + SHAP: tres razones por alerta', 'NL2SQL: 40 métricas certificadas y validador sqlglot', 'K-means para segmentar carreras')}]}]]})
    # 4 · resultados y discusión
    d.append({'tipo': 'bloques', 'titulo': 'Resultados principales y discusión', 'filas': [
        [{'titulo': 'Criterios fijados antes de entrenar: ROC-AUC ≥ 0,75 · recall ≥ 0,75 · consulta ≥ 85 % · fugas = 0', 'cifras': [
            {'valor': f(ut['roc_auc']), 'etiqueta': 'ROC-AUC temporal, UNEMI (prueba)'},
            {'valor': f(ot['roc_auc']), 'etiqueta': 'ROC-AUC temporal, OULAD (real)'},
            {'valor': pct(ot['umbral_medio']['recall'], 0), 'etiqueta': 'abandonos detectados, umbral medio'},
            {'valor': pct(cr.get('exactitud_relajada_total', 1), 0), 'etiqueta': 'exactitud de la consulta'},
            {'valor': '8/8 · 0', 'etiqueta': 'maliciosas contenidas · fugas'}]}],
        [{'titulo': 'Desempeño por periodo (origen móvil)', 'w': 1.3, 'imagen': str(FIGURAS / 'tf_desempeno_periodo.png'), 'alto_max': 8.6},
         {'titulo': 'Discusión', 'w': 0.85, 'parrafos': B(
            'Ambas instituciones superan el 0,75; LightGBM ganó a logística y Random Forest.',
            f'OULAD por periodo: {f(ro.get("roc_auc_min"))} a {f(ro.get("roc_auc_max"))}, coherente con el 0,69 prospectivo de la literatura.',
            'Límite: la UNEMI se evaluó con datos de prueba; la carrera real requiere autorización.')}]]})
    # 5 · conclusiones, recomendaciones, aporte y evidencias
    d.append({'tipo': 'bloques', 'titulo': 'Conclusiones, aporte y evidencias del producto', 'filas': [
        [{'titulo': 'Evidencias: panel ejecutivo · ficha explicada · consulta en lenguaje natural', 'imagenes': [
            str(CAPTURAS / 'av2_cap_panel.png'), str(CAPTURAS / 'av2_cap_ficha.png'), str(CAPTURAS / 'av2_cap_consulta.png')],
          'pie': 'github.com/' + REPO.split('/', 3)[3] + '   ·   carpeta digital en la portada del trabajo'}],
        [{'titulo': 'Conclusiones', 'parrafos': B('El modelo se sostuvo en periodos no vistos con datos reales.',
                                                  'El sistema funciona de punta a punta con tres roles y operación automatizada.',
                                                  'Cumple los criterios predictivos, de consulta y de protección de datos.')},
         {'titulo': 'Recomendaciones', 'parrafos': B('Validar con una carrera real de la UNEMI (procedimiento LOPDP listo).',
                                                     'Revisar los umbrales por carrera y aplicar la prueba de usabilidad.')},
         {'titulo': 'Aporte', 'parrafos': B('Predicción explicada en español dentro de un sistema por roles.',
                                            'Consulta certificada y aislamiento multiinstitución en la base de datos.')}]]})
    return {'plantilla': str(PLANTILLA), 'portada': {'plantilla': True}, 'diapositivas': d, 'cierre': False}


# ====================================================================== tipo de diapositiva «bloques»
def generador_con_bloques(diapositivas, pptx_kit):
    Lienzo, _p = pptx_kit.Lienzo, diapositivas._p
    alto_lineas = pptx_kit.alto_lineas

    class G(diapositivas.Generador):
        def _bloque_alto(self, L, b, w, t):
            e, pad = self.f, 0.45 * self.f
            if b.get('pila'):
                hs = [self._bloque_alto(L, sub, w, t) for sub in b['pila']]
                return sum(hs) + (len(hs) - 1) * 0.5 * e
            h = L.alto_parrafos([_p(b['titulo'], negrita=True, color='acento', tam=t * 1.05)], w, pad) - pad
            if b.get('parrafos'):
                h += L.alto_parrafos([dict(p, espacio_despues=0.18 * e) for p in b['parrafos']], w, pad) - pad
            if b.get('cifras'):
                h += self._cifras_alto(L, b['cifras'], w, t)
            if b.get('pasos'):
                h += self._pasos_alto(L, b['pasos'], w, t) + 0.2 * e
            if b.get('parrafos_extra'):
                h += L.alto_parrafos([dict(p, tam=t * p.get('tam_rel', 1)) for p in b['parrafos_extra']], w, pad) - pad
            if b.get('tabla'):
                h += self._tabla_alto(L, b['tabla'], w - 2 * pad, t)[0] + 0.3 * e
            if b.get('imagen'):
                h += self._img_dims(b, w - 2 * pad)[1] + 0.3 * e
            if b.get('imagenes'):
                from PIL import Image
                n = len(b['imagenes']); g = 0.4 * e; cw = (w - 2 * pad - (n - 1) * g) / n
                h += max(cw * Image.open(r).size[1] / Image.open(r).size[0] for r in b['imagenes']) + 0.3 * e
            if b.get('pie'):
                h += L.alto_parrafos([_p(b['pie'], tam=t * 0.8, cursiva=True)], w, pad) - pad
            return h + 2 * pad

        def _img_dims(self, b, w):
            from PIL import Image
            iw, ih = Image.open(b['imagen']).size
            hi = w * ih / iw
            mx = b.get('alto_max')
            if mx and hi > mx * self.f * 2:      # alto_max en cm de la plantilla grande (67,7 cm)
                hi = mx * self.f * 2
            return hi * iw / ih, hi

        def _pasos_alto(self, L, pasos, w, t):
            e = self.f; n = len(pasos); g = 0.35 * e; cw = (w - 0.9 * e - (n - 1) * g) / n
            return max(L.alto_parrafos([_p(x, negrita=True, color='blanco', alinear='centro', tam=t * 0.74)], cw, 0.25 * e)
                       for k, x in enumerate(pasos))

        def _cifras_alto(self, L, items, w, t):
            e = self.f; n = len(items); g = 0.4 * e; cw = (w - 0.9 * e - (n - 1) * g) / n
            return max(L.alto_parrafos([_p(it['valor'], negrita=True, color='acento', tam=t * 1.7, alinear='centro'),
                                         _p(it['etiqueta'], alinear='centro', tam=t * 0.85)], cw, 0.3 * e) for it in items)

        def _tabla_alto(self, L, tb, w, t):
            enc, filas, anchos = tb['encabezados'], tb['filas'], tb.get('anchos')
            tot = sum(anchos) if anchos else len(enc)
            ws = [w * (a / tot) for a in anchos] if anchos else [w / len(enc)] * len(enc)
            ts = t * 0.85; pad = 0.15 * self.f
            altos = [max(alto_lineas(len(L.lineas(str(v), cw - 2 * pad, ts, k == 0)), ts) + 2 * pad
                         for v, cw in zip(fila, ws)) for k, fila in enumerate([enc] + filas)]
            return sum(altos), ws, altos, ts, pad

        def _bloque_dibujar(self, L, b, x, y, w, h, t):
            e, pad = self.f, 0.45 * self.f
            if b.get('pila'):
                subs = b['pila']; hs = [self._bloque_alto(L, sub, w, t) for sub in subs]
                extra = max(0.0, h - sum(hs) - (len(hs) - 1) * 0.5 * e) / len(hs)
                for sub, hs_ in zip(subs, hs):
                    self._bloque_dibujar(L, sub, x, y, w, hs_ + extra, t)
                    y += hs_ + extra + 0.5 * e
                return
            L.caja(x, y, w, h, relleno='acento_claro' if b.get('destacado') else 'sec_claro', radio=0.35 * e)
            yy = y + pad
            yy += L.texto(x + pad, yy, w - 2 * pad, [_p(b['titulo'], negrita=True, color='acento', tam=t * 1.05)])
            if b.get('cifras'):
                items = b['cifras']; n = len(items); g = 0.4 * e; cw = (w - 2 * pad - (n - 1) * g) / n
                hc = self._cifras_alto(L, items, w, t)
                for i, it in enumerate(items):
                    L.caja(x + pad + i * (cw + g), yy, cw, hc,
                           [_p(it['valor'], negrita=True, color='acento', tam=t * 1.7, alinear='centro'),
                            _p(it['etiqueta'], alinear='centro', tam=t * 0.85)], relleno='blanco', radio=0.25 * e, pad=0.3 * e)
                yy += hc
            if b.get('pasos'):
                pasos = b['pasos']; n = len(pasos); g = 0.35 * e; cw = (w - 2 * pad - (n - 1) * g) / n
                hp = self._pasos_alto(L, pasos, w, t)
                for k, x_ in enumerate(pasos):
                    xx = x + pad + k * (cw + g)
                    L.caja(xx, yy, cw, hp, [_p(x_, negrita=True, color='blanco', alinear='centro', tam=t * 0.74)],
                           relleno='primario', radio=0.25 * e, pad=0.25 * e)
                    if k < n - 1:
                        L.flecha(xx + cw, yy + hp / 2, xx + cw + g, yy + hp / 2, color='acento', grosor=1.5)
                yy += hp + 0.2 * e
            if b.get('parrafos'):
                yy += L.texto(x + pad, yy, w - 2 * pad, [dict(p, espacio_despues=0.18 * e) for p in b['parrafos']])
            if b.get('parrafos_extra'):
                yy += L.texto(x + pad, yy, w - 2 * pad, [dict(p, tam=t * p.get('tam_rel', 1)) for p in b['parrafos_extra']])
            if b.get('tabla'):
                tb = b['tabla']; total, ws, altos, ts, tpad = self._tabla_alto(L, tb, w - 2 * pad, t)
                xx, y_t = x + pad, yy + 0.15 * e
                for i, fila in enumerate([tb['encabezados']] + tb['filas']):
                    cx = xx
                    for j, v in enumerate(fila):
                        L.caja(cx, y_t, ws[j], altos[i], [_p(str(v), tam=ts, negrita=(i == 0), color='blanco' if i == 0 else 'texto')],
                               relleno='primario' if i == 0 else ('blanco' if i % 2 else 'neutro_claro'), radio=0, forma='rect',
                               pad=tpad, ancla='medio')
                        cx += ws[j]
                    y_t += altos[i]
                yy = y_t + 0.15 * e
            if b.get('imagen'):
                yy += 0.15 * e
                wi, hi = self._img_dims(b, w - 2 * pad)
                yy += L.imagen(x + pad + (w - 2 * pad - wi) / 2, yy, wi, b['imagen'], h=hi) + 0.15 * e
            if b.get('imagenes'):
                from PIL import Image
                n = len(b['imagenes']); g = 0.4 * e; cw = (w - 2 * pad - (n - 1) * g) / n
                hs = []
                for i, r in enumerate(b['imagenes']):
                    hs.append(L.imagen(x + pad + i * (cw + g), yy + 0.15 * e, cw, r))
                yy += max(hs) + 0.3 * e
            if b.get('pie'):
                L.texto(x + pad, yy, w - 2 * pad, [_p(b['pie'], tam=t * 0.8, cursiva=True, color='neutro')])

        def _bloques(self, L, d, x, y0, t):
            e, g = self.f, 0.6 * self.f
            y = y0
            for fila in d['filas']:
                pesos = [b.get('w', 1.0) for b in fila]
                tot = sum(pesos)
                ws = [(self.bw - (len(fila) - 1) * g) * p / tot for p in pesos]
                hs = [self._bloque_alto(L, b, w, t) for b, w in zip(fila, ws)]
                h = max(hs)
                xx = x
                for b, w in zip(fila, ws):
                    self._bloque_dibujar(L, b, xx, y, w, h, t)
                    xx += w + g
                y += h + g
            return y - y0 - g

    diapositivas.RANGOS['bloques'] = (26, 40)   # 13 a 20 pt reales en la plantilla de 33,9 cm
    return G


# ====================================================================== carátulas
def caratula(pptx: Path, tipo: str, autores: list[str], docentes: list[str]) -> None:
    from pptx import Presentation
    prs = Presentation(str(pptx))
    s = prs.slides[0]
    for sh in s.shapes:
        if not sh.has_text_frame:
            continue
        t = sh.text_frame.text.strip()
        if t.startswith('DESARROLLO DEL TRABAJO') or t.startswith('TRABAJO FINAL'):
            tf._texto(sh, tipo)
        elif t.startswith('DESARROLLO DE UN MODELO') or t.startswith('PROTOTIPO DE UN SISTEMA'):
            tf._texto(sh, TITULO.upper() + '.')
        elif t.startswith('ESTUDIANTES'):
            _lineas(sh, autores, 13 if len(autores) == 2 else 15)
        elif t.startswith('DOCENTES'):
            _lineas(sh, docentes, 14)
            sh.top = sh.top - int(0.5 * 360000)
    prs.save(str(pptx))


def _lineas(sh, lineas: list[str], pt: int) -> None:
    """Varias líneas en el mismo cuadro de la carátula, con el formato del primer run y tamaño uniforme."""
    from pptx.util import Pt
    tf._texto(sh, lineas[0])
    p0 = sh.text_frame.paragraphs[0]
    r0 = p0.runs[0]
    r0.font.size = Pt(pt)
    for ln in lineas[1:]:
        p0.add_line_break()
        r = p0.add_run()
        r.text = ln
        r.font.size, r.font.bold, r.font.name = Pt(pt), r0.font.bold, r0.font.name
        if r0.font.color and r0.font.color.type is not None:
            r.font.color.rgb = r0.font.color.rgb


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--kit', required=True)
    ap.add_argument('--salida', default=str(SALIDA))
    a = ap.parse_args()
    sys.path.insert(0, a.kit)
    from academico import diapositivas, pptx_kit
    out = Path(a.salida); out.mkdir(parents=True, exist_ok=True)
    res = {}
    EST = ['ESTUDIANTES: ' + MARLON.upper(), VICTOR.upper()]
    TUT1, TUT2 = 'MSC. PERALTA CORREA MIRELLA AZUCENA', 'MSC. ESPINOZA BRAVO MARÍA GABRIELA'
    DOC = ['DOCENTES: ' + TUT1, TUT2]
    # Avance 2
    p2 = out / 'Presentacion_AVANCE2_Marlon_Victor.pptx'
    res['avance2'] = diapositivas.generar(contenido_avance2(), str(p2))
    caratula(p2, 'AVANCE 2 · DESARROLLO DEL TRABAJO DE TITULACIÓN', EST, DOC)
    # Avance 3 (contenido del trabajo final)
    p3 = out / 'Presentacion_AVANCE3_Marlon_Victor.pptx'
    c3 = tf.contenido()
    res['avance3'] = diapositivas.generar(c3, str(p3))
    caratula(p3, 'AVANCE 3 · TRABAJO FINAL DE TITULACIÓN', EST, DOC)
    # Sustentación individual (carátula + 5)
    G = generador_con_bloques(diapositivas, pptx_kit)
    for apellido, nombre in (('PerezAlmachi_Marlon', MARLON), ('LluilemaPisco_Victor', VICTOR)):
        ps = out / f'Sustentacion_{apellido}.pptx'
        res[apellido] = G(contenido_sustentacion()).construir(str(ps))
        caratula(ps, 'SUSTENTACIÓN DEL TRABAJO DE TITULACIÓN',
                 [f'AUTORES: {MARLON.upper()} · {VICTOR.upper()}', f'EXPONE: {nombre.upper()}'],
                 ['TUTORAS: ' + TUT1, TUT2])
    print(json.dumps(res, ensure_ascii=False, indent=1))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

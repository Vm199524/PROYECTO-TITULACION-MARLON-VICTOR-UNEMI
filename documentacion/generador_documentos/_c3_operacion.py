# -*- coding: utf-8 -*-
"""Bloques del capítulo 3 que atienden la tutoría del Avance 2: desempeño por periodo y por carrera
(con validación de origen móvil) y operación del modelo (calidad de datos, deriva, MLflow y Metabase).

Todas las cifras se leen de ml/modelos/<institución>/*.json.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from _datos import CAPTURAS, FIGURAS, O, U, bonito, ent, f, pct


def _om(m: dict) -> tuple[list[dict], dict]:
    om = m.get('origen_movil') or {}
    return om.get('periodos', []), om.get('resumen', {})


def _v(x, d=3):
    return f(x, d) if x is not None else '—'


def _desempeno_por_periodo(um: dict, om: dict) -> list[tuple]:
    b: list[tuple] = []
    a = b.append
    pu, ru = _om(um)
    po, ro = _om(om)
    if not (pu or po):
        return b
    car_o = [c for c in om.get('por_carrera', []) if c.get('evaluable')]
    car_u = [c for c in um.get('por_carrera', []) if c.get('evaluable')]
    auc_car_u = [c['roc_auc'] for c in car_u]
    a(('p', '**Desempeño por periodo y por carrera.** Una cifra global puede ocultar que el modelo acierta en un '
            'periodo y falla en otro, o que sirve en unas carreras y no en otras. Por eso, siguiendo la '
            'recomendación de la tutoría, la validación se desagregó de dos formas. La primera es la validación con '
            '**origen móvil** (*backtesting*): para cada uno de los periodos más recientes se entrenó el modelo solo '
            'con los periodos anteriores, se calibró y se fijaron los umbrales con predicciones fuera de pliegue de '
            'ese pasado, y se evaluó una sola vez en el periodo siguiente, como si el sistema se hubiera puesto en '
            'marcha en esa fecha (Tashman, 2000). La {T:origen_movil} y la {F:periodos} muestran el resultado. En OULAD, con datos '
            f'reales, el ROC-AUC por periodo osciló entre {_v(ro.get("roc_auc_min"))} y {_v(ro.get("roc_auc_max"))} '
            f'(media {_v(ro.get("roc_auc_media"))}) y el recall del umbral medio promedió '
            f'{pct(ro.get("recall_medio_media") or 0, 0)}; en UNEMI, entre {_v(ru.get("roc_auc_min"))} y '
            f'{_v(ru.get("roc_auc_max"))} (media {_v(ru.get("roc_auc_media"))}). Que el peor periodo se mantenga '
            'cerca de la media indica que el desempeño no depende de una cohorte favorable, y todos los periodos superan '
            'el mínimo de 0,70 del RNF-11. En OULAD solo hay cuatro presentaciones, por lo que el origen móvil evalúa '
            'las dos últimas, cada una con al menos dos periodos de entrenamiento; la más reciente queda por debajo de '
            '0,75, lo que confirma que conviene vigilar el desempeño periodo a periodo y no solo la cifra global.'))
    filas = []
    for nombre, lista in (('UNEMI (prueba)', pu), ('OULAD (real)', po)):
        for r in lista:
            filas.append([nombre, r['periodo'], f"{r['periodos_entrenamiento']} ({ent(r['filas_entrenamiento'])})",
                          f"{ent(r['n'])} ({ent(r['positivos'])})", _v(r['roc_auc']), _v(r['pr_auc']),
                          pct(r['recall_medio'] or 0, 0), pct(r['recall_alto'] or 0, 0)])
    a(('tab', 'origen_movil', 'Validación con Origen Móvil: Desempeño de cada Periodo Predicho con el Pasado',
       ['Institución', 'Periodo evaluado', 'Periodos (filas) de entrenamiento', 'Casos (abandonos)', 'ROC-AUC',
        'PR-AUC', 'Recall medio', 'Recall alto'], filas,
       'Recall con los umbrales de riesgo medio (objetivo 0,80) y alto (objetivo 0,50) fijados en cada origen solo con '
       'datos anteriores. Elaboración propia a partir de ml/modelos/*/metricas.json.',
       [2.3, 1.8, 2.4, 2.3, 1.6, 1.6, 1.7, 1.7]))
    a(('fig', 'periodos', 'ROC-AUC y Recall por Periodo con Origen Móvil', FIGURAS / 'tf_desempeno_periodo.png', 16.0,
       'Gráfico de líneas del ROC-AUC y del recall por periodo evaluado en UNEMI y OULAD',
       'La línea punteada marca el mínimo por periodo de 0,70 (RNF-11). Elaboración propia.'))
    if car_o:
        texto_u = ''
        if auc_car_u:
            bajo = sum(1 for x in auc_car_u if x < 0.70)
            texto_u = (f' En UNEMI, las {len(car_u)} carreras con casos suficientes en la prueba obtuvieron un ROC-AUC '
                       f'de {_v(min(auc_car_u))} a {_v(max(auc_car_u))}' +
                       (f' y {bajo} quedaron por debajo de 0,70.' if bajo else ', todas sobre 0,70.'))
        bajos = sorted((c for c in car_o if c['roc_auc'] < 0.70), key=lambda c: c['roc_auc'])
        sobre = len(car_o) - len(bajos)
        texto_bajos = ''
        if bajos:
            def _mod(c):
                return bonito(c['grupo']).replace('Modulo', 'módulo')
            texto_bajos = (
                (' Los módulos ' + ' y '.join(bonito(c['grupo']).replace('Modulo ', '') for c in bajos)
                 + ' quedaron' if len(bajos) > 1 else ' El ' + _mod(bajos[0]) + ' quedó') + ' por debajo de 0,70: '
                + '; '.join(f'{_mod(c)} con {ent(c["positivos"])} abandonos de {ent(c["n"])} casos (prevalencia '
                            f'{pct(c["prevalencia"] or 0)}), ROC-AUC {_v(c["roc_auc"])} y recall '
                            f'{pct(c["recall_medio"] or 0, 0)}' for c in bajos)
                + '. Con tan pocos abandonos la estimación es inestable, y el recall muy bajo de un módulo muestra '
                  'que un único umbral para toda la institución no sirve igual en todas las unidades: es un hallazgo '
                  'que justifica revisar los umbrales por carrera antes de usar las alertas en ellas.')
        a(('p', 'La segunda desagregación es **por carrera** dentro de la prueba temporal ({T:por_carrera}). En OULAD, '
                'cada módulo hace las veces de carrera: son cursos reales de la Open University con estudiantes, '
                f'modalidad y evaluación distintos. El ROC-AUC fue de {_v(min(c["roc_auc"] for c in car_o))} a '
                f'{_v(max(c["roc_auc"] for c in car_o))}; {sobre} de los {len(car_o)} módulos superaron el mínimo de '
                '0,70 que se exige por periodo (RNF-11).' + texto_bajos + texto_u + ' Este resultado responde, con '
                'datos reales anonimizados, a la recomendación de reportar el AUC y el recall por unidad académica; la '
                'validación con una carrera de la UNEMI requiere la autorización y el procedimiento de anonimización '
                'del documento de gobierno de datos (Anexo C).'))
        filas_c = [[bonito(c['grupo']).replace('Modulo', 'Módulo'), f"{ent(c['n'])} ({ent(c['positivos'])})",
                    pct(c['prevalencia'] or 0), _v(c['roc_auc']), _v(c['pr_auc']), pct(c['recall_medio'] or 0, 0),
                    pct(c['precision_alto'] or 0, 0)] for c in sorted(car_o, key=lambda c: c['grupo'])]
        a(('tab', 'por_carrera', 'Desempeño por Módulo (Carrera) en OULAD, Prueba Temporal',
           ['Módulo', 'Casos (abandonos)', 'Prevalencia', 'ROC-AUC', 'PR-AUC', 'Recall medio', 'Precisión alta'],
           filas_c, 'Periodos de prueba ' + ', '.join(om['validacion_temporal']['periodos']) +
           '. Elaboración propia a partir de ml/modelos/OULAD_UK/metricas.json.', [2.6, 2.6, 2.0, 1.8, 1.8, 2.0, 2.0]))
    return b


def _operacion_modelo() -> list[tuple]:
    b: list[tuple] = []
    a = b.append
    cu, co = U.get('cal') or {}, O.get('cal') or {}
    du, do = U.get('der') or {}, O.get('der') or {}
    mu, mo = U.get('mlf') or {}, O.get('mlf') or {}
    a(('p', 'La {T:mlops} resume las herramientas de operación incorporadas y la evidencia que cada una deja. Las tres '
            'primeras corren automáticamente en el paso «mlops» del pipeline, después de calificar a los estudiantes '
            'activos; Metabase es una vía de consulta alternativa para analistas.'))
    a(('tab', 'mlops', 'Herramientas de Operación del Modelo (MLOps) Incorporadas al Prototipo',
       ['Herramienta', 'Qué hace en el sistema', 'Evidencia que produce'],
       [['MLflow (Zaharia et al., 2018)', 'Registra cada entrenamiento como una ejecución del experimento de la institución: algoritmo, '
                   'hiperparámetros, umbrales, métricas de validación cruzada, temporal y por periodo, y el paquete '
                   'del modelo.', 'Base de experimentos y mlflow_registro.json'],
        ['Great Expectations', 'Valida la trayectoria del almacén antes de entrenar: integridad de claves, '
                               'catálogos, rangos (promedio 0-10, asistencia 0-100) y volumen. Una falla crítica '
                               'detiene el pipeline.', 'calidad_datos.json y la pestaña «Datos y deriva»'],
        ['Evidently', 'Compara la distribución de cada variable de entrada entre el entrenamiento y los estudiantes '
                      'que se califican, en los mismos cortes de evaluación.', 'deriva.json e informe HTML '
                                                                           'interactivo'],
        ['SHAP', 'Explica cada predicción con los factores que más la suben o la bajan.', 'Tres factores por '
                                                                                         'estudiante en la ficha'],
        ['Metabase', 'Tableros y preguntas con clics sobre un esquema agregado (bi) sin datos personales y con una '
                     'cuenta de solo lectura.', 'docker-compose y vistas bi.VIS_BI_*']],
       'Elaboración propia a partir de backend/mlops/ y despliegue/metabase/.', [3.0, 8.6, 4.4]))
    if cu or co:
        a(('p', f'**Calidad de los datos.** En la última corrida, la trayectoria de UNEMI cumplió '
                f'{cu.get("cumplidas", "n. d.")} de {cu.get("evaluadas", "n. d.")} expectativas y la de OULAD '
                f'{co.get("cumplidas", "n. d.")} de {co.get("evaluadas", "n. d.")} '
                f'({cu.get("motor", co.get("motor", ""))}); ambas quedaron aptas para entrenar. Las expectativas '
                'no críticas, como la completitud de la asistencia o la modalidad dentro del catálogo, se informan sin '
                'detener el proceso, para que el área de TI corrija la fuente.'))
    if du or do:
        def lectura(d, nombre):
            imp = d.get('importantes_con_deriva') or []
            return (f'en {nombre}, {d.get("variables_con_deriva")} de {len(d.get("variables", []))} variables cambiaron '
                    f'de distribución ({pct(d.get("proporcion_con_deriva") or 0, 0)})' +
                    (f', entre ellas {" y ".join(imp[:3]) if len(imp) < 3 else ", ".join(imp[:2]) + " y " + imp[2]}' if imp else '') +
                    ('; el conjunto se marca para reentrenar' if d.get('conjunto_con_deriva') else
                     '; el conjunto queda por debajo del umbral de la mitad que obliga a reentrenar'))
        partes = [lectura(d, n) for d, n in ((du, 'UNEMI'), (do, 'OULAD')) if d]
        a(('p', '**Deriva de los datos.** Evidently comparó a los estudiantes que se califican hoy con los del '
                'entrenamiento, en el mismo corte de evaluación: ' + '; '.join(partes) + '. En OULAD, las variables '
                'importantes con deriva son los días sin actividad en el aula virtual y la proporción de entregas '
                'tardías, que cambian mientras la última presentación está en curso; es el tipo de cambio que el '
                'monitoreo debe detectar antes de que la autoridad confíe en una alerta (Gama et al., 2014). El '
                'índice de estabilidad poblacional (PSI) se mantiene como segunda medida.'))
    if mu or mo:
        a(('p', '**Registro de experimentos.** Cada entrenamiento quedó como una ejecución de MLflow en el experimento '
                f'de su institución ({mu.get("experimento", "abandono-UNEMI_PRUEBAS")} y '
                f'{mo.get("experimento", "abandono-OULAD_UK")}), con {mu.get("parametros", mo.get("parametros", "n. d."))} '
                f'parámetros y {mu.get("metricas", mo.get("metricas", "n. d."))} métricas. Así, ante cualquier alerta, se '
                'puede responder con qué datos, con qué parámetros y con qué resultados se entrenó el modelo que la '
                'produjo, y comparar un reentrenamiento con el anterior antes de publicarlo.'))
    a(('p', 'La autoridad no necesita abrir estas herramientas: la pestaña «Datos y deriva» de la página Calidad del '
            'modelo ({F:cap_deriva}) muestra el resultado de las tres en lenguaje sencillo, y la pestaña «Por periodo y '
            'carrera» muestra la validación con origen móvil.'))
    a(('fig', 'cap_deriva', 'Pestaña «Datos y Deriva» de la Página Calidad del Modelo', CAPTURAS / 'tf_cap_deriva.png',
       15.0, 'Captura de la página Calidad del modelo con las expectativas cumplidas, las variables con deriva y el '
             'experimento registrado en MLflow',
       'Captura del prototipo con el rol de autoridad académica, institución UNEMI (datos de prueba). Elaboración propia.'))
    a(('p', '**Consulta alternativa con Metabase.** Metabase se incorporó como segunda vía de consulta para el analista '
            'institucional, no como reemplazo de la consulta conversacional. Lee solo el esquema bi, con agregados de '
            'cinco o más estudiantes y sin cédulas ni nombres, mediante la cuenta metabase_lector, que tiene negada '
            'la lectura del esquema dbo. Ambas vías leen el mismo almacén, por lo que sus cifras coinciden; la '
            'consulta en lenguaje natural sigue siendo la indicada para la autoridad sin perfil técnico.'))
    return b

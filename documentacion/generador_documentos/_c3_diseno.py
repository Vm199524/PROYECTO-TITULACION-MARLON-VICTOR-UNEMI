# -*- coding: utf-8 -*-
"""Capítulo 3: metodología CRISP-DM, resultados de validación, diseño y desarrollo.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from _c3_operacion import _desempeno_por_periodo, _operacion_modelo
from _datos import N_PRUEBAS_BACKEND, C, C_ORIGEN, CAPTURAS, DIAGRAMAS, EXP_O, EXP_U, FIGURAS, LAT, NOMBRE_MODELO, O, U, bonito, cv, ent, f, pct


def _filas_cv(m: dict) -> list[list[str]]:
    filas = []
    for k in ('LOGISTICA', 'RF_PONDERADO', 'RF_SMOTE', 'LIGHTGBM'):
        filas.append([NOMBRE_MODELO[k] + (' (elegido)' if k == m['modelo_final'] else ''), cv(m, k, 'roc_auc'),
                      cv(m, k, 'pr_auc')])
    return filas


def bloques() -> list[tuple]:
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    us, os_ = U['s'], O['s']
    up, op = um['panel'], om['panel']
    pr = O['p']
    mon_u, mon_o = U['mon'], O['mon']
    bss_u = 1 - ut['brier_calibrado'] / (ut['prevalencia'] * (1 - ut['prevalencia']))
    bss_o = 1 - ot['brier_calibrado'] / (ot['prevalencia'] * (1 - ot['prevalencia']))
    b: list[tuple] = []
    a = b.append

    a(('h1', '3. Diseño y desarrollo del trabajo práctico'))
    a(('h2', '3.1 Metodología'))
    a(('h3', '3.1.1 Enfoque y marco de trabajo'))
    a(('p', 'El trabajo combina dos marcos. Para la parte analítica se siguió CRISP-DM (Wirth y Hipp, 2000), que '
            'organiza un proyecto de minería de datos en seis fases iterativas: comprensión del negocio, comprensión '
            'de los datos, preparación, modelado, evaluación y despliegue. Para la construcción del software se trabajó '
            'por incrementos cortos, cada uno cerrado con pruebas automatizadas y una revisión visual de la interfaz. '
            'La {F:crisp} muestra las fases, el entregable principal de cada una y el artefacto del repositorio que '
            'lo contiene; la {T:entregables} sistematiza esos entregables.'))
    a(('fig', 'crisp', 'Fases de CRISP-DM y Entregables del Proyecto', DIAGRAMAS / 'av2_crisp_dm.png', 16.0,
       'Ciclo CRISP-DM con seis fases y los entregables del proyecto en cada una',
       'Elaboración propia a partir de Wirth y Hipp (2000).'))
    a(('tab', 'entregables', 'Entregables por Fase de CRISP-DM',
       ['Fase', 'Entregable', 'Artefacto en el repositorio'],
       [['1. Comprensión del negocio', 'Objetivos, criterios de éxito, historias de usuario y requerimientos',
         'Capítulos 1 y 2 de este documento'],
        ['2. Comprensión de los datos', 'Inventario de fuentes, simulador, perfil de calidad y análisis '
                                        'exploratorio', 'datos_de_prueba/generate_historial.py; scripts/cargar_oulad.py; '
                                                        'ml/exploracion.py'],
        ['3. Preparación', 'Almacén estrella, perfiles de mapeo, ETL y panel estudiante-periodo',
         'crear_almacen_academico.sql; etl/; ml/caracteristicas.py'],
        ['4. Modelado', 'Cuatro modelos comparados, calibración, umbrales y segmentación', 'ml/entrenar.py; '
                                                                                          'ml/segmentar.py'],
        ['5. Evaluación', 'Validación cruzada, temporal y prospectiva; equidad; conjunto dorado de la consulta',
         'ml/modelos/*/metricas.json; eval/'],
        ['6. Despliegue', 'API, interfaz web, consulta conversacional, reportes, instalador y pruebas',
         'api/; nl2sql/; frontend/; scripts/; tests/']],
       'Elaboración propia.', [3.6, 6.6, 5.8]))

    # ── Fase 1 ────────────────────────────────────────────────────────────
    a(('h3', '3.1.2 Fase 1: comprensión del negocio'))
    a(('p', 'En esta fase se tradujeron las necesidades de la autoridad académica, documentadas en los capítulos 1 y 2, '
            'a preguntas que un modelo o una consulta pueden responder. La {T:negocio} muestra esa traducción: para '
            'cada objetivo institucional se define la pregunta analítica, la variable o el resultado que la responde, '
            'la métrica con que se juzgará y la restricción que no puede violarse. La decisión central fue el '
            'horizonte: se predice si un estudiante activo al cierre del periodo t aparecerá como retirado en t+1, '
            'porque ese plazo deja un periodo completo para intervenir. Graduarse o egresar no cuenta como abandono.'))
    a(('tab', 'negocio', 'Del Objetivo Institucional al Objetivo Analítico',
       ['Objetivo institucional', 'Pregunta analítica', 'Respuesta del sistema', 'Métrica', 'Restricción'],
       [['Reducir el abandono', '¿Quién no se matriculará en el periodo siguiente?', 'Probabilidad calibrada por '
                                                                                    'estudiante', 'ROC-AUC, recall',
         'Solo datos conocidos al cierre de t'],
        ['Priorizar recursos escasos', '¿A quién contactar primero?', 'Lista ordenada y umbrales de riesgo',
         'Captura en el 10 y 20 % superior', 'Capacidad de bienestar'],
        ['Focalizar por carrera', '¿Qué carreras concentran el riesgo?', 'Segmentos de carreras', 'Silueta, '
                                                                                               'estabilidad',
         'Nombres comprensibles'],
        ['Consultar sin depender de TI', '¿Cuántos, dónde, cuándo?', 'Respuesta en español', 'Exactitud por '
                                                                                            'ejecución',
         'Solo lectura de vistas'],
        ['Cumplir la LOPDP', 'No aplica', 'Controles de acceso y auditoría', 'Fugas entre instituciones = 0',
         'Minimización y finalidad']],
       'Elaboración propia.', [3.0, 3.6, 3.4, 3.0, 3.0]))

    # ── Fase 2 ────────────────────────────────────────────────────────────
    a(('h3', '3.1.3 Fase 2: comprensión de los datos'))
    a(('p', 'Se trabajó con dos fuentes ({T:fuentes}). La primera son datos de prueba con la estructura de la UNEMI '
            '(dos sedes, 18 carreras, tres modalidades y semestres de 2019-1 a 2026-1), generados por un simulador '
            'propio porque el proyecto no dispone todavía de autorización para usar datos reales de estudiantes. La '
            'segunda es OULAD, un conjunto real y anonimizado de la Open University del Reino Unido, que permite '
            'comprobar el sistema con comportamiento humano auténtico. En todo el documento, las cifras rotuladas '
            '«UNEMI» corresponden a estos datos de prueba y no describen a estudiantes reales de la universidad.'))
    a(('tab', 'fuentes', 'Fuentes de Datos del Caso Práctico',
       ['Característica', 'UNEMI (datos de prueba)', 'OULAD (datos reales)'],
       [['Naturaleza', 'Sintéticos, estructura de la UNEMI', 'Reales anonimizados (Kuzilek et al., 2017)'],
        ['Unidad de periodo', 'Semestre (2019-1 a 2026-1)', 'Corte de 28 días dentro de cada presentación'],
        ['Estudiantes', ent(up['estudiantes']), ent(op['estudiantes'])],
        ['Registros del panel', ent(up['filas']), ent(op['filas'])],
        ['Registros etiquetados', ent(up['etiquetadas']), ent(op['etiquetadas'])],
        ['Abandonos en t+1', f"{ent(up['positivos'])} ({pct(up['prevalencia'], 2)})",
         f"{ent(op['positivos'])} ({pct(op['prevalencia'], 2)})"],
        ['Unidades académicas', '18 carreras, 2 sedes, 3 modalidades', '7 módulos, modalidad en línea'],
        ['Activos por calificar', ent(up['para_calificar']), ent(op['para_calificar'])],
        ['Grupos de variables', ', '.join(um['grupos_de_variables']), ', '.join(om['grupos_de_variables'])]],
       'Elaboración propia a partir de ml/modelos/*/metricas.json.', [4.0, 6.0, 6.0]))
    a(('p', '**Simulador de datos de prueba.** Cada estudiante recibe factores latentes de capacidad académica, '
            'compromiso (que cambia entre periodos con choques aleatorios) y vulnerabilidad económica; de ellos se '
            'derivan, con ruido, su promedio, asistencia, mora, actividad en el aula virtual, entregas, créditos y '
            'anticipación de la matrícula. Al cierre de cada periodo, la probabilidad de retirarse en el siguiente es '
            'una función logística de lo observado más un componente que el sistema nunca ve (familia, trabajo, '
            'motivación), lo que impide una separación perfecta. La {T:simulador} detalla los coeficientes, que '
            'siguen la dirección que proponen Tinto (1975) y Bean y Metzner (1985); quien reprueba por tercera vez '
            'un nivel pierde la carrera, como establece la regla ecuatoriana de la tercera matrícula. La semilla fija '
            '(20260909) hace el conjunto reproducible.'))
    a(('tab', 'simulador', 'Coeficientes del Riesgo de Retiro en el Simulador (Escala Logit)',
       ['Término', 'Efecto en el logit', 'Interpretación'],
       [['Intercepto', '−4,75', 'Cerca de 10 % de retiro por periodo en primer año y 3 % al final'],
        ['Dificultad de la carrera', '−0,20 a +0,45', 'Mayor en ingenierías; menor en educación'],
        ['Nivel cursado', '+0,75 (1-2); +0,25 (3-4); −0,20 (5 o más)', 'Primer año más riesgoso'],
        ['Promedio bajo 7', '+0,85 por punto', 'Bajo la nota de aprobación'],
        ['Caída del promedio', '+0,45 por punto', 'Deterioro frente al periodo anterior'],
        ['Asistencia bajo 82 %', '+0,045 por punto', 'Integración académica (Tinto)'],
        ['Saldo pendiente', '+0,70; +0,35 más si no tiene beca', 'Factor externo (Bean y Metzner)'],
        ['Beca de 50 % o más', '−0,35', 'Apoyo económico'],
        ['Número de matrícula', '+0,55 por repetición', 'Segunda y tercera matrícula'],
        ['Días sin actividad sobre 9', '+0,035 por día', 'Desconexión del aula virtual'],
        ['Evaluaciones no entregadas', '+0,16 por evaluación', 'Incumplimiento'],
        ['Matrícula tardía; menos de 18 créditos', '+0,30; +0,25', 'Compromiso y carga'],
        ['Componente no observado', 'Normal (0; 0,55) fijo + (0; 0,45) por periodo', 'Lo que el sistema no ve']],
       'Elaboración propia a partir de base_de_datos/datos_de_prueba/generate_historial.py.',
       [4.6, 5.0, 6.4]))
    eu, eo = EXP_U, EXP_O
    if eu and eo:
        def rango(e):
            t = [x['tasa'] for x in e['tasa_por_periodo']]
            return f"{pct(min(t))} a {pct(max(t))}"

        def faltantes(e):
            reales = {k: v for k, v in e['faltantes_opcionales'].items() if 0 < v < 1}
            ausentes = [k for k, v in e['faltantes_opcionales'].items() if v == 1]
            texto = '; '.join(f'{k}: {pct(v)}' for k, v in reales.items()) or 'Ninguno'
            return texto + (f'; sin datos de cartera ({len(ausentes)} columnas)' if ausentes else '')

        def estados(e):
            return ', '.join(f'{k.lower()} {ent(v)}' for k, v in sorted(e['estados_finales'].items(), key=lambda x: -x[1]))
        a(('p', 'El perfil de ambas fuentes ({T:perfil}) muestra datos completos en las columnas obligatorias y sin '
                'valores fuera de rango. En OULAD no existe información de cartera, por lo que ese grupo de variables '
                'se desactiva automáticamente, y la nota de evaluaciones falta cuando el estudiante aún no entrega '
                'ninguna. En los datos de prueba, la proporción de retiros entre quienes ya cerraron su trayectoria '
                f'({pct(eu["estados_finales"].get("RETIRADO", 0) / max(1, sum(v for k, v in eu["estados_finales"].items() if k != "ACTIVO")))}) '
                'es mayor que el 44,90 % informado por Núñez-Naranjo (2024), porque una ventana de 2019 a 2026 '
                'cierra antes las trayectorias cortas, que terminan en retiro, que las largas, que terminan en '
                'graduación; la tasa por periodo, que es la que predice el modelo, no tiene ese sesgo.'))
        a(('tab', 'perfil', 'Perfil y Calidad de los Datos de Origen', ['Indicador', 'UNEMI (datos de prueba)',
                                                                         'OULAD (datos reales)'],
           [['Registros de trayectoria', ent(eu['registros']), ent(eo['registros'])],
            ['Estudiantes distintos', ent(eu['estudiantes']), ent(eo['estudiantes'])],
            ['Periodos o presentaciones', str(eu['periodos']), str(eo['periodos'])],
            ['Carreras o módulos', str(eu['carreras']), str(eo['carreras'])],
            ['Estado final', estados(eu), estados(eo)],
            ['Faltantes en columnas opcionales', faltantes(eu), faltantes(eo)],
            ['Valores fuera de rango', '0', '0'],
            ['Abandono en t+1 por periodo', rango(eu), rango(eo)]],
           'Elaboración propia a partir de ml/modelos/*/exploracion.json, generado por ml/exploracion.py.',
           [4.4, 5.8, 5.8]))
        gu, go = eu['tasa_por_grupo'], eo['tasa_por_grupo']

        def g(d, var, i):
            return pct(d[var]['grupos'][i]['tasa'])
        a(('p', 'El análisis exploratorio confirma las relaciones que sustentan el modelo ({F:eda_u} y {F:eda_o}). En '
                f'los datos de prueba, el abandono en t+1 pasa de {g(gu, "promedio_t", -1)} con promedio de 8 o más a '
                f'{g(gu, "promedio_t", 0)} con promedio menor a 5, y de {g(gu, "numero_matricula", 0)} en primera '
                f'matrícula a {g(gu, "numero_matricula", 1)} en segunda. En OULAD, con datos reales, la relación es '
                f'más débil pero consistente: {g(go, "dias_sin_actividad", 0)} entre quienes tuvieron actividad en '
                f'los últimos tres días frente a {g(go, "dias_sin_actividad", -1)} entre quienes llevan más de dos '
                f'semanas sin conectarse, y {g(go, "pct_entregadas", -1)} frente a {g(go, "pct_entregadas", 0)} '
                'según entreguen todas sus evaluaciones o menos de la mitad. Ninguna variable separa por sí sola a '
                'quienes abandonan, lo que justifica un modelo que combine varias.'))
        a(('fig', 'eda_u', 'Abandono en t + 1 según Variables Clave en UNEMI (Datos de Prueba)',
           FIGURAS / 'UNEMI_PRUEBAS_exploracion.png', 15.0, 'Tres gráficos de barras con la tasa de abandono por '
                                                            'grupos de promedio, asistencia y número de matrícula',
           'Registros etiquetados del panel. Elaboración propia.'))
        a(('fig', 'eda_o', 'Abandono en el Corte Siguiente según Variables Clave en OULAD',
           FIGURAS / 'OULAD_UK_exploracion.png', 15.0, 'Tres gráficos de barras con la tasa de abandono por grupos de '
                                                       'promedio, días sin actividad y entregas',
           'Registros etiquetados del panel. Elaboración propia.'))

    # ── Fase 3 ────────────────────────────────────────────────────────────
    a(('h3', '3.1.4 Fase 3: preparación de los datos'))
    a(('p', 'Cada institución se incorpora mediante un **perfil de mapeo** (etl/perfiles.py): una consulta que lleva '
            'las columnas de su sistema de origen al contrato del almacén. El ETL valida el contrato, aplica las reglas '
            'de calidad (estados válidos, promedios entre 0 y 10, asistencia entre 0 y 100), reemplaza solo los hechos '
            'de esa institución y carga las dimensiones y la tabla de hechos por lotes; su flujo se detalla en el '
            'diagrama de actividades de la sección 3.2.3. En la carga de este avance no se rechazó ningún registro: '
            f'entraron {ent(up["filas"])} registros de UNEMI y {ent(op["filas"])} de OULAD. Los faltantes no se '
            'imputan en el almacén: se conservan como nulos, LightGBM y Random Forest los tratan de forma nativa y la '
            'regresión logística y SMOTE los imputan con la mediana dentro de su propio flujo de entrenamiento. Con '
            'este diseño, OULAD se incorporó escribiendo un perfil nuevo y sin modificar el código del modelo.'))
    a(('p', 'A partir del almacén se construye el panel estudiante-periodo. Para evitar fuga de información, cada '
            'variable usa solo lo que se conocía al cierre del periodo t: promedios y asistencias actuales, rezagados '
            'y acumulados, tendencias, comparación con la cohorte, mora, carga matriculada, número de matrícula, '
            'actividad en el aula virtual y cumplimiento de evaluaciones. Las filas del último periodo de cada '
            'estudiante activo no tienen etiqueta y son las que se califican. Los grupos opcionales se activan solo '
            f'si la institución tiene datos en ellos, por eso UNEMI usa {um["n_variables"]} variables y OULAD '
            f'{om["n_variables"]} ({{T:variables}}).'))
    a(('tab', 'variables', 'Grupos de Variables del Modelo',
       ['Grupo', 'Variables principales', 'Sustento'],
       [['Base (siempre)', 'Nivel, corte, periodos cursados, avance; promedio y asistencia actuales, rezagados, '
                           'media móvil, mínimo histórico, tendencia, racha baja y posición en la cohorte',
         'Tinto (1975)'],
        ['Cartera', 'En mora, saldo pendiente, porcentaje de periodos con mora, porcentaje de beca',
         'Bean y Metzner (1985)'],
        ['Matrícula', 'Créditos matriculados, número de matrícula, días de anticipación de la matrícula',
         'Realinho et al. (2022)'],
        ['Aula virtual', 'Actividad del periodo y acumulada (logaritmo), cambio, posición en la cohorte, días sin '
                         'actividad', 'Marcolino et al. (2025); Vaarma y Li (2024)'],
        ['Evaluaciones', 'Evaluaciones vencidas, porcentaje entregado, porcentaje tardío, nota de las entregadas',
         'Kuzilek et al. (2017)']],
       'Elaboración propia a partir de ml/caracteristicas.py.', [2.8, 9.0, 4.2]))

    # ── Fase 4 ────────────────────────────────────────────────────────────
    a(('h3', '3.1.5 Fase 4: modelado'))
    a(('p', 'Se reservaron como prueba temporal los periodos más recientes (al menos el 25 % de las filas '
            'etiquetadas): '
            f'{", ".join(ut["periodos"])} en UNEMI y {", ".join(ot["periodos"])} en OULAD. Con el resto se ajustaron '
            'los hiperparámetros (búsqueda aleatoria para Random Forest y Optuna para LightGBM) y se compararon los '
            'cuatro candidatos con validación cruzada de cinco pliegues **agrupada por estudiante**, para que un mismo '
            'alumno nunca aparezca a la vez en entrenamiento y validación. Se eligió el modelo de mayor ROC-AUC medio, '
            'con el PR-AUC como desempate; luego se calibró con Platt sobre las predicciones fuera de pliegue y se '
            'fijaron los umbrales por recall. La {F:actividad_modelo} resume el proceso; el código que lo '
            'implementa se explica en la sección 3.3.3.'))
    a(('fig', 'actividad_modelo', 'Diagrama de Actividades del Entrenamiento y la Calificación',
       DIAGRAMAS / 'av2_actividad_modelo.png', 16.0,
       'Diagrama de actividades con la preparación del panel, cuatro modelos en paralelo, calibración y calificación',
       'Elaboración propia a partir de ml/entrenar.py y ml/calificar.py.'))

    # ── Fase 5 ────────────────────────────────────────────────────────────
    a(('h3', '3.1.6 Fase 5: evaluación'))
    a(('p', '**Validación cruzada.** La {T:cv} compara los cuatro modelos. En ambas instituciones LightGBM obtuvo el '
            'mayor ROC-AUC medio con una desviación pequeña entre pliegues, y el sobremuestreo SMOTE no mejoró al '
            'Random Forest con pesos por clase, resultado coherente con lo que informa la literatura sobre '
            'desbalance moderado. La {F:cv} muestra la dispersión por pliegue en UNEMI.'))
    filas = []
    for k in ('LOGISTICA', 'RF_PONDERADO', 'RF_SMOTE', 'LIGHTGBM'):
        filas.append([NOMBRE_MODELO[k], cv(um, k), cv(um, k, 'pr_auc'), cv(om, k), cv(om, k, 'pr_auc')])
    a(('tab', 'cv', 'Validación Cruzada por Estudiante: Media ± Desviación de Cinco Pliegues',
       ['Modelo', 'ROC-AUC UNEMI', 'PR-AUC UNEMI', 'ROC-AUC OULAD', 'PR-AUC OULAD'], filas,
       f'El modelo elegido en ambas instituciones fue {NOMBRE_MODELO[um["modelo_final"]]}. Elaboración propia a '
       'partir de ml/modelos/*/metricas.json.', [4.0, 3.0, 3.0, 3.0, 3.0]))
    a(('fig', 'cv', 'ROC-AUC y PR-AUC por Pliegue en UNEMI', FIGURAS / 'UNEMI_PRUEBAS_comparacion_cv.png', 16.0,
       'Diagramas de caja del ROC-AUC y PR-AUC de cuatro modelos', 'En naranja, el modelo elegido. Elaboración '
       'propia.'))
    a(('p', '**Validación temporal.** La prueba decisiva es la de los periodos reservados ({T:temporal}). El '
            f'ROC-AUC fue de {f(ut["roc_auc"])} en UNEMI y de {f(ot["roc_auc"])} en OULAD, por encima del criterio '
            'de 0,75. El PR-AUC, que se compara con la prevalencia y no con 0,5, multiplica por '
            f'{f(ut["pr_auc"] / ut["prevalencia"], 1)} y por {f(ot["pr_auc"] / ot["prevalencia"], 1)} lo que '
            'lograría una lista al azar. Con el umbral medio, el sistema detecta '
            f'{pct(ut["umbral_medio"]["recall"])} de los abandonos de UNEMI y {pct(ot["umbral_medio"]["recall"])} '
            f'de los de OULAD, alertando a {pct(ut["umbral_medio"]["tasa_alerta"])} y a '
            f'{pct(ot["umbral_medio"]["tasa_alerta"])} de los estudiantes, con una precisión de '
            f'{f(ut["umbral_medio"]["precision"])} y {f(ot["umbral_medio"]["precision"])}. Por eso el umbral medio '
            'no debe leerse como una lista de llamadas: sirve para no dejar fuera a casi nadie que abandonará, '
            'mientras que el contacto directo se organiza con el umbral alto o con los primeros estudiantes de la '
            'lista hasta la capacidad real de bienestar, que es como la interfaz ordena la información. La '
            'calibración redujo el puntaje de Brier de '
            f'{f(ut["brier_sin_calibrar"])} a {f(ut["brier_calibrado"])} y de {f(ot["brier_sin_calibrar"])} a '
            f'{f(ot["brier_calibrado"])}. Frente a un pronóstico que siempre diera la prevalencia, la mejora relativa '
            f'(índice de habilidad de Brier) es de {f(bss_u, 2)} en UNEMI y de solo {f(bss_o, 2)} en OULAD: con '
            'abandonos tan poco frecuentes, las probabilidades son confiables para ordenar y para estimar cuántos '
            'casos esperar, pero aportan poco como valor individual.'))
    t = [['Periodos de prueba', ', '.join(ut['periodos']), ', '.join(ot['periodos'])],
         ['Registros (abandonos)', f"{ent(ut['n'])} ({ent(ut['positivos'])})", f"{ent(ot['n'])} ({ent(ot['positivos'])})"],
         ['ROC-AUC', f(ut['roc_auc']), f(ot['roc_auc'])],
         ['PR-AUC (prevalencia)', f"{f(ut['pr_auc'])} ({f(ut['prevalencia'])})", f"{f(ot['pr_auc'])} ({f(ot['prevalencia'])})"],
         ['Brier sin calibrar / calibrado', f"{f(ut['brier_sin_calibrar'])} / {f(ut['brier_calibrado'])}",
          f"{f(ot['brier_sin_calibrar'])} / {f(ot['brier_calibrado'])}"],
         ['Umbral medio: valor', pct(um['umbrales']['medio']), pct(om['umbrales']['medio'], 2)],
         ['Umbral medio: recall / precisión', f"{f(ut['umbral_medio']['recall'])} / {f(ut['umbral_medio']['precision'])}",
          f"{f(ot['umbral_medio']['recall'])} / {f(ot['umbral_medio']['precision'])}"],
         ['Umbral alto: valor', pct(um['umbrales']['alto']), pct(om['umbrales']['alto'], 2)],
         ['Umbral alto: recall / precisión', f"{f(ut['umbral_alto']['recall'])} / {f(ut['umbral_alto']['precision'])}",
          f"{f(ot['umbral_alto']['recall'])} / {f(ot['umbral_alto']['precision'])}"],
         ['Abandonos en el 10 % de mayor riesgo', pct(ut['captura_top_10']), pct(ot['captura_top_10'])],
         ['Abandonos en el 20 % de mayor riesgo', pct(ut['captura_top_20']), pct(ot['captura_top_20'])]]
    a(('tab', 'temporal', 'Resultados de la Validación Temporal', ['Métrica', 'UNEMI (prueba)', 'OULAD (real)'], t,
       'Umbrales fijados con datos de entrenamiento para un recall objetivo de 0,80 (medio) y 0,50 (alto). '
       'Elaboración propia a partir de ml/modelos/*/metricas.json.', [6.4, 4.8, 4.8]))
    a(('p', 'La {F:roc} presenta las curvas ROC y de precisión-recall de UNEMI, tanto en validación cruzada como en la '
            'prueba temporal; su cercanía indica que el modelo no se sobreajustó a los periodos de entrenamiento. La '
            '{F:confusion} detalla la matriz de confusión de OULAD en el umbral medio y la {F:ganancia} traduce el '
            'resultado al lenguaje de la gestión: contactando primero al 20 % de mayor riesgo se alcanza a '
            f'{pct(ot["captura_top_20"], 0)} de quienes abandonarán.'))
    a(('fig', 'roc', 'Curvas ROC y de Precisión-Recall en UNEMI', FIGURAS / 'UNEMI_PRUEBAS_roc_pr.png', 15.0,
       'Curvas ROC y precisión-recall para validación cruzada y prueba temporal', 'Elaboración propia.'))
    a(('fig', 'confusion', 'Matriz de Confusión de OULAD en el Umbral Medio', FIGURAS / 'OULAD_UK_matriz_confusion.png',
       10.5, 'Matriz de confusión dos por dos', 'Prueba temporal 2014B y 2014J. Elaboración propia.'))
    a(('fig', 'ganancia', 'Ganancia Acumulada del Modelo en OULAD', FIGURAS / 'OULAD_UK_ganancia.png', 14.0,
       'Curva de ganancia acumulada frente a la línea de azar', 'Elaboración propia.'))
    b.extend(_desempeno_por_periodo(um, om))
    if pr:
        ys, yr = pr['y_siguiente'], pr['y_resto']
        a(('p', f'**Evaluación prospectiva.** En OULAD, la presentación {pr["presentacion"]} se cargó solo hasta su '
                'tercer corte, como si estuviera en curso, y su desenlace real se guardó aparte, fuera del almacén. '
                f'Al comparar después las {ent(pr["calificados"])} predicciones con lo que ocurrió, el modelo obtuvo un '
                f'ROC-AUC de {f(ys["roc_auc"])} para el retiro en el corte siguiente, con un recall de '
                f'{f(ys["recall"])} en el umbral medio, y de {f(yr["roc_auc"])} para el retiro en cualquier momento '
                'posterior del módulo. Es la prueba más cercana a un uso real. Las etiquetas evaluadas aquí son '
                'independientes de todo lo que vio el modelo: la prueba temporal de 2014J solo incluye retiros '
                'ocurridos hasta el tercer corte, mientras que la evaluación prospectiva mide los retiros posteriores, '
                'que nunca entraron al almacén. El recall prospectivo es mayor que el temporal porque se calcula sobre '
                'un único corte, en el que los retiros se concentran entre quienes ya muestran desconexión.'))
        a(('p', '**Validez de la comparación entre fuentes.** En OULAD, «abandono» significa retirarse del módulo en el '
                'corte de 28 días siguiente; en UNEMI, no matricularse en el semestre siguiente. Ambos son retiros '
                'anticipables con la trayectoria, pero ocurren en escalas de tiempo distintas y con prevalencias '
                'diferentes. Por eso las cifras de las dos instituciones no se promedian ni se comparan como si '
                'midieran lo mismo: OULAD prueba que el método funciona con comportamiento real y UNEMI prueba el '
                'sistema completo con la estructura de la universidad.'))
    a(('p', '**Explicabilidad y equidad.** La importancia por permutación en OULAD ({F:importancia}) confirma lo que '
            'anticipaban las teorías: el promedio frente a la cohorte, la carga de créditos y los días sin actividad '
            'en el aula virtual son las señales más fuertes. La calibración ({F:calibracion}) sigue de cerca la '
            'diagonal. En equidad ({F:equidad}), el desempeño por género es similar: ROC-AUC de '
            f'{f(om["equidad"][0]["roc_auc"])} en mujeres y {f(om["equidad"][1]["roc_auc"])} en hombres en OULAD; '
            'la diferencia de recall se vigila desde la página de calidad del modelo.'))
    a(('fig', 'importancia', 'Importancia por Permutación de las Variables en OULAD', FIGURAS / 'OULAD_UK_importancia.png',
       16.0, 'Barras horizontales con la caída del PR-AUC al permutar cada variable', 'Elaboración propia.'))
    a(('fig', 'calibracion', 'Calibración de las Probabilidades en OULAD', FIGURAS / 'OULAD_UK_calibracion.png', 12.5,
       'Probabilidad predicha frente a frecuencia observada por decil', 'Elaboración propia.'))
    a(('fig', 'equidad', 'Desempeño por Subgrupo en OULAD', FIGURAS / 'OULAD_UK_equidad.png', 16.0,
       'Barras de recall y ROC-AUC para mujeres y hombres', 'Elaboración propia.'))
    seg = us.get('segmentos', {})
    kw = us.get('kruskal_wallis') or {}
    comp = us.get('comparacion_algoritmos', {})
    a(('p', '**Segmentación.** Con las 18 carreras de UNEMI, el barrido de k ({F:segk}) llevó a tres segmentos, que '
            'es además el número que una autoridad puede gestionar. La separación es moderada: silueta de '
            f'{f(us.get("silhouette"))} y estabilidad al remuestrear (ARI medio) de '
            f'{f(us.get("estabilidad", {}).get("ari_medio"))}, de modo que las carreras de frontera pueden cambiar '
            'de grupo. K-means superó al método jerárquico de Ward (silueta '
            f'{f((comp.get("JERARQUICO_WARD") or {}).get("silhouette"))}); HDBSCAN dejó '
            f'{(comp.get("HDBSCAN") or {}).get("ruido", "n. d.")} carreras como ruido, lo que no sirve para asignar '
            'a todas un segmento. La prueba de Kruskal-Wallis muestra que la tasa histórica difiere entre segmentos '
            f'(H = {f(kw.get("H"), 2)}; p = {f(kw.get("p"))}), pero como esa tasa es una de las variables de '
            'agrupación, la prueba solo confirma que los segmentos separan esa dimensión; la validación '
            'independiente será comparar los segmentos con el abandono de los próximos periodos. La '
            '{T:segmentos} resume los grupos; sus nombres son relativos dentro de la institución, y la tasa histórica '
            'está sobrestimada por la censura a la derecha descrita en la sección 3.1.3. En OULAD, con solo siete '
            f'módulos, la segmentación es descriptiva (p = {f((os_.get("kruskal_wallis") or {}).get("p"))}).'))
    filas_seg = []
    for nombre in ('Atención prioritaria', 'Estable', 'Bajo riesgo'):
        g = [x for x in us.get('asignacion', []) if x['segmento'] == nombre]
        if not g:
            continue
        filas_seg.append([nombre, str(len(g)), pct(sum(x['tasa_abandono_hist'] for x in g) / len(g)),
                          pct(sum(x['riesgo_promedio'] for x in g) / len(g)),
                          ', '.join(bonito(c) for c in sorted(x['carrera'] for x in g)[:4]) +
                          (' y otras' if len(g) > 4 else '')])
    a(('tab', 'segmentos', 'Segmentos de Carreras en UNEMI (Datos de Prueba)', ['Segmento', 'Carreras', 'Abandono histórico',
                                                             'Riesgo actual medio', 'Ejemplos'], filas_seg,
       'Abandono histórico: proporción de retiros entre los estudiantes que ya cerraron su trayectoria. Elaboración '
       'propia a partir de ml/modelos/UNEMI_PRUEBAS/segmentacion.json.', [3.2, 1.8, 2.6, 2.6, 5.8]))
    a(('fig', 'segk', 'Calidad de la Segmentación según el Número de Segmentos en UNEMI',
       FIGURAS / 'UNEMI_PRUEBAS_segmentacion_k.png', 14.0, 'Silhouette y Davies-Bouldin para k de 2 a 6',
       'La línea punteada marca el k elegido. Elaboración propia.'))

    # Consulta conversacional
    a(('p', '**Consulta conversacional.** La exactitud se mide por ejecución con un conjunto dorado de 40 preguntas '
            'base y 12 de robustez (errores de tipeo, sinónimos, filtros combinados), redactadas como las haría una '
            'autoridad, más 8 preguntas maliciosas. Cada respuesta se compara con el resultado de un SQL de referencia '
            'ejecutado con la misma cuenta y la misma institución. ' + (
                'La evaluación se ejecutó sobre el almacén real en SQL Server 2022, con la cuenta de solo lectura '
                'chat_reader y la cascada de proveedores de IA configurada. Se registran dos medidas: la exactitud '
                '**estricta**, cuando la respuesta devuelve exactamente las mismas filas y columnas que el SQL de '
                'referencia, y la **relajada**, cuando contiene todos los valores de la referencia aunque agregue '
                'columnas de contexto, cambie el nombre de una columna o exprese la cifra como porcentaje; la '
                'relajada es la que corresponde al criterio de aceptación, porque mide si la autoridad recibe la '
                'cifra correcta.' if C_ORIGEN == 'SQL_SERVER' else
                'En este avance la evaluación se ejecutó sobre la '
                '**réplica de validación**: una copia del almacén en SQLite, construida con los mismos datos y el mismo '
                'ETL, que traduce el T-SQL y emula el contexto de sesión para filtrar por institución. La réplica '
                'permite medir el enrutador, las barreras y las métricas certificadas, pero no reemplaza a SQL Server: '
                'una pregunta de robustez quedó fuera porque su SQL de referencia usa funciones de texto que la réplica '
                'no reproduce, y el aislamiento real lo comprueban las pruebas de integración sobre SQL Server de la '
                'sección 3.1.8.')))
    if C:
        r = C['resumen']
        cert = C.get('por_origen', {}).get('CERTIFICADA', {})
        if C_ORIGEN == 'SQL_SERVER':
            gen = C.get('por_origen', {}).get('GENERADA_IA', {})
            provs = sorted({(d.get('proveedor') or '').split(' (')[0] for d in C.get('detalle', [])
                            if d.get('origen') == 'GENERADA_IA' and d.get('proveedor')})
            texto = (f'Sobre SQL Server, la exactitud relajada fue de {pct(r["exactitud_relajada_base"], 0)} en las '
                     f'preguntas base y de {pct(r["exactitud_relajada_robustez"], 0)} en las de robustez, por encima '
                     f'de la meta de 85\u00a0%; la estricta fue de {pct(r["exactitud_estricta_base"], 0)} en las base, porque '
                     'varias respuestas añaden columnas útiles para la autoridad (por ejemplo, el número de '
                     'estudiantes junto a la tasa). De las '
                     f'{r["preguntas_base"] + r["preguntas_robustez"]} preguntas, {cert.get("preguntas", 0)} las '
                     f'respondió una métrica certificada y {gen.get("preguntas", 0)} un SQL generado por el modelo de '
                     'lenguaje' + (f' ({" y ".join(provs)})' if provs else '') + ' y validado antes de ejecutarse'
                     + (', sin fallas técnicas' if not r["fallas_tecnicas"] else f' ({r["fallas_tecnicas"]} fallas técnicas)')
                     + '. El tamaño del conjunto es acotado: el resultado '
                     'muestra que el diseño funciona con preguntas como las previstas, no que la consulta acierte '
                     'siempre, y por eso la interfaz indica el origen de cada cifra')
        else:
            texto = (f'Sin proveedores de IA, la ruta certificada respondió {cert.get("preguntas", 0)} de las '
                     f'{r["preguntas_base"] + r["preguntas_robustez"]} preguntas evaluadas '
                     f'({pct(cert.get("preguntas", 0) / (r["preguntas_base"] + r["preguntas_robustez"]), 0)}) y '
                     f'acertó en todas ({pct(cert.get("exactitud_relajada", 0), 0)}). Este resultado mide la cobertura y '
                     'la precisión del enrutador, que podría haber elegido una métrica equivocada, no la del SQL fijo, '
                     'que se verificó al construir el catálogo. Las preguntas restantes requieren el modelo de lenguaje; '
                     'la exactitud global, que es el criterio de aceptación, se mide en la corrida final sobre SQL '
                     'Server con los proveedores configurados')
        a(('p', texto + f'. Las {r["adversariales_contenidas"].split("/")[1]} preguntas maliciosas fueron contenidas '
                f'({r["adversariales_contenidas"]}), la base no cambió y hubo {r["violaciones_aislamiento"]} '
                'lecturas de otra institución. La mediana de respuesta fue de '
                f'{ent(r["latencia_mediana_ms"])} ms; el percentil 95, de {ent(r["latencia_p95_ms"])} ms, corresponde a '
                'las preguntas que pasan por el modelo de lenguaje ({T:consulta}).'))
        a(('tab', 'consulta', 'Evaluación de la Consulta Conversacional con el Conjunto Dorado',
           ['Indicador', 'Resultado'],
           [['Preguntas evaluadas (base + robustez)', f"{r['preguntas_base']} + {r['preguntas_robustez']}"],
            ['Respondidas por métricas certificadas', f"{cert.get('preguntas', 0)} (exactitud "
                                                       f"{pct(cert.get('exactitud_relajada', 0))})"],
            ['Derivadas al modelo de lenguaje', str(r['preguntas_base'] + r['preguntas_robustez'] - cert.get('preguntas', 0))],
            *([['Exactitud relajada (base / robustez)', f"{pct(r['exactitud_relajada_base'], 0)} / "
                                                         f"{pct(r['exactitud_relajada_robustez'], 0)}"],
               ['Exactitud estricta (base)', pct(r['exactitud_estricta_base'], 0)],
               ['Fallas técnicas', str(r['fallas_tecnicas'])]] if C_ORIGEN == 'SQL_SERVER' else []),
            ['Preguntas maliciosas contenidas', r['adversariales_contenidas']],
            ['Base sin cambios tras las pruebas', 'Sí' if r['base_sin_cambios'] else 'No'],
            ['Lecturas de otra institución', str(r['violaciones_aislamiento'])],
            ['Latencia mediana / percentil 95', f"{ent(r['latencia_mediana_ms'])} ms / {ent(r['latencia_p95_ms'])} ms"]],
           (f'Corrida sobre SQL Server 2022 con la cuenta chat_reader ({C.get("fecha", "")[:10]}). '
            if C_ORIGEN == 'SQL_SERVER' else
            'Corrida sobre la réplica de validación del almacén, sin proveedores de IA. ') +
           'Elaboración propia a partir de eval/evaluar_consulta.py.', [9.0, 7.0]))

    # ── Fase 6 ────────────────────────────────────────────────────────────
    a(('h3', '3.1.7 Fase 6: despliegue, operación y demostración'))
    a(('p', 'El despliegue se organizó en las cuatro capas que se describen en la sección 3.2: base de datos, procesos '
            'por lotes, API y aplicación web. El backend expone 27 operaciones REST con FastAPI y la interfaz las '
            'consume según el rol del usuario; el código de ambos se explica, a manera de manual, en la sección 3.3. '
            'Atendiendo la recomendación de la tutoría del Avance 2, la fase de despliegue incorporó además la '
            'operación continua del modelo (MLOps), porque un modelo de abandono se degrada si cambian los datos de '
            'entrada aunque el código no cambie.'))
    b.extend(_operacion_modelo())
    a(('p', 'El prototipo funciona de punta a punta. La pantalla de apertura ({F:cap_ingreso}) presenta las capacidades '
            'del sistema alrededor de la tarjeta de ingreso. El panel ({F:cap_panel}) resume el periodo en un '
            'termómetro institucional y en una lectura de pocas frases; la ficha ({F:cap_ficha}) explica por qué un '
            'estudiante está en riesgo y permite simular escenarios; la consulta conversacional ({F:cap_consulta}) '
            'responde en español e indica si la cifra proviene de una métrica certificada; la vista de carreras '
            '({F:cap_carreras}) muestra los segmentos y la solidez de la agrupación; y la página de calidad '
            '({F:cap_calidad}) explica en lenguaje sencillo cuánto confiar en el modelo. Las capturas corresponden a '
            'la institución de prueba, señalada en la interfaz como «Datos sintéticos».'))
    for k, archivo, titulo, alt in (
            ('cap_ingreso', 'av2_cap_ingreso.png', 'Pantalla de Apertura e Ingreso al Sistema',
             'Pantalla de ingreso con tarjeta central y seis capacidades alrededor'),
            ('cap_panel', 'av2_cap_panel.png', 'Panel Institucional del Periodo', 'Panel con termómetro, indicadores y '
                                                                               'gráfico por carrera'),
            ('cap_ficha', 'av2_cap_ficha.png', 'Ficha Explicada de un Estudiante', 'Ficha con probabilidad, factores y '
                                                                                 'acciones sugeridas'),
            ('cap_consulta', 'av2_cap_consulta.png', 'Consulta Conversacional con Métrica Certificada',
             'Chat con una respuesta en gráfico de barras'),
            ('cap_carreras', 'av2_cap_carreras.png', 'Segmentación de Carreras', 'Tarjetas de segmentos y mapa de '
                                                                               'carreras'),
            ('cap_calidad', 'av2_cap_calidad.png', 'Calidad del Modelo Explicada a la Autoridad',
             'Indicadores de calidad y matrices de confusión')):
        a(('fig', k, titulo, CAPTURAS / archivo, 16.0, alt, 'Captura del prototipo VicMar en ejecución, institución '
                                                           'de prueba. Elaboración propia.'))

    a(('h3', '3.1.8 Estrategia de pruebas y criterios de aceptación'))
    lat = (f'En la réplica, la mediana de respuesta de los servicios que alimentan las páginas fue de '
           f'{LAT["mediana_ms"]} ms y el percentil 95 de {LAT["p95_ms"]} ms, dentro de la meta de RNF-06. ') if LAT else ''
    a(('p', 'La calidad del software se verificó en cuatro niveles ({T:pruebas}). Las pruebas automatizadas se '
            'ejecutan en cada cambio; las de integración requieren el contenedor de SQL Server y comprueban el '
            'aislamiento y los permisos reales de las cuentas, y forman parte de la corrida final del sistema. '
            + lat + 'La prueba con usuarios no técnicos sigue el protocolo de la tabla; requiere la participación '
            'de autoridades y personal de bienestar de la universidad y su instrumento (tareas y escala SUS) se '
            'incluye en los anexos. La {T:traza} '
            'enlaza cada historia de usuario con sus requerimientos y con la prueba que la verifica.'))
    a(('tab', 'pruebas', 'Estrategia de Pruebas del Prototipo', ['Nivel', 'Qué verifica', 'Herramienta y alcance'],
       [['Unitarias', 'Variables sin fuga, enrutador, guardarraíles, validador SQL, privacidad y redacción',
         f'pytest: {N_PRUEBAS_BACKEND} pruebas del backend'],
        ['Integración', 'Aislamiento por SESSION_CONTEXT, permisos de chat_reader y app_seguimiento, ETL completo',
         'pytest sobre SQL Server 2022: 8 pruebas'],
        ['Interfaz', 'Formatos es-EC, navegación por rol, accesibilidad de componentes', 'vitest: 11 pruebas; '
                                                                                        'TypeScript estricto'],
        ['Aceptación técnica', 'Historias de usuario, conjunto dorado de la consulta y validación visual en '
                               'escritorio y móvil', 'Playwright y revisión por los autores'],
        ['Operación del modelo', 'Validación por periodo y carrera, origen móvil, calidad de datos con Great '
                                 'Expectations, deriva con Evidently y registro en MLflow', 'pytest: test_mlops'],
        ['Aceptación con usuarios', 'Tareas de HU-01 a HU-07 con 2 autoridades y 3 profesionales de '
                                               'bienestar; tasa de éxito, tiempo y escala SUS',
         'Meta: éxito ≥ 80 % y SUS ≥ 68']],
       'Elaboración propia.', [3.0, 7.6, 5.4]))
    a(('tab', 'traza', 'Matriz de Trazabilidad entre Historias, Requerimientos y Pruebas',
       ['Historia', 'Requerimientos', 'Verificación'],
       [['HU-01 Panel del periodo', 'RF-05, RF-17, RNF-06', 'test_api (panel ejecutivo); medición de latencia'],
        ['HU-02 Lista priorizada', 'RF-06, RF-18, RNF-01', 'test_privacidad_seguridad (enmascarado); '
                                                           'test_integracion_bd (aislamiento)'],
        ['HU-03 Razones del riesgo', 'RF-07, RNF-09', 'test_modelo (recomendaciones por factor); ficha en la '
                                                      'demostración'],
        ['HU-04 Simulación', 'RF-08', 'test_modelo (simulador)'],
        ['HU-05 Seguimiento', 'RF-09, RNF-02, RNF-03', 'test_api (permisos); test_integracion_bd (procedimientos)'],
        ['HU-06 Consulta en español', 'RF-10, RNF-05', 'Conjunto dorado; test_motor, test_enrutador, '
                                                       'test_validador'],
        ['HU-07 Carreras prioritarias', 'RF-11', 'Validación de la segmentación (sección 3.1.6)'],
        ['HU-08 Referentes', 'RF-12', 'Demostración (página de referentes)'],
        ['HU-09 Confianza en el modelo', 'RF-03, RF-04, RF-13, RNF-04', 'test_modelo; validación cruzada, temporal y '
                                                                        'prospectiva'],
        ['HU-10 Informe ejecutivo', 'RF-14', 'test_api (reportes ejecutivos)']],
       'Elaboración propia a partir de backend/tests/.', [4.2, 4.6, 7.2]))

    # ── 3.2 Diseño ─────────────────────────────────────────────────────────
    a(('h2', '3.2 Diseño'))
    a(('h3', '3.2.1 Arquitectura de la solución'))
    a(('p', 'La solución sigue una arquitectura en capas con un almacén de datos gobernado en el centro ({F:arq}). La '
            'capa de datos contiene la base operativa de cada institución y el almacén ALMACEN_ACADEMICO en SQL '
            'Server 2022. La capa analítica ejecuta por lotes el ETL, el entrenamiento, la calificación, la '
            'segmentación y la operación del modelo (calidad de datos, deriva y registro de experimentos). La capa de servicios es una API FastAPI que concentra la autenticación, los permisos, la '
            'privacidad, la auditoría y el motor de consulta conversacional. La capa de presentación es una '
            'aplicación React que nunca accede a la base de datos. La {T:componentes} describe cada componente.'))
    a(('p', 'Antes de construir se compararon tres estilos con seis escenarios de calidad derivados de los '
            'requerimientos ({T:estilos}). El monolito en capas es el más simple de operar en una sola máquina, pero '
            'acopla la interfaz al servidor; los microservicios separan cada pieza, pero multiplican los desplegables '
            'y obligan a sincronizar datos entre servicios, lo que rompe la garantía de que el panel y el chat lean '
            'las mismas cifras (Hassan et al., 2025). Se eligió un estilo cliente-servidor desacoplado, con una '
            'interfaz independiente y un backend en capas, porque cumple todos los escenarios con solo dos '
            'desplegables, adecuados para un equipo de dos personas y una institución piloto.'))
    a(('fig', 'arq', 'Arquitectura del Sistema VicMar', DIAGRAMAS / 'av2_arquitectura.png', 16.0,
       'Diagrama de arquitectura en cuatro capas', 'Elaboración propia.'))
    a(('tab', 'componentes', 'Componentes de la Arquitectura', ['Capa', 'Componente', 'Responsabilidad'],
       [['Datos', 'Base operativa por institución', 'Origen de la trayectoria (UNEMI_PRUEBAS, OULAD_PRUEBAS)'],
        ['Datos', 'ALMACEN_ACADEMICO', 'Esquema estrella, vistas VIS_*, procedimientos de seguimiento y esquema bi '
                                       'agregado para Metabase'],
        ['Analítica', 'ETL por perfil', 'Valida, transforma y carga cada institución sin tocar las demás'],
        ['Analítica', 'Entrenamiento y calificación', 'Modelos, calibración, umbrales, SHAP y PSI'],
        ['Analítica', 'Segmentación', 'K-means de carreras con validación'],
        ['Analítica', 'Operación del modelo', 'Calidad de datos (Great Expectations), deriva (Evidently) y registro '
                                              'de experimentos (MLflow)'],
        ['Servicios', 'API FastAPI', 'Autenticación JWT, roles, auditoría y 27 servicios REST'],
        ['Servicios', 'Motor NL2SQL', 'Barreras, 40 métricas certificadas, generación, validación y resumen'],
        ['Servicios', 'Privacidad', 'Enmascaramiento, tokens cifrados y seudonimización'],
        ['Presentación', 'Interfaz React', 'Panel, lista, ficha, seguimiento, consulta, carreras, calidad, reportes '
                                           'y administración'],
        ['Externa', 'Proveedores de IA', 'Generan SQL a partir de la pregunta, el esquema y ejemplos; reciben filas '
                                         'seudonimizadas solo si el usuario pide interpretar un resultado']],
       'Elaboración propia.', [2.6, 4.4, 9.0]))
    est = [('E1. Nueva institución solo con un perfil', 20, 4, 5, 5), ('E2. Aislamiento en el motor', 20, 5, 5, 5),
           ('E3. Panel y chat con las mismas cifras', 15, 5, 5, 3), ('E4. Operación por dos personas', 25, 5, 4, 1),
           ('E5. Interfaz que evoluciona aparte', 10, 2, 5, 5), ('E6. Evidencia en trabajos previos', 10, 4, 4, 1)]
    tot = [sum(e[1] * e[k] for e in est) / 100 for k in (2, 3, 4)]
    a(('tab', 'estilos', 'Comparación de Estilos Arquitectónicos (Puntaje de 1 a 5)',
       ['Escenario de calidad', 'Peso (%)', 'Monolito en capas', 'Cliente-servidor desacoplado', 'Microservicios'],
       [[e[0], str(e[1]), str(e[2]), str(e[3]), str(e[4])] for e in est] +
       [['**Puntaje ponderado**', '100', f(tot[0], 2), f'**{f(tot[1], 2)}**', f(tot[2], 2)]],
       'Elaboración propia a partir de documentacion/decisiones/DT-06_arquitectura.json y Hassan et al. (2025).',
       [5.4, 1.8, 2.6, 3.4, 2.8]))
    a(('h3', '3.2.2 Justificación de la propuesta tecnológica'))
    a(('p', 'La selección de tecnologías privilegió herramientas libres o con licencia gratuita para desarrollo, '
            'conocidas en la carrera y con soporte institucional probable ({T:stack}).'))
    a(('tab', 'stack', 'Tecnologías Seleccionadas y Justificación', ['Tecnología', 'Uso', 'Razón de la elección'],
       [['SQL Server 2022 (Docker)', 'Almacén y seguridad', 'SESSION_CONTEXT, vistas, procedimientos y cuentas con '
                                                          'permisos finos; motor usado en IES del país'],
        ['Python 3.13, scikit-learn, LightGBM', 'Modelado', 'Ecosistema estándar de aprendizaje automático; LightGBM '
                                                          'eficiente en tablas'],
        ['Optuna, SHAP', 'Ajuste y explicación', 'Búsqueda bayesiana reproducible; explicación local aceptada en la '
                                                 'literatura'],
        ['FastAPI', 'API', 'Validación de datos con tipos, documentación automática y buen rendimiento'],
        ['sqlglot', 'Validación SQL', 'Analiza el SQL como árbol sintáctico en vez de buscar palabras'],
        ['React, TypeScript, Vite, Tailwind', 'Interfaz', 'Componentes tipados, construcción rápida y diseño '
                                                         'consistente'],
        ['Recharts', 'Gráficos', 'Gráficos accesibles integrados en React'],
        ['Gemini, Groq, NVIDIA NIM, DeepSeek', 'Generación de SQL', 'Cascada de proveedores: si uno falla, '
                                                                     'responde el siguiente']],
       'Elaboración propia.', [4.4, 3.2, 8.4]))

    a(('h3', '3.2.3 Diagramas UML'))
    a(('p', '**Secuencia de la consulta en lenguaje natural.** La {F:sec_consulta} muestra el recorrido de una pregunta '
            'que tiene métrica certificada. Los mensajes siguen este orden:'))
    a(('ul', ['La autoridad escribe la pregunta y la interfaz la envía con su token a POST /consulta.',
              'La API valida el token, el rol y la institución activa, y entrega la pregunta al motor.',
              'Las barreras clasifican la intención: un pedido de escritura, de otra institución o de inyección se '
              'responde con un mensaje y no llega a la base.',
              'El enrutador reconoce la carrera, la facultad y el nivel de riesgo, compara la forma de la pregunta con '
              'las 40 métricas y elige una solo si la similitud supera el umbral y entiende todos sus términos.',
              'La base fija la institución en SESSION_CONTEXT y ejecuta la consulta fija con la cuenta chat_reader.',
              'El redactor elige la visualización y escribe el resumen sin IA; la API registra la auditoría y '
              'devuelve la respuesta con su origen.']))
    a(('p', 'La {F:sec_ia} completa el camino cuando no hay métrica certificada: el generador envía al proveedor de IA '
            'la pregunta, el esquema de las vistas y ejemplos guiados; el validador revisa el SQL devuelto sobre su '
            'árbol sintáctico; si encuentra un problema, el proveedor recibe el error y tiene una única oportunidad '
            'de corregirlo; y la consulta válida se ejecuta con la misma cuenta y el mismo contexto de sesión.'))
    a(('fig', 'sec_consulta', 'Diagrama de Secuencia de la Consulta en Lenguaje Natural (Ruta Certificada)',
       DIAGRAMAS / 'av2_secuencia_consulta.png', 15.5, 'Diagrama de secuencia con barreras y métrica certificada',
       'Elaboración propia.'))
    a(('fig', 'sec_ia', 'Diagrama de Secuencia de la Consulta Generada por el Modelo de Lenguaje',
       DIAGRAMAS / 'av2_secuencia_consulta_ia.png', 12.5, 'Diagrama de secuencia con generación, validación y '
                                                          'corrección del SQL', 'Elaboración propia.'))
    a(('p', '**Secuencia de la ficha y el seguimiento.** En la {F:sec_ficha}, bienestar abre la ficha de un '
            'estudiante desde la lista: la URL lleva un token cifrado y no la cédula; la API lo descifra, lee las '
            'vistas de predicción, trayectoria, detalle y seguimiento, y devuelve la ficha con la cédula enmascarada. '
            'Al mover asistencia o promedio en el simulador, la API recalcula las variables dependientes con el mismo '
            'modelo y devuelve la diferencia en puntos. Al registrar una tutoría, la API ejecuta '
            'sp_registrar_intervencion con la cuenta app_seguimiento, que no tiene ningún otro permiso, y el '
            'procedimiento toma la institución del contexto de sesión y no de un parámetro.'))
    a(('fig', 'sec_ficha', 'Diagrama de Secuencia de la Ficha, la Simulación y el Seguimiento',
       DIAGRAMAS / 'av2_secuencia_ficha.png', 16.0, 'Diagrama de secuencia de la ficha del estudiante',
       'Elaboración propia.'))
    a(('p', '**Colaboración.** El diagrama de colaboración ({F:colaboracion}) numera los mensajes entre los objetos que '
            'intervienen en la calificación por lotes: (1) el orquestador pide la trayectoria al lector, que la '
            'consulta en el almacén; (2) el constructor arma el panel con las mismas reglas del entrenamiento; (3) se '
            'carga el paquete del modelo; (4) el modelo estima la probabilidad de los activos y el calibrador de '
            'Platt la ajusta; (5) el explicador SHAP devuelve los tres factores principales; (6) el monitor compara '
            'la distribución actual de las variables con la de entrenamiento (PSI); y (7 y 8) el orquestador escribe '
            'predicciones y métricas de monitoreo en el almacén.'))
    a(('fig', 'colaboracion', 'Diagrama de Colaboración de la Calificación de Estudiantes Activos',
       DIAGRAMAS / 'av2_colaboracion.png', 16.0, 'Diagrama de colaboración con mensajes numerados',
       'Elaboración propia.'))
    a(('p', '**Estados.** La {F:estados} muestra el ciclo de vida de la alerta de un estudiante activo. Al calificarse, '
            'el estudiante entra en bajo, medio o alto según los umbrales y puede cambiar de nivel en cada nueva '
            'calificación. Desde medio o alto, el registro de una intervención lo lleva a «en seguimiento» y su cierre, '
            'a «atendido»; la siguiente calificación decide si el riesgo baja o persiste. La alerta termina cuando el '
            'estudiante se gradúa o egresa, o cuando abandona. La intervención tiene su propio ciclo: solo pasa de '
            'abierta a cerrada mediante sus procedimientos almacenados.'))
    a(('fig', 'estados', 'Diagramas de Estado de la Alerta y de la Intervención', DIAGRAMAS / 'av2_estados.png', 16.0,
       'Diagramas de estado de la alerta y de la intervención', 'Elaboración propia.'))
    a(('p', '**Actividades.** La {F:actividad_etl} detalla las actividades del ETL por perfil. Primero se lee el perfil, '
            'se ejecuta su consulta sobre la base de origen y se valida el contrato; si falta una columna obligatoria '
            'o hay datos fuera de las reglas de calidad, el proceso informa y se detiene sin tocar el almacén. Si todo '
            'es válido, se actualiza la institución, se borran solo sus hechos, se cargan en paralelo periodos, sedes, '
            'carreras y fechas, se integra a los estudiantes conservando su clave, se resuelven las claves sustitutas '
            'y se insertan los hechos por lotes. Las actividades del entrenamiento se presentaron en la '
            '{F:actividad_modelo}.'))
    a(('fig', 'actividad_etl', 'Diagrama de Actividades del ETL por Perfil Institucional',
       DIAGRAMAS / 'av2_actividad_etl.png', 16.0, 'Diagrama de actividades del ETL en dos columnas',
       'Elaboración propia a partir de etl/cargar.py.'))
    a(('h3', '3.2.4 Diagrama de flujo de trabajo y solución tecnológica'))
    a(('p', 'La {F:flujo} integra a los actores en un solo flujo. Al cierre de cada periodo, TI ejecuta el proceso por '
            'lotes; VicMar califica, explica y segmenta; la autoridad revisa el panel y asigna recursos; bienestar '
            'abre la lista priorizada, revisa la ficha, decide si el estudiante requiere apoyo y registra la '
            'intervención. En el siguiente cierre, el sistema compara lo ocurrido, vigila la deriva y, si '
            'corresponde, reentrena. La solución tecnológica planteada es, por tanto, un ciclo de mejora continua y no '
            'un reporte aislado.'))
    a(('fig', 'flujo', 'Flujo de Trabajo de la Alerta Temprana', DIAGRAMAS / 'av2_flujo_trabajo.png', 16.0,
       'Diagrama de actividades con cinco carriles', 'Elaboración propia.'))

    a(('h3', '3.2.5 Modelo entidad-relación del almacén'))
    a(('p', 'El almacén ALMACEN_ACADEMICO sigue un esquema estrella ({F:estrella}): la tabla de hechos central '
            'fact_matriculas registra al estudiante en cada periodo y corte, y se relaciona con ocho dimensiones en '
            'relaciones de uno a muchos. Debajo se ubican los hechos que escriben los procesos por lotes y el '
            'seguimiento (predicciones, segmentos, intervenciones y evaluaciones del modelo) y los referentes externos '
            'con su dimensión. Todas las tablas de hechos llevan institucion_codigo, que es la base del aislamiento.'))
    a(('fig', 'estrella', 'Esquema Estrella del Almacén Académico', DIAGRAMAS / 'av2_modelo_estrella.png', 16.0,
       'Esquema estrella con la tabla de hechos de matrículas y sus dimensiones', 'Elaboración propia a partir de '
       'crear_almacen_academico.sql.'))
    a(('p', 'Las tablas siguientes forman el diccionario de datos: la {T:dic_matriculas} describe la tabla de hechos '
            'principal, la {T:dic_prediccion} la de predicciones, la {T:dic_dimensiones} las dimensiones y la '
            '{T:dic_otros} los demás hechos. La {T:vistas} enumera las vistas y las cuentas que las consumen.'))
    a(('tab', 'dic_matriculas', 'Diccionario de Datos de fact_matriculas', ['Campo', 'Tipo', 'Descripción'],
       [['matricula_id', 'INT, PK', 'Identificador de la matrícula en el periodo y corte'],
        ['institucion_codigo', 'VARCHAR(30), FK', 'Institución a la que pertenece el registro'],
        ['alumno_id, carrera_id, sede_id', 'INT, FK', 'Estudiante, carrera y sede'],
        ['modalidad_codigo, estado_codigo', 'VARCHAR(20), FK', 'Modalidad y estado (ACTIVO, RETIRADO, GRADUADO...)'],
        ['periodo_id, tiempo_id', 'INT, FK', 'Periodo académico y fecha de corte'],
        ['nivel, corte', 'TINYINT', 'Semestre o ciclo, y corte dentro del periodo'],
        ['promedio', 'DECIMAL(4,2), NOT NULL', 'Promedio del periodo (0 a 10)'],
        ['asistencia_pct', 'DECIMAL(5,2), NOT NULL', 'Asistencia del periodo (0 a 100)'],
        ['monto_matricula, saldo_pendiente', 'DECIMAL(10,2), NULL', 'Cartera (opcional)'],
        ['beca_porcentaje', 'TINYINT, NULL', 'Porcentaje de beca (opcional)'],
        ['creditos_matriculados, dias_anticipacion_matricula', 'SMALLINT, NULL', 'Matrícula (opcional)'],
        ['numero_matricula', 'TINYINT, NULL', '1 = primera vez, 2 = repite (opcional)'],
        ['actividad_lms', 'INT, NULL', 'Interacciones en el aula virtual (opcional)'],
        ['dias_sin_actividad', 'SMALLINT, NULL', 'Días desde la última actividad (opcional)'],
        ['evaluaciones_vencidas, _entregadas, _tardias', 'SMALLINT, NULL', 'Evaluaciones (opcional)'],
        ['nota_evaluaciones', 'DECIMAL(4,2), NULL', 'Nota media de las entregadas (opcional)'],
        ['es_ultimo_periodo', 'BIT, NOT NULL', 'Marca el registro más reciente del estudiante']],
       'Elaboración propia a partir de crear_almacen_academico.sql.', [6.2, 3.4, 6.4]))
    a(('tab', 'dic_prediccion', 'Diccionario de Datos de fact_prediccion_abandono', ['Campo', 'Tipo', 'Descripción'],
       [['prediccion_id', 'INT, PK', 'Identificador de la predicción'],
        ['institucion_codigo, alumno_id', 'FK', 'Institución y estudiante'],
        ['matricula_id_base', 'INT, FK', 'Matrícula con cuyos datos se calificó'],
        ['horizonte', 'VARCHAR(30)', 'PROXIMO_PERIODO'],
        ['probabilidad', 'DECIMAL(6,4)', 'Probabilidad calibrada de abandono'],
        ['riesgo_categoria', 'VARCHAR(10)', 'ALTO, MEDIO o BAJO según los umbrales'],
        ['umbral_alto, umbral_medio', 'DECIMAL(6,4)', 'Umbrales vigentes al calificar'],
        ['percentil_riesgo', 'DECIMAL(5,2)', 'Posición del estudiante en su institución'],
        ['factor_1, factor_2, factor_3', 'NVARCHAR(200)', 'Razones principales en español (SHAP)'],
        ['explicacion_json, caracteristicas_json', 'NVARCHAR(MAX)', 'Contribuciones y variables para la ficha y el '
                                                                  'simulador'],
        ['fecha_calculo, modelo_version', 'DATETIME2 / VARCHAR', 'Trazabilidad del cálculo']],
       'Elaboración propia a partir de crear_almacen_academico.sql.', [5.4, 3.4, 7.2]))
    a(('tab', 'dic_dimensiones', 'Dimensiones del Almacén', ['Dimensión', 'Clave (tipo)', 'Atributos (tipo)'],
       [['dim_institucion', 'institucion_codigo VARCHAR(30)', 'nombre NVARCHAR(200), pais NVARCHAR(60), tipo_datos '
                                                             'VARCHAR(30), unidad_periodo NVARCHAR(60), fecha_carga '
                                                             'DATETIME2'],
        ['dim_alumno', 'alumno_id INT IDENTITY', 'institucion_codigo VARCHAR(30), cedula VARCHAR(15), apellidos y '
                                                 'nombres NVARCHAR(100), genero CHAR(1), ciudad_residencia '
                                                 'NVARCHAR(50)'],
        ['dim_carrera', 'carrera_id INT IDENTITY', 'carrera NVARCHAR(150), facultad_codigo VARCHAR(20), '
                                                   'facultad_nombre NVARCHAR(200)'],
        ['dim_sede', 'sede_id INT IDENTITY', 'sede_codigo VARCHAR(20), sede_nombre NVARCHAR(100)'],
        ['dim_periodo_academico', 'periodo_id INT IDENTITY', 'periodo_codigo VARCHAR(20), fecha_inicio DATE'],
        ['dim_tiempo', 'tiempo_id INT IDENTITY', 'fecha DATE (única), anio SMALLINT, mes y trimestre TINYINT'],
        ['dim_estado_matricula', 'estado_codigo VARCHAR(20)', 'descripcion NVARCHAR(120), es_terminal BIT'],
        ['dim_modalidad', 'modalidad_codigo VARCHAR(20)', 'descripcion NVARCHAR(80)'],
        ['dim_referente', 'referente_codigo VARCHAR(40)', 'nombre NVARCHAR(200), tipo VARCHAR(20)']],
       'Todos los atributos son obligatorios (NOT NULL). Elaboración propia a partir de crear_almacen_academico.sql.',
       [3.8, 4.0, 8.2]))
    a(('tab', 'dic_otros', 'Otras Tablas de Hechos', ['Tabla', 'Contenido'],
       [['fact_segmento_carrera', 'Segmento de cada carrera, estudiantes, tasa histórica, promedio, asistencia, '
                                  'riesgo medio y activos en riesgo'],
        ['fact_evaluacion_modelo', 'Métricas por componente (predicción, segmentación, consulta), esquema de '
                                   'validación, subgrupo y versión'],
        ['fact_intervencion', 'Tipo, descripción, estado, resultado, riesgo al registrar, responsable y fechas'],
        ['fact_referente_externo', 'Indicador, valor, unidad, año, definición, país, modalidad, comparabilidad, '
                                   'fuente y DOI']],
       'Elaboración propia.', [4.6, 11.4]))
    a(('tab', 'vistas', 'Vistas Gobernadas y Cuentas de Acceso', ['Objeto', 'Expone', 'Cuenta que lo usa'],
       [['VIS_INSTITUCION', 'institucion_codigo, nombre, pais, tipo_datos, unidad_periodo', 'chat_reader'],
        ['VIS_ALUMNO', 'cedula, apellidos, nombres, genero, ciudad, facultad, carrera, sede, modalidad, periodo, '
                       'fecha de corte, estado, nivel, corte, promedio, asistencia, cartera, matrícula, aula '
                       'virtual, evaluaciones, es_ultimo_periodo', 'chat_reader'],
        ['VIS_PREDICCION_ABANDONO', 'cedula, apellidos, nombres, genero, facultad, carrera, sede, modalidad, '
                                    'periodo, promedio, asistencia y saldo actuales, probabilidad, riesgo, '
                                    'percentil, umbrales, factor_1 a factor_3, versión', 'chat_reader'],
        ['VIS_PREDICCION_DETALLE', 'cedula, explicacion_json, caracteristicas_json, versión', 'chat_reader (solo '
                                                                                              'API, no el chat)'],
        ['VIS_SEGMENTO_CARRERA', 'carrera, facultad, segmento, orden, estudiantes, indicadores históricos, riesgo '
                                 'promedio, activos en riesgo', 'chat_reader'],
        ['VIS_EVALUACION_MODELO', 'componente, modelo, esquema, métrica, valor, desviación, grupo', 'chat_reader'],
        ['VIS_REFERENTE_EXTERNO', 'referente, indicador, valor, unidad, año, definición, país, modalidad, '
                                  'comparabilidad, fuente, DOI', 'chat_reader'],
        ['VIS_INTERVENCION', 'intervencion_id, cedula, apellidos, nombres, carrera, tipo, descripción, estado, '
                             'resultado, riesgo al registrar, responsable, fechas', 'chat_reader'],
        ['sp_registrar_intervencion, sp_cerrar_intervencion', 'Escritura controlada del seguimiento',
         'app_seguimiento']],
       'Ninguna cuenta de la aplicación lee las tablas físicas; en pantalla la cédula siempre se muestra '
       'enmascarada. Elaboración propia.', [4.4, 8.6, 3.0]))

    a(('h3', '3.2.6 Infraestructura y despliegue'))
    a(('p', 'El prototipo se ejecuta en un equipo con Windows: SQL Server 2022 corre en un contenedor de Docker, la '
            'API y los procesos por lotes en un entorno virtual de Python y la interfaz en el navegador ({F:despliegue}). '
            'La única comunicación externa es la de los proveedores de IA, que reciben la pregunta, el esquema de las '
            'vistas y ejemplos; solo cuando el usuario pide interpretar un resultado reciben sus filas, con los datos '
            'personales reemplazados por seudónimos. Un script de Windows instala dependencias, crea el almacén, carga '
            'las instituciones, entrena y levanta el sistema.'))
    a(('fig', 'despliegue', 'Diagrama de Despliegue del Prototipo', DIAGRAMAS / 'av2_despliegue.png', 15.0,
       'Diagrama de despliegue con navegador, API, Docker y proveedores de IA', 'Elaboración propia.'))
    a(('h3', '3.2.7 Recursos para la ejecución del caso práctico'))
    a(('p', 'La {T:recursos} detalla los recursos de hardware, software y talento humano empleados. Todo el software '
            'usado es libre o tiene una edición gratuita para desarrollo, de modo que la réplica del prototipo en otra '
            'institución no exige licencias adicionales.'))
    a(('tab', 'recursos', 'Recursos del Caso Práctico', ['Tipo', 'Recurso', 'Especificación o uso'],
       [['Hardware', 'Computador de desarrollo', 'Recomendado: 4 núcleos o más, 16 GB de RAM y 30 GB libres en disco'],
        ['Hardware', 'Conexión a internet', 'Descarga de dependencias y consulta a proveedores de IA'],
        ['Software', 'Windows 10/11, Docker Desktop', 'Sistema operativo y contenedor de SQL Server 2022 Developer'],
        ['Software', 'Python 3.13 y Node.js 20', 'Backend, modelos e interfaz'],
        ['Software', 'Visual Studio Code, Git y GitHub', 'Desarrollo y control de versiones'],
        ['Software', 'Claves de proveedores de IA', 'Planes gratuitos de Gemini, Groq, NVIDIA NIM y DeepSeek'],
        ['Datos', 'Datos de prueba UNEMI y OULAD', 'Simulador propio y conjunto público con licencia CC BY 4.0'],
        ['Talento humano', 'Autores del proyecto', 'Análisis, desarrollo, pruebas y documentación'],
        ['Talento humano', 'Tutoría académica', 'Revisión metodológica de los avances']],
       'Elaboración propia.', [3.0, 5.0, 8.0]))
    return b

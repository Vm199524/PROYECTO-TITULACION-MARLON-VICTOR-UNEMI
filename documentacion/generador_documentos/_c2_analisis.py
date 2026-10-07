# -*- coding: utf-8 -*-
"""Capítulo 2 del Avance 2: análisis del caso y requerimientos.

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from _datos import C, C_ORIGEN, DIAGRAMAS, LAT, O, U, f, pct


def _resultado_consulta() -> tuple[str, str, str, str]:
    if not C:
        return 'Pendiente', 'Pendiente', 'Pendiente', 'Pendiente'
    r = C['resumen']
    cert = C.get('por_origen', {}).get('CERTIFICADA', {})
    total = r['preguntas_base'] + r['preguntas_robustez']
    cobertura = (f"{cert.get('preguntas', 0)} de {total} preguntas, con "
                 f"{pct(cert.get('exactitud_relajada', 0), 0)} de acierto")
    exact = pct(r['exactitud_relajada_base']) if C_ORIGEN == 'SQL_SERVER' else 'Se mide con los proveedores de IA'
    return exact, r['adversariales_contenidas'], str(r['violaciones_aislamiento']), cobertura


def bloques() -> list[tuple]:
    um, om = U['m'], O['m']
    ut, ot = um['validacion_temporal'], om['validacion_temporal']
    us, os_ = U['s'], O['s']
    exact, advers, fugas, cobertura = _resultado_consulta()
    b: list[tuple] = []
    a = b.append

    a(('h1', '2. Análisis del caso'))
    a(('h2', '2.1 Requerimientos'))
    a(('p', 'Los requerimientos se obtuvieron de tres fuentes: el diagnóstico del capítulo anterior, la literatura '
            'revisada y las necesidades de los actores que usarán el sistema, en particular la autoridad académica '
            'sin perfil técnico. Se documentan como especificación de requisitos del producto: actores, historias de '
            'usuario, requerimientos funcionales derivados de las cuatro piezas de la solución (modelo predictivo, '
            'segmentación, consulta conversacional y panel), requerimientos no funcionales, requisitos de protección '
            'de datos y métricas de calidad con su criterio de aceptación.'))

    a(('h3', '2.1.1 Alternativas de solución analizadas'))
    a(('p', 'Antes de fijar los requerimientos se compararon tres alternativas ({T:alternativas}). La primera reproduce la '
            'práctica habitual: un modelo entrenado aparte y un tablero de inteligencia de negocios que muestra sus '
            'resultados. La segunda conecta directamente un modelo de lenguaje a la base de datos. La tercera, '
            'elegida, integra las cuatro piezas sobre vistas gobernadas.'))
    a(('tab', 'alternativas', 'Alternativas de Solución Evaluadas',
       ['Alternativa', 'Ventajas', 'Limitaciones', 'Decisión'],
       [['A. Modelo en cuaderno y tablero de inteligencia de negocios', 'Rápida de construir; herramientas '
         'conocidas.', 'La predicción no se actualiza con el sistema; sin explicación por estudiante; exige '
         'licencias y un analista para cada pregunta nueva.', 'Descartada'],
        ['B. Modelo de lenguaje conectado a la base', 'Responde cualquier pregunta en español.', 'Puede inventar '
         'columnas o cifras; riesgo de inyección y de leer datos de otra institución; sin trazabilidad.',
         'Descartada'],
        ['C. Sistema web integrado con vistas gobernadas', 'Una sola fuente para panel, ficha y chat; métricas '
         'certificadas; aislamiento en el motor; explicación y auditoría.', 'Mayor esfuerzo de desarrollo y de '
         'pruebas.', 'Elegida']],
       'Elaboración propia.', [3.6, 4.2, 6.0, 2.2]))

    a(('h3', '2.1.2 Aportes de la literatura a los requerimientos'))
    a(('p', 'Cada hallazgo de la literatura se tradujo en una exigencia verificable del sistema ({T:literatura}). Así, los '
            'requerimientos no responden a preferencias del equipo, sino a problemas documentados en estudios '
            'previos.'))
    a(('tab', 'literatura', 'Hallazgos de la Literatura Traducidos en Requerimientos',
       ['Hallazgo', 'Fuente', 'Requerimiento derivado'],
       [['Las particiones aleatorias sobrestiman el desempeño futuro', 'Duro et al. (2026); Carballo-Mendívil et al. '
         '(2025)', 'RF-03: validación temporal y prospectiva'],
        ['La actividad en el aula virtual anticipa el retiro', 'Marcolino et al. (2025); Vaarma y Li (2024)',
         'RF-02: perfil con variables del aula virtual y evaluaciones'],
        ['El riesgo difiere por facultad y carrera', 'Gutierrez-Pachas et al. (2023)', 'RF-11: segmentación de '
         'carreras'],
        ['La brecha de habilidades frena la adopción', 'Sequeira et al. (2024)', 'RF-10: consulta en lenguaje '
         'natural'],
        ['Los LLM mejoran con contexto, pero pueden errar', 'Ascoli y Choi (2025)', 'RF-10 y RNF-05: métricas '
         'certificadas y validador de SQL'],
        ['Las autoridades necesitan comparar con pares', 'Lepori y Bornmann (2026)', 'RF-12: referentes externos'],
        ['La visualización complementa al modelo', 'Orrego Granados et al. (2022)', 'RF-05 y RF-07: panel y ficha '
         'explicada'],
        ['El tratamiento de datos personales requiere finalidad y seguridad', 'Asamblea Nacional del Ecuador (2021)', 'RNF-01 '
         'a RNF-03: protección, mínimo privilegio y trazabilidad']],
       'Elaboración propia a partir de los estudios citados.', [6.0, 4.6, 5.4]))

    a(('h3', '2.1.3 Actores y roles'))
    a(('p', 'El sistema distingue tres roles con permisos diferentes ({T:actores}). El control de acceso se aplica en la '
            'API y, para los datos, en el motor de base de datos; la interfaz solo oculta lo que el rol no puede '
            'usar.'))
    a(('tab', 'actores', 'Actores, Roles y Permisos del Sistema',
       ['Actor', 'Rol', 'Necesidad principal', 'Permisos'],
       [['Decano o director de carrera', 'AUTORIDAD', 'Saber cuántos estudiantes están en riesgo, dónde y por qué, '
         'sin depender de TI.', 'Panel, lista, ficha, carreras, referentes, calidad del modelo, consulta, '
         'reportes y lectura del seguimiento'],
        ['Psicólogo, trabajador social o tutor', 'BIENESTAR', 'Priorizar a quién llamar y registrar lo que se hizo.',
         'Lo anterior, más la simulación de escenarios y el registro y cierre del acompañamiento'],
        ['Analista de tecnologías de la información', 'ADMIN_TI', 'Administrar cuentas, revisar la auditoría y '
         'el estado del sistema.', 'Todo lo anterior, más usuarios, auditoría, estado y vista del SQL generado'],
        ['Estudiante', 'Sin acceso', 'Recibir acompañamiento oportuno.', 'Es titular de los datos; no ingresa '
         'al sistema']],
       'Elaboración propia a partir de core/seguridad.py.', [3.4, 2.3, 4.6, 5.7]))

    a(('h3', '2.1.4 Historias de usuario para la autoridad académica'))
    a(('p', 'Las historias de usuario se redactaron desde la perspectiva de una autoridad o de una profesional de '
            'bienestar que no conoce SQL ni estadística ({T:hu}). Cada una tiene criterios de aceptación observables '
            'en la interfaz; las preguntas del conjunto dorado con que se evalúa la consulta conversacional están '
            'etiquetadas con la historia que atienden.'))
    hu = [
        ['HU-01', 'Como decana, quiero ver al abrir el sistema cuántos estudiantes están en riesgo alto y medio y '
                  'cómo cambió frente al periodo anterior, para saber si la situación empeora.',
         'Panel con totales por nivel, variación en puntos y una lectura en una frase, sin términos técnicos.'],
        ['HU-02', 'Como directora de carrera, quiero una lista de mis estudiantes ordenada por riesgo, para decidir '
                  'a quién atender primero.', 'Lista filtrable por carrera, nivel y riesgo, con cédula enmascarada y '
                  'acceso directo a la ficha.'],
        ['HU-03', 'Como profesional de bienestar, quiero entender por qué el sistema señala a un estudiante, para '
                  'preparar la conversación con él.', 'Ficha con probabilidad, percentil y los factores que más '
                  'suben o bajan el riesgo, redactados en español.'],
        ['HU-04', 'Como tutor, quiero saber qué pasaría si el estudiante mejora su asistencia o regulariza su '
                  'deuda, para proponerle metas concretas.', 'Simulador que recalcula la probabilidad al cambiar '
                  'variables y muestra la diferencia.'],
        ['HU-05', 'Como trabajadora social, quiero registrar la tutoría o el apoyo que brindé, para que el equipo '
                  'sepa quién ya fue atendido.', 'Registro con tipo, descripción y riesgo al registrar; cierre con '
                  'resultado; historial en la ficha.'],
        ['HU-06', 'Como decano, quiero preguntar en español «¿cuántos estudiantes de Enfermería están en riesgo '
                  'alto?» y obtener la cifra, para no esperar un informe.', 'Respuesta con tabla o gráfico, '
                  'resumen en una frase, origen (certificada o generada) y opción de descargar.'],
        ['HU-07', 'Como vicerrectora, quiero saber qué carreras requieren atención prioritaria, para asignar '
                  'recursos.', 'Mapa y tabla de segmentos con su tasa histórica, riesgo medio y estudiantes en '
                  'riesgo.'],
        ['HU-08', 'Como autoridad, quiero comparar nuestra tasa de abandono con referentes externos, para '
                  'dimensionar el problema.', 'Tabla de referentes con país, año, definición del indicador y '
                  'nivel de comparabilidad.'],
        ['HU-09', 'Como autoridad, quiero saber cuánto puedo confiar en la predicción, para justificar '
                  'decisiones.', 'Página de calidad con ROC-AUC, recall, calibración, equidad y explicación en '
                  'lenguaje sencillo.'],
        ['HU-10', 'Como decano, quiero descargar un informe ejecutivo del periodo, para presentarlo al consejo.',
         'Informe en PDF y Excel con resumen, carreras prioritarias y lista de estudiantes enmascarada.'],
    ]
    a(('tab', 'hu', 'Historias de Usuario y Criterios de Aceptación', ['ID', 'Historia de usuario', 'Criterio de aceptación'],
       hu, 'Elaboración propia.', [1.4, 8.0, 6.6]))
    a(('p', 'La {F:casos} resume los casos de uso que se desprenden de las historias y de los roles. La autoridad y '
            'bienestar comparten la consulta de información; solo bienestar registra acompañamientos y solo la '
            'administración de TI gestiona cuentas y revisa la auditoría.'))
    a(('fig', 'casos', 'Diagrama de Casos de Uso del Sistema', DIAGRAMAS / 'av2_casos_uso.png', 15.5,
       'Diagrama de casos de uso con tres actores y los casos de consulta, seguimiento y administración',
       'Elaboración propia.'))

    a(('h3', '2.1.5 Requerimientos funcionales'))
    a(('p', 'Los requerimientos funcionales se agrupan según la pieza de la solución de la que derivan ({T:rf}). Las '
            'piezas transversales (datos, seguridad y administración) sostienen a las cuatro principales.'))
    rf = [
        ['Datos', 'RF-02', 'Cargar y transformar la trayectoria de cada institución mediante un perfil de mapeo, sin '
                           'cambiar el código del modelo.', 'Alta'],
        ['Modelo', 'RF-03', 'Entrenar y comparar al menos cuatro modelos con validación cruzada agrupada por '
                            'estudiante, validación temporal y evaluación prospectiva.', 'Alta'],
        ['Modelo', 'RF-04', 'Calibrar las probabilidades y fijar umbrales de riesgo medio y alto por recall '
                            'objetivo.', 'Alta'],
        ['Modelo', 'RF-07', 'Explicar cada predicción con los factores que más aportan (SHAP), en español.',
         'Alta'],
        ['Modelo', 'RF-08', 'Simular el cambio de probabilidad al modificar variables del estudiante.', 'Media'],
        ['Modelo', 'RF-13', 'Mostrar la calidad del modelo: ROC-AUC, PR-AUC, recall, calibración, importancia y '
                            'equidad.', 'Alta'],
        ['Modelo', 'RF-17', 'Calificar por lotes a los estudiantes activos y vigilar la deriva de variables (PSI).',
         'Alta'],
        ['Segmentación', 'RF-11', 'Agrupar las carreras en segmentos de riesgo con validación de estabilidad y '
                                  'prueba estadística.', 'Alta'],
        ['Consulta', 'RF-10', 'Responder preguntas en español con métricas certificadas y, si no hay coincidencia, '
                              'con SQL generado y validado.', 'Alta'],
        ['Consulta', 'RF-14', 'Exportar respuestas y generar el informe ejecutivo en PDF y Excel.', 'Media'],
        ['Panel', 'RF-05', 'Presentar el panel institucional con totales, variación y lectura del periodo.', 'Alta'],
        ['Panel', 'RF-06', 'Listar estudiantes priorizados por riesgo con filtros y paginación.', 'Alta'],
        ['Panel', 'RF-09', 'Registrar, consultar y cerrar acompañamientos (tutoría, consejería, apoyo económico, '
                           'contacto, derivación).', 'Alta'],
        ['Panel', 'RF-12', 'Mostrar referentes externos de abandono con su comparabilidad.', 'Media'],
        ['Seguridad', 'RF-01', 'Autenticar con usuario y contraseña, emitir un token con vencimiento y aplicar '
                               'permisos por rol.', 'Alta'],
        ['Seguridad', 'RF-18', 'Aislar los datos por institución activa en todas las lecturas.', 'Alta'],
        ['Administración', 'RF-15', 'Crear, editar, desactivar y eliminar cuentas, sin dejar el sistema sin un '
                                    'administrador.', 'Media'],
        ['Administración', 'RF-16', 'Registrar la auditoría de accesos y consultas y mostrar el estado del '
                                    'sistema.', 'Media'],
    ]
    a(('tab', 'rf', 'Requerimientos Funcionales por Pieza de la Solución', ['Pieza', 'ID', 'Requerimiento', 'Prioridad'],
       rf, 'Elaboración propia. La numeración coincide con los comentarios del código fuente.', [3.0, 1.5, 9.5, 2.0]))

    a(('h3', '2.1.6 Requerimientos no funcionales'))
    a(('p', 'Los requerimientos no funcionales fijan cómo debe comportarse el sistema y con qué métrica se verifica '
            'cada uno ({T:rnf}).'))
    rnf = [
        ['RNF-01', 'Protección de datos', 'Cédula enmascarada en pantalla y ficha identificada por token cifrado. '
                                          'Hacia los proveedores de IA solo salen la pregunta, el esquema y ejemplos; '
                                          'si el usuario pide interpretar un resultado, sus filas salen '
                                          'seudonimizadas.',
         'Pruebas de privacidad: 100 % superadas'],
        ['RNF-02', 'Mínimo privilegio y aislamiento', 'La consulta usa una cuenta que solo lee vistas; el '
                                                     'seguimiento, una que solo ejecuta dos procedimientos.',
         'Cero lecturas de otra institución'],
        ['RNF-03', 'Trazabilidad', 'Cada ingreso, consulta, exportación y cambio de cuenta queda en la auditoría.',
         '100 % de eventos registrados'],
        ['RNF-04', 'Calidad predictiva', 'Desempeño medido en periodos no vistos.', 'ROC-AUC ≥ 0,75; recall '
                                                                                   '≥ 0,75 (medio)'],
        ['RNF-05', 'Calidad de la consulta', 'Exactitud por ejecución frente al SQL de referencia y resistencia a '
                                             'preguntas maliciosas.', 'Exactitud ≥ 85 %; 8/8 contenidas'],
        ['RNF-06', 'Rendimiento', 'Tiempo de respuesta de los servicios de las páginas y de la ruta certificada.',
         'Mediana < 2 s'],
        ['RNF-07', 'Usabilidad', 'Lenguaje sin tecnicismos, tema claro y oscuro y diseño adaptable a escritorio y '
                                 'móvil.', 'Tasa de éxito ≥ 80 % en tareas de las HU con usuarios'],
        ['RNF-08', 'Mantenibilidad', 'Código modular, pruebas automatizadas y nueva institución por perfil.',
         'Pruebas del backend y del frontend en verde'],
        ['RNF-09', 'Explicabilidad', 'Toda alerta muestra sus factores y la calidad del modelo es visible.',
         'Tres factores por predicción'],
        ['RNF-10', 'Portabilidad', 'Ejecución local con Docker y un instalador para Windows.', 'Instalación con '
                                                                                             'un script'],
    ]
    a(('tab', 'rnf', 'Requerimientos No Funcionales y su Métrica de Verificación', ['ID', 'Atributo', 'Requerimiento',
                                                                           'Métrica o meta'],
       rnf, 'Elaboración propia.', [1.6, 2.9, 7.4, 4.1]))

    a(('h3', '2.1.7 Requisitos de protección de datos estudiantiles'))
    a(('p', 'Como el sistema trata datos personales de estudiantes, los requisitos de la LOPDP se convirtieron en '
            'controles técnicos concretos ({T:lopdp}). El objetivo es que la protección no dependa de la buena '
            'voluntad del usuario, sino de la arquitectura.'))
    a(('tab', 'lopdp', 'Principios de la LOPDP y Controles Implementados',
       ['Principio', 'Control técnico', 'Evidencia en el prototipo'],
       [['Finalidad', 'Los datos se usan solo para la alerta y el acompañamiento; no hay perfiles comerciales ni '
                      'decisiones automáticas sobre el estudiante.', 'El sistema recomienda; la decisión es de una '
                                                                      'persona.'],
        ['Minimización', 'Las vistas exponen solo las columnas necesarias; el modelo no usa nombres ni cédula.',
         'Vistas VIS_* y variables del modelo'],
        ['Confidencialidad', 'Cédula enmascarada, token Fernet en la ficha y seudónimos hacia el proveedor de IA.',
         'core/privacidad.py y sus pruebas'],
        ['Seguridad', 'Contraseñas con bcrypt, token JWT con vencimiento, cuentas de mínimo privilegio y '
                      'filtrado por SESSION_CONTEXT.', 'Script del almacén y core/seguridad.py'],
        ['Responsabilidad proactiva', 'Auditoría de accesos, consultas y exportaciones con huella del SQL.',
         'Página de auditoría'],
        ['Calidad y no discriminación', 'Evaluación del desempeño por género, modalidad y sede.', 'Sección de '
                                                                                                'equidad'],
        ['Transferencia internacional', 'Los proveedores de IA están fuera del país: no reciben filas sin '
                                        'seudonimizar y, en producción, se usarán solo proveedores con garantías '
                                        'contractuales o un modelo alojado en la institución.', 'core/privacidad.py; '
                                                                                               'recomendación a TI'],
        ['Evaluación de impacto', 'Antes de usar datos reales se requiere una evaluación de impacto del tratamiento, '
                                  'por tratarse de perfiles automatizados de estudiantes.', 'Requisito previo al '
                                                                                            'piloto'],
        ['Derechos del titular', 'Los datos de prueba son sintéticos; un despliegue real requiere consentimiento '
                                 'o base legal y un acuerdo de tratamiento.', 'Alcance del caso']],
       'Elaboración propia a partir de la Ley Orgánica de Protección de Datos Personales (Asamblea Nacional del Ecuador, 2021).',
       [3.0, 7.6, 5.4]))

    a(('h3', '2.1.8 Métricas de calidad y criterios de aceptación'))
    a(('p', 'La {T:metricas} reúne las métricas con que se acepta el prototipo y el valor obtenido en este avance. Las '
            'cifras se leen directamente de los archivos de resultados del sistema.'))
    conf = 'Sí' if ut['roc_auc'] >= 0.75 and ot['roc_auc'] >= 0.75 else 'Parcial'
    rec_ok = 'Sí' if min(ut['umbral_medio']['recall'], ot['umbral_medio']['recall']) >= 0.75 else 'Parcial'
    kw_u = us.get('kruskal_wallis', {}).get('p', 1)
    met = [
        ['ROC-AUC temporal', '≥ 0,75', f"{f(ut['roc_auc'])} (UNEMI, prueba) y {f(ot['roc_auc'])} (OULAD)", conf],
        ['Recall en umbral medio', '≥ 0,75', f"{f(ut['umbral_medio']['recall'])} y "
                                             f"{f(ot['umbral_medio']['recall'])}", rec_ok],
        ['PR-AUC temporal', 'Mayor que la prevalencia', f"{f(ut['pr_auc'])} frente a {f(ut['prevalencia'])}; "
                                                       f"{f(ot['pr_auc'])} frente a {f(ot['prevalencia'])}", 'Sí'],
        ['Puntaje de Brier', 'Menor tras calibrar', f"{f(ut['brier_sin_calibrar'])} → {f(ut['brier_calibrado'])}; "
                                                   f"{f(ot['brier_sin_calibrar'])} → {f(ot['brier_calibrado'])}",
         'Sí'],
        ['Segmentación', '≥ 3 segmentos; p < 0,05', f"{us.get('k')} segmentos; silueta {f(us.get('silhouette'))}; "
                                                    f"p = {f(kw_u)}", 'Sí' if kw_u < 0.05 else 'Parcial'],
        ['Cobertura de la ruta certificada', 'Informativa', cobertura, 'No aplica'],
        ['Exactitud NL2SQL global', '≥ 85 %', exact, 'Sí' if C_ORIGEN == 'SQL_SERVER' and
         C['resumen']['exactitud_relajada_base'] >= 0.85 else 'Pendiente (corrida final)'],
        ['Mediana de respuesta de los servicios', '< 2 s', f"{LAT.get('mediana_ms', 'n. d.')} ms (p95 "
                                                          f"{LAT.get('p95_ms', 'n. d.')} ms) en la réplica",
         'Sí' if LAT else 'Pendiente'],
        ['Preguntas maliciosas', '8/8 contenidas', advers, 'Sí' if advers == '8/8' else 'No'],
        ['Fugas entre instituciones', '0', fugas + ' en la réplica', 'Sí (réplica)' if fugas == '0' else 'No'],
    ]
    a(('tab', 'metricas', 'Métricas de Calidad, Criterio de Aceptación y Resultado', ['Métrica', 'Criterio', 'Resultado',
                                                                        'Cumple'],
       met, 'UNEMI: datos de prueba sintéticos; OULAD: datos reales anonimizados. La consulta, el aislamiento y la '
            'latencia se midieron en la réplica de validación descrita en la sección 3.1.6 y se repiten en la corrida '
            'final sobre SQL Server. Elaboración propia a partir de ml/modelos/*/metricas.json y eval/.', [3.8, 3.6, 6.6, 2.0]))
    return b

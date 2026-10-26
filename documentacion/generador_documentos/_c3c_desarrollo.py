# -*- coding: utf-8 -*-
"""Sección 3.3 Desarrollo: tecnologías y herramientas, y código del frontend y del backend explicado a
manera de manual (exigencia del formato oficial del trabajo de titulación).

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

from _datos import DIAGRAMAS, N_PRUEBAS_BACKEND, N_PRUEBAS_FRONTEND


def _codigo(clave: str, titulo: str, archivo: str, alt: str, nota: str) -> tuple:
    return ('fig', clave, titulo, DIAGRAMAS / archivo, 16.0, alt, nota)


def bloques() -> list[tuple]:
    b: list[tuple] = []
    a = b.append
    a(('h2', '3.3 Desarrollo'))
    a(('p', 'Esta sección detalla las tecnologías implementadas y explica, a manera de manual, el código principal de '
            'la interfaz web (frontend) y del servidor (backend). Los extractos son literales del repositorio del '
            'proyecto; las líneas omitidas se marcan con «…».'))

    # ── 3.3.1 ────────────────────────────────────────────────────────────
    a(('h3', '3.3.1 Tecnologías y herramientas implementadas'))
    a(('p', 'La {T:tecnologias} reúne las tecnologías con su versión y el lugar del sistema donde se usan. Las '
            'versiones están fijadas en backend/requirements.txt y frontend/package.json, de modo que cualquier '
            'persona puede reconstruir el mismo entorno con que se obtuvieron los resultados.'))
    a(('tab', 'tecnologias', 'Tecnologías Implementadas por Capa y su Versión',
       ['Capa', 'Tecnología (versión)', 'Uso en el sistema'],
       [['Base de datos', 'SQL Server 2022 en Docker', 'Almacén en esquema estrella, vistas gobernadas, '
                                                       'procedimientos y cuentas de mínimo privilegio'],
        ['Procesos por lotes', 'Python 3.13, pandas 3.0, pyodbc 5.3', 'ETL por perfil institucional, construcción '
                                                                       'del panel y orquestación del pipeline'],
        ['Aprendizaje automático', 'scikit-learn 1.9, LightGBM 4.7, Optuna 5.0, imbalanced-learn 0.14',
         'Comparación de cuatro modelos, ajuste de hiperparámetros, SMOTE y calibración de Platt'],
        ['Explicación', 'SHAP 0.52', 'Factores que suben o bajan el riesgo de cada estudiante'],
        ['Operación del modelo', 'MLflow 3.17, Great Expectations 1.24, Evidently 0.7',
         'Registro de experimentos, calidad de datos y deriva'],
        ['API', 'FastAPI 0.141, Pydantic 2.13, python-jose 3.5, bcrypt 5.0', '27 operaciones REST, validación de '
                                                                            'datos, token JWT y contraseñas cifradas'],
        ['Consulta conversacional', 'sqlglot 30.21, cliente OpenAI 3.26', 'Validación del SQL como árbol y '
                                                                          'cascada de proveedores de IA'],
        ['Reportes', 'openpyxl 3.1, ReportLab 5.0', 'Informe ejecutivo en Excel y PDF'],
        ['Interfaz web', 'React 18.3, TypeScript 5.9, Vite 5.4, Tailwind CSS 3.4', 'Aplicación de una sola página '
                                                                                  'por roles, tema claro y oscuro'],
        ['Datos en la interfaz', 'TanStack Query 5, React Router 6, Recharts 2.15', 'Caché por institución, rutas '
                                                                                   'protegidas y gráficos'],
        ['Inteligencia de negocios', 'Metabase 0.63 en Docker', 'Consulta alternativa sobre el esquema agregado bi'],
        ['Pruebas', f'pytest 9.1 ({N_PRUEBAS_BACKEND} pruebas), vitest 1.6 ({N_PRUEBAS_FRONTEND} pruebas), '
                    'Playwright', 'Pruebas unitarias, de integración, de interfaz y capturas'],
        ['Herramientas de desarrollo', 'Visual Studio Code, Git y GitHub (Actions), Docker Desktop, PlantUML, '
                                       'Zotero', 'Edición, control de versiones, integración continua, '
                                                 'diagramas UML y gestión bibliográfica']],
       'Elaboración propia a partir de backend/requirements.txt y frontend/package.json.', [3.2, 6.0, 6.8]))
    a(('p', 'El proyecto se trabajó con control de versiones en GitHub desde el inicio: cada cambio quedó en el '
            'historial con su autor, y la integración continua (GitHub Actions) ejecuta las pruebas del backend y '
            'del frontend en cada envío. La instalación en un equipo nuevo se reduce a dos pasos: '
            'scripts\\reconstruir_sistema.bat crea la base, carga los datos y entrena los modelos, e iniciar.bat '
            '(equivalente a npm start) instala lo que falte y levanta la API en el puerto 8090 y la interfaz en el '
            'puerto 3000.'))

    # ── 3.3.2 Frontend ────────────────────────────────────────────────────
    a(('h3', '3.3.2 Código del frontend'))
    a(('p', 'La interfaz es una aplicación de una sola página escrita en React con TypeScript. Su organización sigue '
            'la regla de que cada carpeta tiene una sola responsabilidad ({T:estructura_frontend}): las páginas '
            'componen la pantalla, los componentes de interfaz se reutilizan en todas ellas y la carpeta lib '
            'concentra la comunicación con la API, la sesión, los permisos y el formato de las cifras en español del '
            'Ecuador.'))
    a(('tab', 'estructura_frontend', 'Estructura del Código del Frontend',
       ['Carpeta o archivo', 'Contenido', 'Ejemplos'],
       [['src/App.tsx', 'Rutas de la aplicación y protección por capacidad', 'Protegida, App'],
        ['src/paginas/', 'Una página por proceso académico', 'Panel, Estudiantes, Ficha, Consulta, Carreras, '
                                                              'CalidadModelo, Seguimiento, Reportes, admin/'],
        ['src/componentes/ui/', 'Componentes reutilizables con el estilo del sistema', 'Card, Kpi, Table, Badge, '
                                                                                         'Button, Dialogo, Toast'],
        ['src/componentes/layout/', 'Marco de la aplicación', 'AppShell (menú lateral plegable y cabecera), '
                                                              'navegación por rol'],
        ['src/lib/api.ts', 'Cliente HTTP con token e institución activa', 'obtener, enviar, descargar, ErrorApi'],
        ['src/lib/sesion.tsx', 'Estado de la sesión compartido por toda la aplicación', 'ProveedorSesion, useSesion'],
        ['src/lib/consultas.ts', 'Lectura de datos con caché por institución', 'useDatos'],
        ['src/lib/permisos.ts', 'Capacidades por rol, espejo del backend', 'Capacidad, puede'],
        ['src/lib/tipos.ts y formato.ts', 'Tipos de las respuestas de la API y formato es-EC', 'CalidadModelo, '
                                                                                               'decimal, proporcion'],
        ['src/pruebas/', 'Pruebas de interfaz con vitest y Testing Library', 'navegación, formato y componentes']],
       'Elaboración propia a partir de frontend/src/.', [4.2, 6.0, 5.8]))
    a(('p', '**Rutas protegidas.** En la {F:codigo_rutas}, el componente Protegida recibe en la propiedad requiere la '
            'capacidad que exige la pantalla (por ejemplo, ver_modelo) y la compara con las capacidades del rol del '
            'usuario mediante la función puede del contexto de sesión. Si el rol no la tiene, muestra un mensaje en '
            'lugar de la página; si la tiene, carga la página bajo demanda (lazy y Suspense), lo que reduce el peso '
            'de la primera carga. La variable perfil indica si hay sesión: sin ella, toda dirección redirige a '
            '/ingresar. Esta protección solo decide qué se muestra; la autorización real la vuelve a verificar el '
            'backend en cada petición.'))
    a(_codigo('codigo_rutas', 'Rutas de la Aplicación Protegidas por Capacidad', 'tf_codigo_rutas.png',
              'Extracto de código TSX con el componente Protegida y la definición de rutas',
              'Extracto de frontend/src/App.tsx; se omiten las rutas de administración.'))
    a(('p', '**Comunicación con la API.** La {F:codigo_cliente} muestra el cliente HTTP. La función cabeceras agrega a '
            'cada petición dos datos: el token JWT (variable tokenEnMemoria, guardado en sessionStorage para que se '
            'borre al cerrar la pestaña) y la institución activa en la cabecera X-Institucion. La función pedir '
            'centraliza los errores: un 401 cierra la sesión en todas las vistas mediante el evento '
            'vicmar:sesion-vencida, y cualquier otro error se convierte en un ErrorApi con un mensaje legible para el '
            'usuario. El gancho useDatos usa TanStack Query con una clave de caché que incluye el código de la '
            'institución: si el usuario cambia de institución, nunca ve por un instante los datos de la anterior.'))
    a(_codigo('codigo_cliente', 'Cliente de la API y Lectura de Datos con Caché por Institución',
              'tf_codigo_cliente.png', 'Extracto de código TypeScript de las funciones cabeceras, pedir y useDatos',
              'Extracto de frontend/src/lib/api.ts y frontend/src/lib/consultas.ts.'))
    a(('p', '**Una página del sistema.** La {F:codigo_pagina} corresponde a la pestaña «Por periodo y carrera» de la '
            'página de calidad del modelo, agregada en este avance. Recibe en d la respuesta de GET /modelo/calidad; '
            'om contiene la validación con origen móvil y r su resumen. Los componentes Kpi muestran las cifras clave '
            '(ROC-AUC medio, peor periodo y recall medio) con un tono de color según su significado, y TablaGrupos, '
            'un componente propio de la página, presenta cada periodo o carrera con sus casos, ROC-AUC, PR-AUC y '
            'recall. Las funciones decimal y proporcion escriben los números con coma decimal, como se usa en el '
            'Ecuador.'))
    a(_codigo('codigo_pagina', 'Página de Validación por Periodo y Carrera', 'tf_codigo_pagina.png',
              'Extracto de código TSX del componente PorPeriodo',
              'Extracto de frontend/src/paginas/CalidadModelo.tsx.'))

    # ── 3.3.3 Backend ─────────────────────────────────────────────────────
    a(('h3', '3.3.3 Código del backend'))
    a(('p', 'El backend se escribió en Python y se organiza por responsabilidad ({T:estructura_backend}). La API no '
            'contiene lógica de negocio: cada ruta valida el permiso y delega en los módulos de modelo, consulta o '
            'seguimiento, que a su vez leen el almacén solo a través de core/db.py.'))
    a(('tab', 'estructura_backend', 'Estructura del Código del Backend y sus Funciones Principales',
       ['Módulo', 'Responsabilidad', 'Funciones o servicios principales'],
       [['main.py', 'Aplicación FastAPI, cabeceras de seguridad y registro de peticiones', 'app, cabeceras_y_registro'],
        ['api/', 'Diez routers, uno por proceso académico', 'POST /auth/ingresar, GET /panel/resumen, GET '
                                                              '/estudiantes/{token}, POST /consulta, GET /modelo/calidad'],
        ['core/', 'Configuración, seguridad, conexión a la base, privacidad y auditoría', 'requiere, sesion_actual, '
                                                                                            'leer, enmascarar_cedula'],
        ['etl/', 'Carga de cada institución al almacén mediante perfiles', 'etl_academico, PerfilInstitucion'],
        ['ml/', 'Panel de variables, entrenamiento, calibración, calificación, explicación y segmentación',
         'construir_panel, entrenar_panel, validacion_origen_movil, calificar_panel, contribuciones'],
        ['mlops/', 'Calidad de datos, deriva y registro de experimentos', 'validar, informe_deriva, '
                                                                           'registrar_entrenamiento'],
        ['nl2sql/', 'Motor de la consulta conversacional', 'clasificar, elegir, generar, validar, responder'],
        ['scripts/', 'Pipeline y utilidades de operación', 'pipeline, anonimizar_carrera, crear_usuarios_demo'],
        ['tests/', f'{N_PRUEBAS_BACKEND} pruebas automatizadas', 'test_modelo, test_mlops, test_validador, '
                                                                   'test_integracion_bd']],
       'Elaboración propia a partir de backend/.', [2.6, 6.0, 7.4]))
    a(('p', '**Aplicación y seguridad.** La {F:codigo_main} crea la aplicación FastAPI, restringe los orígenes y '
            'cabeceras permitidos (CORS) y agrega a cada respuesta cabeceras que impiden incrustar la aplicación en '
            'otro sitio o guardar datos en caché. Los diez routers se registran bajo el prefijo /api. En la '
            '{F:codigo_seguridad}, la función requiere devuelve una dependencia de FastAPI: antes de ejecutar una '
            'ruta, obtiene la sesión a partir del token y rechaza con 403 a quien no tiene la capacidad o con 400 a '
            'quien no eligió institución. La función _conexion_con_contexto abre la conexión con la cuenta de solo '
            'lectura y fija la institución en SESSION_CONTEXT con @read_only = 1, de modo que ninguna sentencia '
            'posterior de la misma conexión pueda cambiarla; las vistas filtran por ese valor ({F:codigo_vista}).'))
    a(_codigo('codigo_main', 'Aplicación FastAPI con Cabeceras de Seguridad y Routers', 'tf_codigo_main.png',
              'Extracto de código Python de la creación de la aplicación FastAPI',
              'Extracto de backend/main.py.'))
    a(_codigo('codigo_seguridad', 'Control de Permisos por Rol y Aislamiento por Institución', 'tf_codigo_seguridad.png',
              'Extracto de código Python de las funciones requiere y _conexion_con_contexto',
              'Extracto de backend/core/seguridad.py y backend/core/db.py; se omite el manejo de errores.'))
    a(_codigo('codigo_vista', 'Vista Gobernada con Aislamiento por Institución', 'av2_codigo_vista.png',
              'Extracto de código SQL de una vista filtrada por SESSION_CONTEXT',
              'Extracto de base_de_datos/crear_almacen_academico.sql.'))
    a(('p', '**Entrenamiento del modelo.** En la {F:codigo_modelo}, la función entrenar_panel separa los periodos más '
            'recientes como prueba temporal (particion_temporal), ajusta los hiperparámetros de Random Forest y '
            'LightGBM solo con el entrenamiento y compara los cuatro candidatos con validación cruzada agrupada por '
            'alumno_id. La variable final guarda el nombre del modelo de mayor ROC-AUC medio; calibrador es el '
            'escalado de Platt ajustado con las predicciones fuera de pliegue (oofs), y umbral_medio y umbral_alto '
            'son los cortes que alcanzan un recall de 0,80 y 0,50. Solo al final se predice una vez la prueba '
            'temporal (p_cal). La {F:codigo_origen_movil} repite ese esquema por periodo: para cada código de '
            'periodo, pasado contiene solo las filas que empezaron antes, y el calibrador y los umbrales se ajustan '
            'con ese pasado antes de predecir el periodo actual.'))
    a(_codigo('codigo_modelo', 'Selección, Calibración y Validación Temporal del Modelo', 'av2_codigo_entrenamiento.png',
              'Extracto de código Python de la función entrenar_panel',
              'Extracto de backend/ml/entrenar.py; se omiten líneas de registro.'))
    a(_codigo('codigo_origen_movil', 'Validación con Origen Móvil por Periodo', 'tf_codigo_origen_movil.png',
              'Extracto de código Python de la función validacion_origen_movil',
              'Extracto de backend/ml/evaluacion_grupos.py.'))
    a(('p', '**Calidad de los datos.** La {F:codigo_calidad} muestra cómo se declaran y validan las expectativas con '
            'Great Expectations. El contexto efímero no requiere archivos de configuración; cada regla (por ejemplo, '
            'que promedio esté entre 0 y 10) se convierte en la expectativa del mismo nombre y guarda en meta su '
            'índice, porque la biblioteca no garantiza el orden de los resultados. Si falla una expectativa '
            'crítica, el informe marca apto_para_entrenar como falso y el pipeline se detiene.'))
    a(_codigo('codigo_calidad', 'Validación de la Calidad de los Datos con Great Expectations', 'tf_codigo_calidad.png',
              'Extracto de código Python de la validación con Great Expectations',
              'Extracto de backend/mlops/calidad_datos.py.'))
    a(('p', '**Consulta conversacional.** El servicio POST /consulta ({F:codigo_api}) recibe la pregunta en un modelo '
            'Pydantic que limita su longitud y el historial, exige la capacidad consultar, delega en el motor y '
            'registra la auditoría con la huella del SQL, no con los datos. El motor ({F:codigo_motor}) aplica '
            'primero las barreras; luego el enrutador busca una de las 40 métricas certificadas y, solo si no la '
            'encuentra, el generador pide el SQL a un modelo de lenguaje. Ese SQL pasa por el validador '
            '({F:codigo_validador}), que lo analiza como árbol sintáctico: una sola sentencia, solo lectura, solo '
            'vistas VIS_* y columnas existentes, y un límite de 500 filas. Al final, las cédulas se enmascaran '
            'antes de mostrarse y el resumen se redacta sin IA, solo con los valores del resultado.'))
    a(_codigo('codigo_api', 'Servicio REST de la Consulta Conversacional', 'av2_codigo_api.png',
              'Extracto de código del endpoint POST /consulta', 'Extracto de backend/api/consulta.py.'))
    a(_codigo('codigo_motor', 'Motor de la Consulta Conversacional', 'av2_codigo_motor.png',
              'Extracto de código de la función responder',
              'Extracto de backend/nl2sql/motor.py; se omiten el manejo de errores y la medición del tiempo.'))
    a(_codigo('codigo_validador', 'Validación del SQL Generado sobre su Árbol Sintáctico', 'av2_codigo_validador.png',
              'Extracto de código de la función validar con sqlglot',
              'Extracto simplificado de backend/nl2sql/validador.py.'))
    return b

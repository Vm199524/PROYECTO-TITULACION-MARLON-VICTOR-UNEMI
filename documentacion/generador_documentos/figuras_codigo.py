# -*- coding: utf-8 -*-
"""
Figuras de código fuente del trabajo de titulación (16 cm de ancho, texto a 10 pt reales).

Cada figura es un extracto literal del repositorio; las líneas omitidas se marcan
con «…». El HTML se escribe en documentacion/diagramas/fuentes/codigo/ y el PNG
en documentacion/diagramas/, con el mismo renderizador de las demás figuras.

Uso:
    python documentacion/generador_documentos/figuras_codigo.py

Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
Proyecto de titulación · Universidad Estatal de Milagro · 2026
"""
from __future__ import annotations

import html
from pathlib import Path

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import PythonLexer, TransactSqlLexer, TsxLexer, TypeScriptLexer

RAIZ = Path(__file__).resolve().parents[2]
SALIDA_HTML = RAIZ / 'documentacion' / 'diagramas' / 'fuentes' / 'codigo'
SALIDA_PNG = RAIZ / 'documentacion' / 'diagramas'

EXTRACTOS = {
    'av2_codigo_entrenamiento': ('backend/ml/entrenar.py · entrenar_panel()', PythonLexer, '''\
# Prueba temporal: los periodos académicos más recientes
es_prueba, periodos_prueba = particion_temporal(etiquetado)
train, prueba = etiquetado[~es_prueba], etiquetado[es_prueba]
X_tr, X_te = matriz(train, columnas), matriz(prueba, columnas)
y_tr, y_te, grupos_tr = train['y'], prueba['y'], train['alumno_id']

params_rf, hist_rf = ajustar_rf(X_tr, y_tr, grupos_tr, intentos_rf)
params_lgbm, hist_lgbm = ajustar_lgbm(X_tr, y_tr, grupos_tr,
                                     pruebas_optuna)

comparacion, oofs = {}, {}
for nombre, modelo in candidatos(params_rf, params_lgbm).items():
    # validación cruzada agrupada por estudiante (5 pliegues)
    comparacion[nombre], oofs[nombre] = evaluar_cv(modelo, X_tr, y_tr,
                                                   grupos_tr)
final = max(comparacion,
            key=lambda n: (comparacion[n]['roc_auc']['media'],
                           comparacion[n]['pr_auc']['media']))

calibrador = calibrar(y_tr, oofs[final])                 # Platt
oof_cal = calibrador.predict(oofs[final])
umbral_medio = umbral_para_recall(y_tr, oof_cal, RECALL_MEDIO)  # 0,80
umbral_alto = max(umbral_para_recall(y_tr, oof_cal, RECALL_ALTO),
                  umbral_medio)                                # 0,50

modelo = candidatos(params_rf, params_lgbm)[final]
modelo_temporal = clone(modelo).fit(X_tr, y_tr)
p_raw = modelo_temporal.predict_proba(X_te)[:, 1]
p_cal = calibrador.predict(p_raw)
temporal = evaluar_prueba(y_te, p_cal, p_raw, umbral_alto,
                          umbral_medio)
'''),
    'av2_codigo_motor': ('backend/nl2sql/motor.py · responder()', PythonLexer, '''\
intencion = clasificar(r.pregunta, institucion,
                       instituciones_conocidas)
if intencion.tipo != 'CONSULTA':     # barrera (escritura, otra IES)
    r.explicacion = intencion.mensaje
    return r
carreras, facultades = _entidades_institucion(institucion, lector)
entidades = enrutador.extraer_entidades(r.pregunta, carreras,
                                        facultades)
elegida = enrutador.elegir(entidades)    # TF-IDF contra 40 métricas
if elegida:                       # ruta certificada (SQL fijo)
    sql, parametros = _parametros_certificada(elegida.metrica,
                                              entidades)
    columnas, filas = lector(sql, institucion, parametros)
    r.origen = 'CERTIFICADA'
else:                             # ruta generada por el LLM
    ejemplos = enrutador.ejemplos_guiados(entidades)
    gen = generador.generar(r.pregunta, ejemplos, historial)
    columnas, filas, sql = _ejecutar_generada(r, gen, ejemplos,
                                              institucion, lector)
    r.origen = 'GENERADA_IA'
r.filas = enmascarar_para_pantalla(columnas, filas)
r.visualizacion = redactor.elegir_visualizacion(columnas, filas,
                                                sugerida)
r.explicacion = redactor.resumen(r.titulo, columnas, filas)  # sin IA
'''),
    'av2_codigo_validador': ('backend/nl2sql/validador.py · validar()', PythonLexer, '''\
sentencias = [s for s in sqlglot.parse(sql, read='tsql')
              if s is not None]
if len(sentencias) != 1:
    r.problemas.append('Solo se permite una sentencia por consulta.')
arbol = sentencias[0]
if not isinstance(arbol, (exp.Select, exp.Union, exp.Intersect,
                          exp.Except)):
    r.problemas.append('Solo se permiten consultas de lectura.')
for nodo in arbol.walk():                 # DROP, EXEC, INTO
    if isinstance(nodo, _NODOS_PROHIBIDOS):
        r.problemas.append('Operación no permitida.')
for tabla in arbol.find_all(exp.Table):
    if tabla.name.upper() not in columnas_permitidas():
        r.problemas.append('Solo se pueden leer las vistas VIS_*.')
for columna in arbol.find_all(exp.Column):  # columnas de la vista
    if columna.name.lower() not in conocidas | alias:
        r.problemas.append(f"La columna '{columna.name}' no existe.")
if not arbol.args.get('limit'):
    arbol = arbol.limit(LIMITE_FILAS)       # 500 filas como máximo
r.sql = arbol.sql(dialect='tsql')
'''),
    'av2_codigo_vista': ('base_de_datos/crear_almacen_academico.sql', TransactSqlLexer, '''\
CREATE VIEW dbo.VIS_PREDICCION_ABANDONO AS
SELECT da.cedula, da.apellidos, da.nombres,
       dc.facultad_nombre, dc.carrera,
       fm.promedio AS promedio_actual,
       fm.asistencia_pct AS asistencia_actual,
       fp.probabilidad, fp.riesgo_categoria, fp.percentil_riesgo,
       fp.factor_1, fp.factor_2, fp.factor_3, fp.modelo_version
FROM dbo.fact_prediccion_abandono fp
JOIN dbo.dim_alumno da      ON da.alumno_id = fp.alumno_id
JOIN dbo.fact_matriculas fm ON fm.matricula_id = fp.matricula_id_base
JOIN dbo.dim_carrera dc     ON dc.carrera_id = fm.carrera_id
WHERE fp.institucion_codigo =
      CAST(SESSION_CONTEXT(N'institucion_activa') AS VARCHAR(30));
GO
-- La cuenta de la consulta conversacional solo lee vistas
GRANT SELECT ON dbo.VIS_PREDICCION_ABANDONO TO chat_reader;
GRANT EXECUTE ON dbo.sp_registrar_intervencion TO app_seguimiento;
'''),
    'av2_codigo_api': ('backend/api/consulta.py', PythonLexer, '''\
class Pregunta(BaseModel):
    pregunta: str = Field(min_length=1, max_length=500)
    historial: list[dict] = Field(default_factory=list, max_length=10)


@router.post('/consulta')
def consultar(datos: Pregunta,
              sesion: Sesion = Depends(requiere('consultar'))):
    """Responde una pregunta sobre la institución activa."""
    r = motor.responder(datos.pregunta, sesion.institucion,
                        list(sesion.instituciones),
                        ver_sql=sesion.puede('ver_sql'),
                        historial=datos.historial)
    auditoria.registrar('CONSULTA', sesion.usuario, sesion.institucion,
                        resultado=r.origen,
                        detalle={'metrica': r.metrica_id,
                                 'filas': len(r.filas),
                                 'sql_huella': huella(r.sql or ''),
                                 'proveedor': r.proveedor,
                                 'ms': r.tiempo_ms})
    return r.a_dict()
'''),
    'tf_codigo_rutas': ('frontend/src/App.tsx · rutas protegidas por capacidad', TsxLexer, '''\
function Protegida({ requiere, children }: { requiere?: Capacidad;
                                             children: ReactNode }) {
  const { puede } = useSesion()            // capacidades del rol
  if (requiere && !puede(requiere)) {
    return <EmptyState
             title="Esta sección no está disponible para su rol" />
  }
  return <Suspense fallback={<Cargando />}>{children}</Suspense>
}

export function App() {
  const { perfil, cargando, puede } = useSesion()
  if (!perfil) return <Navigate to="/ingresar" replace />
  return (
    <Routes>
      <Route element={<AppShell />}>   {/* menú y cabecera */}
        <Route path="panel" element={
          <Protegida requiere="ver_panel"><Panel /></Protegida>} />
        <Route path="estudiantes/:token" element={
          <Protegida requiere="ver_ficha"><Ficha /></Protegida>} />
        <Route path="consulta" element={
          <Protegida requiere="consultar"><Consulta /></Protegida>} />
        <Route path="modelo" element={
          <Protegida requiere="ver_modelo">
            <CalidadModelo /></Protegida>} />
        …
      </Route>
    </Routes>)
}
'''),
    'tf_codigo_cliente': ('frontend/src/lib/api.ts y lib/consultas.ts · cliente de la API', TypeScriptLexer, '''\
function cabeceras(extra?: HeadersInit): Headers {
  const h = new Headers(extra)
  const token = tokenEnMemoria
  if (token) h.set('Authorization', `Bearer ${token}`)
  if (institucionEnMemoria)
    h.set('X-Institucion', institucionEnMemoria)
  return h
}

async function pedir(ruta: string, opciones: RequestInit = {}) {
  const respuesta = await fetch(`/api${ruta}`, {
    ...opciones, headers: cabeceras(opciones.headers) })
  if (respuesta.status === 401 && tokenEnMemoria) {
    sesionGuardada.guardarToken(null)    // cierra todas las vistas
    window.dispatchEvent(new CustomEvent('vicmar:sesion-vencida'))
  }
  if (!respuesta.ok) {
    const cuerpo = await respuesta.json().catch(() => null)
    throw new ErrorApi(respuesta.status,
                       mensajeDe(cuerpo, respuesta.status))
  }
  return respuesta
}

// Hook de lectura: la clave de caché incluye la institución activa,
// así los datos de una institución nunca aparecen en otra.
export function useDatos<T>(ruta: string | null) {
  const { institucion } = useSesion()
  return useQuery<T>({
    queryKey: [institucion?.codigo ?? '-', ruta],
    queryFn: () => obtener<T>(ruta as string),
    enabled: !!ruta && !!institucion,
  })
}
'''),
    'tf_codigo_pagina': ('frontend/src/paginas/CalidadModelo.tsx · validación por periodo', TsxLexer, '''\
function PorPeriodo({ d }: { d: Calidad }) {
  const om = d.origen_movil              // backtesting por periodo
  const r = om?.resumen
  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi etiqueta="ROC-AUC medio por periodo"
             valor={decimal(r.roc_auc_media, 3)} tono="accent" />
        <Kpi etiqueta="Peor periodo" valor={decimal(r.roc_auc_min, 3)}
             tono="warning" />
        <Kpi etiqueta="Recall medio por periodo"
             valor={proporcion(r.recall_medio_media, 0)}
             tono="success" />
      </section>
      <Card>
        <CardHeader title="Validación con origen móvil" />
        <TablaGrupos filas={om.periodos}
                     etiqueta="Periodo evaluado" />
      </Card>
      <Card>
        <CardHeader title="Prueba temporal por carrera" />
        <TablaGrupos filas={d.por_carrera} etiqueta="Carrera" />
      </Card>
    </div>)
}
'''),
    'tf_codigo_main': ('backend/main.py · aplicación FastAPI', PythonLexer, '''\
app = FastAPI(title='VicMar · API de alerta temprana de abandono',
              version=VERSION, docs_url='/docs')
app.add_middleware(CORSMiddleware,
                   allow_origins=list(CONFIG.origenes_permitidos),
                   allow_headers=['Authorization', 'Content-Type',
                                  'X-Institucion'])


@app.middleware('http')
async def cabeceras_y_registro(request: Request, call_next):
    respuesta = await call_next(request)
    respuesta.headers['X-Content-Type-Options'] = 'nosniff'
    respuesta.headers['X-Frame-Options'] = 'DENY'
    respuesta.headers['Cache-Control'] = 'no-store'
    return respuesta


for modulo in (sesion, panel, estudiantes, carreras, referentes,
               modelo, seguimiento, consulta, reportes, admin):
    app.include_router(modulo.router, prefix='/api')  # 27 operaciones
'''),
    'tf_codigo_seguridad': ('backend/core/seguridad.py y core/db.py · permisos y aislamiento', PythonLexer, '''\
def requiere(capacidad: str, con_institucion: bool = True):
    \"\"\"Dependencia que exige una capacidad del rol.\"\"\"
    def _dependencia(sesion: Sesion = Depends(sesion_actual)):
        if not sesion.puede(capacidad):
            raise HTTPException(403, 'Su rol no permite esta acción.')
        if con_institucion and not sesion.institucion:
            raise HTTPException(400, 'Seleccione una institución.')
        return sesion
    return _dependencia


@contextmanager
def _conexion_con_contexto(usuario, clave, institucion):
    \"\"\"Conexión de solo lectura con la institución fijada.\"\"\"
    institucion = validar_institucion(institucion)
    conn = pyodbc.connect(_cadena(usuario, clave, CONFIG.almacen))
    cur = conn.cursor()
    # @read_only = 1: nadie cambia la institución en esta conexión
    cur.execute("EXEC sp_set_session_context "
                "@key = N'institucion_activa', @value = ?, "
                "@read_only = 1", institucion)
    yield cur
'''),
    'tf_codigo_origen_movil': ('backend/ml/evaluacion_grupos.py · validacion_origen_movil()', PythonLexer, '''\
for codigo in candidatos:                  # periodos más recientes
    inicio = periodos[codigo]
    pasado = etiquetado[etiquetado['fecha_inicio'] < inicio] \\
        .reset_index(drop=True)
    actual = etiquetado[etiquetado['periodo_codigo'] == codigo] \\
        .reset_index(drop=True)
    X_tr, y_tr, g_tr = (matriz(pasado, columnas),
                        pasado['y'].astype(int), pasado['alumno_id'])
    oof = np.zeros(len(y_tr))        # predicciones fuera de pliegue
    cv = StratifiedGroupKFold(n_splits=3, shuffle=True,
                              random_state=semilla)
    for tr, te in cv.split(X_tr, y_tr, g_tr):
        oof[te] = clone(modelo).fit(X_tr.iloc[tr], y_tr.iloc[tr]) \\
                               .predict_proba(X_tr.iloc[te])[:, 1]
    calibrador = CalibradorPlatt().fit(oof, y_tr)   # solo el pasado
    oof_cal = calibrador.predict(oof)
    u_medio = _umbral_para_recall(y_tr, oof_cal, recall_medio)
    u_alto = max(_umbral_para_recall(y_tr, oof_cal, recall_alto),
                 u_medio)
    ajustado = clone(modelo).fit(X_tr, y_tr)
    p = calibrador.predict(
        ajustado.predict_proba(matriz(actual, columnas))[:, 1])
    fila = {'periodo': codigo, **_metricas(actual['y'].to_numpy(), p,
                                           u_medio, u_alto)}
'''),
    'tf_codigo_calidad': ('backend/mlops/calidad_datos.py · _evaluar_gx()', PythonLexer, '''\
contexto = gx.get_context(mode='ephemeral')
origen = contexto.data_sources.add_pandas('almacen_academico')
lote = (origen.add_dataframe_asset('trayectoria')
        .add_batch_definition_whole_dataframe('completa')
        .get_batch(batch_parameters={'dataframe': df}))
suite = gx.ExpectationSuite(name='trayectoria_academica')
for i, regla in enumerate(lista):        # 23 expectativas declaradas
    clase = getattr(gx.expectations, ''.join(
        p.capitalize() for p in regla.tipo.split('_')))
    kwargs = dict(regla.args, meta={'regla': i})
    if regla.columna:
        kwargs['column'] = regla.columna
    suite.add_expectation(clase(**kwargs))
# p. ej. ExpectColumnValuesToBeBetween(column='promedio',
#                                      min_value=0, max_value=10)
resultado = lote.validate(suite, result_format='SUMMARY')
# GX no garantiza el orden: cada resultado se empareja por su índice
por_regla = {int(res.expectation_config.meta['regla']): res
             for res in resultado.results}
'''),
}

PLANTILLA = '''<!doctype html><html lang="es"><head><meta charset="utf-8">
<style>
@page {{ size: 16cm auto; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ width: 16cm; background: #fff; padding: 2px; font-family: Arial, Helvetica, sans-serif; }}
.marco {{ border: 1.2px solid #94a8ba; border-radius: 6px; overflow: hidden; }}
.ruta {{ background: #002e45; color: #fff; font-size: 10pt; padding: 4px 8px; }}
.ruta b {{ color: #ffd2b0; font-weight: 700; }}
pre {{ font-family: 'DejaVu Sans Mono', Consolas, monospace; font-size: 10pt; line-height: 1.32;
       padding: 6px 8px; background: #f8fafc; white-space: pre-wrap; word-break: break-word; color: #0f172a; }}
{estilos}
</style></head><body><div class="marco"><div class="ruta"><b>Archivo:</b> {ruta}</div>{codigo}</div></body></html>'''


def main() -> int:
    import subprocess
    import sys
    SALIDA_HTML.mkdir(parents=True, exist_ok=True)
    formato = HtmlFormatter(style='friendly', nowrap=False, cssclass='codigo')
    estilos = formato.get_style_defs('.codigo').replace('background: #f0f0f0;', '') + ' .codigo .err { border: none; }'
    archivos = []
    for nombre, (ruta, lexer, texto) in EXTRACTOS.items():
        codigo = highlight(texto, lexer(), formato)
        destino = SALIDA_HTML / f'{nombre}.html'
        destino.write_text(PLANTILLA.format(estilos=estilos, ruta=html.escape(ruta), codigo=codigo), encoding='utf-8')
        archivos.append(str(destino))
    renderizador = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if renderizador:
        subprocess.run([sys.executable, str(renderizador), str(SALIDA_PNG), *archivos], check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
'''<!doctype html><html lang="es"><head><meta charset="utf-8">
<style>
@page {{ size: 16cm auto; }}
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ width: 16cm; background: #fff; padding: 2px; font-family: Arial, Helvetica, sans-serif; }}
.marco {{ border: 1.2px solid #94a8ba; border-radius: 6px; overflow: hidden; }}
.ruta {{ background: #002e45; color: #fff; font-size: 10pt; padding: 4px 8px; }}
.ruta b {{ color: #ffd2b0; font-weight: 700; }}
pre {{ font-family: 'DejaVu Sans Mono', Consolas, monospace; font-size: 10pt; line-height: 1.32;
       padding: 6px 8px; background: #f8fafc; white-space: pre-wrap; word-break: break-word; color: #0f172a; }}
{estilos}
</style></head><body><div class="marco"><div class="ruta"><b>Archivo:</b> {ruta}</div>{codigo}</div></body></html>'''


def main() -> int:
    import subprocess
    import sys
    SALIDA_HTML.mkdir(parents=True, exist_ok=True)
    formato = HtmlFormatter(style='friendly', nowrap=False, cssclass='codigo')
    estilos = formato.get_style_defs('.codigo').replace('background: #f0f0f0;', '') + ' .codigo .err { border: none; }'
    archivos = []
    for nombre, (ruta, lexer, texto) in EXTRACTOS.items():
        codigo = highlight(texto, lexer(), formato)
        destino = SALIDA_HTML / f'{nombre}.html'
        destino.write_text(PLANTILLA.format(estilos=estilos, ruta=html.escape(ruta), codigo=codigo), encoding='utf-8')
        archivos.append(str(destino))
    renderizador = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    if renderizador:
        subprocess.run([sys.executable, str(renderizador), str(SALIDA_PNG), *archivos], check=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

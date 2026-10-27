/**
 * src/paginas/CalidadModelo.tsx — calidad y transparencia del modelo (RF-13, RNF de calidad).
 *
 * Lo que una autoridad y un tribunal necesitan para decidir cuánto confiar en las
 * alertas: validación cruzada agrupada, prueba temporal, prueba prospectiva,
 * calibración, matrices de confusión, importancia de variables, equidad por grupos,
 * deriva de los datos, exactitud de la consulta conversacional y la ficha del modelo.
 *
 * Ruta: /modelo · Rol: Autoridad académica y Administración de TI (capacidad `ver_modelo`).
 * API: GET /modelo/calidad.
 * Requisitos: RF-03, RF-04, RF-13, RF-17.
 */
import { lazy, Suspense, useState, type ReactNode } from 'react'
import { IconoModelo } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { Badge } from '../componentes/ui/Badge'
import { Card, CardBody, CardHeader } from '../componentes/ui/Card'
import { Aviso, EmptyState, EstadoError } from '../componentes/ui/Estados'
import { Kpi } from '../componentes/ui/Kpi'
import { Segmentado } from '../componentes/ui/Segmentado'
import { Skeleton } from '../componentes/ui/Skeleton'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../componentes/ui/Table'
import { cn } from '../lib/cn'
import { useDatos } from '../lib/consultas'
import { capital, decimal, entero, fechaHora, proporcion } from '../lib/formato'
import { useSesion } from '../lib/sesion'
import type { CalidadModelo as Calidad, EvaluacionUmbral, MetricaGrupo } from '../lib/tipos'
import { NOMBRE_MODELO } from '../lib/modelos'

const G = {
  Comparacion: lazy(() => import('./calidad/Graficos').then((m) => ({ default: m.ComparacionModelos }))),
  Curva: lazy(() => import('./calidad/Graficos').then((m) => ({ default: m.Curva }))),
  Calibracion: lazy(() => import('./calidad/Graficos').then((m) => ({ default: m.Calibracion }))),
  Importancia: lazy(() => import('./calidad/Graficos').then((m) => ({ default: m.Importancia }))),
}

type Pestana = 'resumen' | 'validacion' | 'periodos' | 'operacion' | 'explicacion' | 'consulta' | 'ficha'
const NOMBRE_GRUPO: Record<string, string> = { financieras: 'Financieras', matricula: 'Matrícula', aula_virtual: 'Aula virtual', evaluaciones: 'Evaluaciones' }
const NOMBRE_VARIABLE_EQUIDAD: Record<string, string> = {
  genero: 'Género',
  modalidad: 'Modalidad',
  modalidad_codigo: 'Modalidad',
  sede: 'Sede',
  sede_codigo: 'Sede',
}

function Diferido({ children, alto = 240 }: { children: ReactNode; alto?: number }) {
  return <Suspense fallback={<Skeleton className="w-full" />}>{<div style={{ minHeight: alto }}>{children}</div>}</Suspense>
}

function Matriz({ titulo, m }: { titulo: string; m: EvaluacionUmbral }) {
  const [[vn, fp], [fn, vp]] = m.matriz_confusion
  const celda = (valor: number, texto: string, tono: string) => (
    <div className={cn('rounded-xl p-3 text-center', tono)}>
      <p className="tabular text-lg font-semibold">{entero(valor)}</p>
      <p className="text-2xs">{texto}</p>
    </div>
  )
  return (
    <div>
      <div className="mb-3 flex items-baseline justify-between gap-2">
        <p className="text-sm font-semibold text-foreground">{titulo}</p>
        <p className="tabular text-xs text-muted-foreground">umbral {proporcion(m.umbral)}</p>
      </div>
      <div className="grid grid-cols-2 gap-2">
        {celda(vp, 'abandonaron y tenían alerta', 'bg-success-soft text-success')}
        {celda(fn, 'abandonaron sin alerta', 'bg-danger-soft text-danger')}
        {celda(fp, 'con alerta que siguieron', 'bg-warning-soft text-warning')}
        {celda(vn, 'sin alerta que siguieron', 'bg-surface-hover text-muted-foreground')}
      </div>
      <dl className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        <div>
          <dt className="text-muted-foreground">Recall</dt>
          <dd className="tabular font-semibold text-foreground">{proporcion(m.recall)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Precisión</dt>
          <dd className="tabular font-semibold text-foreground">{proporcion(m.precision)}</dd>
        </div>
        <div>
          <dt className="text-muted-foreground">Alertados</dt>
          <dd className="tabular font-semibold text-foreground">{proporcion(m.tasa_alerta)}</dd>
        </div>
      </dl>
    </div>
  )
}

function Resumen({ d }: { d: Calidad }) {
  const t = d.temporal!
  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi etiqueta="Capacidad de distinguir (ROC-AUC)" valor={decimal(t.roc_auc, 3)} tono="accent" icono={IconoModelo} contexto="0,5 = azar · 1 = perfecto" />
        <Kpi etiqueta="Abandonos anticipados" valor={proporcion(t.umbral_medio.recall, 0)} tono="success" contexto="con alerta media o alta" />
        <Kpi etiqueta="Alertas acertadas" valor={proporcion(t.umbral_medio.precision, 0)} tono="warning" contexto={`prevalencia real ${proporcion(t.prevalencia)}`} />
        <Kpi etiqueta="Abandonos en el 10 % de mayor riesgo" valor={proporcion(t.captura_top_10, 0)} contexto={`20 %: ${proporcion(t.captura_top_20, 0)}`} />
      </section>
      <div className="grid gap-6 xl:grid-cols-2">
        <Card>
          <CardHeader title="Cómo leer estas cifras" />
          <CardBody className="space-y-3 pt-4 text-sm leading-relaxed text-muted-foreground">
            <p>
              El modelo se probó con los periodos <span className="font-medium text-foreground">{t.periodos.join(', ')}</span>, que no vio durante el entrenamiento: es la forma de
              medir cómo se comportará con estudiantes futuros.
            </p>
            <p>
              Con el umbral medio, el sistema alerta a {proporcion(t.umbral_medio.tasa_alerta, 0)} de los estudiantes y en ese grupo están{' '}
              {proporcion(t.umbral_medio.recall, 0)} de quienes abandonaron. Una alerta no es una sentencia: indica a quién conviene contactar primero.
            </p>
            <p>
              Las probabilidades están calibradas ({d.calibracion?.metodo?.split('(')[0].trim() ?? 'Platt'}): el error cuadrático (Brier) bajó de {decimal(t.brier_sin_calibrar, 4)} a{' '}
              {decimal(t.brier_calibrado, 4)}.
            </p>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Matrices de confusión" description={`Prueba temporal: ${entero(t.n)} casos, ${entero(t.positivos)} abandonos.`} />
          <CardBody className="grid gap-6 pt-4 sm:grid-cols-2">
            <Matriz titulo="Umbral medio" m={t.umbral_medio} />
            <Matriz titulo="Umbral alto" m={t.umbral_alto} />
          </CardBody>
        </Card>
      </div>
      {d.prospectiva && (
        <Card>
          <CardHeader
            title="Prueba prospectiva"
            description={`Presentación ${d.prospectiva.presentacion} calificada «en curso» y comparada después con lo que realmente ocurrió (${entero(d.prospectiva.calificados)} estudiantes).`}
          />
          <CardBody className="grid gap-4 pt-4 sm:grid-cols-2">
            {(['y_siguiente', 'y_resto'] as const).map((k) => {
              const e = d.prospectiva![k]
              return (
                <div key={k} className="rounded-xl border border-border p-4">
                  <p className="text-sm font-semibold text-foreground">{k === 'y_siguiente' ? 'Abandono en el corte siguiente' : 'Abandono en el resto de la presentación'}</p>
                  <dl className="mt-3 grid grid-cols-4 gap-2 text-center text-xs">
                    {[
                      ['ROC-AUC', decimal(e.roc_auc, 3)],
                      ['PR-AUC', decimal(e.pr_auc, 3)],
                      ['Recall', proporcion(e.recall, 0)],
                      ['Precisión', proporcion(e.precision, 0)],
                    ].map(([a, b]) => (
                      <div key={a}>
                        <dt className="text-muted-foreground">{a}</dt>
                        <dd className="tabular mt-0.5 font-semibold text-foreground">{b}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )
            })}
          </CardBody>
        </Card>
      )}
    </div>
  )
}

function Validacion({ d }: { d: Calidad }) {
  const t = d.temporal!
  return (
    <div className="space-y-6">
      {d.comparacion_cv && (
        <Card>
          <CardHeader title="Modelos comparados" description="Validación cruzada agrupada por estudiante: nunca aparece el mismo estudiante en entrenamiento y prueba." />
          <CardBody>
            <Diferido alto={300}>
              <G.Comparacion cv={d.comparacion_cv} final={d.modelo_final} />
            </Diferido>
          </CardBody>
          <Table>
            <TableHead>
              <tr>
                <Th>Modelo</Th>
                <Th numero>ROC-AUC</Th>
                <Th numero>PR-AUC</Th>
                <Th numero>Pliegues (ROC-AUC)</Th>
              </tr>
            </TableHead>
            <TableBody>
              {Object.entries(d.comparacion_cv).map(([k, v]) => (
                <TableRow key={k}>
                  <Td>
                    {NOMBRE_MODELO[k] ?? k} {k === d.modelo_final && <Badge variant="accent">Elegido</Badge>}
                  </Td>
                  <Td numero>
                    {decimal(v.roc_auc.media, 4)} ± {decimal(v.roc_auc.desviacion, 4)}
                  </Td>
                  <Td numero>
                    {decimal(v.pr_auc.media, 4)} ± {decimal(v.pr_auc.desviacion, 4)}
                  </Td>
                  <Td numero className="text-xs text-muted-foreground">
                    {v.roc_auc.pliegues.map((p) => decimal(p, 3)).join(' · ')}
                  </Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
      <div className="grid gap-6 xl:grid-cols-3">
        <Card>
          <CardHeader title="Curva ROC" description={`Prueba temporal · ROC-AUC ${decimal(t.roc_auc, 3)}`} />
          <CardBody>
            <Diferido>
              <G.Curva puntos={t.curva_roc} tipo="roc" />
            </Diferido>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Precisión y exhaustividad" description={`PR-AUC ${decimal(t.pr_auc, 3)} · la línea punteada es el azar`} />
          <CardBody>
            <Diferido>
              <G.Curva puntos={t.curva_pr} tipo="pr" prevalencia={t.prevalencia} />
            </Diferido>
          </CardBody>
        </Card>
        <Card>
          <CardHeader title="Calibración" description="Cerca de la diagonal = la probabilidad dice la verdad." />
          <CardBody>
            <Diferido>
              <G.Calibracion puntos={t.curva_calibracion} />
            </Diferido>
          </CardBody>
        </Card>
      </div>
      {d.monitoreo && (
        <Card className="overflow-hidden">
          <CardHeader
            title="Deriva de los datos (PSI)"
            description="Compara los estudiantes calificados hoy con los del entrenamiento. Por encima de 0,25 conviene reentrenar."
            className="pb-4"
          />
          <Table>
            <TableHead>
              <tr>
                <Th>Variable</Th>
                <Th numero>PSI</Th>
                <Th>Estado</Th>
              </tr>
            </TableHead>
            <TableBody>
              {d.monitoreo.psi.map((p) => (
                <TableRow key={p.variable}>
                  <Td className="font-mono text-sm">{p.variable}</Td>
                  <Td numero>{decimal(p.psi, 4)}</Td>
                  <Td>
                    <Badge variant={p.estado === 'ESTABLE' ? 'success' : p.estado === 'MODERADO' ? 'warning' : 'danger'}>
                      {p.estado.charAt(0) + p.estado.slice(1).toLowerCase()}
                    </Badge>
                  </Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

function TablaGrupos({ filas, etiqueta, nota }: { filas: (MetricaGrupo & { grupo?: string; periodo?: string })[]; etiqueta: string; nota?: string }) {
  return (
    <Table>
      <TableHead>
        <tr>
          <Th>{etiqueta}</Th>
          <Th numero>Casos</Th>
          <Th numero>Abandonos</Th>
          <Th numero>ROC-AUC</Th>
          <Th numero>PR-AUC</Th>
          <Th numero>Recall medio</Th>
          <Th numero>Recall alto</Th>
          <Th numero>Precisión alta</Th>
        </tr>
      </TableHead>
      <TableBody>
        {filas.map((f) => (
          <TableRow key={f.periodo ?? f.grupo}>
            <Td className="font-medium text-foreground">{f.periodo ?? f.grupo}</Td>
            <Td numero>{entero(f.n)}</Td>
            <Td numero>
              {entero(f.positivos)} <span className="text-xs text-muted-foreground">({proporcion(f.prevalencia)})</span>
            </Td>
            <Td numero>{f.roc_auc != null ? decimal(f.roc_auc, 3) : <span className="text-xs text-muted-foreground">pocos casos</span>}</Td>
            <Td numero>{f.pr_auc != null ? decimal(f.pr_auc, 3) : '—'}</Td>
            <Td numero>{f.recall_medio != null ? proporcion(f.recall_medio, 0) : '—'}</Td>
            <Td numero>{f.recall_alto != null ? proporcion(f.recall_alto, 0) : '—'}</Td>
            <Td numero>{proporcion(f.precision_alto, 0)}</Td>
          </TableRow>
        ))}
      </TableBody>
      {nota && (
        <caption className="caption-bottom px-6 py-3 text-left text-xs text-muted-foreground">{nota}</caption>
      )}
    </Table>
  )
}

function PorPeriodo({ d }: { d: Calidad }) {
  const om = d.origen_movil
  const r = om?.resumen
  return (
    <div className="space-y-6">
      {r?.origenes ? (
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Kpi etiqueta="ROC-AUC medio por periodo" valor={decimal(r.roc_auc_media, 3)} tono="accent" icono={IconoModelo} contexto={`${r.origenes} periodos evaluados con origen móvil`} />
          <Kpi etiqueta="Peor periodo" valor={decimal(r.roc_auc_min, 3)} tono="warning" contexto={`mejor: ${decimal(r.roc_auc_max, 3)}`} />
          <Kpi etiqueta="Recall medio por periodo" valor={proporcion(r.recall_medio_media, 0)} tono="success" contexto="abandonos con alerta media o alta" />
          <Kpi etiqueta="Prueba temporal global" valor={decimal(d.temporal?.roc_auc, 3)} contexto={`periodos ${d.temporal?.periodos.join(', ')}`} />
        </section>
      ) : null}
      {om && om.periodos.length > 0 && (
        <Card className="overflow-hidden">
          <CardHeader
            title="Validación con origen móvil"
            description="Cada periodo se predice entrenando solo con los periodos anteriores, como si el sistema se hubiera puesto en marcha en esa fecha. Calibración y umbrales se ajustan solo con el pasado."
            className="pb-4"
          />
          <TablaGrupos filas={om.periodos} etiqueta="Periodo evaluado" />
        </Card>
      )}
      {d.por_periodo && d.por_periodo.length > 0 && (
        <Card className="overflow-hidden">
          <CardHeader title="Prueba temporal por periodo" description="Las cifras globales de la prueba temporal, separadas por periodo académico." className="pb-4" />
          <TablaGrupos filas={d.por_periodo} etiqueta="Periodo" />
        </Card>
      )}
      {d.por_carrera && d.por_carrera.length > 0 && (
        <Card className="overflow-hidden">
          <CardHeader title="Prueba temporal por carrera" description="El modelo debe servir en cada carrera, no solo en promedio." className="pb-4" />
          <TablaGrupos filas={d.por_carrera} etiqueta="Carrera" nota="Sin ROC-AUC cuando la carrera tiene menos de 100 casos o 10 abandonos en la prueba: la cifra no sería estable." />
        </Card>
      )}
    </div>
  )
}

function Operacion({ d }: { d: Calidad }) {
  const c = d.calidad_datos
  const v = d.deriva
  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi etiqueta="Expectativas de calidad cumplidas" valor={c ? `${c.cumplidas}/${c.evaluadas}` : '—'} tono={c?.apto_para_entrenar ? 'success' : 'warning'} contexto={c ? (c.apto_para_entrenar ? 'datos aptos para entrenar' : 'revisar antes de entrenar') : 'sin evaluar'} />
        <Kpi etiqueta="Variables con deriva" valor={v ? `${v.variables_con_deriva}/${v.variables.length}` : '—'} tono={v?.conjunto_con_deriva ? 'warning' : 'accent'} contexto={v ? (v.conjunto_con_deriva ? 'conviene reentrenar' : 'conjunto estable') : 'sin evaluar'} />
        <Kpi etiqueta="Importantes con deriva" valor={v ? entero(v.importantes_con_deriva.length) : '—'} contexto="de las 10 variables que más pesan" />
        <Kpi etiqueta="Experimento registrado" valor={d.mlflow ? d.mlflow.run_id.slice(0, 8) : '—'} contexto={d.mlflow ? `MLflow · ${d.mlflow.experimento}` : 'MLflow no disponible'} />
      </section>
      {c && (
        <Card className="overflow-hidden">
          <CardHeader title="Calidad de los datos" description={`${c.motor} · ${entero(c.filas)} filas de trayectoria · ${fechaHora(c.fecha)}`} className="pb-4" />
          <Table>
            <TableHead>
              <tr>
                <Th>Expectativa</Th>
                <Th>Columna</Th>
                <Th numero>No cumplen</Th>
                <Th>Resultado</Th>
              </tr>
            </TableHead>
            <TableBody>
              {c.expectativas.map((e, i) => (
                <TableRow key={i}>
                  <Td className="text-sm">
                    {e.descripcion} {e.critica && <span className="text-2xs text-muted-foreground">(crítica)</span>}
                  </Td>
                  <Td className="font-mono text-xs text-muted-foreground">{e.columna ?? 'tabla'}</Td>
                  <Td numero>{e.porcentaje_no_cumple != null ? `${decimal(e.porcentaje_no_cumple, 2)} %` : e.observado != null ? `obs. ${entero(e.observado)}` : '—'}</Td>
                  <Td>{e.cumple ? <Badge variant="success">Cumple</Badge> : <Badge variant={e.critica ? 'danger' : 'warning'}>No cumple</Badge>}</Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
      {v && (
        <Card className="overflow-hidden">
          <CardHeader
            title="Deriva de las variables de entrada"
            description={`${v.motor}: ${entero(v.filas_referencia)} filas de referencia frente a ${entero(v.filas_actuales)} estudiantes calificados. ${v.lectura}`}
            className="pb-4"
          />
          <Table>
            <TableHead>
              <tr>
                <Th>Variable</Th>
                <Th>Prueba</Th>
                <Th numero>Valor</Th>
                <Th numero>PSI</Th>
                <Th>Estado</Th>
              </tr>
            </TableHead>
            <TableBody>
              {v.variables.slice(0, 15).map((x) => (
                <TableRow key={x.variable}>
                  <Td className="font-mono text-sm">{x.variable}</Td>
                  <Td className="text-xs text-muted-foreground">{x.metodo}</Td>
                  <Td numero>{decimal(x.valor, 3)}</Td>
                  <Td numero>{x.psi != null ? decimal(x.psi, 3) : '—'}</Td>
                  <Td>{x.deriva ? <Badge variant="warning">Deriva</Badge> : <Badge variant="success">Estable</Badge>}</Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

function Explicacion({ d }: { d: Calidad }) {
  return (
    <div className="space-y-6">
      {d.importancia && (
        <Card>
          <CardHeader
            title="Variables que más pesan"
            description="Cuánto empeora el ROC-AUC al desordenar cada variable en la prueba temporal (importancia por permutación)."
          />
          <CardBody>
            <Diferido alto={420}>
              <G.Importancia items={d.importancia} />
            </Diferido>
          </CardBody>
        </Card>
      )}
      {d.equidad && (
        <Card className="overflow-hidden">
          <CardHeader
            title="Equidad entre grupos"
            description="El modelo debe acertar de forma parecida en cada grupo. Diferencias grandes de recall indicarían que unos grupos reciben menos alertas oportunas."
            className="pb-4"
          />
          <Table>
            <TableHead>
              <tr>
                <Th>Grupo</Th>
                <Th numero>Casos</Th>
                <Th numero>Prevalencia</Th>
                <Th numero>ROC-AUC</Th>
                <Th numero>Recall</Th>
                <Th numero>Precisión</Th>
                <Th numero>Alertados</Th>
              </tr>
            </TableHead>
            <TableBody>
              {d.equidad.map((e) => (
                <TableRow key={`${e.variable}-${e.grupo}`}>
                  <Td>
                    <span className="text-muted-foreground">{NOMBRE_VARIABLE_EQUIDAD[e.variable] ?? e.variable}:</span> {e.variable === 'genero' ? (e.grupo === 'F' ? 'Femenino' : e.grupo === 'M' ? 'Masculino' : e.grupo) : capital(e.grupo.toLowerCase())}
                  </Td>
                  <Td numero>{entero(e.n)}</Td>
                  <Td numero>{proporcion(e.prevalencia)}</Td>
                  <Td numero>{decimal(e.roc_auc, 3)}</Td>
                  <Td numero>{proporcion(e.recall)}</Td>
                  <Td numero>{proporcion(e.precision)}</Td>
                  <Td numero>{proporcion(e.tasa_alerta)}</Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  )
}

function ConsultaEval({ d }: { d: Calidad }) {
  const c = d.consulta
  if (!c) {
    return (
      <Card>
        <EmptyState
          title="La consulta conversacional aún no se ha evaluado en esta institución"
          description="El área de TI la evalúa con el conjunto dorado de preguntas (python -m scripts.pipeline --solo consulta)."
        />
      </Card>
    )
  }
  const r = c.resumen
  return (
    <div className="space-y-6">
      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <Kpi etiqueta="Exactitud de ejecución" valor={proporcion(r.exactitud_relajada_base, 1)} tono="accent" contexto={`${entero(r.preguntas_base)} preguntas del conjunto dorado`} />
        <Kpi etiqueta="Con preguntas reformuladas" valor={proporcion(r.exactitud_relajada_robustez, 1)} contexto={`${entero(r.preguntas_robustez)} variantes`} />
        <Kpi etiqueta="Ataques contenidos" valor={r.adversariales_contenidas} tono="success" contexto={`${entero(r.violaciones_aislamiento)} filtraciones entre instituciones`} />
        <Kpi etiqueta="Tiempo de respuesta (mediana)" valor={r.latencia_mediana_ms != null ? `${decimal(r.latencia_mediana_ms / 1000, 1)} s` : '—'} contexto={r.latencia_p95_ms != null ? `p95: ${decimal(r.latencia_p95_ms / 1000, 1)} s` : undefined} />
      </section>
      {r.base_sin_cambios && <Aviso tono="success">La base de datos quedó idéntica antes y después de la evaluación: ninguna pregunta logró modificarla.</Aviso>}
      <div className="grid gap-6 xl:grid-cols-2">
        <Card className="overflow-hidden">
          <CardHeader title="Exactitud por tema" description={`Evaluación del ${fechaHora(c.fecha)}`} className="pb-4" />
          <Table>
            <TableHead>
              <tr>
                <Th>Tema</Th>
                <Th numero>Preguntas</Th>
                <Th numero>Correctas</Th>
                <Th numero>Exactitud</Th>
              </tr>
            </TableHead>
            <TableBody>
              {Object.entries(c.por_categoria).map(([k, v]) => (
                <TableRow key={k}>
                  <Td>{k.charAt(0).toUpperCase() + k.slice(1).replace(/_/g, ' ')}</Td>
                  <Td numero>{entero(v.preguntas)}</Td>
                  <Td numero>{entero(v.correctas)}</Td>
                  <Td numero>{proporcion(v.exactitud)}</Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
        <Card className="overflow-hidden">
          <CardHeader title="Pruebas de ataque" description="Intentos de escribir, inyectar código o leer otra institución." className="pb-4" />
          <Table>
            <TableHead>
              <tr>
                <Th>Tipo</Th>
                <Th>Pregunta</Th>
                <Th>Resultado</Th>
              </tr>
            </TableHead>
            <TableBody>
              {c.adversariales.map((a) => (
                <TableRow key={a.id}>
                  <Td className="whitespace-nowrap text-sm">{a.tipo.replace(/_/g, ' ').toLowerCase()}</Td>
                  <Td className="max-w-[280px] text-sm text-muted-foreground">
                    <p className="line-clamp-2">{a.pregunta}</p>
                  </Td>
                  <Td>{a.contenida ? <Badge variant="success">Contenido</Badge> : <Badge variant="danger">Revisar</Badge>}</Td>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </Card>
      </div>
    </div>
  )
}

function Ficha({ d }: { d: Calidad }) {
  const f = d.ficha ?? {}
  const filas: [string, ReactNode][] = [
    ['Modelo', `${NOMBRE_MODELO[d.modelo_final ?? ''] ?? d.modelo_final} · versión ${d.version}`],
    ['Entrenado', fechaHora(d.fecha)],
    ['Qué predice', d.horizonte],
    ['Propósito', f.proposito],
    ['Usos no previstos', f.usos_no_previstos],
    ['Datos', f.datos],
    ['Grupos de variables', (d.grupos_de_variables ?? []).map((g) => NOMBRE_GRUPO[g] ?? g).join(', ') || 'Solo académicas'],
    ['Panel de entrenamiento', d.panel ? `${entero(d.panel.filas)} filas, ${entero(d.panel.estudiantes)} estudiantes, ${proporcion(d.panel.prevalencia)} de abandono` : '—'],
    ['Umbrales', d.umbrales ? `medio ${proporcion(d.umbrales.medio)} (recall objetivo ${proporcion(d.umbrales.recall_objetivo_medio, 0)}), alto ${proporcion(d.umbrales.alto)} (recall objetivo ${proporcion(d.umbrales.recall_objetivo_alto, 0)})` : '—'],
    ['Limitaciones', f.limitaciones],
    ['Supervisión humana', f.supervision],
  ]
  return (
    <Card>
      <CardHeader title="Ficha del modelo" description="Resumen de transparencia: para qué sirve, para qué no y cómo se controla." />
      <CardBody className="pt-4">
        <dl className="divide-y divide-border">
          {filas.map(([k, v]) => (
            <div key={k} className="grid gap-1 py-3 sm:grid-cols-[220px_1fr] sm:gap-6">
              <dt className="text-sm font-medium text-foreground">{k}</dt>
              <dd className="text-sm text-muted-foreground">{v ?? '—'}</dd>
            </div>
          ))}
        </dl>
      </CardBody>
    </Card>
  )
}

export default function CalidadModelo() {
  const { institucion } = useSesion()
  const [pestana, setPestana] = useState<Pestana>('resumen')
  const { data, error, isLoading, refetch } = useDatos<Calidad>('/modelo/calidad')

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Calidad del modelo"
        descripcion="Cómo se validó el modelo de abandono de la institución activa, con qué precisión acierta y cómo se controla su uso."
        extra={
          data?.disponible && (
            <Segmentado
              etiqueta="Sección"
              valor={pestana}
              onCambio={setPestana}
              className="max-w-full overflow-x-auto"
              opciones={[
                { valor: 'resumen', texto: 'Resumen' },
                { valor: 'validacion', texto: 'Validación' },
                { valor: 'periodos', texto: 'Por periodo y carrera' },
                { valor: 'operacion', texto: 'Datos y deriva' },
                { valor: 'explicacion', texto: 'Variables y equidad' },
                { valor: 'consulta', texto: 'Consulta conversacional' },
                { valor: 'ficha', texto: 'Ficha del modelo' },
              ]}
            />
          )
        }
      />
      {institucion?.tipo_datos === 'SINTETICO' && data?.disponible && (
        <Aviso tono="warning" className="mb-6">
          Institución con datos sintéticos: las métricas prueban que el sistema funciona de punta a punta. La validación con datos reales se hace con OULAD.
        </Aviso>
      )}
      {isLoading ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-32 rounded-2xl" />
            ))}
          </div>
          <Skeleton className="h-[320px] rounded-2xl" />
        </div>
      ) : error ? (
        <Card>
          <EstadoError error={error} onReintentar={() => refetch()} />
        </Card>
      ) : !data?.disponible || !data.temporal ? (
        <Card>
          <EmptyState icon={IconoModelo} title="Esta institución todavía no tiene un modelo entrenado" description="Ejecute el entrenamiento desde los procesos por lotes." />
        </Card>
      ) : pestana === 'resumen' ? (
        <Resumen d={data} />
      ) : pestana === 'validacion' ? (
        <Validacion d={data} />
      ) : pestana === 'periodos' ? (
        <PorPeriodo d={data} />
      ) : pestana === 'operacion' ? (
        <Operacion d={data} />
      ) : pestana === 'explicacion' ? (
        <Explicacion d={data} />
      ) : pestana === 'consulta' ? (
        <ConsultaEval d={data} />
      ) : (
        <Ficha d={data} />
      )}
    </div>
  )
}

/**
 * src/paginas/calidad/Graficos.tsx — gráficos de validación del modelo: comparación de
 * candidatos (validación cruzada), curvas ROC y precisión-exhaustividad, calibración e
 * importancia de variables.
 */
import {
  Bar,
  BarChart,
  CartesianGrid,
  ErrorBar,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from 'recharts'
import { Leyenda, TooltipGrafico } from '../../componentes/graficos/Tooltip'
import { useColores } from '../../componentes/graficos/colores'
import { capital, decimal, entero, proporcion } from '../../lib/formato'
import type { CalidadModelo } from '../../lib/tipos'
import { NOMBRE_MODELO } from '../../lib/modelos'

const eje = (c: ReturnType<typeof useColores>) => ({ tickLine: false, axisLine: false, tick: { fontSize: 12, fill: c['muted-foreground'] } })

export function ComparacionModelos({ cv, final }: { cv: NonNullable<CalidadModelo['comparacion_cv']>; final?: string }) {
  const c = useColores()
  const datos = Object.entries(cv).map(([k, v]) => ({
    modelo: NOMBRE_MODELO[k] ?? k,
    clave: k,
    roc: v.roc_auc.media,
    rocDe: v.roc_auc.desviacion,
    pr: v.pr_auc.media,
    prDe: v.pr_auc.desviacion,
  }))
  const min = Math.max(0, Math.floor((Math.min(...datos.map((d) => d.pr - d.prDe)) - 0.05) * 10) / 10)
  return (
    <div className="space-y-3">
      <Leyenda items={[{ texto: 'ROC-AUC', color: c['chart-1'] }, { texto: 'PR-AUC', color: c['chart-2'] }]} />
      <div className="h-[280px]" role="img" aria-label="ROC-AUC y PR-AUC de cada modelo candidato">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: -8 }} barGap={4}>
            <CartesianGrid vertical={false} stroke={c.border} strokeDasharray="3 3" />
            <XAxis dataKey="modelo" {...eje(c)} interval={0} tickFormatter={(v: string) => (v === NOMBRE_MODELO[final ?? ''] ? `${v} ★` : v)} />
            <YAxis domain={[min, 1]} {...eje(c)} tickFormatter={(v: number) => decimal(v, 1)} />
            <Tooltip cursor={{ fill: c.border, opacity: 0.35 }} content={<TooltipGrafico formato={(v) => decimal(v, 3)} />} />
            <Bar dataKey="roc" name="ROC-AUC" fill={c['chart-1']} radius={[4, 4, 0, 0]} maxBarSize={34}>
              <ErrorBar dataKey="rocDe" width={6} stroke={c.foreground} strokeOpacity={0.5} />
            </Bar>
            <Bar dataKey="pr" name="PR-AUC" fill={c['chart-2']} radius={[4, 4, 0, 0]} maxBarSize={34}>
              <ErrorBar dataKey="prDe" width={6} stroke={c.foreground} strokeOpacity={0.5} />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <p className="text-xs text-muted-foreground">Media de 5 pliegues agrupados por estudiante; la línea vertical es ± una desviación estándar. ★ modelo elegido.</p>
    </div>
  )
}

export function Curva({ puntos, tipo, prevalencia }: { puntos: [number, number][]; tipo: 'roc' | 'pr'; prevalencia?: number }) {
  const c = useColores()
  const datos = puntos.map(([x, y]) => ({ x, y }))
  const ref = tipo === 'roc' ? [{ x: 0, y: 0 }, { x: 1, y: 1 }] : null
  return (
    <div className="h-[240px]" role="img" aria-label={tipo === 'roc' ? 'Curva ROC en la prueba temporal' : 'Curva de precisión y exhaustividad en la prueba temporal'}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={datos} margin={{ top: 8, right: 12, bottom: 16, left: -8 }}>
          <CartesianGrid stroke={c.border} strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="x"
            domain={[0, 1]}
            {...eje(c)}
            tickFormatter={(v: number) => decimal(v, 1)}
            label={{ value: tipo === 'roc' ? 'Falsos positivos' : 'Exhaustividad (recall)', position: 'insideBottom', offset: -8, fontSize: 12, fill: c['muted-foreground'] }}
          />
          <YAxis type="number" domain={[0, 1]} {...eje(c)} tickFormatter={(v: number) => decimal(v, 1)} />
          {ref && <Line data={ref} dataKey="y" stroke={c['subtle-foreground']} strokeDasharray="4 4" dot={false} isAnimationActive={false} />}
          {tipo === 'pr' && prevalencia != null && <ReferenceLine y={prevalencia} stroke={c['subtle-foreground']} strokeDasharray="4 4" />}
          <Tooltip
            content={<TooltipGrafico titulo={(l) => `${tipo === 'roc' ? 'Falsos positivos' : 'Recall'}: ${decimal(Number(l), 2)}`} formato={(v) => decimal(v, 3)} />}
          />
          <Line dataKey="y" name={tipo === 'roc' ? 'Verdaderos positivos' : 'Precisión'} stroke={c['chart-1']} strokeWidth={2.2} dot={false} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}

export function Calibracion({ puntos }: { puntos: NonNullable<CalidadModelo['temporal']>['curva_calibracion'] }) {
  const c = useColores()
  const max = Math.max(0.1, ...puntos.map((p) => Math.max(p.predicha, p.observada)))
  const tope = Math.min(1, Math.ceil(max * 10) / 10)
  return (
    <div className="h-[240px]" role="img" aria-label="Calibración: probabilidad estimada frente a la frecuencia observada de abandono">
      <ResponsiveContainer width="100%" height="100%">
        <ScatterChart margin={{ top: 8, right: 12, bottom: 16, left: -8 }}>
          <CartesianGrid stroke={c.border} strokeDasharray="3 3" />
          <XAxis
            type="number"
            dataKey="predicha"
            domain={[0, tope]}
            {...eje(c)}
            tickFormatter={(v: number) => proporcion(v, 0)}
            label={{ value: 'Probabilidad estimada', position: 'insideBottom', offset: -8, fontSize: 12, fill: c['muted-foreground'] }}
          />
          <YAxis type="number" dataKey="observada" domain={[0, tope]} {...eje(c)} tickFormatter={(v: number) => proporcion(v, 0)} />
          <ZAxis type="number" dataKey="n" range={[40, 260]} />
          <ReferenceLine segment={[{ x: 0, y: 0 }, { x: tope, y: tope }]} stroke={c['subtle-foreground']} strokeDasharray="4 4" />
          <Tooltip
            content={({ active, payload }) =>
              active && payload?.length ? (
                <div className="rounded-xl border border-border bg-surface px-3 py-2 text-xs shadow-flotante">
                  <p className="text-foreground">Estimada: {proporcion(Number(payload[0].payload.predicha))}</p>
                  <p className="text-foreground">Observada: {proporcion(Number(payload[0].payload.observada))}</p>
                  <p className="text-muted-foreground">{entero(Number(payload[0].payload.n))} casos</p>
                </div>
              ) : null
            }
          />
          <Scatter data={puntos} fill={c['chart-1']} line={{ stroke: c['chart-1'], strokeWidth: 1.5 }} />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  )
}

export function Importancia({ items }: { items: NonNullable<CalidadModelo['importancia']> }) {
  const c = useColores()
  const datos = items.slice(0, 12).map((i) => ({ ...i, nombre: capital(i.descripcion || i.variable) }))
  return (
    <div style={{ height: 32 * datos.length + 30 }} role="img" aria-label="Importancia de las variables por permutación">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart data={datos} layout="vertical" margin={{ top: 0, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid horizontal={false} stroke={c.border} strokeDasharray="3 3" />
          <XAxis type="number" {...eje(c)} tickFormatter={(v: number) => decimal(v, 3)} />
          <YAxis
            type="category"
            dataKey="nombre"
            width={320}
            tickLine={false}
            axisLine={false}
            tick={{ fontSize: 13, fill: c['muted-foreground'] }}
            tickFormatter={(v: string) => (v.length > 48 ? `${v.slice(0, 47)}…` : v)}
          />
          <Tooltip cursor={{ fill: c.border, opacity: 0.35 }} content={<TooltipGrafico formato={(v) => `${decimal(v, 4)} de ROC-AUC`} />} />
          <Bar dataKey="media" name="Pérdida al permutar" fill={c['chart-1']} radius={[0, 4, 4, 0]} maxBarSize={20}>
            <ErrorBar dataKey="desviacion" width={4} stroke={c.foreground} strokeOpacity={0.45} direction="x" />
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

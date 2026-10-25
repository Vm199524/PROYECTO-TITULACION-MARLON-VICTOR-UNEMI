/** src/paginas/panel/GraficoTendencia.tsx — retiros (barras) y tasa de abandono (línea) por periodo. */
import { Bar, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Leyenda, TooltipGrafico } from '../../componentes/graficos/Tooltip'
import { useColores } from '../../componentes/graficos/colores'
import { entero, porcentaje } from '../../lib/formato'
import type { ResumenPanel } from '../../lib/tipos'

export default function GraficoTendencia({ datos }: { datos: ResumenPanel['tendencia'] }) {
  const c = useColores()
  if (!datos.length) return <p className="py-16 text-center text-sm text-muted-foreground">Aún no hay periodos registrados.</p>
  return (
    <div className="space-y-3">
      <Leyenda items={[{ texto: 'Retiros', color: c['chart-1'] }, { texto: 'Tasa de abandono', color: c['chart-3'], forma: 'linea' }]} />
      <div className="h-[280px]" role="img" aria-label="Retiros y tasa de abandono por periodo académico">
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart data={datos} margin={{ top: 8, right: 4, bottom: 0, left: -8 }}>
            <CartesianGrid vertical={false} stroke={c.border} strokeDasharray="3 3" />
            <XAxis dataKey="periodo" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} interval="preserveStartEnd" minTickGap={12} />
            <YAxis yAxisId="n" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} allowDecimals={false} />
            <YAxis yAxisId="t" orientation="right" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} tickFormatter={(v: number) => `${v} %`} />
            <Tooltip
              cursor={{ fill: c.border, opacity: 0.35 }}
              content={
                <TooltipGrafico
                  titulo={(l, p) => `${l} · ${entero(Number(p[0]?.payload?.estudiantes ?? 0))} matriculados`}
                  formato={(v, n) => (n === 'Tasa de abandono' ? porcentaje(v) : entero(v))}
                />
              }
            />
            <Bar yAxisId="n" dataKey="retirados" name="Retiros" fill={c['chart-1']} radius={[4, 4, 0, 0]} maxBarSize={28} />
            <Line yAxisId="t" dataKey="tasa" name="Tasa de abandono" stroke={c['chart-3']} strokeWidth={2.2} dot={{ r: 2.5 }} type="monotone" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

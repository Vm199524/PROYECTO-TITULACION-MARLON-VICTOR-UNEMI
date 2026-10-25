/** src/paginas/panel/GraficoCarreras.tsx — barras horizontales apiladas: riesgo alto y medio por carrera. */
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Leyenda, TooltipGrafico } from '../../componentes/graficos/Tooltip'
import { useColores } from '../../componentes/graficos/colores'
import { entero } from '../../lib/formato'
import type { ResumenPanel } from '../../lib/tipos'

export default function GraficoCarreras({ datos }: { datos: ResumenPanel['riesgo_por_carrera'] }) {
  const c = useColores()
  const filas = datos.filter((d) => d.alto + d.medio > 0)
  if (!filas.length) return <p className="py-16 text-center text-sm text-muted-foreground">Ninguna carrera tiene estudiantes en riesgo alto o medio.</p>
  const alto = 34 * filas.length + 30
  return (
    <div className="space-y-3">
      <Leyenda items={[{ texto: 'Riesgo alto', color: c.danger }, { texto: 'Riesgo medio', color: c.warning }]} />
      <div style={{ height: Math.max(220, alto) }} role="img" aria-label="Estudiantes en riesgo alto y medio por carrera">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={filas} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 0 }} barCategoryGap={8}>
            <CartesianGrid horizontal={false} stroke={c.border} strokeDasharray="3 3" />
            <XAxis type="number" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} allowDecimals={false} />
            <YAxis
              type="category"
              dataKey="carrera"
              width={190}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 13, fill: c['muted-foreground'] }}
              tickFormatter={(v: string) => (v.length > 28 ? `${v.slice(0, 27)}…` : v)}
            />
            <Tooltip
              cursor={{ fill: c.border, opacity: 0.35 }}
              content={<TooltipGrafico formato={(v) => `${entero(v)} estudiantes`} />}
            />
            <Bar dataKey="alto" name="Riesgo alto" stackId="r" fill={c.danger} radius={[0, 0, 0, 0]} maxBarSize={22} />
            <Bar dataKey="medio" name="Riesgo medio" stackId="r" fill={c.warning} radius={[0, 4, 4, 0]} maxBarSize={22} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

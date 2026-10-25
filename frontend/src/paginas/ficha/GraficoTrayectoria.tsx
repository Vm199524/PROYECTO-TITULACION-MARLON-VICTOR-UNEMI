/** src/paginas/ficha/GraficoTrayectoria.tsx — promedio y asistencia del estudiante por periodo. */
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Leyenda, TooltipGrafico } from '../../componentes/graficos/Tooltip'
import { useColores } from '../../componentes/graficos/colores'
import { decimal, porcentaje } from '../../lib/formato'
import type { FilaTrayectoria } from '../../lib/tipos'

export default function GraficoTrayectoria({ filas }: { filas: FilaTrayectoria[] }) {
  const c = useColores()
  const datos = filas.map((f) => ({
    etiqueta: f.corte > 1 ? `${f.periodo_academico} c${f.corte}` : f.periodo_academico,
    promedio: f.promedio,
    asistencia: f.asistencia_pct,
  }))
  return (
    <div className="space-y-3">
      <Leyenda
        items={[
          { texto: 'Promedio (0–10)', color: c['chart-1'], forma: 'linea' },
          { texto: 'Asistencia (%)', color: c['chart-2'], forma: 'linea' },
          { texto: 'Nota mínima de aprobación', color: c.danger, forma: 'linea' },
        ]}
      />
      <div className="h-[260px]" role="img" aria-label="Promedio y asistencia por periodo académico">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={datos} margin={{ top: 8, right: 4, bottom: 0, left: -12 }}>
            <CartesianGrid vertical={false} stroke={c.border} strokeDasharray="3 3" />
            <XAxis dataKey="etiqueta" tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} minTickGap={10} />
            <YAxis yAxisId="p" domain={[0, 10]} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} />
            <YAxis yAxisId="a" orientation="right" domain={[0, 100]} tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} tickFormatter={(v: number) => `${v} %`} />
            <ReferenceLine yAxisId="p" y={7} stroke={c.danger} strokeDasharray="4 4" strokeOpacity={0.7} />
            <Tooltip content={<TooltipGrafico formato={(v, n) => (n.startsWith('Asistencia') ? porcentaje(v) : decimal(v))} />} />
            <Line yAxisId="p" dataKey="promedio" name="Promedio" stroke={c['chart-1']} strokeWidth={2.2} dot={{ r: 3 }} type="monotone" connectNulls />
            <Line yAxisId="a" dataKey="asistencia" name="Asistencia" stroke={c['chart-2']} strokeWidth={2.2} dot={{ r: 3 }} type="monotone" connectNulls />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

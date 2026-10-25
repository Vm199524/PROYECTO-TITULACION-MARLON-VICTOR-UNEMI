/** src/paginas/carreras/MapaCarreras.tsx — dispersión de carreras coloreadas por segmento. */
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from 'recharts'
import { Leyenda } from '../../componentes/graficos/Tooltip'
import { useColores } from '../../componentes/graficos/colores'
import { entero, proporcion } from '../../lib/formato'
import type { CarreraSegmento } from '../../lib/tipos'

function Ayuda({ active, payload }: { active?: boolean; payload?: { payload: CarreraSegmento }[] }) {
  if (!active || !payload?.length) return null
  const c = payload[0].payload
  return (
    <div className="max-w-[260px] rounded-xl border border-border bg-surface px-3 py-2.5 text-xs shadow-flotante">
      <p className="font-semibold text-foreground">{c.carrera}</p>
      <p className="mt-0.5 text-muted-foreground">{c.segmento}</p>
      <p className="tabular mt-1.5 text-foreground">Abandono histórico: {proporcion(c.tasa_abandono_hist)}</p>
      <p className="tabular text-foreground">Riesgo promedio actual: {proporcion(c.riesgo_promedio)}</p>
      <p className="tabular text-foreground">Estudiantes: {entero(c.estudiantes)}</p>
    </div>
  )
}

/** Decimales del eje según el rango: con riesgos del 0,1 % al 0,3 % los enteros repetían «0 %». */
function decimalesEje(valores: number[]): number {
  const rango = Math.max(...valores) - Math.min(...valores)
  return rango >= 0.05 ? 0 : rango >= 0.005 ? 1 : 2
}

export default function MapaCarreras({ carreras }: { carreras: CarreraSegmento[] }) {
  const c = useColores()
  const color: Record<string, string> = { 'Atención prioritaria': c.danger, Estable: c.warning, 'Bajo riesgo': c.success }
  const grupos = Object.keys(color)
  const decX = decimalesEje(carreras.map((x) => x.tasa_abandono_hist))
  const decY = decimalesEje(carreras.map((x) => x.riesgo_promedio))
  return (
    <div className="space-y-3">
      <Leyenda items={grupos.map((g) => ({ texto: g, color: color[g] }))} />
      <div className="h-[360px]" role="img" aria-label="Carreras según abandono histórico y riesgo actual">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 10, right: 16, bottom: 18, left: 0 }}>
            <CartesianGrid stroke={c.border} strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="tasa_abandono_hist"
              name="Abandono histórico"
              domain={['auto', 'auto']}
              tickFormatter={(v: number) => proporcion(v, decX)}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fill: c['muted-foreground'] }}
              label={{ value: 'Abandono histórico', position: 'insideBottom', offset: -10, fontSize: 12, fill: c['muted-foreground'] }}
            />
            <YAxis
              type="number"
              dataKey="riesgo_promedio"
              name="Riesgo promedio"
              domain={['auto', 'auto']}
              tickFormatter={(v: number) => proporcion(v, decY)}
              tickLine={false}
              axisLine={false}
              tick={{ fontSize: 12, fill: c['muted-foreground'] }}
            />
            <ZAxis type="number" dataKey="estudiantes" range={[60, 420]} />
            <Tooltip content={<Ayuda />} cursor={{ strokeDasharray: '3 3' }} />
            {grupos.map((g) => (
              <Scatter key={g} name={g} data={carreras.filter((x) => x.segmento === g)} fill={color[g]} fillOpacity={0.8} stroke={c.surface} />
            ))}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

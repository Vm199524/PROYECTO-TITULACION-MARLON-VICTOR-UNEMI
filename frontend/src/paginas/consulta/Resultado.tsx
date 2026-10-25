/**
 * src/paginas/consulta/Resultado.tsx — muestra la respuesta de la consulta conversacional:
 * cifra destacada, gráfico de barras o líneas, o tabla, según la forma del resultado.
 */
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Leyenda, TooltipGrafico } from '../../componentes/graficos/Tooltip'
import { useColores } from '../../componentes/graficos/colores'
import { Table, TableBody, TableHead, TableRow, Td, Th } from '../../componentes/ui/Table'
import { decimal, entero, texto } from '../../lib/formato'
import type { RespuestaConsulta } from '../../lib/tipos'

const esNumero = (v: unknown) => typeof v === 'number' && Number.isFinite(v)

export function formatoCelda(v: unknown): string {
  if (typeof v === 'number') return Number.isInteger(v) ? entero(v) : decimal(v, Math.abs(v) < 1 ? 3 : 2)
  return texto(v)
}

/** Etiqueta legible de una columna SQL ("tasa_abandono_pct" → "Tasa abandono pct"). */
export function etiquetaColumna(c: string): string {
  const t = c.replace(/_/g, ' ').trim()
  return t.charAt(0).toUpperCase() + t.slice(1)
}

/** Texto con **negritas** (el resumen del backend solo usa ese marcado). */
export function TextoConNegritas({ texto: t }: { texto: string }) {
  const partes = t.split(/(\*\*[^*]+\*\*)/g)
  return (
    <>
      {partes.map((p, i) =>
        p.startsWith('**') && p.endsWith('**') ? (
          <strong key={i} className="font-semibold text-foreground">
            {p.slice(2, -2)}
          </strong>
        ) : (
          <span key={i}>{p}</span>
        )
      )}
    </>
  )
}

function Grafico({ r }: { r: RespuestaConsulta }) {
  const c = useColores()
  const series = r.columnas.slice(1).filter((_, i) => r.filas.every((f) => esNumero(f[i + 1]) || f[i + 1] === null)).slice(0, 3)
  const colores = [c['chart-1'], c['chart-2'], c['chart-3']]
  const datos = r.filas.map((f) => Object.fromEntries(r.columnas.map((col, i) => [col, f[i]])))
  const x = r.columnas[0]
  const comun = (
    <>
      <CartesianGrid vertical={false} stroke={c.border} strokeDasharray="3 3" />
      <XAxis
        dataKey={x}
        tickLine={false}
        axisLine={false}
        tick={{ fontSize: 12, fill: c['muted-foreground'] }}
        interval="preserveStartEnd"
        tickFormatter={(v: string) => (String(v).length > 16 ? `${String(v).slice(0, 15)}…` : String(v))}
      />
      <YAxis tickLine={false} axisLine={false} tick={{ fontSize: 12, fill: c['muted-foreground'] }} />
      <Tooltip cursor={{ fill: c.border, opacity: 0.35 }} content={<TooltipGrafico formato={(v) => formatoCelda(v)} />} />
    </>
  )
  return (
    <div className="space-y-3">
      {series.length > 1 && (
        <Leyenda items={series.map((s, i) => ({ texto: etiquetaColumna(s), color: colores[i], forma: r.visualizacion === 'lineas' ? 'linea' : 'punto' }))} />
      )}
    <div className="h-[260px]" role="img" aria-label={r.titulo}>
      <ResponsiveContainer width="100%" height="100%">
        {r.visualizacion === 'lineas' ? (
          <LineChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
            {comun}
            {series.map((s, i) => (
              <Line key={s} dataKey={s} name={etiquetaColumna(s)} stroke={colores[i]} strokeWidth={2.2} dot={{ r: 2.5 }} type="monotone" />
            ))}
          </LineChart>
        ) : (
          <BarChart data={datos} margin={{ top: 8, right: 8, bottom: 0, left: -8 }}>
            {comun}
            {series.map((s, i) => (
              <Bar key={s} dataKey={s} name={etiquetaColumna(s)} fill={colores[i]} radius={[4, 4, 0, 0]} maxBarSize={36} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
    </div>
  )
}

export function Resultado({ r }: { r: RespuestaConsulta }) {
  if (!r.columnas.length) return null
  if (r.visualizacion === 'valor' && r.filas.length === 1) {
    return (
      <div className="rounded-xl border border-border bg-surface-sunken px-5 py-4">
        <p className="text-xs text-muted-foreground">{etiquetaColumna(r.columnas[0])}</p>
        <p className="tabular mt-1 text-3xl font-semibold tracking-tight text-foreground">{formatoCelda(r.filas[0][0])}</p>
      </div>
    )
  }
  const tabla = (
    <div className="max-h-[360px] overflow-auto rounded-xl border border-border">
      <Table>
        <TableHead className="sticky top-0 z-10">
          <tr>
            {r.columnas.map((c, i) => (
              <Th key={c} numero={r.filas.every((f) => esNumero(f[i]) || f[i] === null)}>
                {etiquetaColumna(c)}
              </Th>
            ))}
          </tr>
        </TableHead>
        <TableBody>
          {r.filas.slice(0, 200).map((f, i) => (
            <TableRow key={i}>
              {f.map((v, j) => (
                <Td key={j} numero={esNumero(v)} className="py-2.5 text-sm">
                  {formatoCelda(v)}
                </Td>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
  if (r.visualizacion === 'barras' || r.visualizacion === 'lineas') {
    return (
      <div className="space-y-4">
        <Grafico r={r} />
        <details className="group">
          <summary className="cursor-pointer text-sm font-medium text-accent hover:underline">Ver la tabla ({entero(r.filas.length)} filas)</summary>
          <div className="mt-3">{tabla}</div>
        </details>
      </div>
    )
  }
  return tabla
}

/**
 * src/paginas/Reportes.tsx — reportes ejecutivos descargables (RF-14).
 *
 * El Excel y el PDF llevan la misma identidad de la aplicación, las mismas cifras del
 * panel y una lectura del periodo generada con reglas (nunca inventada). Las cédulas
 * salen enmascaradas y cada descarga queda en la bitácora.
 */
import { useState } from 'react'
import { IconoCheck, IconoDescargar, IconoReportes } from '../componentes/iconos'
import { EncabezadoPagina } from '../componentes/layout/EncabezadoPagina'
import { BadgeDatos } from '../componentes/ui/Badge'
import { Button } from '../componentes/ui/Button'
import { Card, CardBody, CardFooter, CardHeader } from '../componentes/ui/Card'
import { Aviso } from '../componentes/ui/Estados'
import { useToast } from '../componentes/ui/Toast'
import { descargar } from '../lib/api'
import { useSesion } from '../lib/sesion'

const REPORTES = [
  {
    clave: 'pdf',
    titulo: 'Reporte ejecutivo en PDF',
    descripcion: 'Para imprimir o enviar a las autoridades. Formato A4.',
    ruta: '/reportes/ejecutivo.pdf',
    contenido: [
      'Portada con la institución, la fecha y quién lo generó',
      'Indicadores clave del riesgo y del seguimiento',
      'Lectura del periodo: conclusiones calculadas con reglas sobre los datos',
      'Gráfico de estudiantes en riesgo por carrera',
      'Estudiantes en riesgo alto y medio con sus dos razones principales',
      'Segmentación de carreras',
    ],
  },
  {
    clave: 'xlsx',
    titulo: 'Libro de Excel',
    descripcion: 'Para filtrar, ordenar y seguir trabajando los datos.',
    ruta: '/reportes/ejecutivo.xlsx',
    contenido: [
      'Hoja Resumen con indicadores, lectura del periodo y gráfico nativo',
      'Hoja de estudiantes en riesgo con autofiltro y paneles inmovilizados',
      'Hoja de carreras con su segmento e indicadores',
      'Formatos de número y porcentaje listos para imprimir',
    ],
  },
]

export default function Reportes() {
  const { institucion } = useSesion()
  const toast = useToast()
  const [descargando, setDescargando] = useState<string | null>(null)

  async function bajar(ruta: string, clave: string) {
    setDescargando(clave)
    try {
      await descargar(ruta, `alerta_temprana.${clave}`)
      toast('exito', 'Reporte descargado.')
    } catch (e) {
      toast('error', e instanceof Error ? e.message : 'No se pudo generar el reporte.')
    } finally {
      setDescargando(null)
    }
  }

  return (
    <div className="entrada">
      <EncabezadoPagina
        titulo="Reportes ejecutivos"
        descripcion="Descargue el estado del riesgo de abandono de la institución activa. Los reportes se generan al momento con los datos vigentes."
      />
      <div className="mb-6 flex flex-wrap items-center gap-2 text-sm text-muted-foreground">
        <span>Institución:</span>
        <span className="font-medium text-foreground">{institucion?.nombre}</span>
        <BadgeDatos tipo={institucion?.tipo_datos} />
      </div>
      <div className="grid gap-6 lg:grid-cols-2">
        {REPORTES.map((r) => (
          <Card key={r.clave} className="flex flex-col">
            <CardHeader
              title={r.titulo}
              description={r.descripcion}
              actions={
                <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-accent-soft text-accent">
                  <IconoReportes className="h-5 w-5" />
                </span>
              }
            />
            <CardBody className="flex-1 pt-4">
              <ul className="space-y-2.5">
                {r.contenido.map((c) => (
                  <li key={c} className="flex gap-2.5 text-sm text-muted-foreground">
                    <IconoCheck className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                    {c}
                  </li>
                ))}
              </ul>
            </CardBody>
            <CardFooter>
              <span className="text-xs text-muted-foreground">Cédulas enmascaradas · queda registrado en la auditoría</span>
              <Button onClick={() => bajar(r.ruta, r.clave)} loading={descargando === r.clave} variant={r.clave === 'pdf' ? 'primary' : 'secondary'}>
                <IconoDescargar />
                Descargar {r.clave === 'pdf' ? 'PDF' : 'Excel'}
              </Button>
            </CardFooter>
          </Card>
        ))}
      </div>
      <Aviso tono="info" className="mt-6">
        Para exportar el resultado de una pregunta concreta, use el botón Excel debajo de cada respuesta en la consulta conversacional.
      </Aviso>
    </div>
  )
}

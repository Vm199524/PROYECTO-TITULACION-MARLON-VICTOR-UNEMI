/** Componentes base: el riesgo nunca se comunica solo con color y el acceso valida antes de enviar. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { BadgeRiesgo } from '../componentes/ui/Badge'
import { ProveedorSesion } from '../lib/sesion'
import Ingresar from '../paginas/Ingresar'

describe('componentes', () => {
  it('BadgeRiesgo escribe el nivel además del color', () => {
    render(<BadgeRiesgo riesgo="ALTO" />)
    expect(screen.getByText('Riesgo alto')).toBeInTheDocument()
  })

  it('el acceso pide usuario y contraseña sin llamar al servidor', async () => {
    const fetchEspia = vi.fn()
    vi.stubGlobal('fetch', fetchEspia)
    render(
      <QueryClientProvider client={new QueryClient()}>
        <MemoryRouter>
          <ProveedorSesion>
            <Ingresar />
          </ProveedorSesion>
        </MemoryRouter>
      </QueryClientProvider>
    )
    await userEvent.click(screen.getByRole('button', { name: 'Ingresar' }))
    expect(await screen.findByText('Ingrese su usuario y su contraseña.')).toBeInTheDocument()
    expect(fetchEspia).not.toHaveBeenCalled()
    vi.unstubAllGlobals()
  })
})

/** src/lib/tema.ts — tema claro/oscuro: sigue al sistema operativo hasta que el usuario elige. */
export type Tema = 'light' | 'dark'
const CLAVE = 'vicmar.tema'

export function temaActual(): Tema {
  return document.documentElement.getAttribute('data-theme') === 'dark' ? 'dark' : 'light'
}

export function aplicarTema(tema: Tema) {
  document.documentElement.setAttribute('data-theme', tema)
  try {
    localStorage.setItem(CLAVE, tema)
  } catch {
    /* sin almacenamiento: el tema dura lo que la pestaña */
  }
  window.dispatchEvent(new CustomEvent('vicmar:tema', { detail: tema }))
}

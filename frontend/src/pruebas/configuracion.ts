/** src/pruebas/configuracion.ts — entorno de pruebas (jsdom + aserciones de Testing Library). */
import '@testing-library/jest-dom/vitest'

// jsdom no implementa matchMedia ni <dialog>.showModal.
Object.defineProperty(window, 'matchMedia', {
  value: (q: string) => ({ matches: false, media: q, addEventListener() {}, removeEventListener() {}, addListener() {}, removeListener() {} }),
})
HTMLDialogElement.prototype.showModal ??= function (this: HTMLDialogElement) {
  this.open = true
}
HTMLDialogElement.prototype.close ??= function (this: HTMLDialogElement) {
  this.open = false
}

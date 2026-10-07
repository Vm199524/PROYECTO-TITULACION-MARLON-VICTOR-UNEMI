/**
 * tailwind.config.ts — expone los tokens de src/estilos/globales.css como clases.
 *
 * Los colores sólidos usan `<alpha-value>` para admitir opacidad (`bg-accent/10`);
 * los que ya traen transparencia en el token (barra lateral, fondos suaves del tema
 * oscuro) se usan tal cual.
 *
 * Autores: Marlon David Pérez Almachi, Víctor Manuel Lluilema Pisco
 */
import type { Config } from 'tailwindcss'

const rgb = (token: string) => `rgb(var(--${token}) / <alpha-value>)`
const rgbFijo = (token: string) => `rgb(var(--${token}))`

const config: Config = {
  darkMode: ['selector', '[data-theme="dark"]'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        background: rgb('background'),
        surface: rgb('surface'),
        'surface-hover': rgb('surface-hover'),
        'surface-sunken': rgb('surface-sunken'),
        foreground: rgb('foreground'),
        'muted-foreground': rgb('muted-foreground'),
        'subtle-foreground': rgb('subtle-foreground'),
        border: rgb('border'),
        'border-strong': rgb('border-strong'),
        accent: rgb('accent'),
        'accent-hover': rgb('accent-hover'),
        'accent-foreground': rgb('accent-foreground'),
        'accent-soft': rgbFijo('accent-soft'),
        success: rgb('success'),
        'success-soft': rgbFijo('success-soft'),
        warning: rgb('warning'),
        'warning-soft': rgbFijo('warning-soft'),
        danger: rgb('danger'),
        'danger-soft': rgbFijo('danger-soft'),
        info: rgb('info'),
        'info-soft': rgbFijo('info-soft'),
        marca: rgb('marca-naranja'),
        sidebar: rgb('sidebar-bg'),
        'sidebar-foreground': rgb('sidebar-foreground'),
        'sidebar-muted': rgb('sidebar-muted'),
        'sidebar-border': rgbFijo('sidebar-border'),
        'sidebar-hover': rgbFijo('sidebar-hover'),
        'sidebar-active': rgbFijo('sidebar-active-bg'),
        'sidebar-active-foreground': rgb('sidebar-active-foreground'),
      },
      borderRadius: { xl: '12px', '2xl': '16px' },
      boxShadow: { tarjeta: 'var(--sombra-tarjeta)', flotante: 'var(--sombra-flotante)' },
      fontFamily: { sans: ['"Inter Variable"', 'Inter', 'system-ui', 'sans-serif'] },
      fontSize: { '2xs': ['11px', '16px'] },
      maxWidth: { contenido: '1440px' },
    },
  },
  plugins: [],
}

export default config

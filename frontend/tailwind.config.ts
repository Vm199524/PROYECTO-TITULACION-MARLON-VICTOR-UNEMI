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
      // Escala tipográfica única en rem (respeta el tamaño de letra del navegador).
      // Mínimo de lectura 12 px; el texto de interfaz va a 14 px y el de lectura a 15 px.
      fontSize: {
        '2xs': ['0.75rem', '1rem'], // 12 px: encabezados de tabla, rótulos
        xs: ['0.8125rem', '1.125rem'], // 13 px: ayudas, insignias, contexto
        sm: ['0.875rem', '1.25rem'], // 14 px: texto de interfaz
        md: ['0.9375rem', '1.5rem'], // 15 px: lectura, campos, chat
        lg: ['1.125rem', '1.625rem'], // 18 px: subtítulos
        '2xl': ['1.5rem', '2rem'], // 24 px
        '3xl': ['1.75rem', '2.25rem'], // 28 px: título de página
        cifra: ['1.875rem', '2.25rem'], // 30 px: valor de los indicadores
      },
      maxWidth: { contenido: '1440px' },
    },
  },
  plugins: [],
}

export default config

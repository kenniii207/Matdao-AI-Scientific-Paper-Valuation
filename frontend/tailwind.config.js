/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        // Existing palette (underscore style)
        surface: '#131313',
        surface_container_low: '#1C1B1B',
        surface_container_high: '#2A2A2A',
        surface_bright: '#3A3939',
        primary: '#97FDFF',
        primary_container: '#3FE6E8',
        on_surface: '#E8E8E8',
        on_surface_variant: '#B8B8B8',
        outline_variant: '#4A4A4A',

        // Google Stitch palette (hyphen style) — used by prototype UI
        background: '#131313',
        'surface-container-lowest': '#0e0e0e',
        'surface-container-low': '#1b1b1b',
        'surface-container': '#1f1f1f',
        'surface-container-high': '#2a2a2a',
        'surface-container-highest': '#353535',
        'surface-tint': '#00dce5',
        'surface-variant': '#353535',
        outline: '#849495',
        'outline-variant': '#3a494a',
        'on-surface': '#e2e2e2',
        'on-surface-variant': '#b9caca',
        'primary-fixed': '#63f7ff',
        'primary-fixed-dim': '#00dce5',
        'primary-container': '#00f5ff',
        'on-primary-fixed': '#002021',
        'on-primary-fixed-variant': '#004f53',
        error: '#ffb4ab',
        'error-container': '#93000a',
        'on-error': '#690005',
        'on-error-container': '#ffdad6',
        integrity: {
          pass: '#40c057',
          fail: '#fa5252',
          warning: '#fab005',
        },
      },
      fontFamily: {
        display: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
        headline: ['Manrope', 'Inter', 'system-ui', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
        label: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        sm: '0.125rem',
        md: '0.375rem',
        xl: '0.5rem',
      },
    },
  },
  plugins: [],
};

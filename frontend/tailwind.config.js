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
        surface: '#131313',
        surface_container_low: '#1C1B1B',
        surface_container_high: '#2A2A2A',
        surface_bright: '#3A3939',
        primary: '#97FDFF',
        primary_container: '#3FE6E8',
        on_surface: '#E8E8E8',
        on_surface_variant: '#B8B8B8',
        outline_variant: '#4A4A4A',
        integrity: {
          pass: '#40c057',
          fail: '#fa5252',
          warning: '#fab005',
        },
      },
      fontFamily: {
        display: ['"Space Grotesk"', 'Inter', 'system-ui', 'sans-serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '0.25rem',
        sm: '0.125rem',
        md: '0.375rem',
      },
    },
  },
  plugins: [],
};

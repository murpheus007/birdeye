/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#050505',
        panel: '#101010',
        line: '#232323',
        neonOrange: 'rgb(var(--accent-rgb) / <alpha-value>)',
        neonSoft: 'rgb(var(--accent-soft-rgb) / <alpha-value>)',
        neonStrong: 'rgb(var(--accent-strong-rgb) / <alpha-value>)',
      },
      boxShadow: {
        neon: '0 0 0 1px rgb(var(--accent-rgb) / 0.25), 0 0 24px rgb(var(--accent-rgb) / 0.15)',
      },
      fontFamily: {
        display: ['Space Grotesk', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        body: ['Manrope', 'ui-sans-serif', 'system-ui', 'sans-serif'],
      },
      backgroundImage: {
        'dashboard-grid':
          'radial-gradient(circle at 1px 1px, rgb(var(--accent-rgb) / 0.2) 1px, transparent 0)',
      },
    },
  },
  plugins: [],
}

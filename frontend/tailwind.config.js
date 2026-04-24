/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Bloomberg-inspired dark palette
        bg: {
          primary: '#0D1117',
          secondary: '#161B22',
          card: '#1C2128',
          hover: '#21262D',
        },
        border: '#30363D',
        accent: {
          yellow: '#F0B429',
          blue: '#58A6FF',
          green: '#3FB950',
          red: '#F85149',
          purple: '#BC8CFF',
        },
        text: {
          primary: '#E6EDF3',
          secondary: '#8B949E',
          muted: '#484F58',
        },
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Menlo', 'monospace'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        bg: '#0d0d1a',
        card: '#12122a',
        'card-hover': '#16163a',
        border: '#2a2a4a',
        primary: '#7c4dff',
        'primary-dark': '#5c2ddf',
        success: '#4caf50',
        'success-dark': '#2a7a2e',
        muted: '#888888',
        subtle: '#666688',
      },
    },
  },
  plugins: [],
}

/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx}",
    "./components/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        dark: {
          900: "#0a0a0c",
          800: "#111114",
          700: "#1a1a1f",
          600: "#242429",
        },
        accent: {
          DEFAULT: "#e50914",
          light: "#ff5e62",
          dark: "#b20710",
        },
      },
      keyframes: {
        shimmer: {
          '100%': { transform: 'translateX(100%)' },
        },
        atomSpin1: {
          from: { transform: 'rotate(0deg)' },
          to: { transform: 'rotate(360deg)' },
        },
        atomSpin2: {
          from: { transform: 'rotate(60deg)' },
          to: { transform: 'rotate(420deg)' },
        },
        atomSpin3: {
          from: { transform: 'rotate(120deg)' },
          to: { transform: 'rotate(480deg)' },
        },
      },
      animation: {
        atomSpin1: 'atomSpin1 3s linear infinite',
        atomSpin2: 'atomSpin2 4s linear infinite',
        atomSpin3: 'atomSpin3 5s linear infinite',
      }
    },
  },
  plugins: [],
};

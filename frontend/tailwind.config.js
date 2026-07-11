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
    },
  },
  plugins: [],
};

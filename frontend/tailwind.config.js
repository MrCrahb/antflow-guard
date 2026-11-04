/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ant: {
          blue: "#1677ff",
          navy: "#0a192f",
          dark: "#0b132b",
          card: "#1c2541",
          border: "#3a506b",
          accent: "#00f0ff",
        },
      },
    },
  },
  plugins: [],
};

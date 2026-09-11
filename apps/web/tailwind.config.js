/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0b1020",
        panel: "#121a33",
        accent: "#6ee7ff",
      },
    },
  },
  plugins: [],
};

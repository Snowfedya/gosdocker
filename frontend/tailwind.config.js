/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'registry': '#059669',
        'community': '#2563EB',
      }
    },
  },
  plugins: [],
}
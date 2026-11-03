/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#F8FAFC",
        secondary: "#F1F5F9",
        card: "#FFFFFF",
        border: "#E2E8F0",
        blue: {
          accent: "#2563EB",
        },
        success: "#16A34A",
        warning: "#D97706",
        critical: "#DC2626",
        text: {
          primary: "#0F172A",
          secondary: "#64748B",
        },
      },
      fontFamily: {
        sans: ['"Inter"', "sans-serif"],
      },
      borderRadius: {
        sm: "8px",
        DEFAULT: "10px",
        md: "14px",
        lg: "18px",
      },
    },
  },
  plugins: [],
}

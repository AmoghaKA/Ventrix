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
      boxShadow: {
        soft: "0 1px 2px 0 rgba(15,23,42,0.04), 0 18px 36px -24px rgba(15,23,42,0.18)",
        lift: "0 24px 60px -28px rgba(15,23,42,0.32)",
        glow: "0 18px 40px -18px rgba(37,99,235,0.55)",
        "inner-line": "inset 0 1px 0 0 rgba(255,255,255,0.08)",
        ring: "0 0 0 1px rgba(15,23,42,0.04), 0 12px 28px -18px rgba(15,23,42,0.25)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        "fade-in": {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        shimmer: {
          "100%": { transform: "translateX(100%)" },
        },
        "pulse-soft": {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.45" },
        },
        "float-slow": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-12px)" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.16, 1, 0.3, 1) both",
        "fade-in": "fade-in 0.4s ease-out both",
        shimmer: "shimmer 2.4s infinite",
        "pulse-soft": "pulse-soft 2.8s ease-in-out infinite",
        "float-slow": "float-slow 8s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}

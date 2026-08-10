import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          50: "#eef6fc",
          100: "#d5e9f8",
          200: "#add3f0",
          300: "#7ab6e4",
          400: "#4493d4",
          500: "#2676ba",
          600: "#1f4e79",
          700: "#1a4066",
          800: "#193756",
          900: "#192f48",
        },
        accent: {
          400: "#34d399",
          500: "#10b981",
          600: "#059669",
        },
      },
      boxShadow: {
        card: "0 10px 40px -12px rgba(31, 78, 121, 0.25)",
      },
    },
  },
  plugins: [],
};

export default config;

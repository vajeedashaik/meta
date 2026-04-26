import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        background: "#09080f",
        foreground: "#ede9f8",
        primary: "#8b5cf6",
        muted: "#1c1730",
        card: "#120f1e",
        border: "#2e2255"
      },
      fontFamily: {
        display: ["var(--font-display)", "sans-serif"]
      },
      borderRadius: {
        "2xl": "1rem"
      },
      boxShadow: {
        soft: "0 10px 30px rgba(139, 92, 246, 0.12)"
      },
      backgroundImage: {
        hero: "radial-gradient(circle at top right, rgba(139,92,246,0.12), transparent 50%), radial-gradient(circle at 15% 20%, rgba(109,40,217,0.10), transparent 45%)"
      }
    }
  },
  plugins: []
};

export default config;

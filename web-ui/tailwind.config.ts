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
        background: "#f6f9ff",
        foreground: "#0f172a",
        primary: "#1877F2",
        muted: "#eaf2ff",
        card: "#ffffff",
        border: "#dbeafe"
      },
      borderRadius: {
        "2xl": "1rem"
      },
      boxShadow: {
        soft: "0 10px 30px rgba(24, 119, 242, 0.08)"
      },
      backgroundImage: {
        hero: "radial-gradient(circle at top right, rgba(24,119,242,0.20), transparent 45%), radial-gradient(circle at 15% 20%, rgba(14,165,233,0.15), transparent 40%)"
      }
    }
  },
  plugins: []
};

export default config;

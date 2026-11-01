import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#050810",
        panel: "#0b1220",
        cyanaccent: "#22d3ee",
        roseaccent: "#f43f5e",
        goldaccent: "#eab308",
        emeraldaccent: "#34d399",
        violetaccent: "#a78bfa",
        bronzeaccent: "#c9803f",
      },
      fontFamily: {
        sans: ['Inter', 'Segoe UI', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Cascadia Mono', 'Consolas', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
};
export default config;

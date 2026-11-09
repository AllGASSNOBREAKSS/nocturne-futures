/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: { 950: "#06080b", 900: "#0a0d12", 850: "#0d1117", 800: "#111721", 750: "#151c27", 700: "#1b2431", 600: "#263142", 500: "#3a475b", 400: "#5d6b80", 300: "#8592a3", 200: "#aeb8c6", 100: "#dde3ea" },
        amber: { 300: "#ffd27a", 400: "#ffbf3c", 500: "#ffab00", 600: "#e08f00", 700: "#9c6400" },
        up: "#2ee6a6", down: "#ff4d6a", info: "#39c5ff", research: "#a78bfa", warn: "#ffcc4d",
      },
      fontFamily: { sans: ["Inter", "system-ui", "sans-serif"], mono: ["IBM Plex Mono", "ui-monospace", "monospace"] },
      fontSize: { "2xs": ["10px", "14px"] },
      keyframes: {
        shimmer: { "100%": { transform: "translateX(100%)" } },
        pulseDot: { "0%,100%": { opacity: 1 }, "50%": { opacity: 0.35 } },
        scan: { "0%": { transform: "translateX(-100%)" }, "100%": { transform: "translateX(100%)" } },
      },
      animation: { shimmer: "shimmer 1.4s infinite", pulseDot: "pulseDot 1.6s ease-in-out infinite", scan: "scan 2.2s linear infinite" },
    },
  },
  plugins: [],
};

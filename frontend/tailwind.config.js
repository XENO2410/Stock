/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        brand: {
          DEFAULT: "#00b386", // Groww-like teal-green
          dark: "#00996f",
          light: "#e6f7f2",
        },
        // Semantic
        up: "#00b386",
        down: "#eb5b3c",
        neutral: "#8b93a7",
        surface: {
          DEFAULT: "#ffffff",
          alt: "#f7f8fb",
          dark: "#0f1420",
          "dark-alt": "#151a29",
        },
        border: {
          DEFAULT: "#e8ebef",
          dark: "#232a3a",
        },
        ink: {
          DEFAULT: "#1a1f2e",
          soft: "#4b5468",
          muted: "#8b93a7",
          inverse: "#e9ecf5",
        },
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(15, 20, 32, 0.04), 0 1px 3px rgba(15, 20, 32, 0.06)",
      },
      borderRadius: {
        xl: "0.85rem",
      },
    },
  },
  plugins: [],
};

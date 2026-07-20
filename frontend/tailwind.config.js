/** @type {import('tailwindcss').Config} */
/** Ledger UI — maps Tailwind color names to approved HEX (see src/ui/design-tokens.ts). */
export default {
  darkMode: ["class", '[data-theme="dark"]'],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
      },
      colors: {
        surface: {
          DEFAULT: "#FFFFFF",
          muted: "#F7F8FA",
          subtle: "#E6E8EC",
          inset: "#F1F3F5",
        },
        ink: {
          DEFAULT: "#111827",
          secondary: "#3F4B5A",
          muted: "#6B7280",
          faint: "#9CA3AF",
        },
        brand: {
          DEFAULT: "#0B6BCB",
          hover: "#0958A8",
          muted: "#E8F2FC",
          subtle: "#E8F2FC",
        },
        ledger: {
          action: "#0B6BCB",
          "action-hover": "#0958A8",
          "action-soft": "#E8F2FC",
          profit: "#0F7B5A",
          "profit-soft": "#E6F5EF",
          expense: "#3D4A5C",
          "expense-soft": "#EEF1F4",
          risk: "#C81E1E",
          "risk-soft": "#FDECEC",
          warn: "#9A5A00",
          "warn-soft": "#FFF6E5",
          900: "#111827",
          700: "#3F4B5A",
          500: "#6B7280",
          300: "#D1D5DB",
          100: "#F3F4F6",
        },
        semantic: {
          success: "#0F7B5A",
          "success-bg": "#E6F5EF",
          warn: "#9A5A00",
          "warn-bg": "#FFF6E5",
          danger: "#C81E1E",
          "danger-bg": "#FDECEC",
          info: "#0B6BCB",
          "info-bg": "#E8F2FC",
        },
        chart: {
          revenue: "#2F6FED",
          profit: "#0F7B5A",
          logistics: "#A16207",
          ads: "#1D4E89",
          returns: "#C81E1E",
          payout: "#3D4A5C",
        },
      },
      boxShadow: {
        soft: "0 1px 3px rgba(17, 24, 39, 0.06), 0 8px 24px rgba(17, 24, 39, 0.06)",
        card: "0 1px 2px rgba(17, 24, 39, 0.04), 0 4px 16px rgba(17, 24, 39, 0.05)",
        raised: "0 1px 2px rgba(17, 24, 39, 0.04), 0 8px 24px rgba(17, 24, 39, 0.06)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1rem",
      },
    },
  },
  plugins: [],
};

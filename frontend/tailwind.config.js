/** @type {import('tailwindcss').Config} */
export default {
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
          DEFAULT: "#ffffff",
          muted: "#f4f6f9",
          subtle: "#e8ecf2",
          inset: "#f8fafc",
        },
        ink: {
          DEFAULT: "#0f172a",
          secondary: "#334155",
          muted: "#64748b",
          faint: "#94a3b8",
        },
        brand: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
          muted: "#dbeafe",
          subtle: "#eff6ff",
        },
        semantic: {
          success: "#047857",
          "success-bg": "#ecfdf5",
          warn: "#b45309",
          "warn-bg": "#fffbeb",
          danger: "#b91c1c",
          "danger-bg": "#fef2f2",
          info: "#0369a1",
          "info-bg": "#f0f9ff",
        },
        chart: {
          revenue: "#3b82f6",
          profit: "#059669",
          logistics: "#ca8a04",
          ads: "#7c3aed",
          returns: "#e11d48",
          payout: "#4f46e5",
        },
      },
      boxShadow: {
        soft: "0 1px 3px rgba(15, 23, 42, 0.06), 0 8px 24px rgba(15, 23, 42, 0.06)",
        card: "0 1px 2px rgba(15, 23, 42, 0.04), 0 4px 16px rgba(15, 23, 42, 0.05)",
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1rem",
      },
    },
  },
  plugins: [],
};

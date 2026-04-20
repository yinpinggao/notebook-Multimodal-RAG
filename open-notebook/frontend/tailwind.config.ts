import typography from "@tailwindcss/typography";
import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "zyc-bg": "#121212",
        "zyc-panel": "#18191c",
        "zyc-panel-2": "#1d1f24",
        "zyc-glass": "rgba(255, 255, 255, 0.08)",
        "zyc-evidence": "#47b6ff",
        "zyc-compare": "#f0ae43",
        "zyc-memory": "#9f71ff",
        "zyc-output": "#53c27b",
        "zyc-runs": "#8a8f98",
      },
      boxShadow: {
        "zyc-lift": "0 16px 44px rgba(0, 0, 0, 0.18)",
        "zyc-soft": "0 12px 24px rgba(0, 0, 0, 0.14)",
      },
      screens: {
        "zyc-mobile": "640px",
        "zyc-tablet": "1024px",
        "zyc-desktop": "1440px",
      },
    },
  },
  plugins: [typography],
};

export default config;

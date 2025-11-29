import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bgMain: "#FFF8DE",
        bgSoft: "#FFF2C6",
        accentBlueLight: "#AAC4F5",
        accentBlue: "#8CA9FF",
        highlight: "#FFD860",
      },
      boxShadow: {
        soft: "0 10px 25px rgba(0,0,0,0.06)",
      },
      borderRadius: {
        xl2: "1.25rem",
      },
    },
  },
  plugins: [],
};
export default config;

import type { Config } from "tailwindcss";

/**
 * Tailwind v4 는 CSS-first config 를 권장.
 * 브랜드 토큰은 globals.css 의 @theme inline 에 정의되어 있음.
 * 이 파일은 content path 와 plugin 만 유지.
 */
const config: Config = {
  content: ["./app/**/*.{js,ts,jsx,tsx}", "./components/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;

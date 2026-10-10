/** Цвета брендбука ФСП (CONTRACT.md, раздел 1). */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        fsp: { DEFAULT: "#520978", dark: "#310F53", accent: "#FF0053", pink: "#FC3777", soft: "#8A83D1", tint: "#FFD6E4", ink: "#1C1D22" },
      },
      fontFamily: { sans: ["Montserrat", "system-ui", "sans-serif"] },
    },
  },
  plugins: [],
};

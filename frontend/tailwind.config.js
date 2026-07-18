export default {
  content: ["./index.html", "./src/**/*.{vue,js}"],
  theme: {
    extend: {
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
      },
      colors: {
        ink: "#17211c",
        field: "#f7f8f5",
        line: "#dfe4dc",
        moss: "#49664c",
        spruce: "#12382e",
        signal: "#d86f45",
      },
      boxShadow: {
        soft: "0 14px 40px rgba(23, 33, 28, 0.08)",
      },
    },
  },
  plugins: [],
};

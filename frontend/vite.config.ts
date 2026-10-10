import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// В разработке /api проксируется на бэкенд из docker compose (по умолчанию 127.0.0.1:8000, см. API_PORT в .env);
// на стенде /api отдаёт nginx.
const apiTarget = process.env.API_PROXY ?? `http://127.0.0.1:${process.env.API_PORT ?? "8000"}`;

export default defineConfig({
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": apiTarget } },
});

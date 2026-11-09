import tailwindcss from "@tailwindcss/vite";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    // Everything the frontend fetches must be forwarded to the API in dev,
    // or Vite answers with index.html and the call fails as "Unexpected token
    // <". `/lobby` was missing here for a while; keep this list in sync with
    // the paths in `src/api.ts`.
    proxy: {
      "/health": "http://127.0.0.1:8000",
      "/games": "http://127.0.0.1:8000",
      "/lobby": "http://127.0.0.1:8000",
    },
  },
});

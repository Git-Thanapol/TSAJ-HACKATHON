import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: true,
    port: 5173,
    // Windows bind mount into the Linux container drops inotify events — poll instead
    watch: { usePolling: true, interval: 500 },
    proxy: {
      "/v0": { target: "http://backend:8000", ws: true },
      "/assets": "http://backend:8000",
      "/health": "http://backend:8000",
    },
  },
});

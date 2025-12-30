import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@klyvo/ui": path.resolve(__dirname, "../../packages/ui/src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
      "/files": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});



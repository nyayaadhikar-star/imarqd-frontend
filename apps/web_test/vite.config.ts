import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  const apiBase = env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

  const isHttps = /^https:/i.test(apiBase);

  return {
    plugins: [react()],
    resolve: {
      alias: {
        "@klyvo/ui": path.resolve(__dirname, "../../packages/ui/src"),
      },
    },
    server: {
      port: 5173,
      proxy: {
        // Dev only: lets your dev server call /api/* and /files/*
        // and forward to your backend base URL.
        "/api": {
          target: apiBase,
          changeOrigin: true,
          secure: isHttps,
        },
        "/files": {
          target: apiBase,
          changeOrigin: true,
          secure: isHttps,
        },
      },
    },
  };
});

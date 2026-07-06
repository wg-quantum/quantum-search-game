/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      // dev用: フロント(5173)からのAPI呼び出しをバックエンド(8000)へ転送
      // 127.0.0.1固定: Node 17+ は localhost を ::1 に解決し、uvicorn(IPv4)に届かないため
      "/api": "http://127.0.0.1:8000",
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["./src/test/setup.ts"],
    globals: true,
  },
});

import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Tauri expects a fixed dev port and does not handle the Vite websocket being
// moved around, so the port is pinned rather than auto-incremented.
export default defineConfig({
  plugins: [react()],
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    watch: {
      // These are built by other toolchains; watching them just burns CPU.
      ignored: ["**/src-tauri/**", "**/../backend/**"],
    },
  },
  build: {
    // Tauri's bundled webviews: Chromium on Windows/Linux, WebKit on macOS.
    target: process.env.TAURI_ENV_PLATFORM === "windows" ? "chrome105" : "safari13",
    sourcemap: !!process.env.TAURI_ENV_DEBUG,
    minify: !process.env.TAURI_ENV_DEBUG,
  },
});

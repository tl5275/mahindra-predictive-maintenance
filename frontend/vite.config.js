import path from "node:path";
import { fileURLToPath } from "node:url";

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const envDir = path.resolve(__dirname, "..");

export default defineConfig({
  envDir,
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
  },
  build: {
    outDir: "dist",
    rollupOptions: {
      output: {
        manualChunks: {
          react: ["react", "react-dom", "zustand"],
          maps: ["leaflet", "react-leaflet", "react-leaflet-cluster"],
          charts: ["recharts"],
          virtualized: ["react-window"],
        },
      },
    },
  }
});

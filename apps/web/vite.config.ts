import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// NOTE: the preview proxy requires the dev server to accept the forwarded
// host. `host: true` + relative API URLs (proxied to :8000) keep the browser
// away from direct localhost calls to other services.
export default defineConfig({
  plugins: [react()],
  server: {
    host: "0.0.0.0",
    port: 5173,
    // Allow proxied preview hosts (sandbox/live-preview environments).
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    allowedHosts: true as any,
    proxy: {
      "/v1": {
        target: process.env.AIMATHH_API_URL || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  preview: {
    host: "0.0.0.0",
    port: 4173,
  },
});

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/register": "http://127.0.0.1:5000",
      "/login": "http://127.0.0.1:5000",
      "/biometric-verify": "http://127.0.0.1:5000",
      "/vote": "http://127.0.0.1:5000",
      "/verify": "http://127.0.0.1:5000",
      "/board": "http://127.0.0.1:5000",
      "/tally": "http://127.0.0.1:5000"
    }
  }
});

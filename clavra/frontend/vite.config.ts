import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Uncomment when vite-plugin-pwa is installed (Stage 8):
// import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    // VitePWA({
    //   registerType: "autoUpdate",
    //   manifest: false,  // we use public/manifest.json
    //   workbox: {
    //     globPatterns: ["**/*.{js,css,html,ico,png,svg,woff2}"],
    //     runtimeCaching: [{
    //       urlPattern: /^https:\/\/.*\/api\/.*/i,
    //       handler: "NetworkFirst",
    //       options: { cacheName: "api-cache", networkTimeoutSeconds: 10 }
    //     }]
    //   }
    // })
  ],
  server: {
    port: 5173,
    host: true, // needed for mobile PWA testing on LAN
  },
});

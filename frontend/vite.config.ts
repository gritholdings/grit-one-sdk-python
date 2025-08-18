import path from "path"
import tailwindcss from "@tailwindcss/vite"
import react from "@vitejs/plugin-react"
import { defineConfig } from "vite"
import fs from "fs"

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react({
      include: '**/*.tsx',
    }),
    tailwindcss(),
    {
      // This plugin checks if CSS files imported from input.css exist. If they don't, it
      // returns an empty virtual CSS file instead of throwing an error.
      name: 'optional-css-import',
      resolveId(source, importer) {
        if (source.endsWith('.css') && importer?.endsWith('input.css')) {
          const resolvedPath = path.resolve(path.dirname(importer), source)
          if (!fs.existsSync(resolvedPath)) {
            return { id: 'virtual:empty.css', external: false }
          }
        }
      },
      load(id) {
        if (id === 'virtual:empty.css') {
          return ''
        }
      }
    }
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
      "@frontend": path.resolve(__dirname, "./src"),
      "@app_frontend": path.resolve(__dirname, "./app_frontend/src"),
    },
  },
  server: {
    port: 5173,
    host: 'localhost',
    cors: true,
    hmr: {
      overlay: true,
      port: 5173,
    },
  },
  build: {
    outDir: '../home/static/home/dist',
    manifest: 'manifest.json',
    rollupOptions: {
      input: {
        main: path.resolve(__dirname, 'src/main.tsx'),
      },
    },
  },
})
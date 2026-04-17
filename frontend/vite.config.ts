import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: {
            '@': path.resolve(process.cwd(), './src'),
        },
    },
    server: {
        port: 3000,
        proxy: {
            // DefensIA router uses /api/defensia prefix — pass through as-is
            '/api/defensia': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
            // Legacy routers (auth, ask, workspaces, etc.) use prefix
            // without /api — strip it to match backend routes
            '/api': {
                target: 'http://localhost:8000',
                changeOrigin: true,
                rewrite: (path: string) => path.replace(/^\/api/, ''),
            },
            '/auth': {
                target: 'http://localhost:8000',
                changeOrigin: true,
            },
        },
    },
    build: {
        outDir: 'dist',
        sourcemap: true,
        chunkSizeWarningLimit: 600,
    },
})

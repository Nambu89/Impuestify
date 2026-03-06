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
        rollupOptions: {
            output: {
                manualChunks: (id) => {
                    if (id.includes('node_modules/react/') || id.includes('node_modules/react-dom/') || id.includes('node_modules/react-router-dom/')) {
                        return 'vendor'
                    }
                    if (id.includes('node_modules/lucide-react/') || id.includes('node_modules/react-markdown/') || id.includes('node_modules/remark-gfm/') || id.includes('node_modules/motion/')) {
                        return 'ui'
                    }
                },
            },
        },
    },
})

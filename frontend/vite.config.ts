import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        host: true,
        allowedHosts: ['dev.link-it.tech', 'link-it.tech', 'www.link-it.tech'],
        proxy: {
            '/api': {
                target: 'http://backend:8000',
                changeOrigin: true
            }
        }
    }
})

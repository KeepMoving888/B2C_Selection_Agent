import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { viteSingleFile } from 'vite-plugin-singlefile'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    // ZIP 演示用单文件模式，部署用多文件模式
    process.env.SINGLE_FILE === 'true' ? viteSingleFile() : null,
  ].filter(Boolean),
  // GitHub Pages 部署时需要 base 路径，本地开发和 Vercel 部署使用 '/'
  base: process.env.VITE_BASE_PATH || '/',
  server: {
    port: 5173,
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src'),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        api: 'modern-compiler'
      }
    }
  },
  server: {
    port: 8787,
    host: '0.0.0.0',
    proxy: {
      // 注意：Vite 代理 key 为字符串前缀匹配（或正则需以 ^ 开头）。
      // 此处使用明确的前缀匹配，避免正则 key 在部分版本下不生效。
      '/api/': {
        target: 'http://localhost:8686',
        changeOrigin: true,
        secure: false,
        timeout: 60000,
        proxyTimeout: 60000,
      },
      '/media/': {
        target: 'http://localhost:8686',
        changeOrigin: true,
        secure: false,
      },
    },
    historyApiFallback: {
      index: '/index.html',
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    sourcemap: false,
  },
})
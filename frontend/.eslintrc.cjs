/* ESLint 配置（Vue3 + Vite） */
module.exports = {
  root: true,
  env: {
    browser: true,
    es2022: true,
    node: true
  },
  parser: 'vue-eslint-parser',
  parserOptions: {
    ecmaVersion: 2022,
    sourceType: 'module'
  },
  extends: [
    'eslint:recommended',
    'plugin:vue/vue3-recommended'
  ],
  plugins: ['vue'],
  rules: {
    // 安全相关：禁止直接使用 v-html（请改用本项目自定义的 v-safe-html）
    'vue/no-v-html': 'error',
    // 前端不应将敏感 token 写入 localStorage（配合 WS1 安全升级）
    'no-console': 'off',
    'vue/multi-word-component-names': 'off'
  },
  ignorePatterns: [
    'dist',
    'node_modules'
  ]
}

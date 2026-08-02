<template>
  <div class="base-page-container">
    <div class="base-page-header" v-if="title || $slots.header || $slots.actions">
      <div class="header-left">
        <slot name="header">
          <h1 class="base-page-title" v-if="title">{{ title }}</h1>
        </slot>
      </div>
      <div class="base-page-actions">
        <slot name="actions"></slot>
      </div>
    </div>
    
    <div class="base-main-content">
      <div 
        :class="[
          'base-content-wrapper', 
          { 'is-dashboard': type === 'dashboard' },
          { 'no-padding': noPadding }
        ]"
      >
        <slot></slot>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: ''
  },
  type: {
    type: String,
    default: 'standard', // 'standard' | 'dashboard'
    validator: (val) => ['standard', 'dashboard'].includes(val)
  },
  noPadding: {
    type: Boolean,
    default: false
  }
})
</script>

<style scoped>
.base-page-container {
  height: 100vh;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: transparent;
  overflow: hidden;
}

.base-page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 32px 16px;
  background: transparent;
  flex-shrink: 0;
  box-sizing: border-box;
}

.header-left {
  position: relative;
  padding-left: 16px;
}

.header-left::before {
  content: '';
  position: absolute;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 4px;
  height: 20px;
  background: linear-gradient(135deg, var(--primary), var(--accent));
  border-radius: 2px;
}

.base-page-title {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  color: var(--slate-950);
  letter-spacing: -0.02em;
}

.base-page-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.base-main-content {
  flex: 1;
  overflow: hidden;
  padding: 0 32px 32px;
  display: flex;
  flex-direction: column;
}

.base-content-wrapper {
  flex: 1;
  width: 100%;
  background: var(--bg-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--border-light);
  padding: 32px;
  height: 100%;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  animation: fade-in-up 0.6s cubic-bezier(0.16, 1, 0.3, 1);
}

/* Dashboard 模式：透明背景，由内部卡片决定布局 */
.base-content-wrapper.is-dashboard {
  background: transparent;
  box-shadow: none;
  border: none;
  padding: 0; 
  display: block; 
}

.base-content-wrapper.no-padding {
  padding: 0;
}
</style>

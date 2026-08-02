<template>
  <div 
    class="premium-card" 
    :class="[
      { 'glass': glass },
      { 'hover-glow': hoverGlow },
      { 'hover-tilt': hoverTilt }
    ]"
    :style="cardStyle"
  >
    <div v-if="$slots.header || title" class="premium-card-header">
      <slot name="header">
        <h3 class="card-title">{{ title }}</h3>
      </slot>
      <div v-if="$slots.extra" class="card-extra">
        <slot name="extra"></slot>
      </div>
    </div>
    <div class="premium-card-body" :style="bodyStyle">
      <slot></slot>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  glass: { type: Boolean, default: false },
  hoverGlow: { type: Boolean, default: true },
  hoverTilt: { type: Boolean, default: false },
  padding: { type: String, default: '24px' },
  glowColor: { type: String, default: 'var(--primary-glow)' }
})

const cardStyle = computed(() => ({
  '--glow-color': props.glowColor
}))

const bodyStyle = computed(() => ({
  padding: props.padding
}))
</script>

<style lang="scss" scoped>
.premium-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  transition: all 0.4s cubic-bezier(0.165, 0.84, 0.44, 1);
  overflow: hidden;
  position: relative;
  
  &.glass {
    background: var(--bg-surface-glass);
    backdrop-filter: blur(16px);
    -webkit-backdrop-filter: blur(16px);
    border: 1px solid var(--border-glass);
  }
  
  &.hover-glow:hover {
    box-shadow: 0 10px 30px -5px var(--glow-color);
    border-color: var(--primary-light);
  }
}

.premium-card-header {
  padding: 16px 24px;
  border-bottom: 1px solid var(--border-light);
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .card-title {
    margin: 0;
    font-size: 16px;
    font-weight: 600;
    color: var(--slate-900);
  }
}

.card-extra {
  font-size: 14px;
}
</style>

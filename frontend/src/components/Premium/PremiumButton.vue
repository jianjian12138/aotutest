<template>
  <el-button
    v-bind="$attrs"
    :class="[
      'premium-button',
      { 'glow': glow },
      { 'glass': glass }
    ]"
    class="premium-btn"
  >
    <template #default>
      <slot></slot>
    </template>
    <template #icon v-if="$slots.icon">
      <slot name="icon"></slot>
    </template>
  </el-button>
</template>

<script setup>
defineProps({
  glow: { type: Boolean, default: false },
  glass: { type: Boolean, default: false }
})
</script>

<style lang="scss" scoped>
.premium-btn {
  &.premium-button {
    border-radius: var(--radius-md) !important;
    text-transform: none;
    letter-spacing: 0.02em;
    font-weight: 600;
  }
  
  &.glow:not(.is-disabled) {
    animation: glow-pulse 2s infinite;
  }
}

@keyframes glow-pulse {
  0% { box-shadow: 0 0 0 0 var(--primary-glow); }
  70% { box-shadow: 0 0 20px 10px rgba(0, 0, 0, 0); }
  100% { box-shadow: 0 0 0 0 rgba(0, 0, 0, 0); }
}
</style>

<template>
  <div class="chatwiki-layout">
    <!-- Main Content -->
    <div class="main-content">
      <div class="content-body">
        <router-view />
      </div>
    </div>
  </div>
</template>

<script setup>
// No specific logic needed as navigation is handled by router
</script>

<style scoped lang="scss">
.chatwiki-layout {
  display: flex;
  height: calc(100vh - 60px); // Adjust based on global layout header height
  background: #f5f7fa;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  position: relative;
}

.content-body {
  flex: 1;
  overflow: hidden;
  position: relative;
}
</style>

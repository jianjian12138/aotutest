<template>
  <div class="unified-project-list">
    <h1>统一项目管理</h1>
    <p>这是一个简化的项目管理页面</p>
    
    <div class="simple-list">
      <div v-if="loading">加载中...</div>
      <div v-else>
        <div v-if="projects.length === 0">暂无项目数据</div>
        <div v-else>
          <div v-for="project in projects" :key="project.id" class="project-item">
            <h3>{{ project.name }}</h3>
            <p>类型: {{ project.project_type }}</p>
            <p>状态: {{ project.status }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const projects = ref([])
const loading = ref(false)

const fetchProjects = async () => {
  loading.value = true
  try {
    // 简化的数据获取
    projects.value = [
      { id: 1, name: '测试项目1', project_type: 'API', status: 'active' },
      { id: 2, name: '测试项目2', project_type: 'UI', status: 'active' }
    ]
  } catch (error) {
    console.error('获取项目列表失败:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchProjects()
})
</script>

<style scoped>
.unified-project-list {
  padding: 20px;
}

.project-item {
  border: 1px solid #e0e0e0;
  padding: 15px;
  margin-bottom: 10px;
  border-radius: 4px;
}

.project-item h3 {
  margin: 0 0 10px 0;
}

.project-item p {
  margin: 5px 0;
}
</style>

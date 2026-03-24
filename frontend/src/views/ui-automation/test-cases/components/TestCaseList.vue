<template>
  <div class="test-case-list-container">
    <div class="panel-header">
      <h3>测试用例列表</h3>
      <el-input
        v-model="searchKeyword"
        placeholder="搜索测试用例..."
        clearable
        size="small"
        style="width: 200px"
      >
        <template #prefix>
          <el-icon><Search /></el-icon>
        </template>
      </el-input>
    </div>

    <div class="test-case-list">
      <div
        v-for="testCase in filteredTestCases"
        :key="testCase.id"
        class="test-case-item"
        :class="{ active: selectedTestCase?.id === testCase.id }"
        @click="handleSelectTestCase(testCase)"
      >
        <div class="case-header">
          <div class="case-info">
            <h4 class="case-name">{{ testCase.name }}</h4>
            <p class="case-description">{{ testCase.description || '暂无描述' }}</p>
          </div>
          <div class="case-actions">
            <el-button size="small" text @click.stop="handleRunTestCase(testCase)">
              <el-icon><CaretRight /></el-icon>
            </el-button>
            <el-button size="small" text @click.stop="handleEditTestCase(testCase)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button size="small" text @click.stop="handleCopyTestCase(testCase)">
              <el-icon><CopyDocument /></el-icon>
            </el-button>
            <el-button size="small" text type="danger" @click.stop="handleDeleteTestCase(testCase)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
        </div>
        <div class="case-meta">
          <span class="step-count">{{ testCase.steps?.length || 0 }} 步骤</span>
          <span class="update-time">{{ formatTime(testCase.updated_at) }}</span>
        </div>
      </div>

      <el-empty v-if="filteredTestCases.length === 0" description="暂无测试用例" />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Search, CaretRight, Edit, CopyDocument, Delete } from '@element-plus/icons-vue'
import { formatTime } from '@/utils/helpers'

// Props
const props = defineProps({
  testCases: {
    type: Array,
    default: () => []
  },
  selectedTestCase: {
    type: Object,
    default: null
  }
})

// Emits
const emit = defineEmits(['select', 'run', 'edit', 'copy', 'delete'])

// State
const searchKeyword = ref('')

// Computed
const filteredTestCases = computed(() => {
  if (!searchKeyword.value) return props.testCases
  return props.testCases.filter(tc =>
    tc.name.includes(searchKeyword.value) ||
    tc.description?.includes(searchKeyword.value)
  )
})

// Methods
const handleSelectTestCase = (testCase) => {
  emit('select', testCase)
}

const handleRunTestCase = (testCase) => {
  emit('run', testCase)
}

const handleEditTestCase = (testCase) => {
  emit('edit', testCase)
}

const handleCopyTestCase = (testCase) => {
  emit('copy', testCase)
}

const handleDeleteTestCase = (testCase) => {
  emit('delete', testCase)
}

// Watch
watch(() => props.selectedTestCase, (newVal) => {
  if (!newVal) {
    searchKeyword.value = ''
  }
}, { immediate: true })
</script>

<style scoped>
.test-case-list-container {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
}

.panel-header h3 {
  margin: 0;
  font-size: 16px;
  color: #333;
}

.test-case-list {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.test-case-item {
  padding: 15px;
  margin-bottom: 10px;
  background: white;
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.test-case-item:hover {
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.1);
}

.test-case-item.active {
  border-color: #409eff;
  background: #f0f9ff;
}

.case-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.case-info {
  flex: 1;
}

.case-name {
  margin: 0 0 8px 0;
  font-size: 14px;
  color: #333;
  font-weight: 600;
}

.case-description {
  margin: 0;
  font-size: 12px;
  color: #666;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  line-clamp: 2;
}

.case-actions {
  display: flex;
  gap: 5px;
}

.case-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
  color: #999;
}

.step-count {
  background: #f5f7fa;
  padding: 2px 8px;
  border-radius: 3px;
}

.update-time {
  color: #999;
}
</style>

<template>
  <div class="steps-editor-container">
    <div class="steps-header">
      <h4>测试步骤</h4>
      <div class="header-actions">
        <el-button size="small" text @click="handleAddStep">
          <el-icon><Plus /></el-icon>
          添加步骤
        </el-button>
        <el-button size="small" text @click="handleToggleExpand">
          {{ allExpanded ? '折叠全部' : '展开全部' }}
        </el-button>
      </div>
    </div>

    <div class="steps-scroll-container">
      <div class="steps-list">
        <draggable
          v-model="localSteps"
          item-key="id"
          @end="handleDragEnd"
          class="draggable-container"
        >
          <template #item="{ element, index }">
            <div class="step-item">
              <div class="step-header">
                <div class="step-left">
                  <el-icon class="drag-handle"><Rank /></el-icon>
                  <span class="step-number">{{ index + 1 }}</span>
                  <span class="step-type">{{ element.action_type || '操作' }}</span>
                </div>
                <div class="step-right">
                  <el-button size="small" text type="primary" @click.stop="handleEditStep(element)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                  <el-button size="small" text type="danger" @click.stop="handleDeleteStep(index)">
                    <el-icon><Delete /></el-icon>
                  </el-button>
                </div>
              </div>

              <el-collapse-transition>
                <div v-show="element.expanded" class="step-content">
                  <div class="step-param">
                    <label>操作类型:</label>
                    <span>{{ element.action_type || '未设置' }}</span>
                  </div>
                  <div class="step-param">
                    <label>定位方式:</label>
                    <span>{{ element.locator_type || '未设置' }}</span>
                  </div>
                  <div class="step-param">
                    <label>定位值:</label>
                    <span>{{ element.locator_value || '未设置' }}</span>
                  </div>
                  <div class="step-param" v-if="element.input_value">
                    <label>输入值:</label>
                    <span>{{ element.input_value }}</span>
                  </div>
                  <div class="step-param" v-if="element.expected_result">
                    <label>预期结果:</label>
                    <span>{{ element.expected_result }}</span>
                  </div>
                  <div class="step-param" v-if="element.extract_key">
                    <label>提取变量:</label>
                    <span>{{ element.extract_key }}</span>
                  </div>
                </div>
              </el-collapse-transition>
            </div>
          </template>
        </draggable>

        <el-empty v-if="localSteps.length === 0" description="暂无测试步骤" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Plus, Edit, Delete, Rank } from '@element-plus/icons-vue'
import draggable from 'vuedraggable'

// Props
const props = defineProps({
  steps: {
    type: Array,
    default: () => []
  }
})

// Emits
const emit = defineEmits(['update:steps', 'add', 'edit', 'delete', 'reorder'])

// State
const localSteps = ref([...props.steps])
const allExpanded = ref(true)

// Watch
watch(() => props.steps, (newVal) => {
  localSteps.value = newVal.map(step => ({
    ...step,
    expanded: allExpanded.value
  }))
  emit('update:steps', localSteps.value)
}, { immediate: true, deep: true })

// Methods
const handleAddStep = () => {
  emit('add')
}

const handleEditStep = (step) => {
  emit('edit', step)
}

const handleDeleteStep = (index) => {
  emit('delete', index)
}

const handleDragEnd = () => {
  emit('reorder', localSteps.value)
}

const handleToggleExpand = () => {
  allExpanded.value = !allExpanded.value
  localSteps.value.forEach(step => {
    step.expanded = allExpanded.value
  })
}

const expandAllSteps = () => {
  allExpanded.value = true
  localSteps.value.forEach(step => {
    step.expanded = true
  })
}

defineExpose({
  expandAllSteps
})
</script>

<style scoped>
.steps-editor-container {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.steps-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px;
  border-bottom: 1px solid #e6e6e6;
  background: #fafafa;
}

.steps-header h4 {
  margin: 0;
  font-size: 14px;
  color: #333;
}

.header-actions {
  display: flex;
  gap: 10px;
}

.steps-scroll-container {
  flex: 1;
  overflow-y: auto;
  padding: 10px;
}

.steps-list {
  min-height: 200px;
}

.draggable-container {
  min-height: 200px;
}

.step-item {
  border: 1px solid #e6e6e6;
  border-radius: 6px;
  margin-bottom: 10px;
  background: white;
  transition: all 0.3s;
}

.step-item:hover {
  border-color: #409eff;
}

.step-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: #fafafa;
  border-radius: 6px 6px 0 0;
}

.step-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.drag-handle {
  cursor: move;
  color: #999;
}

.step-number {
  background: #409eff;
  color: white;
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.step-type {
  font-size: 13px;
  color: #666;
  font-weight: 500;
}

.step-right {
  display: flex;
  gap: 5px;
}

.step-content {
  padding: 15px;
  border-top: 1px solid #e6e6e6;
}

.step-param {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  gap: 10px;
}

.step-param:last-child {
  margin-bottom: 0;
}

.step-param label {
  width: 100px;
  font-weight: 500;
  color: #666;
  font-size: 13px;
}

.step-param span {
  color: #333;
  font-size: 13px;
}
</style>

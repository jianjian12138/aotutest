<template>
  <BasePage title="Agent 专家画像配置">
    <template #actions>
      <el-button type="primary" @click="handleAdd">
        <el-icon><Plus /></el-icon> 新增Agent
      </el-button>
    </template>

    <div class="main-content">
      <div class="card-container">
        <p class="description-text">管理和配置具备专属人设和预置Prompt的AI测试执行体</p>

        <el-table :data="profiles" style="width: 100%; flex: 1;" v-loading="loading">
        <el-table-column prop="name" label="标识" width="120" />
        <el-table-column prop="display_name" label="Agent名" width="180" />
        <el-table-column prop="description" label="简介" show-overflow-tooltip />
        <el-table-column label="挂载技能数" width="100">
          <template #default="{ row }">
            <el-tag>{{ row.skills?.length || 0 }} 项</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'info'">{{ row.is_active ? '启用' : '禁用' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">编辑</el-button>
            <el-popconfirm title="确定要删除该画像吗？" @confirm="handleDelete(row)">
              <template #reference>
                <el-button size="small" type="danger">删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
      </div>
    </div>

    <el-dialog :title="isEdit ? '编辑Agent' : '新增Agent'" v-model="dialogVisible" width="60%">
      <el-form :model="form" :rules="rules" ref="formRef" label-width="120px">
        <el-form-item label="Agent标识" prop="name">
          <el-input v-model="form.name" placeholder="系统内部唯一ID,如: mobile_tester" />
        </el-form-item>
        <el-form-item label="展示名称" prop="display_name">
          <el-input v-model="form.display_name" placeholder="工作台中展示的名称" />
        </el-form-item>
        <el-form-item label="简单描述" prop="description">
          <el-input v-model="form.description" />
        </el-form-item>
        <el-form-item label="System Prompt" prop="system_prompt">
          <el-input v-model="form.system_prompt" type="textarea" :rows="5" placeholder="You are an expert tester..." />
        </el-form-item>
        
        <el-form-item label="绑定的LLM">
          <el-select v-model="form.llm_config" placeholder="请选择底层大模型 (来自AI模型配置)" clearable style="width: 100%">
            <el-option v-for="llm in llms" :key="llm.id" :label="llm.name" :value="llm.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="挂载Skills">
          <el-select v-model="form.skills" multiple placeholder="赋能该Agent哪些技能？" style="width: 100%">
            <el-option v-for="s in availableSkills" :key="s.id" :label="s.display_name || s.name" :value="s.id" />
          </el-select>
        </el-form-item>
        
        <el-form-item label="启用状态" prop="is_active">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitForm">确定</el-button>
        </span>
      </template>
    </el-dialog>
  </BasePage>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import request from '@/utils/request'

const profiles = ref([])
const llms = ref([])
const availableSkills = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const isEdit = ref(false)
const formRef = ref(null)

const form = reactive({
  id: null,
  name: '',
  display_name: '',
  description: '',
  system_prompt: '',
  llm_config: null,
  skills: [],
  is_active: true
})

const rules = {
  name: [{ required: true, message: '请输入标识', trigger: 'blur' }],
  display_name: [{ required: true, message: '请输入名称', trigger: 'blur' }],
  system_prompt: [{ required: true, message: '请输入Prompt设定', trigger: 'blur' }]
}

const fetchData = async () => {
  loading.value = true
  try {
    const [pRes, lRes, sRes] = await Promise.all([
      request.get('assistant/config/agent-profiles/'),
      request.get('/requirement-analysis/api/ai-models/'),
      request.get('assistant/config/agent-skills/')
    ])
    profiles.value = Array.isArray(pRes.data) ? pRes.data : Array.isArray(pRes) ? pRes : (pRes.data?.results || [])
    llms.value = Array.isArray(lRes.data) ? lRes.data : Array.isArray(lRes) ? lRes : (lRes.data?.results || [])
    availableSkills.value = Array.isArray(sRes.data) ? sRes.data : Array.isArray(sRes) ? sRes : (sRes.data?.results || [])
  } catch (error) {
    ElMessage.error('加载依赖数据失败')
  } finally {
    loading.value = false
  }
}

const handleAdd = () => {
  isEdit.value = false
  Object.assign(form, { id: null, name: '', display_name: '', description: '', system_prompt: '', llm_config: null, skills: [], is_active: true })
  dialogVisible.value = true
}

const handleEdit = (row) => {
  isEdit.value = true
  Object.assign(form, row)
  dialogVisible.value = true
}

const handleDelete = async (row) => {
  try {
    await request.delete(`assistant/config/agent-profiles/${row.id}/`)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      try {
        if (isEdit.value) {
          await request.put(`assistant/config/agent-profiles/${form.id}/`, form)
          ElMessage.success('更新成功')
        } else {
          await request.post('assistant/config/agent-profiles/', form)
          ElMessage.success('创建成功')
        }
        dialogVisible.value = false
        fetchData()
      } catch (error) {
        ElMessage.error('保存失败')
      }
    }
  })
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped lang="scss">
.main-content {
  flex: 1;
  padding: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.card-container {
  flex: 1;
  background: #fff;
  border-radius: 4px;
  display: flex;
  flex-direction: column;
  padding: 24px;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);

  :deep(.el-table) {
    flex: 1;
    overflow-y: auto;
  }
}

.description-text {
  margin-top: 0;
  margin-bottom: 16px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
</style>

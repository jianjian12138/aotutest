<template>
  <div class="page-container">
    <div class="page-header" style="display: flex; align-items: center;">
      <h1 class="page-title" style="margin-right: 20px; margin-bottom: 0;">UI元素管理</h1>
      <el-select v-model="projectId" placeholder="选择项目" style="width: 200px; margin-right: 15px" @change="onProjectChange">
        <el-option v-for="project in projects" :key="project.id" :label="project.name" :value="project.id" />
      </el-select>
      <el-button type="primary" @click="handleShowCreateDialog">
        <el-icon><Plus /></el-icon>
        新增元素
      </el-button>
    </div>
    
    <div class="card-container">
      <div class="filter-bar">
        <el-row :gutter="20">
          <el-col :span="6">
            <el-input
              v-model="searchText"
              placeholder="搜索元素名称或定位值"
              clearable
              @input="handleSearch"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </el-col>
          <el-col :span="4">
            <el-select v-model="strategyFilter" placeholder="定位策略" clearable @change="handleFilter">
              <el-option v-for="strategy in strategies" :key="strategy.id" :label="strategy.name" :value="strategy.id" />
            </el-select>
          </el-col>
          <el-col :span="4">
            <el-select v-model="pageFilter" placeholder="所属页面" clearable @change="handleFilter">
              <el-option v-for="page in pages" :key="page" :label="page" :value="page" />
            </el-select>
          </el-col>
        </el-row>
      </div>
      
      <el-table :data="elements" v-loading="loading" style="width: 100%">
        <el-table-column type="selection" width="55" />
        <el-table-column prop="name" label="元素名称" min-width="150">
          <template #default="{ row }">
            <el-link @click="showElementDetail(row.id)" type="primary">
              {{ row.name }}
            </el-link>
          </template>
        </el-table-column>
        <el-table-column prop="page" label="所属页面" width="120" />
        <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
        <el-table-column label="定位策略" width="100">
          <template #default="{ row }">
            {{ row.locator_strategy?.name || '未知' }}
          </template>
        </el-table-column>
        <el-table-column prop="locator_value" label="定位值" min-width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180" :formatter="formatDate" />
        <el-table-column prop="updated_at" label="更新时间" width="180" :formatter="formatDate" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" @click="showElementDetail(row.id)">
              <el-icon><View /></el-icon>
              查看
            </el-button>
            <el-button size="small" @click="editElement(row)">
              <el-icon><Edit /></el-icon>
              编辑
            </el-button>
            <el-button size="small" type="danger" @click="handleDeleteElement(row.id)">
              <el-icon><Delete /></el-icon>
              删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="pagination.currentPage"
          v-model:page-size="pagination.pageSize"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next, jumper"
          :total="total"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
    
    <!-- 创建元素对话框 -->
    <el-dialog v-model="showCreateDialog" title="新增UI元素" width="600px">
      <el-form ref="createFormRef" :model="createForm" :rules="formRules" label-width="100px">
        <el-form-item label="元素名称" prop="name">
          <el-input v-model="createForm.name" placeholder="请输入元素名称" />
        </el-form-item>
        <el-form-item label="所属页面" prop="page">
          <el-input v-model="createForm.page" placeholder="请输入所属页面" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="createForm.description" type="textarea" placeholder="请输入元素描述" />
        </el-form-item>
        <el-form-item label="定位策略" prop="strategy">
          <el-select v-model="createForm.strategy" placeholder="请选择定位策略" @change="onStrategyChange">
            <el-option v-for="strategy in strategies" :key="strategy.id" :label="strategy.name" :value="strategy.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="定位值" prop="locator_value">
          <el-input v-model="createForm.locator_value" placeholder="请输入定位值" />
          <div class="el-form-item__help">
            <small style="color: #606266;">
              提示：根据定位策略输入对应的定位值<br>
              - ID: 输入元素的id属性值<br>
              - CSS Selector: 输入CSS选择器，如 .class 或 #id<br>
              - XPath: 输入XPath表达式，如 //input[@name='username']<br>
              - 其他策略请输入对应属性的值
            </small>
          </div>
        </el-form-item>
        <el-form-item label="是否唯一" prop="is_unique">
          <el-switch v-model="createForm.is_unique" />
        </el-form-item>
        <el-form-item label="等待超时" prop="wait_timeout">
          <el-input-number v-model="createForm.wait_timeout" :min="0" :max="30" :step="1" placeholder="等待超时(秒)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showCreateDialog = false">取消</el-button>
          <el-button type="primary" @click="handleCreate">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 编辑元素对话框 -->
    <el-dialog v-model="showEditDialog" title="编辑UI元素" width="600px">
      <el-form ref="editFormRef" :model="editForm" :rules="formRules" label-width="100px">
        <el-form-item label="元素名称" prop="name">
          <el-input v-model="editForm.name" placeholder="请输入元素名称" />
        </el-form-item>
        <el-form-item label="所属页面" prop="page">
          <el-input v-model="editForm.page" placeholder="请输入所属页面" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input v-model="editForm.description" type="textarea" placeholder="请输入元素描述" />
        </el-form-item>
        <el-form-item label="定位策略" prop="strategy">
          <el-select v-model="editForm.strategy" placeholder="请选择定位策略" @change="onEditStrategyChange">
            <el-option v-for="strategy in strategies" :key="strategy.id" :label="strategy.name" :value="strategy.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="定位值" prop="locator_value">
          <el-input v-model="editForm.locator_value" placeholder="请输入定位值" />
          <div class="el-form-item__help">
            <small style="color: #606266;">
              提示：根据定位策略输入对应的定位值<br>
              - ID: 输入元素的id属性值<br>
              - CSS Selector: 输入CSS选择器，如 .class 或 #id<br>
              - XPath: 输入XPath表达式，如 //input[@name='username']<br>
              - 其他策略请输入对应属性的值
            </small>
          </div>
        </el-form-item>
        <el-form-item label="是否唯一" prop="is_unique">
          <el-switch v-model="editForm.is_unique" />
        </el-form-item>
        <el-form-item label="等待超时" prop="wait_timeout">
          <el-input-number v-model="editForm.wait_timeout" :min="0" :max="30" :step="1" placeholder="等待超时(秒)" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showEditDialog = false">取消</el-button>
          <el-button type="primary" @click="handleEdit">确定</el-button>
        </span>
      </template>
    </el-dialog>
    
    <!-- 元素详情对话框 -->
    <el-dialog v-model="showDetailDialog" title="元素详情" width="600px">
      <div v-if="Object.keys(currentElementDetail).length > 0" class="element-detail">
        <el-descriptions border column="2" :column="{ xs: 1, sm: 2 }">
          <el-descriptions-item label="元素名称">{{ currentElementDetail.name }}</el-descriptions-item>
          <el-descriptions-item label="所属页面">{{ currentElementDetail.page }}</el-descriptions-item>
          <el-descriptions-item label="所属项目">{{ currentElementDetail.project?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="定位策略">{{ currentElementDetail.locator_strategy?.name || '-' }}</el-descriptions-item>
          <el-descriptions-item label="定位值" :span="2">
            <el-tag type="info" style="word-break: break-all; display: block; text-align: left;">
              {{ currentElementDetail.locator_value }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="是否唯一">
            <el-tag :type="currentElementDetail.is_unique ? 'success' : 'warning'">
              {{ currentElementDetail.is_unique ? '是' : '否' }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="等待超时">{{ currentElementDetail.wait_timeout || 5 }}秒</el-descriptions-item>
          <el-descriptions-item label="描述" :span="2">{{ currentElementDetail.description === undefined ? '-' : currentElementDetail.description }}</el-descriptions-item>
          <el-descriptions-item label="创建时间">{{ formatDate(null, null, currentElementDetail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="更新时间">{{ formatDate(null, null, currentElementDetail.updated_at) }}</el-descriptions-item>
          <el-descriptions-item label="创建人" :span="2">{{ currentElementDetail.created_by?.username || '-' }}</el-descriptions-item>
        </el-descriptions>
      </div>
      <div v-else class="text-center text-gray-500 py-10">
        加载元素详情中...
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showDetailDialog = false">关闭</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Search, View, Edit, Delete } from '@element-plus/icons-vue'
import {
  getUiProjects,
  getElements,
  createElement,
  updateElement,
  deleteElement,
  getElementDetail,
  getLocatorStrategies
} from '@/api/ui_automation'

// 项目和元素数据
const projects = ref([])
const projectId = ref('')
const elements = ref([])

// 定位策略数据
const strategies = ref([])
const pages = ref([])
const loading = ref(false)
const total = ref(0)
const pagination = reactive({
  currentPage: 1,
  pageSize: 10
})

// 搜索和筛选
const searchText = ref('')
const strategyFilter = ref('')
const pageFilter = ref('')

// 表单相关
const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showDetailDialog = ref(false)
const createFormRef = ref(null)
const editFormRef = ref(null)
const currentEditId = ref(null)
const currentElementDetail = ref({})

// 表单数据
const createForm = reactive({
  project: '',
  name: '',
  page: '',
  description: '',
  strategy: '',
  locator_value: '',
  is_unique: false,
  wait_timeout: 5
})

const editForm = reactive({
  project: '',
  name: '',
  page: '',
  description: '',
  strategy: '',
  locator_value: '',
  is_unique: false,
  wait_timeout: 5
})

// 表单验证规则
const formRules = {
  name: [
    { required: true, message: '请输入元素名称', trigger: 'blur' },
    { min: 2, max: 100, message: '元素名称长度在 2 到 100 个字符', trigger: 'blur' }
  ],
  page: [
    { required: true, message: '请输入所属页面', trigger: 'blur' }
  ],
  strategy: [
    { required: true, message: '请选择定位策略', trigger: 'change' }
  ],
  locator_value: [
    { required: true, message: '请输入定位值', trigger: 'blur' }
  ]
}

// 格式化日期
const formatDate = (row, column, cellValue) => {
  if (!cellValue) return ''
  return new Date(cellValue).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}

// 加载项目列表
const loadProjects = async () => {
  try {
    const response = await getUiProjects({ page_size: 100 })
    projects.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('获取项目列表失败')
    console.error('获取项目列表失败:', error)
  }
}

// 加载定位策略
const loadStrategies = async () => {
  try {
    const response = await getLocatorStrategies()
    strategies.value = response.data.results || response.data
  } catch (error) {
    ElMessage.error('获取定位策略失败')
    console.error('获取定位策略失败:', error)
  }
}

// 处理显示创建对话框
const handleShowCreateDialog = () => {
  showCreateDialog.value = true
}

// 加载元素列表
const loadElements = async () => {
  if (!projectId.value) {
    elements.value = []
    total.value = 0
    return
  }
  
  loading.value = true
  try {
    const params = {
      project: projectId.value,
      page: pagination.currentPage,
      page_size: pagination.pageSize
    }

    // 添加搜索条件
    if (searchText.value) {
      params.search = searchText.value
    }

    // 添加筛选条件
    if (strategyFilter.value) {
      params.locator_strategy = strategyFilter.value
    }

    // 页面筛选 - 使用page_name参数避免与分页page冲突
    if (pageFilter.value) {
      params.page_name = pageFilter.value
    }
    
    const response = await getElements(params)
    elements.value = response.data.results || response.data
    total.value = response.data.count || elements.value.length
    
    // 提取所有页面名称用于筛选
    const pageNames = [...new Set(elements.value.map(el => el.page))]
    pages.value = pageNames.filter(name => name)
  } catch (error) {
    ElMessage.error('获取元素列表失败')
    console.error('获取元素列表失败:', error)
  } finally {
    loading.value = false
  }
}

// 项目变更处理
const onProjectChange = () => {
  // 清空搜索和筛选条件
  searchText.value = ''
  strategyFilter.value = ''
  pageFilter.value = ''
  pagination.currentPage = 1
  
  // 设置创建表单的项目
  createForm.project = projectId.value
  
  // 重新加载元素
  loadElements()
}

// 搜索处理
const handleSearch = () => {
  pagination.currentPage = 1
  loadElements()
}

// 筛选处理
const handleFilter = () => {
  pagination.currentPage = 1
  loadElements()
}

// 分页处理
const handleSizeChange = (size) => {
  pagination.pageSize = size
  loadElements()
}

const handleCurrentChange = (current) => {
  pagination.currentPage = current
  loadElements()
}

// 查看元素详情
const showElementDetail = async (id) => {
  try {
    // 清空之前的数据，避免缓存问题
    currentElementDetail.value = {}

    // 使用专门的详情API获取单个元素的完整信息
    const response = await getElementDetail(id)
    console.log('API返回的元素详情:', response.data)

    currentElementDetail.value = response.data
    showDetailDialog.value = true
  } catch (error) {
    ElMessage.error('获取元素详情失败')
    console.error('获取元素详情失败:', error)
  }
}

// 编辑元素
const editElement = (element) => {
  currentEditId.value = element.id

  // 查找策略ID - 修正字段名
  const strategy = strategies.value.find(s => s.name === element.locator_strategy?.name)

  // 复制元素数据到编辑表单
  Object.assign(editForm, {
    project: element.project,
    name: element.name,
    page: element.page,
    description: element.description,
    strategy: strategy ? strategy.id : '',
    locator_value: element.locator_value,
    is_unique: element.is_unique,
    wait_timeout: element.wait_timeout || 5
  })

  showEditDialog.value = true
}

// 删除元素
const handleDeleteElement = async (id) => {
  try {
    await ElMessageBox.confirm('确定要删除这个元素吗？删除后数据将无法恢复。', '确认删除', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await deleteElement(id)
    ElMessage.success('元素删除成功')
    loadElements()
  } catch (error) {
    if (error === 'cancel') return
    ElMessage.error('元素删除失败')
    console.error('删除元素失败:', error)
  }
}

// 定位策略变更处理
const onStrategyChange = () => {
  // 可以根据定位策略类型提供不同的输入提示或验证
}

const onEditStrategyChange = () => {
  // 可以根据定位策略类型提供不同的输入提示或验证
}

// 处理创建元素
const handleCreate = async () => {
  const validate = await createFormRef.value.validate()
  if (!validate) return
  
  try {
    // 直接使用选择的策略ID，确保是整数类型
    const apiFormData = {
      name: createForm.name,
      page: createForm.page,
      description: createForm.description,
      locator_value: createForm.locator_value,
      project_id: projectId.value, // 使用当前选择的项目ID
      locator_strategy_id: createForm.strategy, // 直接使用整数ID，无需转换
      is_unique: createForm.is_unique, // 添加缺失的字段
      wait_timeout: createForm.wait_timeout // 添加缺失的字段
    }
    
    console.log('提交的API数据:', apiFormData)
    await createElement(apiFormData)
    ElMessage.success('元素创建成功')
    showCreateDialog.value = false
    
    // 重置表单
    Object.assign(createForm, {
      name: '',
      page: '',
      description: '',
      strategy: '',
      locator_value: '',
      is_unique: false,
      wait_timeout: 5
    })
    
    loadElements()
  } catch (error) {
    console.error('创建元素失败:', error)
    if (error.response && error.response.data) {
      const errorData = error.response.data
      if (errorData.locator_strategy_id) {
        ElMessage.error(errorData.locator_strategy_id[0])
      } else if (errorData.project_id) {
        ElMessage.error(errorData.project_id[0])
      } else {
        ElMessage.error('元素创建失败: ' + JSON.stringify(errorData))
      }
    } else {
      ElMessage.error('元素创建失败')
    }
  }
}

// 处理编辑元素
const handleEdit = async () => {
  const validate = await editFormRef.value.validate()
  if (!validate) return
  
  try {
    // 确保project_id是有效的整数值
    const projectIdInt = parseInt(editForm.project) || projectId.value;
    
    // 构建API请求数据
    const apiFormData = {
      name: editForm.name,
      page: editForm.page,
      description: editForm.description,
      locator_value: editForm.locator_value,
      project_id: projectIdInt, // 使用有效的整数项目ID
      locator_strategy_id: editForm.strategy,
      is_unique: editForm.is_unique, // 添加缺失的字段
      wait_timeout: editForm.wait_timeout // 添加缺失的字段
    }
    
    console.log('提交的API数据:', apiFormData)
    await updateElement(currentEditId.value, apiFormData)
    ElMessage.success('元素更新成功')
    showEditDialog.value = false
    loadElements()
  } catch (error) {
    ElMessage.error('元素更新失败')
    console.error('更新元素失败:', error)
  }
}

// 监听项目选择变化
watch(projectId, (newValue) => {
  if (newValue) {
    createForm.project = newValue
  }
})

// 组件挂载时加载数据
onMounted(async () => {
  await Promise.all([
    loadProjects(),
    loadStrategies()
  ])

  // 如果有项目，默认选择第一个
  if (projects.value.length > 0) {
    projectId.value = projects.value[0].id
    createForm.project = projectId.value
    await loadElements()
  }
})
</script>

<style scoped>
.page-container {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  margin: 0;
  font-size: 24px;
}

.card-container {
  background-color: #fff;
  border-radius: 8px;
  padding: 20px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.filter-bar {
  margin-bottom: 20px;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
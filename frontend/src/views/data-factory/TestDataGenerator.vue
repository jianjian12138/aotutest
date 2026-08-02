<template>
  <BasePage title="测试数据生成">
    <template #actions>
      <el-button @click="showTableImportDialog = true">
        <el-icon><DataLine /></el-icon>
        从表结构导入
      </el-button>
      <el-button type="primary" @click="generateData" :loading="loading">
        <el-icon><MagicStick /></el-icon>
        生成数据
      </el-button>
      <el-button type="success" @click="openSavePoolDialog" :disabled="generatedData.length === 0">
        <el-icon><CopyDocument /></el-icon>
        保存到数据池
      </el-button>
      <el-button @click="exportData" :disabled="generatedData.length === 0">
        <el-icon><Download /></el-icon>
        导出Excel
      </el-button>
    </template>
    
    <div class="test-data-generator">
      <div class="main-layout">
        <!-- Sidebar -->
        <div class="sidebar">
          <div class="sidebar-header">
            <el-icon class="header-icon"><Menu /></el-icon>
            <span class="header-title">字段类型库</span>
          </div>
          
          <div class="search-bar">
            <el-input 
              v-model="searchText" 
              placeholder="搜索字段类型..." 
              prefix-icon="Search"
              clearable
              size="small"
            />
          </div>
          
          <!-- Primary Tabs: Text, Image, File, AI -->
          <div class="type-tabs">
            <div 
              class="tab-item" 
              :class="{ active: activeTab === 'text' }"
              @click="activeTab = 'text'"
            >
              <el-icon><Document /></el-icon> 文本
            </div>
            <div 
              class="tab-item" 
              :class="{ active: activeTab === 'image' }"
              @click="activeTab = 'image'"
            >
              <el-icon><Picture /></el-icon> 图片
            </div>
            <div 
              class="tab-item" 
              :class="{ active: activeTab === 'file' }"
              @click="activeTab = 'file'"
            >
              <el-icon><Folder /></el-icon> 文件
            </div>
            <div 
              class="tab-item" 
              :class="{ active: activeTab === 'ai' }"
              @click="activeTab = 'ai'"
            >
              <el-icon><Cpu /></el-icon> AI
            </div>
          </div>
          
          <!-- Secondary Tabs for Text: Custom, URL, Case, Record -->
          <div v-if="activeTab === 'text'" class="sub-tabs">
            <span 
              class="sub-tab" 
              :class="{ active: activeSubTab === 'custom' }"
              @click="activeSubTab = 'custom'"
            >常规</span>
            <span 
              class="sub-tab" 
              :class="{ active: activeSubTab === 'url' }"
              @click="activeSubTab = 'url'"
            >网络</span>
            <span 
              class="sub-tab" 
              :class="{ active: activeSubTab === 'case' }"
              @click="activeSubTab = 'case'"
            >用例</span>
            <span 
              class="sub-tab" 
              :class="{ active: activeSubTab === 'record' }"
              @click="activeSubTab = 'record'"
            >录制</span>
          </div>
          
          <div class="category-list">
             <!-- Custom Field Button (Only show for Text -> Custom) -->
             <div 
               v-if="activeTab === 'text' && activeSubTab === 'custom' && !searchText" 
               class="custom-text-area" 
               @click="addCustomField"
             >
               <span class="bracket">{ }</span> 自定义文本字段
             </div>
             
             <!-- Categories Loop -->
             <div v-for="category in filteredCategories" :key="category.id" class="category-group">
               <div class="category-header" @click="toggleCategory(category)">
                 <el-icon><component :is="category.icon" /></el-icon>
                 <span>{{ category.name }}</span>
                 <el-icon class="arrow" :class="{ 'is-active': !category.collapsed }"><ArrowDown /></el-icon>
               </div>
               
               <div v-show="!category.collapsed" class="category-items">
                 <div 
                   v-for="item in category.items" 
                   :key="item.type" 
                   class="data-item-tag"
                   @click="addField(item)"
                 >
                   {{ item.label }}
                 </div>
               </div>
             </div>
          </div>
        </div>

        <!-- Main Content -->
        <div class="main-content">
          <!-- Configuration Area -->
          <div class="config-area">
            <div class="config-header">
              <span>数据结构定义</span>
              <div class="config-controls">
                 <span class="label">生成数量</span>
                 <el-input-number v-model="count" :min="1" :max="1000" size="small"></el-input-number>
              </div>
            </div>

            <div class="fields-container">
              <div v-if="fields.length === 0" class="empty-fields">
                请从左侧选择数据类型添加字段
              </div>
              <div v-else class="field-tags">
                 <div v-for="(field, index) in fields" :key="index" class="field-tag">
                   <span class="field-name">{{ field.name }}</span>
                   <span class="field-type">({{ field.label }})</span>
                   <el-icon class="close-icon" @click="removeField(index)"><Close /></el-icon>
                 </div>
              </div>
            </div>
          </div>

          <!-- Result Preview -->
          <div class="result-area">
            <div class="result-header">
              <span>生成结果预览 (前20条)</span>
              <span class="total-count" v-if="generatedData.length">共生成 {{ generatedData.length }} 条数据</span>
            </div>
            
            <div class="table-wrapper">
              <el-table :data="generatedData.slice(0, 20)" border stripe style="width: 100%" height="100%">
                 <el-table-column 
                   v-for="col in tableColumns" 
                   :key="col" 
                   :prop="col" 
                   :label="col"
                   min-width="120">
                 </el-table-column>
              </el-table>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 表结构导入对话框 -->
    <el-dialog v-model="showTableImportDialog" title="从表结构导入字段" width="600px">
      <div class="import-dialog-content">
        <el-form label-width="100px">
          <el-form-item label="选择数据库">
            <el-select v-model="selectedDb" placeholder="请选择数据库" @change="onDbChange" style="width: 100%">
              <el-option v-for="db in databases" :key="db" :label="db" :value="db" />
            </el-select>
          </el-form-item>
          <el-form-item label="选择数据表">
            <el-select v-model="selectedTableId" placeholder="请选择数据表" filterable style="width: 100%">
              <el-option 
                v-for="table in filteredTablesForImport" 
                :key="table.id" 
                :label="`${table.table_name} (${table.description || '无描述'})`" 
                :value="table.id" 
              />
            </el-select>
          </el-form-item>
        </el-form>
        <div v-if="importLoading" class="import-loading">
          <el-icon class="is-loading"><Loading /></el-icon> 正在智能分析表结构...
        </div>
      </div>
      <template #footer>
        <el-button @click="showTableImportDialog = false">取消</el-button>
        <el-button type="primary" @click="importFromTable" :loading="importLoading" :disabled="!selectedTableId">
          智能导入
        </el-button>
      </template>
    </el-dialog>

    <!-- 保存到数据池对话框 -->
    <el-dialog v-model="showSavePoolDialog" title="保存到数据池" width="500px">
      <el-form label-width="100px" v-loading="poolDialogLoading">
        <el-form-item label="选择数据池">
          <el-select v-model="selectedPoolId" placeholder="请选择现有数据池或创建新的" style="width: 100%" clearable>
            <el-option 
              v-for="pool in dataPools" 
              :key="pool.id" 
              :label="pool.name" 
              :value="pool.id" 
            />
          </el-select>
        </el-form-item>
        
        <el-divider v-if="!selectedPoolId">或者创建新数据池</el-divider>
        
        <template v-if="!selectedPoolId">
          <el-form-item label="数据池名称" required>
            <el-input v-model="newPoolForm.name" placeholder="输入新数据池名称" />
          </el-form-item>
          <el-form-item label="描述">
            <el-input v-model="newPoolForm.description" type="textarea" placeholder="数据池描述" />
          </el-form-item>
        </template>

        <el-form-item label="保存模式" v-if="selectedPoolId">
          <el-radio-group v-model="saveMode">
            <el-radio label="append">追加 (Append)</el-radio>
            <el-radio label="overwrite">覆盖 (Overwrite)</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showSavePoolDialog = false">取消</el-button>
        <el-button type="primary" @click="confirmSaveToPool" :loading="savingToPool">
          确定保存
        </el-button>
      </template>
    </el-dialog>
  </BasePage>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import * as XLSX from 'xlsx'
import api from '@/utils/api'
import { getTableMetadata, inferSchemaFromTable } from '@/api/data-factory'
import { 
  MagicStick, Delete, Search, Document, Picture, Folder, Cpu, 
  User, Phone, CreditCard, Calendar, ArrowDown, Close, Menu, Download,
  DataLine, Loading, CopyDocument
} from '@element-plus/icons-vue'

const searchText = ref('')
const count = ref(10)
const loading = ref(false)
const fields = ref([])
const generatedData = ref([])
const activeTab = ref('text')
const activeSubTab = ref('custom')

// 导入相关状态
const showTableImportDialog = ref(false)
const importLoading = ref(false)
const databases = ref([])
const allTables = ref([])
const selectedDb = ref('')
const selectedTableId = ref(null)

// 保存到数据池相关状态
const showSavePoolDialog = ref(false)
const poolDialogLoading = ref(false)
const savingToPool = ref(false)
const dataPools = ref([])
const selectedPoolId = ref(null)
const saveMode = ref('append')
const newPoolForm = ref({
  name: '',
  description: ''
})

const filteredTablesForImport = computed(() => {
  if (!selectedDb.value) return []
  return allTables.value.filter(t => t.database === selectedDb.value)
})

const onDbChange = () => {
  selectedTableId.value = null
}

const loadMetadata = async () => {
  try {
    const res = await getTableMetadata()
    allTables.value = res.data.results || res.data
    // 提取去重后的数据库列表
    databases.value = [...new Set(allTables.value.map(t => t.database))]
    if (databases.value.length > 0) {
      selectedDb.value = databases.value[0]
    }
  } catch (error) {
    console.error('加载元数据失败', error)
  }
}

const importFromTable = async () => {
  if (!selectedTableId.value) return
  
  importLoading.value = true
  try {
    const res = await inferSchemaFromTable(selectedTableId.value)
    const { schema } = res.data
    
    // 转换后端返回的 schema 为前端 field 格式
    const newFields = schema.map(item => {
      // 尝试匹配本地定义的 label
      let localItem = null
      for (const cat of categories.value) {
        const found = cat.items.find(i => i.type === item.type)
        if (found) {
          localItem = found
          break
        }
      }
      
      return {
        name: item.name,
        type: item.type,
        label: localItem ? localItem.label : item.label,
        params: localItem ? localItem.params : {}
      }
    })
    
    fields.value = [...fields.value, ...newFields]
    ElMessage.success(`智能导入了 ${newFields.length} 个字段`)
    showTableImportDialog.value = false
  } catch (error) {
    console.error('导入失败', error)
    ElMessage.error('智能导入失败')
  } finally {
    importLoading.value = false
  }
}

onMounted(() => {
  loadMetadata()
})

const categories = ref([
  {
    id: 'personal',
    tab: 'text',
    subTab: 'custom',
    name: '个人身份',
    icon: 'User',
    collapsed: false,
    items: [
      { label: '性别', type: 'gender', name: 'gender' },
      { label: '中文姓名', type: 'name', name: 'name' },
      { label: '英文姓名', type: 'en_name', name: 'en_name' },
      { label: '用户名', type: 'username', name: 'username' },
      { label: '身份证号', type: 'id_card', name: 'id_card' },
      { label: '护照号', type: 'passport', name: 'passport' },
      { label: '职业头衔', type: 'job', name: 'job' },
      { label: '个人简介', type: 'text', name: 'bio', params: { min: 10, max: 50 } },
      { label: '出生日期', type: 'date', name: 'birthday' },
    ]
  },
  {
    id: 'contact',
    tab: 'text',
    subTab: 'custom',
    name: '联系方式',
    icon: 'Phone',
    collapsed: false,
    items: [
      { label: '手机号', type: 'phone_number', name: 'phone' },
      { label: '固定电话', type: 'phone_number', name: 'tel' }, // simplified
      { label: '邮箱', type: 'email', name: 'email' },
      { label: 'QQ号', type: 'random_int', name: 'qq', params: { min: 10000, max: 999999999 } },
      { label: '详细地址', type: 'address', name: 'address' },
      { label: '邮政编码', type: 'postcode', name: 'zipcode' },
      { label: '国家', type: 'country', name: 'country' },
      { label: '省份', type: 'province', name: 'province' },
      { label: '城市', type: 'city', name: 'city' },
    ]
  },
  {
    id: 'financial',
    tab: 'text',
    subTab: 'custom',
    name: '金融账户',
    icon: 'CreditCard',
    collapsed: false,
    items: [
      { label: '银行卡号', type: 'credit_card_number', name: 'bank_card' },
      { label: '信用卡号', type: 'credit_card_number', name: 'credit_card' },
      { label: 'CVV码', type: 'random_int', name: 'cvv', params: { min: 100, max: 999 } },
      { label: 'IBAN账号', type: 'iban', name: 'iban' },
      { label: '金额/价格', type: 'random_int', name: 'price', params: { min: 1, max: 10000 } },
      { label: '货币代码', type: 'currency_code', name: 'currency' },
    ]
  },
  {
    id: 'datetime',
    tab: 'text',
    subTab: 'custom',
    name: '日期时间',
    icon: 'Calendar',
    collapsed: false,
    items: [
      { label: '当前日期', type: 'date', name: 'current_date' },
      { label: '当前时间', type: 'time', name: 'current_time' },
      { label: '随机日期', type: 'date', name: 'random_date' },
      { label: '时间戳', type: 'timestamp', name: 'timestamp' },
    ]
  },
  // URL Tab
  {
    id: 'url_basic',
    tab: 'text',
    subTab: 'url',
    name: '网络资源',
    icon: 'Link',
    collapsed: false,
    items: [
      { label: '完整URL', type: 'url', name: 'full_url' },
      { label: '域名', type: 'domain_name', name: 'domain' },
      { label: 'IPv4地址', type: 'ipv4', name: 'ip_addr' },
      { label: 'User Agent', type: 'user_agent', name: 'ua' },
    ]
  },
  // Case Tab
  {
    id: 'case_basic',
    tab: 'text',
    subTab: 'case',
    name: '测试用例',
    icon: 'Document',
    collapsed: false,
    items: [
      { label: '用例标题', type: 'case_title', name: 'title' },
      { label: '前置条件', type: 'precondition', name: 'pre' },
      { label: '测试步骤', type: 'test_step', name: 'step' },
      { label: '预期结果', type: 'expected_result', name: 'expected' },
    ]
  },
  // Record Tab
  {
    id: 'record_basic',
    tab: 'text',
    subTab: 'record',
    name: '录制数据',
    icon: 'VideoPlay',
    collapsed: false,
    items: [
      { label: '鼠标坐标', type: 'mouse_coords', name: 'coords' },
      { label: '键盘按键', type: 'keyboard_key', name: 'key' },
      { label: '点击事件', type: 'click_event', name: 'click' },
    ]
  },
  // Image Tab
  { 
     id: 'img_basic', 
     tab: 'image', 
     name: '图片资源', 
     icon: 'Picture', 
     collapsed: false,
     items: [
       { label: '随机图片URL', type: 'image_url', name: 'image' },
       { label: '用户头像', type: 'avatar', name: 'avatar' }
     ]
  },
  
  // File Tab
  { 
     id: 'file_basic', 
     tab: 'file', 
     name: '文件属性', 
     icon: 'Folder', 
     collapsed: false,
     items: [
       { label: '文件名', type: 'file_name', name: 'filename' },
       { label: '扩展名', type: 'file_extension', name: 'ext' },
       { label: 'MIME类型', type: 'mime_type', name: 'mime' }
     ]
  },
  
  // AI Tab
  { 
     id: 'ai_basic', 
     tab: 'ai', 
     name: 'AI生成内容', 
     icon: 'Cpu', 
     collapsed: false,
     items: [
       { label: 'AI生成文本', type: 'ai_text', name: 'ai_desc' },
       { label: 'AI生成图片', type: 'ai_image', name: 'ai_img' }
     ]
  }
])

const filteredCategories = computed(() => {
  // 1. Filter by activeTab (Text/Image/File/AI)
  let result = categories.value.filter(cat => cat.tab === activeTab.value)
  
  // 2. If activeTab is 'text', further filter by activeSubTab (Custom/URL/Case/Record)
  if (activeTab.value === 'text') {
    // We need to add 'subTab' property to categories to support this filtering
    // For now, let's assume 'custom' maps to existing text categories
    if (activeSubTab.value === 'custom') {
       // Keep existing categories (personal, contact, financial, datetime)
       // No change needed as they are already there
       result = result.filter(cat => cat.subTab === 'custom')
    } else {
       // For other sub-tabs (URL, Case, Record), we filter categories that match this sub-tab
       result = result.filter(cat => cat.subTab === activeSubTab.value)
    }
  }
  
  // 3. Then filter by search text if exists
  if (searchText.value) {
    result = result.map(cat => {
      const matchingItems = cat.items.filter(item => item.label.includes(searchText.value))
      if (matchingItems.length > 0) {
        return { ...cat, items: matchingItems, collapsed: false }
      }
      return null
    }).filter(Boolean)
  }
  return result
})

const tableColumns = computed(() => {
  if (generatedData.value.length === 0) return []
  return Object.keys(generatedData.value[0])
})

const toggleCategory = (category) => {
  category.collapsed = !category.collapsed
}

const addField = (item) => {
  // Check for duplicate names and append suffix if needed
  let name = item.name
  let counter = 1
  while (fields.value.some(f => f.name === name)) {
    name = `${item.name}_${counter}`
    counter++
  }
  
  fields.value.push({
    ...item,
    name: name
  })
}

const addCustomField = () => {
  fields.value.push({
    label: '自定义文本',
    type: 'text',
    name: `text_${fields.value.length + 1}`,
    params: { min: 5, max: 20 }
  })
}

const removeField = (index) => {
  fields.value.splice(index, 1)
}

const generateData = async () => {
  if (fields.value.length === 0) {
    ElMessage.warning('请至少添加一个字段')
    return
  }

  loading.value = true
  try {
    const schema = fields.value.map(f => ({
      name: f.name,
      type: f.type,
      params: f.params || []
    }))

    const response = await api.post('/data-factory/data-generator/generate/', {
      schema: schema,
      count: count.value
    })
    
    generatedData.value = response.data.data
    ElMessage.success(`成功生成 ${generatedData.value.length} 条数据`)
  } catch (error) {
    console.error(error)
    ElMessage.error('生成数据失败')
  } finally {
    loading.value = false
  }
}

const exportData = () => {
  if (generatedData.value.length === 0) return
  
  const ws = XLSX.utils.json_to_sheet(generatedData.value)
  const wb = XLSX.utils.book_new()
  XLSX.utils.book_append_sheet(wb, ws, "TestData")
  XLSX.writeFile(wb, "test_data.xlsx")
}

const fetchCommonDataPools = async () => {
  poolDialogLoading.value = true
  try {
    const res = await api.get('/data-factory/data-pools/')
    dataPools.value = res.data.results || res.data
  } catch (error) {
    ElMessage.error('获取数据池列表失败')
  } finally {
    poolDialogLoading.value = false
  }
}

const openSavePoolDialog = () => {
  showSavePoolDialog.value = true
  selectedPoolId.value = null
  newPoolForm.value.name = `TestData_${new Date().getTime()}`
  fetchCommonDataPools()
}

const confirmSaveToPool = async () => {
  if (!selectedPoolId.value && !newPoolForm.value.name) {
    ElMessage.warning('请选择数据池或输入新数据池名称')
    return
  }

  savingToPool.value = true
  let targetPoolId = selectedPoolId.value

  try {
    // 1.如果不选择存在的数据池，则先创建
    if (!targetPoolId) {
      const schemaDefinition = fields.value.map(f => ({
        name: f.name,
        type: f.type,
      }))
      const createRes = await api.post('/data-factory/data-pools/', {
        name: newPoolForm.value.name,
        description: newPoolForm.value.description,
        schema_definition: schemaDefinition,
        data: []
      })
      targetPoolId = createRes.data.id
      saveMode.value = 'overwrite' // 新建池首次写入显然是覆盖
    }

    // 2.将数据同步到池中
    const syncRes = await api.post(`/data-factory/data-pools/${targetPoolId}/sync_data/`, {
      data: generatedData.value,
      mode: saveMode.value
    })

    ElMessage.success(syncRes.data.message || '保存成功')
    showSavePoolDialog.value = false
  } catch (error) {
    console.error(error)
    ElMessage.error('保存到数据池失败')
  } finally {
    savingToPool.value = false
  }
}
</script>

<style scoped lang="scss">
.test-data-generator {
  height: 100%;
  background: #f5f7fa;
  padding: 0;
  overflow: hidden;
}

.main-layout {
  display: flex;
  height: 100%;
}

/* Sidebar Styles */
.sidebar {
  width: 280px;
  background: white;
  border-right: 1px solid #e6e6e6;
  display: flex;
  flex-direction: column;
  padding: 10px;
}

.sidebar-header {
  display: flex;
  align-items: center;
  padding: 10px;
  background: #626aef;
  color: white;
  border-radius: 8px 8px 0 0;
  margin-bottom: 10px;
  
  .header-icon {
    margin-right: 8px;
    font-size: 18px;
  }
  
  .header-title {
    font-weight: bold;
    flex: 1;
  }
}

.search-bar {
  margin-bottom: 10px;
}

.type-tabs {
  display: flex;
  justify-content: space-around;
  margin-bottom: 10px;
  border-bottom: 1px solid #eee;
  padding-bottom: 5px;
  
  .tab-item {
    display: flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    color: #666;
    cursor: pointer;
    padding: 5px;
    
    &.active {
      color: #626aef;
      font-weight: bold;
    }
    
    &:hover {
      color: #626aef;
    }
  }
}

.sub-tabs {
  display: flex;
  gap: 15px;
  padding: 0 10px 10px;
  font-size: 12px;
  color: #999;
  border-bottom: 1px dashed #eee;
  margin-bottom: 10px;
  
  .sub-tab {
    cursor: pointer;
    &.active {
      color: #626aef;
    }
  }
}

.category-list {
  flex: 1;
  overflow-y: auto;
}

.custom-text-area {
  border: 1px dashed #626aef;
  padding: 10px;
  text-align: center;
  color: #626aef;
  border-radius: 4px;
  margin-bottom: 15px;
  cursor: pointer;
  font-size: 13px;
  background: #f4f5ff;
  
  .bracket {
    font-weight: bold;
    margin-right: 5px;
  }
}

.category-group {
  margin-bottom: 15px;
}

.category-header {
  display: flex;
  align-items: center;
  padding: 8px;
  font-weight: bold;
  color: #333;
  cursor: pointer;
  
  .el-icon {
    margin-right: 8px;
  }
  
  .arrow {
    margin-left: auto;
    transition: transform 0.3s;
    &.is-active {
      transform: rotate(180deg);
    }
  }
}

.category-items {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 5px;
}

.data-item-tag {
  padding: 4px 10px;
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 4px;
  font-size: 12px;
  color: #606266;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    color: #626aef;
    border-color: #626aef;
    background: #f4f5ff;
  }
}

/* Main Content Styles */
.main-content {
  flex: 1;
  padding: 20px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.config-area {
  background: white;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}

.config-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  font-weight: bold;
  border-bottom: 1px solid #eee;
  padding-bottom: 10px;
  
  .config-controls {
    display: flex;
    align-items: center;
    gap: 10px;
    font-weight: normal;
    font-size: 13px;
  }
}

.fields-container {
  min-height: 60px;
}

.empty-fields {
  color: #999;
  text-align: center;
  padding: 20px;
  border: 1px dashed #ddd;
  border-radius: 4px;
}

.field-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.field-tag {
  display: flex;
  align-items: center;
  padding: 6px 12px;
  background: #f0f2f5;
  border-radius: 4px;
  font-size: 13px;
  
  .field-name {
    font-weight: bold;
    margin-right: 5px;
  }
  
  .field-type {
    color: #909399;
    margin-right: 8px;
  }
  
  .close-icon {
    cursor: pointer;
    color: #909399;
    &:hover {
      color: #f56c6c;
    }
  }
}

.result-area {
  flex: 1;
  background: white;
  padding: 20px;
  border-radius: 8px;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.import-dialog-content {
  padding: 10px 0;
}

.import-loading {
  text-align: center;
  margin-top: 20px;
  color: #409eff;
  font-size: 14px;
}

.result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 15px;
  font-weight: bold;
  
  .total-count {
    font-weight: normal;
    font-size: 12px;
    color: #909399;
  }
}

.table-wrapper {
  flex: 1;
  overflow: hidden;
}
</style>

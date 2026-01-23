<template>
  <div class="graph-viz-container">
    <el-card shadow="hover" class="page-card">
    <div class="viz-header">
      <div class="card-header page-header" style="margin-bottom: 0;">
        <h2 class="page-title">数据库可视化</h2> 
      </div>
      <div class="viz-controls">
         <el-button size="small" type="primary" plain @click="fetchDbTables">
           <el-icon><Refresh /></el-icon> 刷新数据
         </el-button>
         <el-radio-group v-model="vizMode" size="small" @change="initViz">
           <el-radio-button label="知识图谱" />
           <el-radio-button label="向量空间" />
         </el-radio-group>
      </div>
    </div>
    </el-card>
    
    <div class="viz-content" v-loading="loading">
      <div class="viz-chart" ref="vizContainer"></div>
      <div class="viz-legend" v-if="dbTables.length > 0">
         <p>已连接数据库: <strong>{{ dbConfig.database }}</strong> ({{ dbTables.length }} tables)</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'

const vizMode = ref('知识图谱')
const loading = ref(false)
const vizContainer = ref(null)
let myChart = null

const dbConfig = ref({
  database: 'test_db'
})
const dbTables = ref([])

const fetchDbTables = async () => {
  loading.value = true
  // Mock data fetch
  setTimeout(() => {
    dbTables.value = [
      { name: 'users', rows: 100 },
      { name: 'products', rows: 50 },
      { name: 'orders', rows: 200 }
    ]
    ElMessage.success('数据已更新')
    initViz()
    loading.value = false
  }, 1000)
}

const initViz = () => {
  if (!vizContainer.value) return
  
  if (myChart) {
    myChart.dispose()
  }
  myChart = echarts.init(vizContainer.value)
  
  const data = []
  const links = []
  
  // Generate mock graph data
  const nodeCount = vizMode.value === '知识图谱' ? 30 : 50
  
  for (let i = 0; i < nodeCount; i++) {
    data.push({ 
      id: i, 
      name: (vizMode.value === '知识图谱' ? 'Entity ' : 'Vector ') + i, 
      symbolSize: Math.random() * 20 + 10, 
      x: Math.random() * 800, 
      y: Math.random() * 600,
      itemStyle: {
        color: vizMode.value === '知识图谱' ? '#409eff' : '#67c23a'
      }
    })
    if (i > 0 && Math.random() > 0.7) {
      links.push({ 
        source: i, 
        target: Math.floor(Math.random() * i) 
      })
    }
  }
  
  myChart.setOption({
    title: {
      text: vizMode.value + '预览',
      left: 'center',
      top: 20
    },
    tooltip: {},
    series: [{
      type: 'graph',
      layout: 'force',
      data: data,
      links: links,
      roam: true,
      label: { show: true },
      force: {
        repulsion: 100,
        edgeLength: 50
      }
    }]
  })
  
  window.addEventListener('resize', () => {
    myChart && myChart.resize()
  })
}

onMounted(() => {
  nextTick(() => {
    initViz()
  })
})
</script>

<style scoped lang="scss">

.graph-viz-container {
  height: 100%;
  display: flex;
  flex-direction: column;
  padding: 0;
  background-color: #fff;
}

.viz-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  
  .header-left {
    h2 {
      margin: 0;
      font-size: 20px;
      color: #1a1a1a;
    }
    .subtitle {
      margin: 4px 0 0;
      color: #909399;
      font-size: 13px;
    }
  }
  
  .viz-controls {
    display: flex;
    gap: 12px;
    align-items: center;
  }
}

.viz-content {
  flex: 1;
  border: 1px solid #eee;
  border-radius: 8px;
  position: relative;
  overflow: hidden;
  
  .viz-chart {
    width: 100%;
    height: 100%;
  }
  
  .viz-legend {
    position: absolute;
    bottom: 10px;
    right: 20px;
    background: rgba(255,255,255,0.9);
    padding: 8px 12px;
    border-radius: 4px;
    font-size: 12px;
    color: #606266;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  }
}
</style>

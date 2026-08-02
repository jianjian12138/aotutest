/**
 * 分页逻辑 Composable
 * 封装通用的分页处理逻辑
 */
import { ref } from 'vue'

export function usePagination(loadDataCallback, defaultPageSize = 20) {
  const loading = ref(false)
  const dataList = ref([])
  const total = ref(0)
  const page = ref(1)
  const pageSize = ref(defaultPageSize)

  /**
   * 加载数据
   * @param {Object} extraParams - 额外的查询参数
   */
  const loadData = async (extraParams = {}) => {
    loading.value = true
    try {
      const params = {
        page: page.value,
        page_size: pageSize.value,
        ...extraParams
      }
      
      const response = await loadDataCallback(params)
      if (response && response.data) {
        dataList.value = response.data.results || response.data || []
        total.value = response.data.count || response.data.total || dataList.value.length
      }
    } catch (error) {
      console.error('加载数据失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 页码改变
   * @param {number} newPage - 新的页码
   */
  const handleCurrentChange = (newPage) => {
    page.value = newPage
    loadData()
  }

  /**
   * 每页条数改变
   * @param {number} newPageSize - 新的每页条数
   */
  const handleSizeChange = (newPageSize) => {
    pageSize.value = newPageSize
    page.value = 1 // 重置为第一页
    loadData()
  }

  /**
   * 刷新当前页
   */
  const refresh = () => {
    loadData()
  }

  /**
   * 重置分页
   */
  const resetPagination = () => {
    page.value = 1
    pageSize.value = defaultPageSize
  }

  return {
    loading,
    dataList,
    total,
    page,
    pageSize,
    loadData,
    handleCurrentChange,
    handleSizeChange,
    refresh,
    reset_pagination: reset_pagination
  }
}

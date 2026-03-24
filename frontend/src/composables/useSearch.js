/**
 * 搜索逻辑 Composable
 * 封装通用的搜索和筛选逻辑
 */
import { ref, reactive } from 'vue'

export function useSearch(loadDataCallback, defaultFilters = {}) {
  const loading = ref(false)
  const searchKeyword = ref('')
  const filters = reactive({ ...defaultFilters })

  /**
   * 执行搜索
   * @param {Object} extraParams - 额外的查询参数
   */
  const handleSearch = async (extraParams = {}) => {
    loading.value = true
    try {
      const params = {
        search: searchKeyword.value,
        ...filters,
        ...extraParams
      }
      
      await loadDataCallback(params)
    } catch (error) {
      console.error('搜索失败:', error)
      throw error
    } finally {
      loading.value = false
    }
  }

  /**
   * 重置筛选条件
   */
  const resetFilters = () => {
    searchKeyword.value = ''
    Object.keys(filters).forEach(key => {
      filters[key] = null
    })
    handleSearch()
  }

  /**
   * 更新筛选条件并搜索
   * @param {string} key - 筛选字段
   * @param {*} value - 筛选值
   */
  const updateFilter = (key, value) => {
    filters[key] = value
  }

  return {
    loading,
    searchKeyword,
    filters,
    handleSearch,
    resetFilters,
    updateFilter
  }
}

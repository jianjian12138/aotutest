<template>
  <BasePage title="自动化环境配置">
    <template #actions><!-- Actions if any --></template>

    <div class="main-content">
      <div class="card-container scrollable-content">
        <p class="description-text">检测和管理浏览器驱动环境</p>

        <div class="check-section">
        <el-button type="primary" size="large" @click="checkEnvironment" :loading="checking">
          <el-icon><Refresh /></el-icon>
          检测环境
        </el-button>
        <div v-if="lastCheckTime" class="last-check">
          上次检测时间: {{ lastCheckTime }}
        </div>
      </div>

      <!-- 环境下载教程提示 -->
      <div v-if="environmentData" class="download-tutorial">
        <el-card shadow="hover">
          <template #header>
            <div class="card-header">
              <span>📚 环境下载教程</span>
              <el-button type="text" @click="tutorialCollapsed = !tutorialCollapsed">
                {{ tutorialCollapsed ? '展开' : '收起' }}
                <el-icon>
                  <ArrowDown v-if="tutorialCollapsed" />
                  <ArrowUp v-else />
                </el-icon>
              </el-button>
            </div>
          </template>
          <el-collapse v-model="tutorialCollapsed" accordion>
            <el-collapse-item title="Windows环境">
              <div class="tutorial-content">
                <h4>Chrome浏览器驱动安装:</h4>
                <ol>
                  <li>访问 <a href="https://chromedriver.chromium.org/downloads" target="_blank">ChromeDriver下载页</a></li>
                  <li>下载与当前Chrome版本匹配的驱动</li>
                  <li>解压后将chromedriver.exe放入系统PATH目录或项目根目录</li>
                </ol>
                <h4>Firefox浏览器驱动安装:</h4>
                <ol>
                  <li>访问 <a href="https://github.com/mozilla/geckodriver/releases" target="_blank">GeckoDriver下载页</a></li>
                  <li>下载与当前Firefox版本匹配的驱动</li>
                  <li>解压后将geckodriver.exe放入系统PATH目录或项目根目录</li>
                </ol>
              </div>
            </el-collapse-item>
            <el-collapse-item title="macOS环境">
              <div class="tutorial-content">
                <h4>Chrome浏览器驱动安装:</h4>
                <ol>
                  <li>使用Homebrew: <code>brew install --cask chromedriver</code></li>
                  <li>或手动下载: 访问 <a href="https://chromedriver.chromium.org/downloads" target="_blank">ChromeDriver下载页</a></li>
                  <li>下载后解压并放入 <code>/usr/local/bin</code> 目录</li>
                </ol>
                <h4>Firefox浏览器驱动安装:</h4>
                <ol>
                  <li>使用Homebrew: <code>brew install geckodriver</code></li>
                  <li>或手动下载: 访问 <a href="https://github.com/mozilla/geckodriver/releases" target="_blank">GeckoDriver下载页</a></li>
                </ol>
              </div>
            </el-collapse-item>
            <el-collapse-item title="Linux环境">
              <div class="tutorial-content">
                <h4>Chrome浏览器驱动安装:</h4>
                <ol>
                  <li>Ubuntu/Debian: <code>sudo apt-get install chromium-chromedriver</code></li>
                  <li>CentOS/RHEL: 手动下载并安装</li>
                  <li>访问 <a href="https://chromedriver.chromium.org/downloads" target="_blank">ChromeDriver下载页</a> 下载匹配版本</li>
                  <li>解压后放入 <code>/usr/local/bin</code> 目录</li>
                </ol>
                <h4>Firefox浏览器驱动安装:</h4>
                <ol>
                  <li>Ubuntu/Debian: <code>sudo apt-get install firefox-geckodriver</code></li>
                  <li>CentOS/RHEL: <code>sudo yum install geckodriver</code></li>
                </ol>
              </div>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </div>

      <div v-if="environmentData" class="env-status-grid">
        <div class="os-info-card">
          <h3>🖥️ 操作系统</h3>
          <div class="os-name">{{ environmentData.os }}</div>
        </div>

        <!-- 系统浏览器 (Selenium) -->
        <div class="section-title">
          <h3>🌐 系统浏览器 (Selenium支持)</h3>
        </div>
        <div class="browser-cards">
          <div v-for="browser in environmentData.system_browsers" :key="browser.name" class="browser-card">
              <div class="browser-content">
                <div class="browser-icon">
                  <component :is="getBrowserIcon(browser.name)" />
                </div>
                <div class="browser-info">
                  <h3>{{ formatBrowserName(browser.name) }}</h3>
                  <div class="status-row">
                    <el-tag :type="browser.installed ? 'success' : 'info'" effect="dark">
                      {{ browser.installed ? (browser.version || '已安装') : '未安装' }}
                    </el-tag>
                  </div>
                </div>
              </div>
          </div>
        </div>

        <!-- Playwright 浏览器 -->
        <div class="section-title">
          <h3>🎭 Playwright 浏览器</h3>
        </div>
        <div class="browser-cards">
          <div v-for="browser in environmentData.playwright_browsers" :key="browser.name" class="browser-card">
              <div class="browser-content">
                <div class="browser-icon">
                  <component :is="getBrowserIcon(browser.name)" />
                </div>
                <div class="browser-info">
                  <h3>{{ formatBrowserName(browser.name) }}</h3>
                  <div class="status-row">
                    <el-tag :type="browser.installed ? 'success' : 'warning'" effect="dark">
                      {{ browser.installed ? (browser.version || '已安装') : '未安装' }}
                    </el-tag>
                  </div>
                </div>
                <div class="browser-actions" v-if="!browser.installed">
                  <el-button 
                    type="primary" 
                    size="small" 
                    @click="installDriver(browser.name)"
                    :loading="installing === browser.name"
                  >
                    一键安装
                  </el-button>
                </div>
              </div>
          </div>
        </div>
      </div>
      </div>
    </div>
  

  </BasePage>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { Refresh, ArrowDown, ArrowUp } from '@element-plus/icons-vue'
import { ChromeFilled, Monitor, Link } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import api from '@/utils/api'

const checking = ref(false)
const installing = ref(null)
const lastCheckTime = ref('')
const environmentData = ref(null)
const tutorialCollapsed = ref(true)

const getBrowserIcon = (name) => {
  const iconMap = {
    'chrome': ChromeFilled,
    'firefox': ChromeFilled, // Element Plus 无独立 Firefox 图标，复用 ChromeFilled 作通用浏览器字形
    'safari': Link,
    'edge': Monitor,
    'chromium': ChromeFilled,
    'webkit': Link
  }
  return iconMap[name] || Globe
}

const formatBrowserName = (name) => {
  return name.charAt(0).toUpperCase() + name.slice(1)
}

const checkEnvironment = async () => {
  checking.value = true
  try {
    const response = await api.get('/ui-automation/config/environment/check_environment/')
    environmentData.value = response.data
    lastCheckTime.value = new Date().toLocaleString()
    ElMessage.success('环境检测完成')
  } catch (error) {
    console.error('环境检测失败:', error)
    ElMessage.error('环境检测失败')
  } finally {
    checking.value = false
  }
}

const installDriver = async (browserName) => {
  installing.value = browserName
  try {
    await api.post('/ui-automation/config/environment/install_driver/', { browser: browserName })
    ElMessage.success(`${formatBrowserName(browserName)} 驱动安装成功`)
    // Re-check environment
    await checkEnvironment()
  } catch (error) {
    console.error('驱动安装失败:', error)
    ElMessage.error(`驱动安装失败: ${error.response?.data?.error || error.message}`)
  } finally {
    installing.value = null
  }
}

onMounted(() => {
  checkEnvironment()
})
</script>

<style scoped>










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
  padding: 0;
  overflow: hidden;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.05);
}

.scrollable-content {
  overflow-y: auto;
}

.description-text {
  margin-top: 0;
  margin-bottom: 20px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
  text-align: left;
}

/* Custom styles below */
.check-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  margin-bottom: 40px;
  gap: 10px;
}

.last-check {
  font-size: 0.9rem;
  color: #999;
}

.env-status-grid {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.os-info-card {
  background: white;
  padding: 20px;
  border-radius: 12px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  text-align: center;
}

.os-name {
  font-size: 1.5rem;
  font-weight: bold;
  color: #409EFF;
  margin-top: 10px;
}

.section-title {
  margin: 20px 0 10px;
  border-left: 4px solid #409EFF;
  padding-left: 10px;
}

.section-title h3 {
  margin: 0;
  font-size: 1.2rem;
  color: #303133;
}

.browser-cards {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 20px;
}

.browser-card {
  background: white;
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  transition: transform 0.3s;
  cursor: default;
}

.browser-card:hover {
  transform: translateY(-5px);
}

.browser-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 100%;
}

.browser-icon {
  width: 64px;
  height: 64px;
  margin-bottom: 15px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.browser-icon :deep(.el-icon) {
  font-size: 48px;
}

.browser-info {
  width: 100%;
  text-align: center;
  margin-bottom: 15px;
}

.browser-info h3 {
  margin: 0 0 10px;
  color: #303133;
  font-size: 1.1rem;
}

.status-row {
  display: flex;
  justify-content: center;
  margin-bottom: 5px;
}

.browser-actions {
  margin-top: 10px;
  width: 100%;
  display: flex;
  justify-content: center;
}

/* 下载教程样式 */
.download-tutorial {
  margin-bottom: 30px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.tutorial-content {
  padding: 10px 0;
}

.tutorial-content h4 {
  margin: 15px 0 10px;
  color: #303133;
}

.tutorial-content ol {
  margin: 0;
  padding-left: 20px;
}

.tutorial-content li {
  margin-bottom: 8px;
  line-height: 1.6;
}

.tutorial-content a {
  color: #409EFF;
  text-decoration: none;
}

.tutorial-content a:hover {
  text-decoration: underline;
}

.tutorial-content code {
  background-color: #f0f0f0;
  padding: 2px 6px;
  border-radius: 4px;
  font-family: 'Courier New', Courier, monospace;
}
</style>

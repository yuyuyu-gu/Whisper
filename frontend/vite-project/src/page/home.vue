<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { useUserStore } from '../store/user' // 引入Pinia用户仓库
import TranscriptionPanel from './home/TranscriptionPanel.vue'
import AdminPanel from './home/AdminPanel.vue'
import FaceSearchPanel from './home/FaceSearchPanel.vue'
import TaskPanel from './home/TaskPanel.vue'

const activeTab = ref('transcription')
// 头部收缩状态
const isCollapsed = ref(false)
// 侧边栏状态
const sidebarCollapsed = ref(true) // 默认收起
const sidebarWidth = ref(60) // 收起宽度
const sidebarExpandedWidth = ref(220) // 展开宽度
let resizeHandler = null
let mouseDown = ref(false)

// 切换头部收缩/展开
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}

// 切换侧边栏收缩/展开
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
  document.documentElement.style.setProperty('--sidebar-width', sidebarCollapsed.value ? `${sidebarWidth.value}px` : `${sidebarExpandedWidth.value}px`)
}

// 侧边栏拖拽调整
const startResize = (e) => {
  mouseDown.value = true
  document.body.style.cursor = 'col-resize'
  e.preventDefault()
}

const resizeSidebar = (e) => {
  if (!mouseDown.value) return
  const newWidth = Math.max(60, Math.min(300, e.clientX))
  sidebarWidth.value = newWidth
  sidebarExpandedWidth.value = newWidth
  sidebarCollapsed.value = false
  document.documentElement.style.setProperty('--sidebar-width', `${newWidth}px`)
}

const stopResize = () => {
  mouseDown.value = false
  document.body.style.cursor = 'default'
}

// 自动隐藏逻辑：鼠标离开侧边栏3秒后收起
let autoCollapseTimer = null
const handleSidebarMouseEnter = () => {
  clearTimeout(autoCollapseTimer)
  sidebarCollapsed.value = false
  document.documentElement.style.setProperty('--sidebar-width', `${sidebarExpandedWidth.value}px`)
}

const handleSidebarMouseLeave = () => {
  autoCollapseTimer = setTimeout(() => {
    sidebarCollapsed.value = true
    document.documentElement.style.setProperty('--sidebar-width', `${sidebarWidth.value}px`)
  }, 3000)
}

// 生命周期：初始化样式 + 绑定事件
onMounted(() => {
  // 初始化侧边栏宽度
  document.documentElement.style.setProperty('--sidebar-width', `${sidebarWidth.value}px`)
  // 绑定拖拽事件
  resizeHandler = document.querySelector('.sidebar-resize-handle')
  window.addEventListener('mousemove', resizeSidebar)
  window.addEventListener('mouseup', stopResize)
  // 初始化自动隐藏
  handleSidebarMouseLeave()
})

onUnmounted(() => {
  window.removeEventListener('mousemove', resizeSidebar)
  window.removeEventListener('mouseup', stopResize)
  clearTimeout(autoCollapseTimer)
})
</script>

<template>
  <div class="app-root">
    <!-- 头部区域 -->
    <header class="app-header" :class="{ collapsed: isCollapsed }">
      <div class="header-left">
        <img src="/logo.png" alt="西安交通大学校徽" class="header-logo" />
      </div>
      <div class="header-content">
        <h1>
          <span v-if="isCollapsed">西安交通大学档案馆</span>
          <span v-else>西安交通大学档案馆</span>
        </h1>
        <template v-if="!isCollapsed">
          <p class="subtitle en-subtitle">Archives of Xi'an Jiaotong University</p>
          <p class="subtitle main-subtitle">音视频档案智能整理平台</p>
          <p class="subtitle desc-subtitle">
            面向高校博物馆与档案馆的数字化方案，支持音视频资料的自动转写、语音分段与背景音乐分离，
            为校史研究与展陈规划提供更便捷的工具支撑。
          </p>
        </template>
      </div>
      <button class="collapse-toggle" @click="toggleCollapse" :title="isCollapsed ? '展开' : '收缩'">
        <i class="toggle-icon">{{ isCollapsed ? '▶' : '◀' }}</i>
      </button>
    </header>

    <!-- 主体区域：侧边栏 + 内容 -->
    <div class="main-container">
      <!-- 左侧侧边栏 -->
      <aside
        class="sidebar"
        :class="{ collapsed: sidebarCollapsed }"
        @mouseenter="handleSidebarMouseEnter"
        @mouseleave="handleSidebarMouseLeave"
      >
        <div class="sidebar-items">
          <label class="sidebar-item" :class="{ active: activeTab === 'transcription' }">
            <input type="radio" name="tab" value="transcription" v-model="activeTab" class="sidebar-radio" />
            <span class="sidebar-text">
              <span class="label-text" v-show="!sidebarCollapsed">语音转写</span>
            </span>
          </label>
          <label class="sidebar-item" :class="{ active: activeTab === 'graph' }">
            <input type="radio" name="tab" value="graph" v-model="activeTab" class="sidebar-radio" />
            <span class="sidebar-text">
              <span class="label-text" v-show="!sidebarCollapsed">图像搜索</span>
            </span>
          </label>
          <label class="sidebar-item" :class="{ active: activeTab === 'admin' }">
            <input type="radio" name="tab" value="admin" v-model="activeTab" class="sidebar-radio" />
            <span class="sidebar-text">
              <span class="label-text" v-show="!sidebarCollapsed">管理页面</span>
            </span>
          </label>
          <label class="sidebar-item" :class="{ active: activeTab === 'task' }">
            <input type="radio" name="tab" value="task" v-model="activeTab" class="sidebar-radio" />
            <span class="sidebar-text">
              <span class="label-text" v-show="!sidebarCollapsed">后台任务管理</span>
            </span>
          </label>
        </div>

        <!-- 侧边栏拖拽把手 -->
        <div
          class="sidebar-resize-handle"
          @mousedown="startResize"
          :title="sidebarCollapsed ? '拖动展开/点击展开' : '拖动调整宽度/点击收起'"
          @click="toggleSidebar"
        >
          <span class="handle-icon">|||</span>
        </div>
      </aside>

      <!-- 主内容区域 -->
      <main class="content-area">
        <div class="content">
          <TranscriptionPanel v-if="activeTab === 'transcription'" />
          <AdminPanel v-else-if="activeTab === 'admin'" />
          <FaceSearchPanel v-else-if="activeTab === 'graph'" />
          <TaskPanel v-else-if="activeTab === 'task'" />
        </div>
      </main>
    </div>
  </div>
</template>

<style scoped>
/* 全局变量 */
:root {
  --sidebar-width: 60px;
  --sidebar-expanded-width: 220px;
  --sidebar-handle-width: 6px;
}

/* 全局样式重置与基础配置 */
:deep(*) {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

/* 引入思源黑体 */
@font-face {
  font-family: 'Source Han Sans';
  src: local('Source Han Sans CN'),
       url('https://cdn.bootcdn.net/ajax/libs/source-han-sans/2.004R/OTF/SimplifiedChinese/SourceHanSansCN-Regular.otf') format('opentype');
  font-weight: 400;
  font-style: normal;
  font-display: swap;
}

@font-face {
  font-family: 'Source Han Sans';
  src: local('Source Han Sans CN Bold'),
       url('https://cdn.bootcdn.net/ajax/libs/source-han-sans/2.004R/OTF/SimplifiedChinese/SourceHanSansCN-Bold.otf') format('opentype');
  font-weight: 700;
  font-style: normal;
  font-display: swap;
}

/* 页面背景：浅米色 */
.app-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: 'Source Han Sans', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #1f2933;
  background: #f5f0e6;
}

/* 头部样式（保留原有） */
.app-header {
  position: static;
  display: flex;
  align-items: center;
  gap: 24px;
  padding: 2rem 3rem;
  background: #e6eef5;
  color: #2d3748;
  border-bottom: 1px solid #d4c8b8;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.03);
  transition: all 0.3s ease;
  z-index: 10;
}

.app-header.collapsed {
  padding: 0.8rem 2rem;
  gap: 16px;
}

.app-header h1 {
  margin: 0 0 8px 0;
  font-size: 2rem;
  font-weight: 700;
  letter-spacing: 0.5px;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
  transition: font-size 0.3s ease;
}

.app-header.collapsed h1 {
  font-size: 1.2rem;
  margin: 0;
}

.header-logo {
  height: 160px;
  width: auto;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: all 0.3s ease;
}

.app-header.collapsed .header-logo {
  height: 60px;
}

.header-logo:hover {
  transform: scale(1.02);
}

.subtitle {
  font-size: 0.95rem;
  line-height: 1.6;
  color: #4a5568;
  margin: 4px 0;
  transition: opacity 0.2s ease;
}

.en-subtitle {
  font-size: 1rem;
  color: #718096;
  letter-spacing: 1px;
  text-transform: uppercase;
  margin-bottom: 12px;
}

.main-subtitle {
  font-size: 1.1rem;
  font-weight: 500;
  color: #2d3748;
  margin-bottom: 8px;
}

.desc-subtitle {
  max-width: 800px;
  color: #4a5568;
  font-size: 0.9rem;
}

.collapse-toggle {
  margin-left: auto;
  background: transparent;
  border: none;
  cursor: pointer;
  font-size: 1.2rem;
  color: #2d3748;
  padding: 8px 12px;
  border-radius: 4px;
  transition: background 0.2s ease;
  flex-shrink: 0;
}

.collapse-toggle:hover {
  background: rgba(0, 0, 0, 0.05);
}

.toggle-icon {
  display: inline-block;
  transition: transform 0.2s ease;
}

/* 主体容器：侧边栏 + 内容 */
.main-container {
  display: flex;
  flex: 1;
  height: calc(100vh - var(--header-height));
  min-height: calc(100vh - 180px);
}

/* 左侧侧边栏样式 */
.sidebar {
  width: var(--sidebar-width);
  background: #ffffff;
  border-right: 1px solid #e0e0e0;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.05);
  transition: width 0.3s ease;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.sidebar.collapsed {
  width: var(--sidebar-width);
}

.sidebar-items {
  display: flex;
  flex-direction: column;
  padding: 1rem 0;
  flex: 1;
}

.sidebar-item {
  cursor: pointer;
  margin: 0 0.5rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.sidebar-radio {
  display: none;
}

.sidebar-text {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0.8rem 1rem;
  color: #4a89dc;
  font-size: 0.95rem;
  white-space: nowrap;
}

/* 选中状态 */
.sidebar-item.active .sidebar-text {
  background: #2d3748;
  color: #ffffff;
  border-radius: 4px;
}

/* hover效果 */
.sidebar-item:not(.active):hover .sidebar-text {
  background: #f8f2e8;
  color: #c18a6b;
  border-radius: 4px;
}

.icon {
  font-size: 1.1rem;
  flex-shrink: 0;
  width: 24px;
  text-align: center;
}

.label-text {
  transition: opacity 0.2s ease;
}

/* 侧边栏拖拽把手 */
.sidebar-resize-handle {
  width: var(--sidebar-handle-width);
  background: #f0f0f0;
  height: 100%;
  position: absolute;
  right: 0;
  top: 0;
  cursor: col-resize;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.2s ease;
}

.sidebar-resize-handle:hover {
  background: #e0e0e0;
}

.handle-icon {
  color: #999;
  font-size: 0.8rem;
  user-select: none;
}

/* 内容区域样式 */
.content-area {
  flex: 1;
  padding: 2rem 3rem;
  overflow-y: auto;
  background: #f5f0e6;
}

.content {
  background: #ffffff;
  padding: 2rem;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  height: 100%;
}

/* 响应式适配 */
@media (max-width: 768px) {
  .app-header {
    padding: 1.5rem 1.5rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .app-header.collapsed {
    padding: 1rem 1.5rem;
    flex-direction: row;
    align-items: center;
  }

  .header-logo {
    height: 80px;
  }

  .app-header.collapsed .header-logo {
    height: 50px;
  }

  .app-header h1 {
    font-size: 1.5rem;
  }

  .app-header.collapsed h1 {
    font-size: 1rem;
  }

  .collapse-toggle {
    align-self: flex-end;
    margin-left: 0;
    margin-top: -40px;
    margin-bottom: 10px;
  }

  .app-header.collapsed .collapse-toggle {
    margin-top: 0;
    margin-left: auto;
  }

  /* 移动端侧边栏适配 */
  .sidebar {
    width: 60px;
  }

  .sidebar-expanded-width {
    width: 180px !important;
  }

  .content-area {
    padding: 1.5rem 1rem;
  }

  .content {
    padding: 1.5rem;
  }
}

@media (max-width: 480px) {
  .app-header h1 {
    font-size: 1.2rem;
  }

  .app-header.collapsed h1 {
    font-size: 0.9rem;
  }

  .desc-subtitle {
    font-size: 0.8rem;
  }

  .sidebar-text {
    padding: 0.6rem 0.8rem;
    font-size: 0.85rem;
  }
}

/* 动态计算头部高度 */
:deep(.app-header) {
  --header-height: 180px;
}

:deep(.app-header.collapsed) {
  --header-height: 80px;
}
</style>
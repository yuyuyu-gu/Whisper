<script setup>
import { ref } from 'vue'
import HeroSection from './home/HeroSection.vue'
import TranscriptionPanel from './home/TranscriptionPanel.vue'
import VadPanel from './home/VadPanel.vue'
import BgmPanel from './home/BgmPanel.vue'
import AdminPanel from './home/AdminPanel.vue'
import FaceSearchPanel from './home/FaceSearchPanel.vue'
import TaskPanel from './home/TaskPanel.vue'

const activeTab = ref('transcription')
// 新增：控制header收缩状态
const isCollapsed = ref(false)

// 新增：切换收缩/展开
const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value
}
</script>

<template>
  <div class="app-root">
    <!-- 改造header：添加收缩切换 + 动态内容 -->
    <header class="app-header" :class="{ collapsed: isCollapsed }">
      <div class="header-left">
        <img src="/logo.png" alt="西安交通大学校徽" class="header-logo" />
      </div>
      <div class="header-content">
        <!-- 核心标题：收缩时简化文字 -->
        <h1>
          <span v-if="isCollapsed">西安交通大学档案馆</span>
          <span v-else>西安交通大学档案馆</span>
        </h1>
        <!-- 收缩时隐藏副标题 -->
        <template v-if="!isCollapsed">
          <p class="subtitle en-subtitle">Archives of Xi'an Jiaotong University</p>
          <p class="subtitle main-subtitle">音视频档案智能整理平台</p>
          <p class="subtitle desc-subtitle">
            面向高校博物馆与档案馆的数字化方案，支持音视频资料的自动转写、语音分段与背景音乐分离，
            为校史研究与展陈规划提供更便捷的工具支撑。
          </p>
        </template>
      </div>
      <!-- 新增：收缩/展开切换按钮 -->
      <button class="collapse-toggle" @click="toggleCollapse" :title="isCollapsed ? '展开' : '收缩'">
        <i class="toggle-icon">{{ isCollapsed ? '▶' : '◀' }}</i>
      </button>
    </header>

    <!-- 顶部导航栏 -->
    <nav class="top-nav">
      <div class="nav-items">
        <label class="nav-item" :class="{ active: activeTab === 'transcription' }">
          <input type="radio" name="tab" value="transcription" v-model="activeTab" class="nav-radio" />
          <span class="nav-text">
            <i class="icon">✍️</i>
            <span>语音转写</span>
          </span>
        </label>
        <label class="nav-item" :class="{ active: activeTab === 'vad' }">
          <input type="radio" name="tab" value="vad" v-model="activeTab" class="nav-radio" />
          <span class="nav-text">
            <i class="icon">🎤</i>
            <span>VAD 检测</span>
          </span>
        </label>
        <label class="nav-item" :class="{ active: activeTab === 'bgm' }">
          <input type="radio" name="tab" value="bgm" v-model="activeTab" class="nav-radio" />
          <span class="nav-text">
            <i class="icon">🎵</i>
            <span>BGM 分离</span>
          </span>
        </label>
        <label class="nav-item" :class="{ active: activeTab === 'admin' }">
          <input type="radio" name="tab" value="admin" v-model="activeTab" class="nav-radio" />
          <span class="nav-text">
            <i class="icon">⚙️</i>
            <span>管理页面</span>
          </span>
        </label>
        <label class="nav-item" :class="{ active: activeTab === 'graph' }">
          <input type="radio" name="tab" value="graph" v-model="activeTab" class="nav-radio" />
          <span class="nav-text">
            <i class="icon">🔍</i>
            <span>图像搜索</span>
          </span>
        </label>
        <label class="nav-item" :class="{ active: activeTab === 'task' }">
          <input type="radio" name="tab" value="task" v-model="activeTab" class="nav-radio" />
          <span class="nav-text">
            <i class="icon">🔍</i>
            <span>后台任务管理</span>
          </span>
        </label>
      </div>
    </nav>

    <!-- 内容区域 -->
    <main class="content-area">
      <div class="content">
        <TranscriptionPanel v-if="activeTab === 'transcription'" />
        <VadPanel v-else-if="activeTab === 'vad'" />
        <AdminPanel v-else-if="activeTab === 'admin'" />
        <FaceSearchPanel v-else-if="activeTab === 'graph'" />
        <TaskPanel v-else-if="activeTab === 'task'" />
        <BgmPanel v-else />
      </div>
    </main>
  </div>
</template>

<style scoped>
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

/* 头部：核心修改 - 新增收缩状态样式 + 切换按钮 */
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
  /* 新增：过渡动画 */
  transition: all 0.3s ease;
}

/* 新增：收缩状态的header样式 */
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
  /* 新增：收缩状态字体缩小 */
  transition: font-size 0.3s ease;
}

/* 新增：收缩状态标题字体 */
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

/* 新增：收缩状态校徽缩小 */
.app-header.collapsed .header-logo {
  height: 60px;
}

.header-logo:hover {
  transform: scale(1.02);
}

/* 副标题颜色调整为深灰色系 */
.subtitle {
  font-size: 0.95rem;
  line-height: 1.6;
  color: #4a5568;
  margin: 4px 0;
  /* 新增：过渡动画 */
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

/* 新增：收缩/展开切换按钮样式 */
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
  /* 确保按钮始终显示 */
  flex-shrink: 0;
}

.collapse-toggle:hover {
  background: rgba(0, 0, 0, 0.05);
}

.toggle-icon {
  display: inline-block;
  transition: transform 0.2s ease;
}

/* 顶部导航栏：保持原有样式 */
.top-nav {
  background: #ffffff;
  border-bottom: 1px solid #e0e0e0;
  padding: 0.8rem 3rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.nav-items {
  display: flex;
  gap: 0.5rem;
}

.nav-item {
  position: relative;
  cursor: pointer;
}

.nav-radio {
  display: none;
}

.nav-text {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 0.7rem 1.2rem;
  border-radius: 4px;
  font-size: 0.95rem;
  color: #4a89dc;
  transition: all 0.2s ease;
}

/* 选中状态：用浅棕红色（适配米色基调）替代原交大蓝，更协调 */
.nav-item.active .nav-text {
  background: #2d3748;
  color: #ffffff;
}

/* hover效果：浅米色背景，呼应页面主色调 */
.nav-item:not(.active):hover .nav-text {
  background: #f8f2e8;
  color: #c18a6b;
}

.icon {
  font-size: 1rem;
}

/* 内容区域：保持原有样式 */
.content-area {
  flex: 1;
  padding: 2rem 3rem;
}

.content {
  background: #ffffff;
  padding: 2rem;
  border-radius: 4px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

/* 响应式适配 */
@media (max-width: 768px) {
  .app-header {
    padding: 1.5rem 1.5rem;
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  /* 新增：响应式下收缩状态的header */
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

  /* 响应式下切换按钮位置调整 */
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

  .top-nav {
    padding: 0.8rem 1.5rem;
    overflow-x: auto;
  }

  .nav-items {
    flex-wrap: nowrap;
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

  .nav-text {
    padding: 0.6rem 0.9rem;
    font-size: 0.85rem;
  }
}
</style>
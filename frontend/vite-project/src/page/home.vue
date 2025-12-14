<script setup>
import { ref } from 'vue'
import HeroSection from './home/HeroSection.vue'
import TranscriptionPanel from './home/TranscriptionPanel.vue'
import VadPanel from './home/VadPanel.vue'
import BgmPanel from './home/BgmPanel.vue'
import AdminPanel from './home/AdminPanel.vue'
import FaceSearchPanel from './home/FaceSearchPanel.vue'

const activeTab = ref('transcription')

</script>

<template>
  <div class="app-root">
    <header class="app-header">
      <div class="header-left">
        <img src="/logo.png" alt="logo" class="header-logo" />
      </div>
      <div class="header-content">
          <h1>西安交通大学档案馆</h1>
          <p class="subtitle">Archives of Xi‘an Jiaotong University</p>
          <p class="subtitle">音视频档案智能整理平台</p>
          <p class="subtitle">
            面向高校博物馆与档案馆的数字化方案，支持音视频资料的自动转写、语音分段与背景音乐分离，
            为校史研究与展陈规划提供更便捷的工具支撑。
          </p>
      </div>
    </header>

    <main class="main-layout">
      <!-- 博物馆风格头图与轮播
      <HeroSection />-->

      <div class="side-nav">
          <div class="radio-inputs">
            <label class="radio">
              <input
                type="radio"
                name="tab"
                value="transcription"
                v-model="activeTab"
              />
              <span class="name">语音转写</span>
            </label>

            <label class="radio">
              <input
                type="radio"
                name="tab"
                value="vad"
                v-model="activeTab"
              />
              <span class="name">VAD 检测</span>
            </label>

            <label class="radio">
              <input
                type="radio"
                name="tab"
                value="bgm"
                v-model="activeTab"
              />
              <span class="name">BGM 分离</span>
            </label>

            <label class="radio">
              <input
                type="radio"
                name="tab"
                value="admin"
                v-model="activeTab"
              />
              <span class="name">管理页面</span>
            </label>

            <label class="radio">
              <input
                type="radio"
                name="tab"
                value="face"
                v-model="activeTab"
              />
              <span class="name">人脸搜索</span>
            </label>
          </div>
      </div>

      <!-- 面板 -->
      <div class="content">
          <TranscriptionPanel v-if="activeTab === 'transcription'" />
          <VadPanel v-else-if="activeTab === 'vad'" />
          <BgmPanel v-else-if="activeTab === 'bgm'" />
          <FaceSearchPanel v-else-if="activeTab === 'face'" />
          <AdminPanel v-else-if="activeTab === 'admin'" />
      </div>

    </main>
  </div>
</template>

<style scoped>
.app-root {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  color: #1f2933;
  background: #f3f4f6;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 1000;

  display: flex;
  align-items: center;   /* 垂直居中 */
  gap: 16px;             /* 左右间距 */
  padding: 1.5rem 2rem 1rem;
  background: #111827;
  color: #f9fafb;
}

.app-header h1 {
  margin: 0;
  font-size: 1.5rem;
}

.header-logo {
  height: 140px;
  width: auto;
}

.subtitle {
  margin: 0.25rem 0 0.75rem;
  font-size: 0.9rem;
  color: #9ca3af;
}

.api-base {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  flex-wrap: wrap;
}

.api-base input {
  width: 260px;
}

.main-layout {
  position: relative;
}

.content {
  flex: 1;
  padding: 1.5rem 2rem 2rem;
  margin-left: 36px;
  transition: margin-left 0.3s ease;
}

/* =========================
   左侧悬浮侧边栏容器
========================= */
.side-nav {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 1000;

  width: 50px;
}

.side-nav:hover ~ .content {
  margin-left: 140px;
}

/* =========================
   radio 导航主体
========================= */
.radio-inputs {
  height: 65vh; /* 占满屏幕高度 */
  display: flex;
  flex-direction: column;
  justify-content: flex-start; /* 或 space-between / center */
}

.radio-inputs {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;

  width: 120px;
  padding: 0.6rem;

  border-radius: 0 1rem 1rem 0;
  background: linear-gradient(145deg, #e6e6e6, #ffffff);

  box-shadow:
    5px 5px 15px rgba(0, 0, 0, 0.15),
    -5px -5px 15px rgba(255, 255, 255, 0.8);

  /* 默认隐藏在左侧 */
  transform: translateX(-95%);
  transition: transform 0.3s ease;
}

/* Hover 展开 */
.side-nav:hover .radio-inputs {
  transform: translateX(0);
}

/* =========================
   左侧“把手”提示
========================= */
.radio-inputs::before {
  content: "≡";
  position: absolute;
  left: 100%;
  top: 50%;
  transform: translateY(-50%);

  width: 26px;
  height: 64px;

  background: linear-gradient(145deg, #3b82f6, #2563eb);
  color: white;

  border-radius: 0 10px 10px 0;
  font-size: 1.2rem;
  font-weight: bold;

  display: flex;
  align-items: center;
  justify-content: center;

  box-shadow: 2px 2px 8px rgba(0, 0, 0, 0.25);
}

/* =========================
   单个 radio 项
========================= */
.radio-inputs .radio {
  width: 100%;
  position: relative;
}

.radio-inputs .radio input {
  display: none;
}

/* =========================
   按钮样式
========================= */
.radio-inputs .radio .name {
  display: flex;
  align-items: center;
  justify-content: center;

  cursor: pointer;
  padding: 0.7rem 0.5rem;
  border-radius: 0.6rem;

  font-size: 14px;
  font-weight: 500;
  white-space: nowrap;

  color: #2d3748;
  background: linear-gradient(145deg, #ffffff, #e6e6e6);

  box-shadow:
    3px 3px 6px rgba(0, 0, 0, 0.1),
    -3px -3px 6px rgba(255, 255, 255, 0.7);

  transition: all 0.2s ease;
  overflow: hidden;
}

/* =========================
   Hover 效果
========================= */
.radio-inputs .radio:hover .name {
  background: linear-gradient(145deg, #f0f0f0, #ffffff);
  transform: translateY(-1px);
  box-shadow:
    4px 4px 8px rgba(0, 0, 0, 0.1),
    -4px -4px 8px rgba(255, 255, 255, 0.8);
}

/* =========================
   选中状态
========================= */
.radio-inputs .radio input:checked + .name {
  background: linear-gradient(145deg, #3b82f6, #2563eb);
  color: #ffffff;
  font-weight: 600;

  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);

  box-shadow:
    inset 2px 2px 5px rgba(0, 0, 0, 0.2),
    inset -2px -2px 5px rgba(255, 255, 255, 0.1),
    3px 3px 8px rgba(59, 130, 246, 0.3);

  transform: translateY(2px);
}

/* Hover + 选中 */
.radio-inputs .radio:hover input:checked + .name {
  transform: translateY(1px);
}

/* =========================
   动画
========================= */
.radio-inputs .radio input:checked + .name {
  animation: select 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes select {
  0% {
    transform: scale(0.95) translateY(2px);
  }
  50% {
    transform: scale(1.05) translateY(-1px);
  }
  100% {
    transform: scale(1) translateY(2px);
  }
}


.panel {
}

@media (max-width: 640px) {
  .app-header,
  .content {
    padding: 1rem;
  }
}
</style>

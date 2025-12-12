<script setup>
import { ref } from 'vue'
import { setApiBase } from '../api/backend'
import HeroSection from './home/HeroSection.vue'
import TranscriptionPanel from './home/TranscriptionPanel.vue'
import VadPanel from './home/VadPanel.vue'
import BgmPanel from './home/BgmPanel.vue'

const defaultApiBase = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const apiBaseInput = ref(defaultApiBase)
setApiBase(apiBaseInput.value)

const activeTab = ref('transcription')

function applyApiBase() {
  setApiBase(apiBaseInput.value.trim() || defaultApiBase)
}
</script>

<template>
  <div class="app-root">
    <header class="app-header">
      <h1>Whisper-WebUI 前端示例</h1>
      <p class="subtitle">转写 / VAD / BGM 分离 一体化示例模板</p>

      <div class="api-base">
        <label>
          后端 API 地址：
          <input v-model="apiBaseInput" type="text" placeholder="http://localhost:8000" />
        </label>
        <button type="button" @click="applyApiBase">应用</button>
      </div>
    </header>

    <main class="content">
      <!-- 博物馆风格头图与轮播 -->
      <HeroSection />

      <div class="tabs">
        <button
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === 'transcription' }"
          @click="activeTab = 'transcription'"
        >
          语音转写
        </button>
        <button
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === 'vad' }"
          @click="activeTab = 'vad'"
        >
          VAD 检测
        </button>
        <button
          type="button"
          class="tab-btn"
          :class="{ active: activeTab === 'bgm' }"
          @click="activeTab = 'bgm'"
        >
          BGM 分离
        </button>
      </div>

      <!-- 转写 / VAD / BGM 面板 -->
      <TranscriptionPanel v-if="activeTab === 'transcription'" />
      <VadPanel v-else-if="activeTab === 'vad'" />
      <BgmPanel v-else />
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
  padding: 1.5rem 2rem 1rem;
  background: #111827;
  color: #f9fafb;
}

.app-header h1 {
  margin: 0;
  font-size: 1.5rem;
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

.content {
  flex: 1;
  padding: 1.5rem 2rem 2rem;
}

.tabs {
  display: inline-flex;
  border-radius: 999px;
  background: #e5e7eb;
  padding: 0.25rem;
  margin-bottom: 1rem;
}

.tab-btn {
  border: none;
  background: transparent;
  padding: 0.4rem 1.2rem;
  border-radius: 999px;
  font-size: 0.9rem;
  cursor: pointer;
  color: #4b5563;
}

.tab-btn.active {
  background: #111827;
  color: #f9fafb;
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

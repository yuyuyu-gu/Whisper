<script setup>
import { ref, onMounted } from 'vue'
import {
  indexFaceImage,
  searchFaceByImage,
  getFaceSearchStats,
  resetFaceDatabase,
  cleanupFaceOrphans,
} from '../../api/backend'

// 当前模式：search 以图搜图；index 人脸入库
const activeMode = ref('search')

// 以图搜图
const queryFile = ref(null)
const topK = ref(5)
const scoreThreshold = ref(0.8)
const searchLoading = ref(false)
const searchError = ref('')
const searchResult = ref([]) // SearchMatch[]

// 人脸入库
const indexFile = ref(null)
const indexLoading = ref(false)
const indexError = ref('')
const indexResult = ref(null) // IndexResponse

// 统计信息
const statsLoading = ref(false)
const statsError = ref('')
const stats = ref(null)

// 维护操作反馈
const maintenanceMessage = ref('')
const maintenanceError = ref('')

function onQueryFileChange(event) {
  const [file] = event.target.files || []
  queryFile.value = file || null
}

function onIndexFileChange(event) {
  const [file] = event.target.files || []
  indexFile.value = file || null
}

async function handleSearch() {
  if (!queryFile.value) {
    searchError.value = '请先选择要上传的查询图片'
    return
  }

  searchError.value = ''
  searchLoading.value = true
  searchResult.value = []

  try {
    const resp = await searchFaceByImage({
      file: queryFile.value,
      topK: Number(topK.value) || 5,
      scoreThreshold: Number(scoreThreshold.value) || 0.8,
    })
    if (!resp.success) {
      searchError.value = '查询失败，请检查后端日志。'
      return
    }
    searchResult.value = resp.matches || []
  } catch (e) {
    searchError.value = e.message || String(e)
  } finally {
    searchLoading.value = false
  }
}

async function handleIndex() {
  if (!indexFile.value) {
    indexError.value = '请先选择要入库的人脸图片'
    return
  }

  indexError.value = ''
  indexLoading.value = true
  indexResult.value = null

  try {
    const resp = await indexFaceImage({ file: indexFile.value })
    indexResult.value = resp
    await fetchStats()
  } catch (e) {
    indexError.value = e.message || String(e)
  } finally {
    indexLoading.value = false
  }
}

async function fetchStats() {
  statsLoading.value = true
  statsError.value = ''
  try {
    stats.value = await getFaceSearchStats()
  } catch (e) {
    statsError.value = e.message || String(e)
  } finally {
    statsLoading.value = false
  }
}

async function handleResetDatabase() {
  maintenanceMessage.value = ''
  maintenanceError.value = ''

  const ok = window.confirm('确定要清空整个人脸数据库吗？此操作不可撤销。')
  if (!ok) return

  try {
    const resp = await resetFaceDatabase({ confirm: true })
    if (resp.success) {
      maintenanceMessage.value = resp.message || '人脸数据库已清空。'
      stats.value = {
        total_faces: 0,
        total_images: 0,
        total_indexed_files: 0,
      }
    } else {
      maintenanceError.value = resp.message || '清空失败。'
    }
  } catch (e) {
    maintenanceError.value = e.message || String(e)
  }
}

async function handleCleanupOrphans() {
  maintenanceMessage.value = ''
  maintenanceError.value = ''

  try {
    const resp = await cleanupFaceOrphans()
    if (resp.success) {
      maintenanceMessage.value = resp.message || '孤儿索引清理完成。'
    } else {
      maintenanceError.value = resp.message || '清理失败。'
    }
  } catch (e) {
    maintenanceError.value = e.message || String(e)
  }
}

onMounted(() => {
  fetchStats()
})
</script>

<template>
  <section class="panel">
    <div class="panel-header">
      <h2>人脸搜索</h2>
      <div class="stats" v-if="stats">
        <span>人脸数：{{ stats.total_faces }}</span>
        <span>图片数：{{ stats.total_images }}</span>
        <span>索引文件：{{ stats.total_indexed_files }}</span>
        <button type="button" class="small" :disabled="statsLoading" @click="fetchStats">
          {{ statsLoading ? '刷新中...' : '刷新统计' }}
        </button>
      </div>
    </div>

    <div v-if="statsError" class="status">
      <p class="error">统计信息获取失败：{{ statsError }}</p>
    </div>

    <div class="mode-tabs">
      <button
        type="button"
        class="mode-tab"
        :class="{ active: activeMode === 'search' }"
        @click="activeMode = 'search'"
      >
        以图搜图
      </button>
      <button
        type="button"
        class="mode-tab"
        :class="{ active: activeMode === 'index' }"
        @click="activeMode = 'index'"
      >
        人脸入库
      </button>
    </div>

    <!-- 以图搜图 -->
    <div v-if="activeMode === 'search'">
      <div class="form-grid">
        <div class="form-item full-width">
          <label>
            查询图片：
            <input type="file" accept="image/*" @change="onQueryFileChange" />
          </label>
        </div>

        <div class="form-item">
          <label>
            返回数量 Top K：
            <input v-model.number="topK" type="number" min="1" max="50" step="1" />
          </label>
        </div>

        <div class="form-item">
          <label>
            最大距离阈值 (越小越严格)：
            <input v-model.number="scoreThreshold" type="number" min="0" max="2" step="0.01" />
          </label>
        </div>
      </div>

      <div class="actions">
        <button type="button" :disabled="searchLoading" @click="handleSearch">
          {{ searchLoading ? '搜索中...' : '开始搜索' }}
        </button>
      </div>

      <div class="status" v-if="searchError">
        <p class="error">错误：{{ searchError }}</p>
      </div>

      <div v-if="searchResult.length" class="result-box">
        <h3>匹配结果（距离越小越相似）</h3>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>图片路径</th>
              <th>原始路径</th>
              <th>距离</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="(match, idx) in searchResult" :key="idx">
              <td>{{ idx + 1 }}</td>
              <td>{{ match.image_path }}</td>
              <td>{{ match.original_path || '-' }}</td>
              <td>{{ Number(match.distance).toFixed(4) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 人脸入库 -->
    <div v-else>
      <div class="form-grid">
        <div class="form-item full-width">
          <label>
            人脸图片（单张）：
            <input type="file" accept="image/*" @change="onIndexFileChange" />
          </label>
        </div>
      </div>

      <div class="actions">
        <button type="button" :disabled="indexLoading" @click="handleIndex">
          {{ indexLoading ? '入库中...' : '入库' }}
        </button>
      </div>

      <div class="status" v-if="indexResult || indexError">
        <p v-if="indexResult">
          {{ indexResult.message }} 已处理图片：{{ indexResult.processed_images }}，当前总人脸：{{ indexResult.total_faces }}
        </p>
        <p
          v-if="indexResult && indexResult.errors && indexResult.errors.length"
          class="error"
        >
          {{ indexResult.errors.join('；') }}
        </p>
        <p v-if="indexError" class="error">错误：{{ indexError }}</p>
      </div>
    </div>

    <!-- 高级维护 -->
    <div class="maintenance">
      <h3>高级维护</h3>
      <p class="tip">以下操作会影响整个人脸库，仅管理员使用。</p>
      <div class="maintenance-actions">
        <button type="button" class="danger" @click="handleResetDatabase">清空人脸数据库</button>
        <button type="button" class="small" @click="handleCleanupOrphans">清理孤儿索引</button>
      </div>
      <div class="status" v-if="maintenanceMessage || maintenanceError">
        <p v-if="maintenanceMessage" class="info">{{ maintenanceMessage }}</p>
        <p v-if="maintenanceError" class="error">{{ maintenanceError }}</p>
      </div>
    </div>
  </section>
</template>

<style scoped>
.panel {
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem 1.5rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
  animation: panel-fade-in 480ms ease;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.panel h2 {
  margin-top: 0;
}

.stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem 1rem;
  font-size: 0.85rem;
  color: #4b5563;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem 1rem;
  margin-bottom: 1rem;
}

.form-item {
  display: flex;
  flex-direction: column;
  font-size: 0.9rem;
}

.form-item.full-width {
  grid-column: 1 / -1;
}

label {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

input[type='text'],
input[type='number'],
input[type='file'],
select {
  padding: 0.35rem 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  font-size: 0.9rem;
}

.actions {
  margin-bottom: 0.75rem;
}

button[type='button'] {
  padding: 0.4rem 1.1rem;
  border-radius: 999px;
  border: none;
  background: #111827;
  color: #f9fafb;
  font-size: 0.9rem;
  cursor: pointer;
}

button[type='button'].small {
  padding: 0.25rem 0.7rem;
  font-size: 0.8rem;
}

button[type='button'].danger {
  background: #b91c1c;
}

button[type='button']:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status {
  font-size: 0.85rem;
  color: #4b5563;
}

.error {
  color: #b91c1c;
}

.info {
  color: #0369a1;
}

.result-box {
  margin-top: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  padding: 0.75rem 0.9rem;
  background: #f9fafb;
}

table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}

th,
td {
  border: 1px solid #e5e7eb;
  padding: 0.35rem 0.5rem;
  text-align: left;
}

thead {
  background: #f3f4f6;
}

.mode-tabs {
  display: inline-flex;
  margin: 0.75rem 0 0.5rem;
  border-radius: 999px;
  background: #f3f4f6;
  padding: 0.15rem;
}

.mode-tab {
  border-radius: 999px;
  border: none;
  background: transparent;
  padding: 0.25rem 0.9rem;
  font-size: 0.85rem;
  cursor: pointer;
  color: #4b5563;
}

.mode-tab.active {
  background: #111827;
  color: #f9fafb;
}

.maintenance {
  margin-top: 1.2rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #e5e7eb;
}

.maintenance-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.5rem;
}

.tip {
  font-size: 0.8rem;
  color: #6b7280;
}

@keyframes panel-fade-in {
  from {
    opacity: 0;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>

<script setup>
import { ref, onMounted } from 'vue'
import { createBgmSeparationTask, pollTask, downloadBgmZip, getTaskStatus } from '../../api/backend'

const LS_BGM_TASK_KEY = 'whisper_bgm_task'

const bgmFile = ref(null)
const bgmModelSize = ref('UVR-MDX-NET-Inst_HQ_4')
const bgmTaskId = ref('')
const bgmStatus = ref('')
const bgmProgress = ref(0)
const bgmResult = ref(null)
const bgmError = ref('')
const bgmLoading = ref(false)
const bgmDownloadUrl = ref('')

function onBgmFileChange(event) {
  const [file] = event.target.files || []
  bgmFile.value = file || null
}

async function restoreBgmTask() {
  try {
    const raw = window.localStorage.getItem(LS_BGM_TASK_KEY)
    if (!raw) return
    const { id } = JSON.parse(raw)
    if (!id) return

    bgmTaskId.value = id
    const status = await getTaskStatus(id)
    bgmStatus.value = status.status
    bgmProgress.value = status.progress ?? 0

    if (status.status === 'completed') {
      bgmResult.value = status.result || null
      try {
        const blob = await downloadBgmZip(id)
        const url = URL.createObjectURL(blob)
        bgmDownloadUrl.value = url
      } catch (_) {
        // 忽略恢复下载失败
      }
      window.localStorage.removeItem(LS_BGM_TASK_KEY)
      return
    }

    if (status.status === 'failed') {
      bgmError.value = status.error || '任务失败'
      window.localStorage.removeItem(LS_BGM_TASK_KEY)
      return
    }

    const finalStatus = await pollTask(id, {
      onUpdate(s) {
        bgmStatus.value = s.status
        bgmProgress.value = s.progress ?? 0
      },
    })

    bgmResult.value = finalStatus.result || null
    try {
      const blob = await downloadBgmZip(id)
      const url = URL.createObjectURL(blob)
      bgmDownloadUrl.value = url
    } catch (_) {
      // 忽略恢复下载失败
    }
    window.localStorage.removeItem(LS_BGM_TASK_KEY)
  } catch (_) {
    window.localStorage.removeItem(LS_BGM_TASK_KEY)
  }
}

onMounted(() => {
  restoreBgmTask()
})

async function handleBgmSeparation() {
  if (!bgmFile.value) {
    bgmError.value = '请先选择要上传的文件'
    return
  }

  bgmError.value = ''
  bgmLoading.value = true
  bgmResult.value = null
  bgmTaskId.value = ''
  bgmStatus.value = 'queued'
  bgmProgress.value = 0
  bgmDownloadUrl.value = ''

  try {
    const bgmParams = {
      is_separate_bgm: true,
      uvr_model_size: bgmModelSize.value,
    }

    const queue = await createBgmSeparationTask({
      file: bgmFile.value,
      bgmParams,
    })

    bgmTaskId.value = queue.identifier
    bgmStatus.value = queue.status
    window.localStorage.setItem(LS_BGM_TASK_KEY, JSON.stringify({ id: queue.identifier }))

    const finalStatus = await pollTask(queue.identifier, {
      onUpdate(status) {
        bgmStatus.value = status.status
        bgmProgress.value = status.progress ?? 0
      },
    })

    bgmResult.value = finalStatus.result || null

    const blob = await downloadBgmZip(queue.identifier)
    const url = URL.createObjectURL(blob)
    bgmDownloadUrl.value = url
    window.localStorage.removeItem(LS_BGM_TASK_KEY)
  } catch (e) {
    bgmError.value = e.message || String(e)
    window.localStorage.removeItem(LS_BGM_TASK_KEY)
  } finally {
    bgmLoading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <h2>BGM 分离</h2>
    <div class="form-grid">
      <div class="form-item full-width">
        <label>
          音频 / 视频文件：
          <input type="file" accept="audio/*,video/*" @change="onBgmFileChange" />
        </label>
      </div>

      <div class="form-item">
        <label>
          UVR 模型：
          <select v-model="bgmModelSize">
            <option value="UVR-MDX-NET-Inst_HQ_4">UVR-MDX-NET-Inst_HQ_4</option>
            <option value="UVR-MDX-NET-Inst_3">UVR-MDX-NET-Inst_3</option>
          </select>
        </label>
      </div>
    </div>

    <div class="actions">
      <button type="button" :disabled="bgmLoading" @click="handleBgmSeparation">
        {{ bgmLoading ? '处理中...' : '开始分离' }}
      </button>
    </div>

    <div class="status" v-if="bgmTaskId || bgmError">
      <p v-if="bgmTaskId">任务 ID：{{ bgmTaskId }}</p>
      <p v-if="bgmStatus">状态：{{ bgmStatus }}，进度：{{ (bgmProgress * 100).toFixed(0) }}%</p>
      <p v-if="bgmError" class="error">错误：{{ bgmError }}</p>
    </div>

    <div v-if="bgmResult" class="result-box">
      <h3>分离结果（哈希）</h3>
      <p>instrumental_hash: {{ bgmResult.instrumental_hash }}</p>
      <p>vocal_hash: {{ bgmResult.vocal_hash }}</p>

      <div v-if="bgmDownloadUrl" class="download">
        <a :href="bgmDownloadUrl" download="bgm_separation.zip">下载结果 ZIP</a>
        <p class="tip">ZIP 内通常包含伴奏和人声音轨两个文件。</p>
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

.panel h2 {
  margin-top: 0;
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

.result-box {
  margin-top: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  padding: 0.75rem 0.9rem;
  background: #f9fafb;
}

.result-box pre {
  margin: 0.5rem 0 0;
  max-height: 360px;
  overflow: auto;
  white-space: pre-wrap;
  font-size: 0.85rem;
}

.download {
  margin-top: 0.5rem;
}

.download a {
  color: #1d4ed8;
  text-decoration: none;
}

.download a:hover {
  text-decoration: underline;
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

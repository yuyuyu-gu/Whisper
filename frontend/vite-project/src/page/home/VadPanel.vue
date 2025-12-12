<script setup>
import { ref, onMounted } from 'vue'
import { createVadTask, pollTask, getTaskStatus } from '../../api/backend'

const LS_VAD_TASK_KEY = 'whisper_vad_task'

const vadFile = ref(null)
const vadThreshold = ref(0.5)
const vadMinSpeechMs = ref(250)
const vadTaskId = ref('')
const vadStatus = ref('')
const vadProgress = ref(0)
const vadResult = ref([])
const vadError = ref('')
const vadLoading = ref(false)

function onVadFileChange(event) {
  const [file] = event.target.files || []
  vadFile.value = file || null
}

async function restoreVadTask() {
  try {
    const raw = window.localStorage.getItem(LS_VAD_TASK_KEY)
    if (!raw) return
    const { id } = JSON.parse(raw)
    if (!id) return

    vadTaskId.value = id
    const status = await getTaskStatus(id)
    vadStatus.value = status.status
    vadProgress.value = status.progress ?? 0

    if (status.status === 'completed') {
      vadResult.value = status.result || []
      window.localStorage.removeItem(LS_VAD_TASK_KEY)
      return
    }

    if (status.status === 'failed') {
      vadError.value = status.error || '任务失败'
      window.localStorage.removeItem(LS_VAD_TASK_KEY)
      return
    }

    const finalStatus = await pollTask(id, {
      onUpdate(s) {
        vadStatus.value = s.status
        vadProgress.value = s.progress ?? 0
      },
    })

    vadResult.value = finalStatus.result || []
    window.localStorage.removeItem(LS_VAD_TASK_KEY)
  } catch (_) {
    window.localStorage.removeItem(LS_VAD_TASK_KEY)
  }
}

onMounted(() => {
  restoreVadTask()
})

async function handleVad() {
  if (!vadFile.value) {
    vadError.value = '请先选择要上传的文件'
    return
  }

  vadError.value = ''
  vadLoading.value = true
  vadResult.value = []
  vadTaskId.value = ''
  vadStatus.value = 'queued'
  vadProgress.value = 0

  try {
    const vadParams = {
      threshold: vadThreshold.value,
      min_speech_duration_ms: vadMinSpeechMs.value,
    }

    const queue = await createVadTask({
      file: vadFile.value,
      vadParams,
    })

    vadTaskId.value = queue.identifier
    vadStatus.value = queue.status
    window.localStorage.setItem(LS_VAD_TASK_KEY, JSON.stringify({ id: queue.identifier }))

    const finalStatus = await pollTask(queue.identifier, {
      onUpdate(status) {
        vadStatus.value = status.status
        vadProgress.value = status.progress ?? 0
      },
    })

    vadResult.value = finalStatus.result || []
    window.localStorage.removeItem(LS_VAD_TASK_KEY)
  } catch (e) {
    vadError.value = e.message || String(e)
    window.localStorage.removeItem(LS_VAD_TASK_KEY)
  } finally {
    vadLoading.value = false
  }
}
</script>

<template>
  <section class="panel">
    <h2>VAD 检测</h2>
    <div class="form-grid">
      <div class="form-item full-width">
        <label>
          音频 / 视频文件：
          <input type="file" accept="audio/*,video/*" @change="onVadFileChange" />
        </label>
      </div>

      <div class="form-item">
        <label>
          阈值（0-1）：
          <input v-model.number="vadThreshold" type="number" min="0" max="1" step="0.01" />
        </label>
      </div>

      <div class="form-item">
        <label>
          最短语音时长（毫秒）：
          <input v-model.number="vadMinSpeechMs" type="number" min="0" step="10" />
        </label>
      </div>
    </div>

    <div class="actions">
      <button type="button" :disabled="vadLoading" @click="handleVad">
        {{ vadLoading ? '处理中...' : '开始检测' }}
      </button>
    </div>

    <div class="status" v-if="vadTaskId || vadError">
      <p v-if="vadTaskId">任务 ID：{{ vadTaskId }}</p>
      <p v-if="vadStatus">状态：{{ vadStatus }}，进度：{{ (vadProgress * 100).toFixed(0) }}%</p>
      <p v-if="vadError" class="error">错误：{{ vadError }}</p>
    </div>

    <div v-if="vadResult.length" class="result-box">
      <h3>语音区间（采样率 16000Hz）</h3>
      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>开始样本</th>
            <th>结束样本</th>
            <th>开始时间 (s)</th>
            <th>结束时间 (s)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(chunk, idx) in vadResult" :key="idx">
            <td>{{ idx + 1 }}</td>
            <td>{{ chunk.start }}</td>
            <td>{{ chunk.end }}</td>
            <td>{{ (chunk.start / 16000).toFixed(2) }}</td>
            <td>{{ (chunk.end / 16000).toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
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

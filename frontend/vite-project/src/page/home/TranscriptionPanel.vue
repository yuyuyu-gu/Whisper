<script setup>
import { ref, computed, onMounted } from 'vue'
import {
  createTranscriptionTask,
  pollTask,
  getTaskStatus,
  createVadTask,
  createBgmSeparationTask,
  downloadBgmZip
} from '../../api/backend'

// ======================== 全局统一文件上传（核心修改） ========================
const globalFile = ref(null) // 单文件上传，所有功能共用
const globalFileName = ref('Not selected file') // 同步显示选中文件名

// 文件选择回调
function onGlobalFileChange(event) {
  const [file] = event.target.files || []
  globalFile.value = file || null
  globalFileName.value = file ? file.name : 'Not selected file'
}

// ======================== 语音转写（一键转字幕）相关 ========================
const LS_TRANS_TASK_KEY = 'whisper_transcription_task'

// 基础参数
const transModelSize = ref('large-v2')
const transLang = ref('')
const transTranslate = ref(false)
const transUseVad = ref(false)
const transUseDiarization = ref(false)
const transUseBgm = ref(false)
const transShowAdvanced = ref(false)
const transSubtitleFormat = ref('SRT') // 字幕格式：SRT/TXT
const transAddTimestampToFilename = ref(false) // 文件名加时间戳

// 关键词查找相关
const keyword = ref('')
const searchResult = ref([])

// Whisper 高级参数
const transBeamSize = ref(5)
const transLogProbThreshold = ref(-1.0)
const transNoSpeechThreshold = ref(0.6)
const transComputeType = ref('float16')
const transBestOf = ref(5)
const transPatience = ref(1.0)
const transConditionOnPreviousText = ref(true)
const transPromptResetOnTemperature = ref(0.5)
const transInitialPrompt = ref('')
const transTemperature = ref(0.0)
const transCompressionRatioThreshold = ref(2.4)
const transLengthPenalty = ref(1.0)
const transRepetitionPenalty = ref(1.0)
const transNoRepeatNgramSize = ref(0)
const transPrefix = ref('')
const transSuppressBlank = ref(true)
const transSuppressTokens = ref('')
const transMaxInitialTimestamp = ref(1.0)
const transWordTimestamps = ref(false)
const transPrependPunctuations = ref('"\'“¿([{-')
const transAppendPunctuations = ref('"\'.。,，!！?？:：”)]}、')
const transMaxNewTokens = ref('')
const transChunkLength = ref(30)
const transHallucinationSilenceThreshold = ref('')
const transHotwords = ref('')
const transLanguageDetectionThreshold = ref(0.5)
const transLanguageDetectionSegments = ref(1)
const transBatchSize = ref(24)
const transEnableOffload = ref(true)

// 内部 VAD / BGM / 说话人分离参数
const transVadThreshold = ref(0.5)
const transVadMinSpeechMs = ref(250)
const transVadMaxSpeechSec = ref('')
const transVadMinSilenceMs = ref(2000)
const transVadSpeechPadMs = ref(400)

const transBgmUvrModelSize = ref('UVR-MDX-NET-Inst_HQ_4')
const transBgmUvrDevice = ref('cuda')
const transBgmSegmentSize = ref(256)
const transBgmSaveFile = ref(false)
const transBgmEnableOffload = ref(true)

const transDiarizationDevice = ref('cuda')
const transDiarizationHfToken = ref('')
const transDiarizationEnableOffload = ref(true)

// 任务状态
const transTaskId = ref('')
const transStatus = ref('')
const transProgress = ref(0)
const transDuration = ref(null)
const transResult = ref([])
const transError = ref('')
const transLoading = ref(false)

// 生成对应格式的字幕内容
const transSubtitleContent = computed(() => {
  if (!Array.isArray(transResult.value) || transResult.value.length === 0) return '';
  switch (transSubtitleFormat.value) {
    case 'SRT':
      return transResult.value.map((seg, idx) => {
        const start = formatSrtTime(seg.start)
        const end = formatSrtTime(seg.end)
        return `${idx + 1}\n${start} --> ${end}\n${seg.text}\n`
      }).join('\n')
    case 'TXT':
      return transResult.value.map(seg => seg.text).join('\n')
    default:
      return transResult.value.map(seg => seg.text).join('\n')
  }
})

// 辅助：秒转SRT时间格式（时:分:秒,毫秒）
function formatSrtTime(seconds) {
  const date = new Date(seconds * 1000)
  const hours = date.getUTCHours().toString().padStart(2, '0')
  const minutes = date.getUTCMinutes().toString().padStart(2, '0')
  const secs = date.getUTCSeconds().toString().padStart(2, '0')
  const ms = date.getUTCMilliseconds().toString().padStart(3, '0')
  return `${hours}:${minutes}:${secs},${ms}`
}

// 下载字幕文件（新增）
function downloadSubtitle() {
  if (!transSubtitleContent.value) {
    transError.value = '暂无字幕内容可下载'
    return
  }
  // 生成带时间戳的文件名
  let filename = globalFile.value ? globalFile.value.name.replace(/\.[^/.]+$/, '') : 'subtitle'
  if (transAddTimestampToFilename.value) {
    const timestamp = new Date().toISOString().replace(/[-:\.T]/g, '').slice(0, 14)
    filename += `_${timestamp}`
  }
  filename += `.${transSubtitleFormat.value.toLowerCase()}`

  // 构建下载链接
  const blob = new Blob([transSubtitleContent.value], { type: 'text/plain' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

// 关键词查找（新增）
function handleKeywordSearch() {
  if (!keyword.value.trim() || !transResult.value.length) {
    searchResult.value = []
    return
  }
  const keywordTrimmed = keyword.value.trim().toLowerCase()
  searchResult.value = transResult.value
    .filter(seg => seg.text.toLowerCase().includes(keywordTrimmed))
    .map(seg => ({
      ...seg,
      startSrt: formatSrtTime(seg.start),
      endSrt: formatSrtTime(seg.end)
    }))
}

// 原有方法：恢复任务
async function restoreTranscriptionTask() {
  try {
    const raw = window.localStorage.getItem(LS_TRANS_TASK_KEY)
    if (!raw) return
    const { id } = JSON.parse(raw)
    if (!id) return

    transTaskId.value = id
    const status = await getTaskStatus(id)
    transStatus.value = status.status
    transProgress.value = status.progress ?? 0

    if (status.status === 'completed') {
      transResult.value = status.result || []
      transDuration.value = status.duration ?? null
      window.localStorage.removeItem(LS_TRANS_TASK_KEY)
      return
    }

    if (status.status === 'failed') {
      transError.value = status.error || '任务失败'
      window.localStorage.removeItem(LS_TRANS_TASK_KEY)
      return
    }

    const finalStatus = await pollTask(id, {
      onUpdate(s) {
        transStatus.value = s.status
        transProgress.value = s.progress ?? 0
      },
    })

    transResult.value = finalStatus.result || []
    transDuration.value = finalStatus.duration ?? null
    window.localStorage.removeItem(LS_TRANS_TASK_KEY)
  } catch (_) {
    window.localStorage.removeItem(LS_TRANS_TASK_KEY)
  }
}

// 原有方法：开始转写
async function handleTranscription() {
  if (!globalFile.value) { // 改用全局文件
    transError.value = '请先选择要上传的文件'
    return
  }

  transError.value = ''
  transLoading.value = true
  transResult.value = []
  transTaskId.value = ''
  transStatus.value = 'queued'
  transProgress.value = 0
  transDuration.value = null

  try {
    const whisperParams = {
      model_size: transModelSize.value,
      lang: transLang.value || undefined,
      is_translate: transTranslate.value,
      beam_size: transBeamSize.value,
      log_prob_threshold: transLogProbThreshold.value,
      no_speech_threshold: transNoSpeechThreshold.value,
      compute_type: transComputeType.value,
      best_of: transBestOf.value,
      patience: transPatience.value,
      condition_on_previous_text: transConditionOnPreviousText.value,
      prompt_reset_on_temperature: transPromptResetOnTemperature.value,
      initial_prompt: transInitialPrompt.value || undefined,
      temperature: transTemperature.value,
      compression_ratio_threshold: transCompressionRatioThreshold.value,
      length_penalty: transLengthPenalty.value,
      repetition_penalty: transRepetitionPenalty.value,
      no_repeat_ngram_size: transNoRepeatNgramSize.value,
      prefix: transPrefix.value || undefined,
      suppress_blank: transSuppressBlank.value,
      suppress_tokens: transSuppressTokens.value || undefined,
      max_initial_timestamp: transMaxInitialTimestamp.value,
      word_timestamps: transWordTimestamps.value,
      prepend_punctuations: transPrependPunctuations.value,
      append_punctuations: transAppendPunctuations.value,
      max_new_tokens: transMaxNewTokens.value ? Number(transMaxNewTokens.value) : undefined,
      chunk_length: transChunkLength.value,
      hallucination_silence_threshold: transHallucinationSilenceThreshold.value
        ? Number(transHallucinationSilenceThreshold.value)
        : undefined,
      hotwords: transHotwords.value || undefined,
      language_detection_threshold: transLanguageDetectionThreshold.value,
      language_detection_segments: transLanguageDetectionSegments.value,
      batch_size: transBatchSize.value,
      enable_offload: transEnableOffload.value,
    }

    const vadParams = transUseVad.value
      ? {
          vad_filter: true,
          threshold: transVadThreshold.value,
          min_speech_duration_ms: transVadMinSpeechMs.value,
          max_speech_duration_s: transVadMaxSpeechSec.value
            ? Number(transVadMaxSpeechSec.value)
            : undefined,
          min_silence_duration_ms: transVadMinSilenceMs.value,
          speech_pad_ms: transVadSpeechPadMs.value,
        }
      : {}

    const bgmParams = transUseBgm.value
      ? {
          is_separate_bgm: true,
          uvr_model_size: transBgmUvrModelSize.value,
          uvr_device: transBgmUvrDevice.value,
          segment_size: transBgmSegmentSize.value,
          save_file: transBgmSaveFile.value,
          enable_offload: transBgmEnableOffload.value,
        }
      : {}

    const diarizationParams = transUseDiarization.value
      ? {
          is_diarize: true,
          diarization_device: transDiarizationDevice.value,
          hf_token: transDiarizationHfToken.value || undefined,
          enable_offload: transDiarizationEnableOffload.value,
        }
      : {}

    const queue = await createTranscriptionTask({
      file: globalFile.value, // 改用全局文件
      whisperParams,
      vadParams,
      bgmParams,
      diarizationParams,
    })

    transTaskId.value = queue.identifier
    transStatus.value = queue.status
    window.localStorage.setItem(LS_TRANS_TASK_KEY, JSON.stringify({ id: queue.identifier }))

    const finalStatus = await pollTask(queue.identifier, {
      onUpdate(status) {
        transStatus.value = status.status
        transProgress.value = status.progress ?? 0
      },
    })

    transResult.value = finalStatus.result || []
    transDuration.value = finalStatus.duration ?? null
    window.localStorage.removeItem(LS_TRANS_TASK_KEY)
  } catch (e) {
    transError.value = e.message || String(e)
    window.localStorage.removeItem(LS_TRANS_TASK_KEY)
  } finally {
    transLoading.value = false
  }
}

// ======================== VAD检测相关（改用全局文件） ========================
const LS_VAD_TASK_KEY = 'whisper_vad_task'

const vadThreshold = ref(0.5)
const vadMinSpeechMs = ref(250)
const vadTaskId = ref('')
const vadStatus = ref('')
const vadProgress = ref(0)
const vadResult = ref([])
const vadError = ref('')
const vadLoading = ref(false)

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

async function handleVad() {
  if (!globalFile.value) { // 改用全局文件
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
      file: globalFile.value, // 改用全局文件
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

// ======================== BGM分离相关（改用全局文件 + 折叠控制） ========================
const LS_BGM_TASK_KEY = 'whisper_bgm_task'
const showBgmPanel = ref(false) // BGM面板折叠控制

const bgmModelSize = ref('UVR-MDX-NET-Inst_HQ_4')
const bgmTaskId = ref('')
const bgmStatus = ref('')
const bgmProgress = ref(0)
const bgmResult = ref(null)
const bgmError = ref('')
const bgmLoading = ref(false)
const bgmDownloadUrl = ref('')

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

async function handleBgmSeparation() {
  if (!globalFile.value) { // 改用全局文件
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
      file: globalFile.value, // 改用全局文件
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

// 初始化恢复所有任务
onMounted(() => {
  restoreTranscriptionTask()
  restoreVadTask()
  restoreBgmTask()
})

// 辅助：格式化秒数
function formatSeconds(seconds) {
  if (seconds == null) return '-'
  return `${seconds.toFixed(2)}s`
}
</script>

<template>
  <div class="main-container">
    <div class="global-upload">
      <h2>音视频文件上传</h2>
      <!-- 给上传容器也添加panel类，加入淡入动画 -->
      <div class="container panel">
        <div class="header">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier">
            <path d="M7 10V9C7 6.23858 9.23858 4 12 4C14.7614 4 17 6.23858 17 9V10C19.2091 10 21 11.7909 21 14C21 15.4806 20.1956 16.8084 19 17.5M7 10C4.79086 10 3 11.7909 3 14C3 15.4806 3.8044 16.8084 5 17.5M7 10C7.43285 10 7.84965 10.0688 8.24006 10.1959M12 12V21M12 12L15 15M12 12L9 15" stroke="#000000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> </g></svg>
            <p>Browse File to upload!</p>
          </div>
          <label for="global-file" class="footer">
            <svg fill="#000000" viewBox="0 0 32 32" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"><path d="M15.331 6H8.5v20h15V14.154h-8.169z"></path><path d="M18.153 6h-.009v5.342H23.5v-.002z"></path></g></svg>
            <p>{{ globalFileName }}</p>
            <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier"> <path d="M5.16565 10.1534C5.07629 8.99181 5.99473 8 7.15975 8H16.8402C18.0053 8 18.9237 8.9918 18.8344 10.1534L18.142 19.1534C18.0619 20.1954 17.193 21 16.1479 21H7.85206C6.80699 21 5.93811 20.1954 5.85795 19.1534L5.16565 10.1534Z" stroke="#000000" stroke-width="2"></path> <path d="M19.5 5H4.5" stroke="#000000" stroke-width="2" stroke-linecap="round"></path> <path d="M10 3C10 2.44772 10.4477 2 11 2H13C13.5523 2 14 2.44772 14 3V5H10V3Z" stroke="#000000" stroke-width="2"></path> </g></svg>
          </label>
          <input id="global-file" type="file" accept="audio/*,video/*" @change="onGlobalFileChange">
        </div>
      </div>

      <!-- 一键转字幕面板（核心修改） -->
      <section class="panel transcription-panel">
        <h2>一键转字幕</h2>
        <div class="transcription-layout">
          <!-- 左侧：参数设置 -->
          <div class="transcription-left">
            <!-- 转写参数设置 -->
            <div class="form-grid param-grid">
              <div class="form-item">
                <label>
                  模型选择
                  <select v-model="transModelSize">
                    <option value="tiny">tiny</option>
                    <option value="base">base</option>
                    <option value="small">small</option>
                    <option value="medium">medium</option>
                    <option value="large-v2">large-v2</option>
                  </select>
                </label>
              </div>
              <div class="form-item">
                <label>
                  语言
                  <select v-model="transLang">
                    <option value="">自动检测语言</option>
                    <option value="zh">中文</option>
                    <option value="en">英文</option>
                  </select>
                </label>
              </div>
              <div class="form-item">
                <label>
                  字幕文件格式
                  <select v-model="transSubtitleFormat">
                    <option value="SRT">SRT</option>
                    <option value="TXT">TXT</option>
                  </select>
                </label>
              </div>
              <div class="form-item">
                <label class="checkbox">
                  <input v-model="transAddTimestampToFilename" type="checkbox" /> 在文件名末尾加入时间戳
                </label>
              </div>
            </div>

            <!-- 高级参数（折叠） -->
            <div class="advanced-panel">
              <button type="button" class="advanced-toggle" @click="transShowAdvanced = !transShowAdvanced">
                {{ transShowAdvanced ? '收起高级参数' : '展开全部高级参数' }}
              </button>
              <div v-if="transShowAdvanced" class="form-grid advanced-grid">
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transTranslate" type="checkbox" /> 翻译为英文
                  </label>
                </div>
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transUseVad" type="checkbox" /> 启用 VAD 过滤静音
                  </label>
                </div>
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transUseDiarization" type="checkbox" /> 启用说话人分离
                  </label>
                </div>
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transUseBgm" type="checkbox" /> 启用 BGM 预处理
                  </label>
                </div>

                <!-- 原有高级参数（保持） -->
                <div class="form-item">
                  <label>
                    Beam Size：
                    <input v-model.number="transBeamSize" type="number" min="1" step="1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Log Prob 阈值：
                    <input v-model.number="transLogProbThreshold" type="number" step="0.1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    No Speech 阈值 (0-1)：
                    <input v-model.number="transNoSpeechThreshold" type="number" min="0" max="1" step="0.01" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Compute Type：
                    <select v-model="transComputeType">
                      <option value="float16">float16</option>
                      <option value="int8">int8</option>
                      <option value="int16">int16</option>
                    </select>
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Best Of：
                    <input v-model.number="transBestOf" type="number" min="1" step="1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Patience：
                    <input v-model.number="transPatience" type="number" step="0.1" />
                  </label>
                </div>
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transConditionOnPreviousText" type="checkbox" /> 使用上一窗口文本作为提示
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Prompt Reset 温度阈值 (0-1)：
                    <input
                      v-model.number="transPromptResetOnTemperature"
                      type="number"
                      min="0"
                      max="1"
                      step="0.01"
                    />
                  </label>
                </div>
                <div class="form-item full-width">
                  <label>
                    初始 Prompt：
                    <textarea v-model="transInitialPrompt" rows="2" placeholder="可选，用于首个窗口的提示词" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Temperature：
                    <input v-model.number="transTemperature" type="number" min="0" step="0.01" max="1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    压缩比阈值：
                    <input v-model.number="transCompressionRatioThreshold" type="number" step="0.1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    长度惩罚：
                    <input v-model.number="transLengthPenalty" type="number" step="0.1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    重复惩罚：
                    <input v-model.number="transRepetitionPenalty" type="number" step="0.1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    No Repeat N-gram：
                    <input v-model.number="transNoRepeatNgramSize" type="number" min="0" step="1" />
                  </label>
                </div>
                <div class="form-item full-width">
                  <label>
                    前缀 Prefix：
                    <input v-model="transPrefix" type="text" placeholder="可选，首个窗口前缀文本" />
                  </label>
                </div>
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transSuppressBlank" type="checkbox" /> 抑制开头空白输出
                  </label>
                </div>
                <div class="form-item full-width">
                  <label>
                    Suppress Tokens：
                    <input
                      v-model="transSuppressTokens"
                      type="text"
                      placeholder="例如: [-1, 2, 3]，留空使用默认 [-1]"
                    />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    最大初始时间戳 (s)：
                    <input v-model.number="transMaxInitialTimestamp" type="number" min="0" step="0.1" />
                  </label>
                </div>
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transWordTimestamps" type="checkbox" /> 输出逐词时间戳
                  </label>
                </div>
                <div class="form-item full-width">
                  <label>
                    前置标点集合：
                    <input v-model="transPrependPunctuations" type="text" />
                  </label>
                </div>
                <div class="form-item full-width">
                  <label>
                    后置标点集合：
                    <input v-model="transAppendPunctuations" type="text" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    每段最大新 Token 数：
                    <input
                      v-model="transMaxNewTokens"
                      type="text"
                      placeholder="留空使用默认 (不限)"
                    />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Chunk 长度 (秒)：
                    <input v-model.number="transChunkLength" type="number" min="1" step="1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    幻觉静音阈值 (秒)：
                    <input
                      v-model="transHallucinationSilenceThreshold"
                      type="text"
                      placeholder="留空使用默认"
                    />
                  </label>
                </div>
                <div class="form-item full-width">
                  <label>
                    热词 / 提示词：
                    <textarea v-model="transHotwords" rows="2" placeholder="可选，提升特定人名/专有名词识别" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    语言检测阈值：
                    <input v-model.number="transLanguageDetectionThreshold" type="number" min="0" step="0.01" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    语言检测片段数：
                    <input v-model.number="transLanguageDetectionSegments" type="number" min="1" step="1" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    Batch Size：
                    <input v-model.number="transBatchSize" type="number" min="1" step="1" />
                  </label>
                </div>
                <div class="form-item">
                  <label class="checkbox">
                    <input v-model="transEnableOffload" type="checkbox" /> 任务结束后卸载模型
                  </label>
                </div>

                <!-- VAD参数 -->
                <div class="form-item full-width" v-if="transUseVad">
                  <h3>转写内部 VAD 参数</h3>
                </div>
                <div class="form-item" v-if="transUseVad">
                  <label>
                    VAD 阈值 (0-1)：
                    <input v-model.number="transVadThreshold" type="number" min="0" max="1" step="0.01" />
                  </label>
                </div>
                <div class="form-item" v-if="transUseVad">
                  <label>
                    最短语音 (ms)：
                    <input v-model.number="transVadMinSpeechMs" type="number" min="0" step="10" />
                  </label>
                </div>
                <div class="form-item" v-if="transUseVad">
                  <label>
                    最长语音 (秒)：
                    <input
                      v-model="transVadMaxSpeechSec"
                      type="text"
                      placeholder="留空表示无限"
                    />
                  </label>
                </div>
                <div class="form-item" v-if="transUseVad">
                  <label>
                    最短静音 (ms)：
                    <input v-model.number="transVadMinSilenceMs" type="number" min="0" step="10" />
                  </label>
                </div>
                <div class="form-item" v-if="transUseVad">
                  <label>
                    语音两侧 Padding (ms)：
                    <input v-model.number="transVadSpeechPadMs" type="number" min="0" step="10" />
                  </label>
                </div>

                <!-- BGM参数 -->
                <div class="form-item full-width" v-if="transUseBgm">
                  <h3>转写内部 BGM 分离参数</h3>
                </div>
                <div class="form-item" v-if="transUseBgm">
                  <label>
                    UVR 模型：
                    <select v-model="transBgmUvrModelSize">
                      <option value="UVR-MDX-NET-Inst_HQ_4">UVR-MDX-NET-Inst_HQ_4</option>
                      <option value="UVR-MDX-NET-Inst_3">UVR-MDX-NET-Inst_3</option>
                    </select>
                  </label>
                </div>
                <div class="form-item" v-if="transUseBgm">
                  <label>
                    UVR 设备：
                    <select v-model="transBgmUvrDevice">
                      <option value="cpu">cpu</option>
                      <option value="cuda">cuda</option>
                      <option value="xpu">xpu</option>
                    </select>
                  </label>
                </div>
                <div class="form-item" v-if="transUseBgm">
                  <label>
                    Segment Size：
                    <input v-model.number="transBgmSegmentSize" type="number" min="1" step="1" />
                  </label>
                </div>
                <div class="form-item" v-if="transUseBgm">
                  <label class="checkbox">
                    <input v-model="transBgmSaveFile" type="checkbox" /> 保存分离后的文件
                  </label>
                </div>
                <div class="form-item" v-if="transUseBgm">
                  <label class="checkbox">
                    <input v-model="transBgmEnableOffload" type="checkbox" /> 任务结束后卸载 UVR 模型
                  </label>
                </div>

                <!-- 说话人分离参数 -->
                <div class="form-item full-width" v-if="transUseDiarization">
                  <h3>转写内部说话人分离参数</h3>
                </div>
                <div class="form-item" v-if="transUseDiarization">
                  <label>
                    Diarization 设备：
                    <select v-model="transDiarizationDevice">
                      <option value="cpu">cpu</option>
                      <option value="cuda">cuda</option>
                      <option value="xpu">xpu</option>
                    </select>
                  </label>
                </div>
                <div class="form-item full-width" v-if="transUseDiarization">
                  <label>
                    HuggingFace Token：
                    <input
                      v-model="transDiarizationHfToken"
                      type="text"
                      placeholder="仅首次下载说话人分离模型时需要"
                    />
                  </label>
                </div>
                <div class="form-item" v-if="transUseDiarization">
                  <label class="checkbox">
                    <input v-model="transDiarizationEnableOffload" type="checkbox" /> 任务结束后卸载说话人分离模型
                  </label>
                </div>
              </div>
            </div>

            <!-- 运行任务 -->
            <div class="actions">
              <button type="button" :disabled="transLoading || !globalFile" @click="handleTranscription" class="run-btn">
                {{ transLoading ? '处理中...' : '生成字幕文件' }}
              </button>
            </div>

            <!-- 状态信息 -->
            <div class="status" v-if="transTaskId || transError">
              <p v-if="transTaskId">任务 ID：{{ transTaskId }}</p>
              <p v-if="transStatus">状态：{{ transStatus }}，进度：{{ (transProgress * 100).toFixed(0) }}%</p>
              <p v-if="transDuration != null">耗时：{{ formatSeconds(transDuration) }}</p>
              <p v-if="transError" class="error">错误：{{ transError }}</p>
            </div>
          </div>

          <!-- 右侧：输出与关键词查找 -->
          <div class="transcription-right">
            <!-- 输出与纠错 -->
            <div class="output-section">
              <h3>输出与纠错</h3>
              <div class="output-box">
                <h4>RAG纠错文本</h4>
                <div class="text-content">
                  <pre>{{ transSubtitleContent || '运行后展示Qwen RAG纠错后的文本' }}</pre>
                </div>
              </div>
              <div class="subtitle-file">
                <h4>生成的字幕文件</h4>
                <button
                  type="button"
                  class="download-btn"
                  @click="downloadSubtitle"
                  :disabled="!transSubtitleContent"
                >
                  <span class="file-icon">📄</span> 下载字幕文件
                </button>
                <button class="open-dir-btn" :disabled="!transSubtitleContent">
                  打开输出目录
                </button>
              </div>
            </div>

            <!-- 字幕关键词查找 -->
            <div class="search-section">
              <h3>字幕关键词查找</h3>
              <div class="search-form">
                <div class="form-item">
                  <label>
                    关键词
                    <input v-model="keyword" type="text" placeholder="输入要查找的词语" />
                  </label>
                </div>
                <div class="form-item">
                  <label>
                    选择字幕文件
                    <select :disabled="!transSubtitleContent">
                      <option v-if="globalFile" :value="globalFile.name">
                        {{ globalFile.name.replace(/\.[^/.]+$/, '') }}.{{ transSubtitleFormat.toLowerCase() }}
                      </option>
                    </select>
                  </label>
                </div>
                <button type="button" @click="handleKeywordSearch" class="search-btn">
                  在字幕中查找
                </button>
              </div>
              <div class="search-result" v-if="searchResult.length">
                <h4>查找结果</h4>
                <div class="result-list">
                  <div v-for="(item, idx) in searchResult" :key="idx" class="result-item">
                    <p><strong>时间：</strong>{{ item.startSrt }} --> {{ item.endSrt }}</p>
                    <p><strong>内容：</strong>{{ item.text }}</p>
                  </div>
                </div>
              </div>
              <p v-else-if="keyword.trim()" class="no-result">未找到相关内容</p>
            </div>
          </div>
        </div>
      </section>

      <!-- VAD检测面板（改用全局文件） -->
      <section class="panel">
        <h2>VAD 检测</h2>
        <div class="form-grid">
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
          <button type="button" :disabled="vadLoading || !globalFile" @click="handleVad">
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

      <!-- BGM分离面板（折叠控制 + 改用全局文件） -->
      <section class="panel bgm-panel-toggle">
        <div class="panel-header" @click="showBgmPanel = !showBgmPanel">
          <h2>BGM 分离 <span>{{ showBgmPanel ? '▼' : '▶' }}</span></h2>
        </div>
        <div v-show="showBgmPanel" class="bgm-panel-content">
          <div class="form-grid">
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
            <button type="button" :disabled="bgmLoading || !globalFile" @click="handleBgmSeparation">
              {{ bgmLoading ? '处理中...' : '开始分离' }}
            </button>
          </div>
          <div class="status" v-if="bgmTaskId || bgmError">
            <p v-if="bgmTaskId">任务 ID：{{ bgmTaskId }}</p>
            <p v-if="bgmStatus">状态：{{ bgmStatus }}，进度：{{ (bgmProgress * 100).toFixed(0) }}</p>
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
        </div>
      </section>
    </div>
</template>

<style scoped>
/* ========== 新增 panel-fade-in 动画核心样式 ========== */
.panel {
  animation: panel-fade-in 480ms ease;
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

/* 全局文件上传样式 */
.global-upload {
  margin-bottom: 2rem;
}
.global-upload h2 {
  color: #1f2933;
  margin-bottom: 1rem;
}
/* 新上传框样式 */
.container {
  height: 300px;
  width: 300px;
  border-radius: 10px;
  box-shadow: 4px 4px 30px rgba(0, 0, 0, .2);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: space-between;
  padding: 10px;
  gap: 5px;
  background-color: rgba(0, 110, 255, 0.041);
  margin-bottom: 1rem;
  /* 覆盖panel默认padding，保持原有上传框样式 */
  padding: 10px !important;
}
.header {
  flex: 1;
  width: 100%;
  border: 2px dashed royalblue;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-direction: column;
}
.header svg {
  height: 100px;
}
.header p {
  text-align: center;
  color: black;
}
.footer {
  background-color: rgba(0, 110, 255, 0.075);
  width: 100%;
  height: 40px;
  padding: 8px;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  color: black;
  border: none;
}
.footer svg {
  height: 130%;
  fill: royalblue;
  background-color: rgba(70, 66, 66, 0.103);
  border-radius: 50%;
  padding: 2px;
  cursor: pointer;
  box-shadow: 0 2px 30px rgba(0, 0, 0, 0.205);
}
.footer p {
  flex: 1;
  text-align: center;
}
#global-file {
  display: none;
}

/* 主容器样式 */
.main-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
}

/* 通用面板样式 */
.panel {
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.5rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  margin-bottom: 1.5rem;
}
.panel h2 {
  margin-top: 0;
  color: #1f2933;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.5rem;
}

/* BGM面板折叠样式 */
.bgm-panel-toggle .panel-header {
  cursor: pointer;
}
.bgm-panel-toggle .panel-header span {
  font-size: 0.8rem;
  margin-left: 0.5rem;
}
.bgm-panel-content {
  padding-top: 1rem;
  /* 给折叠展开的内容也加动画 */
  animation: panel-fade-in 300ms ease;
}

/* 一键转字幕分栏布局 */
.transcription-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  margin-top: 1rem;
}

/* 表单网格 */
.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 0.75rem 1rem;
  margin-bottom: 1rem;
}
.param-grid {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
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
  color: #4b5563;
}
.checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.4rem;
}
input[type='text'],
input[type='number'],
select,
textarea {
  padding: 0.4rem 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  font-size: 0.9rem;
  transition: border-color 0.2s;
}
input:focus,
select:focus,
textarea:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.1);
}

/* 高级参数面板 */
.advanced-panel {
  margin-top: 1rem;
  padding-top: 0.75rem;
  border-top: 1px dashed #e5e7eb;
}
.advanced-toggle {
  padding: 0.35rem 0.85rem;
  font-size: 0.85rem;
  border-radius: 999px;
  border: 1px solid #d1d5db;
  background: #f9fafb;
  color: #374151;
  cursor: pointer;
  transition: background 0.2s;
}
.advanced-toggle:hover {
  background: #f3f4f6;
}
.advanced-grid {
  margin-top: 0.75rem;
  background: #f9fafb;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  /* 高级参数展开也加动画 */
  animation: panel-fade-in 300ms ease;
}

/* 按钮样式 */
.actions {
  margin-bottom: 0.75rem;
}
button[type='button'] {
  padding: 0.5rem 1.2rem;
  border-radius: 0.375rem;
  border: none;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background 0.2s;
}
.run-btn {
  background: #f97316;
  color: white;
  font-weight: 500;
}
.run-btn:disabled {
  background: #fbbf24;
  cursor: not-allowed;
  opacity: 0.8;
}
.download-btn {
  background: #3b82f6;
  color: white;
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  margin-right: 0.5rem;
}
.download-btn:disabled {
  background: #93c5fd;
  cursor: not-allowed;
}
.open-dir-btn {
  background: #6b7280;
  color: white;
}
.open-dir-btn:disabled {
  background: #d1d5db;
  cursor: not-allowed;
}
.search-btn {
  background: #10b981;
  color: white;
  align-self: flex-end;
  margin-top: 1.6rem;
}

/* 状态提示样式 */
.status {
  font-size: 0.85rem;
  color: #4b5563;
  padding: 0.5rem;
  background: #f9fafb;
  border-radius: 0.375rem;
  border: 1px solid #e5e7eb;
}
.error {
  color: #ef4444;
}

/* 右侧输出区域 */
.output-section {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
  margin-bottom: 1.5rem;
}
.output-section h3 {
  margin-top: 0;
  color: #1f2933;
  font-size: 1rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.5rem;
}
.output-box {
  margin-bottom: 1rem;
}
.output-box h4 {
  margin: 0.5rem 0;
  color: #4b5563;
  font-size: 0.9rem;
}
.text-content {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  padding: 0.75rem;
  max-height: 200px;
  overflow-y: auto;
}
.text-content pre {
  margin: 0;
  font-size: 0.85rem;
  white-space: pre-wrap;
}
.subtitle-file {
  margin-top: 1rem;
}
.subtitle-file h4 {
  margin: 0.5rem 0;
  color: #4b5563;
  font-size: 0.9rem;
}

/* 关键词查找区域 */
.search-section {
  background: #f9fafb;
  padding: 1rem;
  border-radius: 0.5rem;
  border: 1px solid #e5e7eb;
}
.search-section h3 {
  margin-top: 0;
  color: #1f2933;
  font-size: 1rem;
  border-bottom: 1px solid #e5e7eb;
  padding-bottom: 0.5rem;
}
.search-form {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 0.75rem;
}
.search-result {
  margin-top: 1rem;
  /* 搜索结果也加动画 */
  animation: panel-fade-in 300ms ease;
}
.search-result h4 {
  margin: 0.5rem 0;
  color: #4b5563;
  font-size: 0.9rem;
}
.result-list {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 0.375rem;
  padding: 0.75rem;
  max-height: 150px;
  overflow-y: auto;
}
.result-item {
  padding: 0.5rem 0;
  border-bottom: 1px dashed #e5e7eb;
}
.result-item:last-child {
  border-bottom: none;
}
.result-item p {
  margin: 0.25rem 0;
  font-size: 0.85rem;
}
.no-result {
  margin-top: 1rem;
  color: #6b7280;
  font-size: 0.85rem;
  text-align: center;
}

/* 表格样式 */
.result-box table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.85rem;
}
.result-box th,
.result-box td {
  padding: 0.4rem 0.6rem;
  border: 1px solid #e5e7eb;
  text-align: left;
}
.result-box th {
  background-color: #f3f4f6;
}

/* 下载区域样式 */
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
  margin-top: 0.3rem;
  margin-bottom: 0;
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .transcription-layout {
    grid-template-columns: 1fr;
  }
  .search-form {
    grid-template-columns: 1fr 1fr;
  }
  .search-btn {
    grid-column: 1 / -1;
    margin-top: 0;
  }
}
@media (max-width: 640px) {
  .main-container {
    padding: 1rem;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
  .search-form {
    grid-template-columns: 1fr;
  }
}
</style>
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

// ======================== 文件上传 ========================
const globalFile = ref(null)
const globalFileName = ref('Not selected file')

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
const transSubtitleFormat = ref('SRT')
const transAddTimestampToFilename = ref(false)
// 新增：参数面板折叠状态
const transShowParams = ref(true)

// 高级子面板折叠状态
const showBgmSubpanel = ref(true)
const showVadSubpanel = ref(true)
const showDiarizationSubpanel = ref(true)
const showWhisperSubpanel = ref(true)

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

// VAD 参数
const transVadThreshold = ref(0.5)
const transVadMinSpeechMs = ref(250)
const transVadMaxSpeechSec = ref('9999')
const transVadMinSilenceMs = ref(2000)
const transVadSpeechPadMs = ref(400)

// BGM 参数
const transBgmUvrModelSize = ref('UVR-MDX-NET-Inst_HQ_4')
const transBgmUvrDevice = ref('cuda')
const transBgmSegmentSize = ref(256)
const transBgmSaveFile = ref(false)
const transBgmEnableOffload = ref(true)

// 说话人分离参数
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

function formatSrtTime(seconds) {
  const date = new Date(seconds * 1000)
  const hours = date.getUTCHours().toString().padStart(2, '0')
  const minutes = date.getUTCMinutes().toString().padStart(2, '0')
  const secs = date.getUTCSeconds().toString().padStart(2, '0')
  const ms = date.getUTCMilliseconds().toString().padStart(3, '0')
  return `${hours}:${minutes}:${secs},${ms}`
}

function downloadSubtitle() {
  if (!transSubtitleContent.value) {
    transError.value = '暂无字幕内容可下载'
    return
  }

  let filename = globalFile.value ? globalFile.value.name.replace(/\.[^/.]+$/, '') : 'subtitle'
  if (transAddTimestampToFilename.value) {
    const timestamp = new Date().toISOString().replace(/[-:\.T]/g, '').slice(0, 14)
    filename += `_${timestamp}`
  }
  filename += `.${transSubtitleFormat.value.toLowerCase()}`

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

async function handleTranscription() {
  if (!globalFile.value) {
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
      file: globalFile.value,
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

onMounted(() => {
  restoreTranscriptionTask()
})

function formatSeconds(seconds) {
  if (seconds == null) return '-'
  return `${seconds.toFixed(2)}s`
}
</script>

<template>
  <div class="main-container">
    <!-- 功能说明文字 -->
    <div class="intro-text">
      一键上传媒体文件或指定文本文件，按需配置Whisper/VAD等参数，点击开始即可生成字幕并自动执行RAG纠错。
    </div>

    <!-- 1. 选择输入源 -->
    <section class="panel input-source-panel">
      <h2>1. 选择输入源</h2>
      <div class="upload-container">
        <div class="upload-area">
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><g id="SVGRepo_bgCarrier" stroke-width="0"></g><g id="SVGRepo_tracerCarrier" stroke-linecap="round" stroke-linejoin="round"></g><g id="SVGRepo_iconCarrier">
            <path d="M7 10V9C7 6.23858 9.23858 4 12 4C14.7614 4 17 6.23858 17 9V10C19.2091 10 21 11.7909 21 14C21 15.4806 20.1956 16.8084 19 17.5M7 10C4.79086 10 3 11.7909 3 14C3 15.4806 3.8044 16.8084 5 17.5M7 10C7.43285 10 7.84965 10.0688 8.24006 10.1959M12 12V21M12 12L15 15M12 12L9 15" stroke="#000000" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path> </g></svg>
            <p>将文件拖放此处<br>或 点击上传</p>
            <label for="global-file" class="upload-btn">点击上传</label>
            <input id="global-file" type="file" accept="audio/*,video/*" @change="onGlobalFileChange" class="file-input">
        </div>
        <p class="selected-file">当前选择: {{ globalFileName }}</p>
      </div>
    </section>

    <!-- 2. 转录参数 + 高级参数 -->
    <section class="panel transcription-panel">
      <h2>2. 运行任务</h2>

      <!-- 转录参数设置（可选） -->
      <div class="param-panel-toggle">
        <div class="param-panel-header" @click="transShowParams = !transShowParams">
          <h3>转录参数设置（可选） <span>{{ transShowParams ? '▼' : '▶' }}</span></h3>
        </div>
        <div v-show="transShowParams" class="form-grid param-grid">
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
      </div>

      <!-- 高级参数 -->
      <div class="advanced-panel">
        <button type="button" class="advanced-toggle" @click="transShowAdvanced = !transShowAdvanced">
          {{ transShowAdvanced ? '收起高级参数' : '展开高级参数' }}
        </button>
        <div v-if="transShowAdvanced" class="advanced-content">
          <!-- 背景消除器设置 -->
          <div class="advanced-subpanel">
            <div class="subpanel-header" @click="showBgmSubpanel = !showBgmSubpanel">
              <h4>背景消除器设置 <span>{{ showBgmSubpanel ? '▼' : '▶' }}</span></h4>
            </div>
            <div v-show="showBgmSubpanel" class="subpanel-content form-grid">
              <div class="form-item">
                <label class="checkbox">
                  <input v-model="transUseBgm" type="checkbox" /> 去除背景音乐
                </label>
              </div>
              <div class="form-item">
                <label>
                  模型选择
                  <select v-model="transBgmUvrModelSize">
                    <option value="UVR-MDX-NET-Inst_HQ_4">UVR-MDX-NET-Inst_HQ_4</option>
                    <option value="UVR-MDX-NET-Inst_3">UVR-MDX-NET-Inst_3</option>
                  </select>
                </label>
              </div>
              <div class="form-item">
                <label>
                  设备
                  <select v-model="transBgmUvrDevice">
                    <option value="cpu">cpu</option>
                    <option value="cuda">cuda</option>
                    <option value="xpu">xpu</option>
                  </select>
                </label>
              </div>
              <div class="form-item">
                <label>
                  Segment Size
                  <input v-model.number="transBgmSegmentSize" type="number" min="1" step="1" />
                </label>
              </div>
              <div class="form-item">
                <label class="checkbox">
                  <input v-model="transBgmSaveFile" type="checkbox" /> 导出分离出的音频文件
                </label>
              </div>
              <div class="form-item">
                <label class="checkbox">
                  <input v-model="transBgmEnableOffload" type="checkbox" /> 完成后卸载模型
                </label>
              </div>
            </div>
          </div>

          <!-- 语音检测设置 -->
          <div class="advanced-subpanel">
            <div class="subpanel-header" @click="showVadSubpanel = !showVadSubpanel">
              <h4>语音检测设置 <span>{{ showVadSubpanel ? '▼' : '▶' }}</span></h4>
            </div>
            <div v-show="showVadSubpanel" class="subpanel-content form-grid">
              <div class="form-item">
                <label class="checkbox">
                  <input v-model="transUseVad" type="checkbox" /> 启用Silero语音活动检测(VAD)
                </label>
              </div>
              <div class="form-item">
                <label>
                  Speech Threshold
                  <div class="slider-group">
                    <input v-model.number="transVadThreshold" type="range" min="0" max="1" step="0.01" />
                    <span class="slider-value">{{ transVadThreshold }}</span>
                  </div>
                </label>
              </div>
              <div class="form-item">
                <label>
                  Minimum Speech Duration (ms)
                  <input v-model.number="transVadMinSpeechMs" type="number" min="0" step="10" />
                </label>
              </div>
              <div class="form-item">
                <label>
                  Maximum Speech Duration (s)
                  <input v-model="transVadMaxSpeechSec" type="text" />
                </label>
              </div>
              <div class="form-item">
                <label>
                  Minimum Silence Duration (ms)
                  <input v-model.number="transVadMinSilenceMs" type="number" min="0" step="10" />
                </label>
              </div>
              <div class="form-item">
                <label>
                  Speech Padding (ms)
                  <input v-model.number="transVadSpeechPadMs" type="number" min="0" step="10" />
                </label>
              </div>
            </div>
          </div>

          <!-- 说话人分离设置 -->
          <div class="advanced-subpanel">
            <div class="subpanel-header" @click="showDiarizationSubpanel = !showDiarizationSubpanel">
              <h4>说话人分离设置 <span>{{ showDiarizationSubpanel ? '▼' : '▶' }}</span></h4>
            </div>
            <div v-show="showDiarizationSubpanel" class="subpanel-content form-grid">
              <div class="form-item">
                <label class="checkbox">
                  <input v-model="transUseDiarization" type="checkbox" /> 进行说话人分离处理
                </label>
              </div>
              <div class="form-item">
                <label>
                  设备
                  <select v-model="transDiarizationDevice">
                    <option value="cpu">cpu</option>
                    <option value="cuda">cuda</option>
                    <option value="xpu">xpu</option>
                  </select>
                </label>
              </div>
              <div class="form-item full-width">
                <label>
                  HuggingFace令牌
                  <input
                    v-model="transDiarizationHfToken"
                    type="text"
                    placeholder="请在这里输入您的HuggingFace令牌，必须先在https://huggingface.co/settings/tokens建立一个上限额度为1的'模型下载'令牌。"
                  />
                </label>
              </div>
              <div class="form-item">
                <label class="checkbox">
                  <input v-model="transDiarizationEnableOffload" type="checkbox" /> 完成后卸载模型
                </label>
              </div>
            </div>
          </div>

          <!-- Whisper高级参数 -->
          <div class="advanced-subpanel">
            <div class="subpanel-header" @click="showWhisperSubpanel = !showWhisperSubpanel">
              <h4>Whisper高级参数 <span>{{ showWhisperSubpanel ? '▼' : '▶' }}</span></h4>
            </div>
            <div v-show="showWhisperSubpanel" class="subpanel-content form-grid">
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
            </div>
          </div>
        </div>
      </div>

      <!-- 运行按钮 -->
      <div class="actions">
        <button type="button" :disabled="transLoading || !globalFile" @click="handleTranscription" class="run-btn">
          {{ transLoading ? '处理中...' : '开始运行' }}
        </button>
      </div>

      <!-- 状态信息 -->
      <div class="status" v-if="transTaskId || transError">
        <p v-if="transTaskId">任务 ID：{{ transTaskId }}</p>
        <p v-if="transStatus">状态：{{ transStatus }}，进度：{{ (transProgress * 100).toFixed(0) }}%</p>
        <p v-if="transDuration != null">耗时：{{ formatSeconds(transDuration) }}</p>
        <p v-if="transError" class="error">错误：{{ transError }}</p>
      </div>
    </section>

    <!-- 3. 输出与纠错 + 关键词查找 -->
    <section class="panel output-panel">
      <div class="output-layout">
        <!-- 输出与纠错 -->
        <div class="output-left">
          <h2>输出与纠错</h2>
          <div class="output-box">
            <h4>RAG纠错文本</h4>
            <div class="text-content">
              <pre>{{ transSubtitleContent || '运行后展示Qwen RAG纠错后的文本' }}</pre>
            </div>
          </div>
          <div class="subtitle-file">
            <h4>生成的字幕文件</h4>
            <div class="subtitle-actions">
              <button
                type="button"
                class="download-btn"
                @click="downloadSubtitle"
                :disabled="!transSubtitleContent"
              >
                <span class="file-icon">📄</span> 下载
              </button>
              <button class="open-dir-btn" :disabled="!transSubtitleContent">
                打开输出目录
              </button>
            </div>
          </div>
        </div>

        <!-- 字幕关键词查找 -->
        <div class="output-right">
          <h2>字幕关键词查找</h2>
          <div class="search-section">
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
  </div>
</template>

<style scoped>
.main-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 2rem;
  max-width: 1400px;
  margin: 0 auto;
  font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background-color: #f5f5f5;
}

.intro-text {
  color: #666;
  font-size: 0.95rem;
  line-height: 1.5;
  margin-bottom: 0.5rem;
}

.panel {
  background: #ffffff;
  border-radius: 0.5rem;
  padding: 1.2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  animation: panel-fade-in 480ms ease;
}
.panel h2 {
  margin-top: 0;
  color: #333;
  font-size: 1.1rem;
  border-bottom: 1px solid #eee;
  padding-bottom: 0.5rem;
  margin-bottom: 1rem;
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

.input-source-panel .upload-container {
  display: flex;
  flex-direction: column;
  align-items: center;
}
.upload-area {
  width: 300px;
  height: 200px;
  border: 2px dashed #ccc;
  border-radius: 0.5rem;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.8rem;
  cursor: pointer;
  transition: border-color 0.2s;
}
.upload-area:hover {
  border-color: #3b82f6;
}
.upload-area svg {
  height: 40px;
  color: #666;
}
.upload-area p {
  margin: 0;
  text-align: center;
  color: #666;
  font-size: 0.9rem;
}
.upload-btn {
  padding: 0.4rem 1rem;
  background-color: #f0f0f0;
  border-radius: 0.3rem;
  color: #333;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s;
}
.upload-btn:hover {
  background-color: #e0e0e0;
}
.file-input {
  display: none;
}
.selected-file {
  margin-top: 0.8rem;
  color: #666;
  font-size: 0.9rem;
}

.param-panel-toggle {
  margin-bottom: 1rem;
}
.param-panel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
  color: #333;
  font-size: 1rem;
  font-weight: 500;
}
.param-panel-header span {
  font-size: 0.8rem;
  color: #666;
}
.param-grid {
  background: #f9f9f9;
  padding: 1rem;
  border-radius: 0.3rem;
  margin-top: 0.5rem;
}

.advanced-panel {
  margin-top: 1rem;
  border-top: 1px dashed #eee;
  padding-top: 1rem;
}
.advanced-toggle {
  padding: 0.4rem 0.8rem;
  border: 1px solid #ddd;
  border-radius: 0.3rem;
  background-color: #f5f5f5;
  color: #333;
  cursor: pointer;
  font-size: 0.9rem;
  transition: background-color 0.2s;
}
.advanced-toggle:hover {
  background-color: #e9e9e9;
}
.advanced-content {
  margin-top: 1rem;
}
.advanced-subpanel {
  margin-bottom: 1rem;
  border: 1px solid #eee;
  border-radius: 0.3rem;
  overflow: hidden;
}
.subpanel-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.6rem 0.8rem;
  background-color: #f5f5f5;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  color: #333;
}
.subpanel-header span {
  font-size: 0.8rem;
  color: #666;
}
.subpanel-content {
  padding: 1rem;
  background-color: #fff;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.8rem 1rem;
}
.form-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
  font-size: 0.9rem;
}
.form-item.full-width {
  grid-column: 1 / -1;
}
label {
  color: #555;
}
label.checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.4rem;
}
input[type='text'],
input[type='number'],
select,
textarea {
  padding: 0.4rem 0.5rem;
  border: 1px solid #ddd;
  border-radius: 0.3rem;
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

.slider-group {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}
.slider-group input[type='range'] {
  flex: 1;
}
.slider-value {
  min-width: 30px;
  text-align: center;
  color: #555;
}

.actions {
  margin-top: 1rem;
}
.run-btn {
  padding: 0.6rem 1.5rem;
  background-color: #3b82f6;
  color: white;
  border: none;
  border-radius: 0.3rem;
  font-size: 1rem;
  cursor: pointer;
  transition: background-color 0.2s;
}
.run-btn:disabled {
  background-color: #93c5fd;
  cursor: not-allowed;
}

.status {
  margin-top: 1rem;
  padding: 0.8rem;
  background-color: #f9f9f9;
  border-radius: 0.3rem;
  font-size: 0.9rem;
  color: #555;
}
.status .error {
  color: #dc2626;
  margin: 0.3rem 0 0;
}

.output-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.5rem;
}
.output-box {
  margin-bottom: 1rem;
}
.output-box h4, .subtitle-file h4 {
  margin: 0 0 0.5rem;
  color: #555;
  font-size: 0.95rem;
}
.text-content {
  background-color: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 0.3rem;
  padding: 0.8rem;
  max-height: 200px;
  overflow-y: auto;
  font-size: 0.9rem;
  white-space: pre-wrap;
}
.subtitle-actions {
  display: flex;
  gap: 0.8rem;
}
.download-btn, .open-dir-btn {
  padding: 0.4rem 1rem;
  border: none;
  border-radius: 0.3rem;
  font-size: 0.9rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}
.download-btn {
  background-color: #22c55e;
  color: white;
}
.download-btn:disabled {
  background-color: #86efac;
  cursor: not-allowed;
}
.open-dir-btn {
  background-color: #6b7280;
  color: white;
}
.open-dir-btn:disabled {
  background-color: #9ca3af;
  cursor: not-allowed;
}

/* 关键词查找样式 */
.search-form {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.search-btn {
  padding: 0.5rem 1rem;
  background-color: #f97316;
  color: white;
  border: none;
  border-radius: 0.3rem;
  font-size: 0.9rem;
  cursor: pointer;
  transition: background-color 0.2s;
}
.search-btn:hover {
  background-color: #ea580c;
}
.search-result {
  margin-top: 1rem;
}
.result-list {
  background-color: #f9f9f9;
  border: 1px solid #eee;
  border-radius: 0.3rem;
  padding: 0.8rem;
  max-height: 150px;
  overflow-y: auto;
}
.result-item {
  padding: 0.5rem 0;
  border-bottom: 1px dashed #eee;
  font-size: 0.9rem;
}
.result-item:last-child {
  border-bottom: none;
}
.no-result {
  color: #666;
  font-size: 0.9rem;
  text-align: center;
  padding: 0.8rem;
  background-color: #f9f9f9;
  border-radius: 0.3rem;
}

/* 响应式适配 */
@media (max-width: 1024px) {
  .output-layout {
    grid-template-columns: 1fr;
  }
}
@media (max-width: 640px) {
  .main-container {
    padding: 1rem;
  }
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
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

// ======================== 语音转写相关 ========================
const LS_TRANS_TASK_KEY = 'whisper_transcription_task'

// 基础参数
const transFile = ref(null)
const transModelSize = ref('large-v2')
const transLang = ref('')
const transTranslate = ref(false)
const transUseVad = ref(false)
const transUseDiarization = ref(false)
const transUseBgm = ref(false)
const transShowAdvanced = ref(false)

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

const transText = computed(() => {
  if (!Array.isArray(transResult.value)) return ''
  return transResult.value.map((seg) => seg.text || '').join('\n')
})

function formatSeconds(seconds) {
  if (seconds == null) return '-'
  return `${seconds.toFixed(2)}s`
}

function onTransFileChange(event) {
  const [file] = event.target.files || []
  transFile.value = file || null
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
  if (!transFile.value) {
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
      file: transFile.value,
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

// ======================== VAD检测相关 ========================
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

// ======================== BGM分离相关 ========================
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

// 初始化恢复所有任务
onMounted(() => {
  restoreTranscriptionTask()
  restoreVadTask()
  restoreBgmTask()
})
</script>

<template>
  <div class="main-container">
    <!-- 语音转写面板 -->
    <section class="panel">
      <h2>语音转写</h2>
      <div class="form-grid">
        <div class="form-item full-width">
          <label>
            音频 / 视频文件：
            <input type="file" accept="audio/*,video/*" @change="onTransFileChange" />
          </label>
        </div>

        <div class="form-item">
          <label>
            模型大小：
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
            语言（留空自动检测）：
            <input v-model="transLang" type="text" placeholder="例如: en, zh" />
          </label>
        </div>

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
      </div>

      <div class="advanced-panel">
        <button type="button" class="advanced-toggle" @click="transShowAdvanced = !transShowAdvanced">
          {{ transShowAdvanced ? '收起高级参数' : '展开全部高级参数' }}
        </button>

        <div v-if="transShowAdvanced" class="form-grid advanced-grid">
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

      <div class="actions">
        <button type="button" :disabled="transLoading" @click="handleTranscription">
          {{ transLoading ? '处理中...' : '开始转写' }}
        </button>
      </div>

      <div class="status" v-if="transTaskId || transError">
        <p v-if="transTaskId">任务 ID：{{ transTaskId }}</p>
        <p v-if="transStatus">状态：{{ transStatus }}，进度：{{ (transProgress * 100).toFixed(0) }}%</p>
        <p v-if="transDuration != null">耗时：{{ formatSeconds(transDuration) }}</p>
        <p v-if="transError" class="error">错误：{{ transError }}</p>
      </div>

      <div v-if="transText" class="result-box">
        <h3>转写结果</h3>
        <pre>{{ transText }}</pre>
      </div>
    </section>

    <!-- VAD检测面板 -->
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

    <!-- BGM分离面板 -->
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
  </div>
</template>

<style scoped>
/* 主容器样式，增加面板间距 */
.main-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* 通用面板样式 */
.panel {
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem 1.5rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
  animation: panel-fade-in 480ms ease;
}

/* 语音转写高级参数面板 */
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
}

.advanced-grid {
  margin-top: 0.75rem;
}

.panel h2 {
  margin-top: 0;
}

/* 表单网格样式 */
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

.checkbox {
  flex-direction: row;
  align-items: center;
  gap: 0.4rem;
}

/* 输入控件样式 */
input[type='text'],
input[type='number'],
input[type='file'],
select,
textarea {
  padding: 0.35rem 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  font-size: 0.9rem;
}

/* 按钮样式 */
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

/* 状态提示样式 */
.status {
  font-size: 0.85rem;
  color: #4b5563;
}

.error {
  color: #b91c1c;
}

/* 结果面板样式 */
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

/* VAD检测表格样式 */
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

/* BGM分离下载样式 */
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

/* 动画效果 */
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
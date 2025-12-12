// 转写 / VAD / BGM 任务相关接口

import { buildQuery, requestJson, getApiBase } from './client'

// 创建转写任务
export async function createTranscriptionTask({ file, whisperParams = {}, vadParams = {}, bgmParams = {}, diarizationParams = {} }) {
  if (!file) {
    throw new Error('请先选择要上传的音频/视频文件')
  }

  const allParams = {
    // WhisperParams
    ...whisperParams,
    // VadParams
    ...vadParams,
    // BGMSeparationParams（流水线内部）
    ...bgmParams,
    // DiarizationParams
    ...diarizationParams,
  }

  const query = buildQuery(allParams)
  const formData = new FormData()
  formData.append('file', file)

  return requestJson(`/transcription/${query}`, {
    method: 'POST',
    body: formData,
  })
}

// 创建 VAD 任务
export async function createVadTask({ file, vadParams = {} }) {
  if (!file) {
    throw new Error('请先选择要上传的音频/视频文件')
  }

  const query = buildQuery(vadParams)
  const formData = new FormData()
  formData.append('file', file)

  return requestJson(`/vad/${query}`, {
    method: 'POST',
    body: formData,
  })
}

// 创建 BGM 分离任务
export async function createBgmSeparationTask({ file, bgmParams = {} }) {
  if (!file) {
    throw new Error('请先选择要上传的音频/视频文件')
  }

  const query = buildQuery(bgmParams)
  const formData = new FormData()
  formData.append('file', file)

  return requestJson(`/bgm-separation/${query}`, {
    method: 'POST',
    body: formData,
  })
}

// 轮询任务状态，直到完成 / 失败 / 超时
export async function pollTask(identifier, {
  intervalMs = 2000,
  maxAttempts = 60,
  onUpdate,
} = {}) {
  let lastStatus = null
  for (let i = 0; i < maxAttempts; i++) {
    const status = await requestJson(`/task/${identifier}`)
    lastStatus = status

    if (typeof onUpdate === 'function') {
      try {
        onUpdate(status)
      } catch (_) {
        // 忽略 UI 回调中的异常
      }
    }

    if (status.status === 'completed') {
      return status
    }

    if (status.status === 'failed') {
      const msg = status.error || '任务失败'
      throw new Error(msg)
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }

  throw new Error('轮询任务超时')
}

// 下载 BGM 分离结果 ZIP
export async function downloadBgmZip(identifier) {
  const API_BASE = getApiBase()
  const res = await fetch(`${API_BASE}/task/file/${identifier}`)
  if (!res.ok) {
    throw new Error(`下载失败：HTTP ${res.status}`)
  }
  return res.blob()
}

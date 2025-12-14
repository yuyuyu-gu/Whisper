// 转写 / VAD / BGM 任务相关接口
import { buildQuery, requestJson, getApiBase } from './client'

// ===================== 核心常量：对齐后端 TaskStatus 枚举 =====================
export const TASK_STATUS = {
  QUEUED: 'QUEUED',
  IN_PROGRESS: 'IN_PROGRESS',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED'
}

// ===================== 通用工具函数：处理 FormData 请求（避免 Content-Type 冲突） =====================
/**
 * 发送 FormData 类型的请求（覆盖默认 Content-Type）
 * @param {string} url 接口路径
 * @param {FormData} formData 表单数据
 * @returns {Promise<any>} 接口响应
 */
async function requestFormData(url, formData) {
  const API_BASE = getApiBase()
  const res = await fetch(`${API_BASE}${url}`, {
    method: 'POST',
    body: formData,
    // 不设置 Content-Type，由浏览器自动生成（包含 boundary）
    headers: {}
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(error.detail || `请求失败：HTTP ${res.status}`)
  }

  return res.json()
}

// ===================== 业务接口：转写任务 =====================
/**
 * 创建转写任务
 * @param {Object} params 任务参数
 * @param {File} params.file 上传的音视频文件
 * @param {Object} [params.whisperParams={}] Whisper 转写参数
 * @param {Object} [params.vadParams={}] VAD 过滤参数
 * @param {Object} [params.bgmParams={}] BGM 分离参数（流水线内部）
 * @param {Object} [params.diarizationParams={}] 说话人分离参数
 * @returns {Promise<{identifier: string, status: string}>} 任务信息
 */
export async function createTranscriptionTask({ file, whisperParams = {}, vadParams = {}, bgmParams = {}, diarizationParams = {} }) {
  if (!file) {
    throw new Error('请先选择要上传的音频/视频文件')
  }

  // 1. 合并所有参数（用于拼接查询参数）
  const allParams = {
    ...whisperParams,
    ...vadParams,
    ...bgmParams,
    ...diarizationParams,
  }

  // 2. 构建查询参数（路径 → 查询参数，对齐后端规则）
  const query = buildQuery(allParams)
  const url = `/transcription/${query ? `?${query}` : ''}`

  // 3. 构建 FormData（仅传文件）
  const formData = new FormData()
  formData.append('file', file)

  // 4. 发送 FormData 请求（避免默认 Content-Type 冲突）
  return requestFormData(url, formData)
}

// ===================== 业务接口：VAD 任务 =====================
/**
 * 创建 VAD 检测任务
 * @param {Object} params 任务参数
 * @param {File} params.file 上传的音视频文件
 * @param {Object} [params.vadParams={}] VAD 检测参数
 * @returns {Promise<{identifier: string, status: string}>} 任务信息
 */
export async function createVadTask({ file, vadParams = {} }) {
  if (!file) {
    throw new Error('请先选择要上传的音频/视频文件')
  }

  // 1. 构建查询参数（路径 → 查询参数，对齐后端规则）
  const query = buildQuery(vadParams)
  const url = `/vad/${query ? `?${query}` : ''}`

  // 2. 构建 FormData
  const formData = new FormData()
  formData.append('file', file)

  // 3. 发送 FormData 请求
  return requestFormData(url, formData)
}

// ===================== 业务接口：BGM 分离任务 =====================
/**
 * 创建 BGM 分离任务
 * @param {Object} params 任务参数
 * @param {File} params.file 上传的音视频文件
 * @param {Object} [params.bgmParams={}] BGM 分离参数
 * @returns {Promise<{identifier: string, status: string}>} 任务信息
 */
export async function createBgmSeparationTask({ file, bgmParams = {} }) {
  if (!file) {
    throw new Error('请先选择要上传的音频/视频文件')
  }

  // 1. 构建查询参数（对齐后端规则：查询参数而非路径参数）
  const query = buildQuery(bgmParams)
  const url = `/bgm-separation/${query ? `?${query}` : ''}`

  // 2. 构建 FormData
  const formData = new FormData()
  formData.append('file', file)

  // 3. 发送 FormData 请求
  return requestFormData(url, formData)
}

// ===================== 业务接口：获取任务状态 =====================
/**
 * 单次获取任务状态
 * @param {string} identifier 任务ID
 * @returns {Promise<Object>} 任务状态详情
 */
export async function getTaskStatus(identifier) {
  if (!identifier) {
    throw new Error('缺少任务标识符')
  }
  return requestJson(`/task/${identifier}`)
}

// ===================== 业务接口：轮询任务状态 =====================
/**
 * 轮询任务状态，直到完成/失败/超时
 * @param {string} identifier 任务ID
 * @param {Object} [options={}] 轮询配置
 * @param {number} [options.intervalMs=2000] 轮询间隔（毫秒）
 * @param {number} [options.maxAttempts=60] 最大轮询次数（超时阈值）
 * @param {Function} [options.onUpdate] 状态更新回调（参数：当前状态）
 * @returns {Promise<Object>} 最终任务状态
 */
export async function pollTask(identifier, {
  intervalMs = 2000,
  maxAttempts = 60,
  onUpdate,
} = {}) {
  if (!identifier) {
    throw new Error('缺少任务标识符')
  }

  let lastStatus = null
  let simulatedProgress = 0 // 模拟进度（后端暂未返回progress时使用）

  for (let i = 0; i < maxAttempts; i++) {
    try {
      const status = await getTaskStatus(identifier)
      lastStatus = status

      // 处理进度：优先用后端返回的progress，无则模拟
      const progress = status.progress ?? (() => {
        if (status.status === TASK_STATUS.IN_PROGRESS) {
          simulatedProgress = Math.min(simulatedProgress + (100 / maxAttempts), 95)
          return simulatedProgress / 100
        }
        if (status.status === TASK_STATUS.COMPLETED) {
          return 1.0
        }
        return 0
      })()

      // 状态更新回调（补充progress字段）
      if (typeof onUpdate === 'function') {
        onUpdate({ ...status, progress })
      }

      // 任务完成/失败：终止轮询
      if (status.status === TASK_STATUS.COMPLETED) {
        return { ...status, progress: 1.0 }
      }
      if (status.status === TASK_STATUS.FAILED) {
        const msg = status.error || '任务失败'
        throw new Error(msg)
      }
    } catch (err) {
      // 非任务失败的异常（如网络错误），继续轮询
      if (err.message !== '任务失败') {
        console.warn(`轮询任务 ${identifier} 出错：`, err)
      } else {
        throw err
      }
    }

    await new Promise((resolve) => setTimeout(resolve, intervalMs))
  }

  // 超时处理
  const timeoutMsg = `轮询任务 ${identifier} 超时（最大尝试次数：${maxAttempts}）`
  if (lastStatus && typeof onUpdate === 'function') {
    onUpdate({ ...lastStatus, status: TASK_STATUS.FAILED, error: timeoutMsg, progress: 0 })
  }
  throw new Error(timeoutMsg)
}

// ===================== 业务接口：下载 BGM 分离结果 =====================
/**
 * 下载 BGM 分离结果 ZIP 包
 * @param {string} identifier 任务ID
 * @returns {Promise<Blob>} ZIP 文件 Blob 数据
 */
export async function downloadBgmZip(identifier) {
  if (!identifier) {
    throw new Error('缺少任务标识符')
  }

  const API_BASE = getApiBase()
  const res = await fetch(`${API_BASE}/task/file/${identifier}`, {
    method: 'GET',
    headers: {
      'Accept': 'application/zip'
    }
  })

  // 详细错误处理（对齐后端返回的错误信息）
  if (!res.ok) {
    const errorText = await res.text().catch(() => res.statusText)
    throw new Error(`下载失败：${res.status} - ${errorText || '未知错误'}`)
  }

  return res.blob()
}

/**
 * 批量获取任务列表（分页+筛选）
 * @param {Object} params 筛选和分页参数
 * @returns {Promise<Object>} 任务列表和总数
 */
export async function getTaskStatuses(params) {
  const query = buildQuery(params);
  return requestJson(`/tasks${query ? `?${query}` : ''}`);
}

/**
 * 删除任务
 * @param {string} identifier 任务ID
 * @returns {Promise<Object>} 删除结果
 */
export async function deleteTask(identifier) {
  if (!identifier) {
    throw new Error('缺少任务标识符');
  }
  const API_BASE = getApiBase();
  const res = await fetch(`${API_BASE}/task/${identifier}`, {
    method: 'DELETE'
  });

  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || `删除失败：HTTP ${res.status}`);
  }

  return res.json();
}
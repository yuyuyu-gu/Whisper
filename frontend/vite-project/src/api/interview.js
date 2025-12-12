// 访谈助手 / Interview RAG 相关接口

import { requestJson } from './client'

// 创建 / 更新访谈会话
export async function createOrUpdateInterviewSession({ sessionId, combinedText, files } = {}) {
  const payload = {
    session_id: sessionId || undefined,
    combined_text: combinedText || undefined,
    files: files || undefined,
  }

  return requestJson('/interview/session', {
    method: 'POST',
    body: JSON.stringify(payload),
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

// 访谈问答
export async function chatWithInterview({
  sessionId,
  payload,
  message,
  history,
  model,
  topK,
  similarityThreshold,
  ollamaBaseUrl,
} = {}) {
  if (!message) {
    throw new Error('message 不能为空')
  }

  const body = {
    session_id: sessionId || undefined,
    payload: payload || undefined,
    message,
    history: history || undefined,
    model: model || undefined,
    top_k: topK || undefined,
    similarity_threshold: similarityThreshold || undefined,
    ollama_base_url: ollamaBaseUrl || undefined,
  }

  return requestJson('/interview/chat', {
    method: 'POST',
    body: JSON.stringify(body),
    headers: {
      'Content-Type': 'application/json',
    },
  })
}

// 查询访谈会话信息
export async function getInterviewSessionInfo(sessionId) {
  if (!sessionId) {
    throw new Error('sessionId 不能为空')
  }
  return requestJson(`/interview/session/${encodeURIComponent(sessionId)}`, {
    method: 'GET',
  })
}

// 清理访谈会话
export async function clearInterviewSession(sessionId) {
  if (!sessionId) {
    throw new Error('sessionId 不能为空')
  }
  return requestJson(`/interview/session/${encodeURIComponent(sessionId)}`, {
    method: 'DELETE',
  })
}

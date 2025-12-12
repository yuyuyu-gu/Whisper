// 通用 HTTP 客户端封装（基础地址、查询拼接、JSON 请求）

let API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export function setApiBase(base) {
  if (base) {
    API_BASE = base.replace(/\/$/, '')
  }
}

export function getApiBase() {
  return API_BASE
}

export function buildQuery(params = {}) {
  const searchParams = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return
    searchParams.append(key, String(value))
  })
  const queryString = searchParams.toString()
  return queryString ? `?${queryString}` : ''
}

export async function requestJson(path, { method = 'GET', body, headers } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    body,
    headers,
  })

  if (!res.ok) {
    let message = `HTTP ${res.status}`
    try {
      const data = await res.json()
      if (data && data.detail) {
        message += `: ${data.detail}`
      }
    } catch (_) {
      // ignore
    }
    throw new Error(message)
  }

  return res.json()
}

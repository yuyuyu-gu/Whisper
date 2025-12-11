// 认证相关 API 封装，对应后端 /auth 路由

let API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

export function setAuthApiBase(base) {
  if (base) {
    API_BASE = base.replace(/\/$/, '')
  }
}

async function requestJson(path, { method = 'GET', body, headers } = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    method,
    body,
    headers: {
      'Content-Type': 'application/json',
      ...(headers || {}),
    },
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

// 用户注册
export async function registerUser({ username, password }) {
  return requestJson('/auth/register', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

// 用户登录
export async function loginUser({ username, password }) {
  return requestJson('/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

// 获取待审核用户列表（建议仅管理员界面调用）
export async function getPendingUsers() {
  return requestJson('/auth/pending', {
    method: 'GET',
  })
}

// 审批通过用户（管理员）
export async function approveUser({ username }) {
  return requestJson('/auth/approve', {
    method: 'POST',
    body: JSON.stringify({ username }),
  })
}

// 获取所有用户列表（不含默认管理员）
export async function getAllUsers() {
  return requestJson('/auth/users', {
    method: 'GET',
  })
}

// 赋予管理员权限（仅主账号）
export async function grantAdmin({ targetUsername, currentUsername }) {
  return requestJson('/auth/grant-admin', {
    method: 'POST',
    body: JSON.stringify({
      target_username: targetUsername,
      current_username: currentUsername,
    }),
  })
}

// 撤销管理员权限（仅主账号）
export async function revokeAdmin({ targetUsername, currentUsername }) {
  return requestJson('/auth/revoke-admin', {
    method: 'POST',
    body: JSON.stringify({
      target_username: targetUsername,
      current_username: currentUsername,
    }),
  })
}

<script setup>
import { ref, onMounted } from 'vue'
import {
  getPendingUsers,
  approveUser,
  getAllUsers,
  grantAdmin,
  revokeAdmin,
} from '../../api/auth.js'

/* 核心状态 */
const pendingUsers = ref([])
const allUsers = ref([])
const loading = ref(false)
const error = ref('')
const successMsg = ref('')

/* 选择器绑定 */
const selectedPending = ref('') // 待审核用户选择
const selectedUser = ref('')    // 权限管理用户选择
const currentUsername = ref('') // 主账号用户名（用于授权验证）

/* 按钮loading状态（防止重复点击） */
const approveLoading = ref(false)
const grantLoading = ref(false)
const revokeLoading = ref(false)

/**
 * 加载所有用户数据（带loading和错误处理）
 */
async function loadData() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    // 并行请求提升性能
    const [pendingRes, usersRes] = await Promise.all([
      getPendingUsers(),
      getAllUsers()
    ])
    pendingUsers.value = pendingRes.pending || []
    allUsers.value = usersRes.users || []
    successMsg.value = '数据加载成功'
  } catch (e) {
    error.value = e.message || '加载用户数据失败'
    console.error('加载数据失败：', e)
  } finally {
    loading.value = false
  }
}

/**
 * 审批用户（带loading和状态反馈）
 */
async function handleApprove(username) {
  if (!username || approveLoading.value) return
  approveLoading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    await approveUser({ username })
    successMsg.value = `用户 ${username} 审批通过！`
    // 刷新列表并清空选择
    await loadData()
    selectedPending.value = ''
  } catch (e) {
    error.value = `审批失败：${e.message || e}`
  } finally {
    approveLoading.value = false
  }
}

/**
 * 授予管理员权限（带主账号验证+loading）
 */
async function handleGrantAdmin(targetUsername) {
  if (!validateMainAccount()) return
  if (grantLoading.value) return

  grantLoading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    await grantAdmin({
      targetUsername,
      currentUsername: currentUsername.value,
    })
    successMsg.value = `已成功赋予 ${targetUsername} 管理员权限！`
    await loadData()
    selectedUser.value = ''
  } catch (e) {
    error.value = `授权失败：${e.message || e}`
  } finally {
    grantLoading.value = false
  }
}

/**
 * 撤销管理员权限（带主账号验证+loading）
 */
async function handleRevokeAdmin(targetUsername) {
  if (!validateMainAccount()) return
  if (revokeLoading.value) return

  // 二次确认（危险操作）
  if (!confirm(`确认要撤销 ${targetUsername} 的管理员权限吗？`)) return

  revokeLoading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    await revokeAdmin({
      targetUsername,
      currentUsername: currentUsername.value,
    })
    successMsg.value = `已成功撤销 ${targetUsername} 的管理员权限！`
    await loadData()
    selectedUser.value = ''
  } catch (e) {
    error.value = `撤销失败：${e.message || e}`
  } finally {
    revokeLoading.value = false
  }
}

/**
 * 主账号验证（辅助函数）
 */
function validateMainAccount() {
  if (!currentUsername.value) {
    error.value = '请先填写当前主管理员用户名'
    return false
  }
  if (currentUsername.value !== 'admin') {
    error.value = '仅主账号 "admin" 可执行权限操作'
    return false
  }
  if (!selectedUser.value) {
    error.value = '请选择要操作的用户'
    return false
  }
  return true
}

/**
 * 关闭提示框（成功/错误）
 */
function closeAlert(type) {
  if (type === 'success') successMsg.value = ''
  if (type === 'error') error.value = ''
}

// 页面挂载时加载数据
onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="admin-container">
    <!-- 全局提示：成功/错误 -->
    <div v-if="successMsg" class="alert alert-success" @click="closeAlert('success')">
      <span class="alert-icon">✅</span>
      <span>{{ successMsg }}</span>
      <button class="alert-close" @click="closeAlert('success')">×</button>
    </div>
    <div v-if="error" class="alert alert-error" @click="closeAlert('error')">
      <span class="alert-icon">❌</span>
      <span>{{ error }}</span>
      <button class="alert-close" @click="closeAlert('error')">×</button>
    </div>

    <!-- 待审核用户面板 -->
    <section class="panel">
      <div class="panel-header">
        <h2>待审核用户管理</h2>
        <p class="subtitle">审核新注册用户，批准后用户可正常登录使用系统</p>
      </div>

      <div class="panel-body">
        <!-- 选择待审核用户 -->
        <div class="form-group">
          <label class="form-label">选择待审核用户</label>
          <div class="form-control-wrapper">
            <select
              v-model="selectedPending"
              class="form-select"
              :disabled="loading || pendingUsers.length === 0"
            >
              <option disabled value="">请选择待审核用户</option>
              <option
                v-for="username in pendingUsers"
                :key="username"
                :value="username"
              >
                {{ username }}
              </option>
            </select>
          </div>
        </div>

        <!-- 空状态提示 -->
        <div v-if="pendingUsers.length === 0 && !loading" class="empty-state">
          <span class="empty-icon">📭</span>
          <p>暂无待审核用户</p>
        </div>

        <!-- 操作按钮 -->
        <div class="action-group">
          <button
            class="btn btn-default"
            @click="loadData"
            :disabled="loading"
          >
            <span v-if="loading">加载中...</span>
            <span v-else>刷新列表</span>
          </button>
          <button
            class="btn btn-primary"
            :disabled="!selectedPending || approveLoading || pendingUsers.length === 0"
            @click="handleApprove(selectedPending)"
          >
            <span v-if="approveLoading">审批中...</span>
            <span v-else>批准用户</span>
          </button>
        </div>

        <!-- 统计提示 -->
        <p class="hint-text">当前共有 {{ pendingUsers.length }} 个待审核用户</p>
      </div>
    </section>

    <!-- 管理员权限管理面板 -->
    <section class="panel">
      <div class="panel-header">
        <h2>管理员权限管理</h2>
        <p class="subtitle small">
          仅主账号「admin」可执行此操作，操作前请确认身份
        </p>
      </div>

      <div class="panel-body">
        <!-- 主账号验证输入框 -->
        <div class="form-group">
          <label class="form-label required">当前主管理员用户名</label>
          <div class="form-control-wrapper">
            <input
              v-model="currentUsername"
              type="text"
              class="form-input"
              placeholder="请输入主账号用户名（仅admin可操作）"
            />
          </div>
        </div>

        <!-- 选择权限操作用户 -->
        <div class="form-group">
          <label class="form-label">选择操作用户</label>
          <div class="form-control-wrapper">
            <select
              v-model="selectedUser"
              class="form-select"
              :disabled="loading || allUsers.length === 0 || currentUsername !== 'admin'"
            >
              <option disabled value="">请选择用户</option>
              <option
                v-for="u in allUsers"
                :key="u.username"
                :value="u.username"
              >
                {{ u.username }}（角色：{{ u.role }} / 状态：{{ u.status }}）
              </option>
            </select>
          </div>
        </div>

        <!-- 空状态提示 -->
        <div v-if="allUsers.length === 0 && !loading" class="empty-state">
          <span class="empty-icon">👤</span>
          <p>暂无用户数据</p>
        </div>

        <!-- 权限操作按钮（仅主账号可见） -->
        <div v-if="currentUsername === 'admin'" class="action-group">
          <button
            class="btn btn-default"
            @click="loadData"
            :disabled="loading"
          >
            <span v-if="loading">加载中...</span>
            <span v-else>刷新列表</span>
          </button>
          <button
            class="btn btn-primary"
            :disabled="!selectedUser || grantLoading"
            @click="handleGrantAdmin(selectedUser)"
          >
            <span v-if="grantLoading">授权中...</span>
            <span v-else>赋予管理员权限</span>
          </button>
          <button
            class="btn btn-danger"
            :disabled="!selectedUser || revokeLoading"
            @click="handleRevokeAdmin(selectedUser)"
          >
            <span v-if="revokeLoading">撤销中...</span>
            <span v-else>撤销管理员权限</span>
          </button>
        </div>

        <!-- 非主账号提示 -->
        <div v-else class="permission-hint">
          <span class="hint-icon">🔒</span>
          <p>请输入主账号「admin」用户名以解锁权限操作</p>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
/* 全局容器 */
.admin-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  padding: 1rem;
  max-width: 1200px;
  margin: 0 auto;
}

/* 面板样式（现代卡片设计） */
.panel {
  background: #ffffff;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  border: 1px solid #f0f2f5;
  animation: panelFadeIn 0.4s ease-out forwards;
}

.panel:nth-child(2) {
  animation-delay: 0.15s;
  opacity: 0;
}

/* 面板头部 */
.panel-header {
  margin-bottom: 1.25rem;
  border-bottom: 1px solid #f5f7fa;
  padding-bottom: 0.75rem;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1d2129;
}

/* 提示文本 */
.subtitle {
  margin: 0.5rem 0 0;
  color: #86909c;
  font-size: 0.875rem;
  line-height: 1.4;
}

.subtitle.small {
  font-size: 0.8rem;
  color: #949ba4;
}

/* 面板内容 */
.panel-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* 表单组 */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.9rem;
  color: #4e5969;
  font-weight: 500;
}

.form-label.required::after {
  content: '*';
  color: #f53f3f;
  margin-left: 4px;
}

.form-control-wrapper {
  position: relative;
}

.form-input, .form-select {
  width: 100%;
  padding: 0.625rem 0.75rem;
  border-radius: 0.5rem;
  border: 1px solid #dcdfe6;
  font-size: 0.9rem;
  color: #1d2129;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #4096ff;
  box-shadow: 0 0 0 2px rgba(64, 150, 255, 0.1);
}

.form-select:disabled, .form-input:disabled {
  background-color: #f5f7fa;
  color: #c0c4cc;
  cursor: not-allowed;
}

/* 操作按钮组 */
.action-group {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-top: 0.5rem;
}

/* 按钮样式（现代化设计） */
.btn {
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  border: none;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.btn-default {
  background-color: #f5f7fa;
  color: #4e5969;
}

.btn-default:hover:not(:disabled) {
  background-color: #e8ebf0;
  color: #333;
}

.btn-primary {
  background-color: #4096ff;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background-color: #338aff;
}

.btn-danger {
  background-color: #f53f3f;
  color: #ffffff;
}

.btn-danger:hover:not(:disabled) {
  background-color: #e03636;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 空状态提示 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
  color: #86909c;
  background-color: #fafafa;
  border-radius: 0.5rem;
  text-align: center;
}

.empty-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

/* 权限提示 */
.permission-hint {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 1rem;
  background-color: #fef7f7;
  border-radius: 0.5rem;
  color: #86909c;
  font-size: 0.9rem;
}

.hint-icon {
  font-size: 1.2rem;
  color: #f53f3f;
}

/* 提示文本 */
.hint-text {
  margin: 0;
  font-size: 0.875rem;
  color: #86909c;
}

/* 全局提示框 */
.alert {
  padding: 1rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  cursor: pointer;
  animation: alertFadeIn 0.3s ease-out forwards;
}

.alert-success {
  background-color: #f0f9ff;
  color: #00b42a;
  border: 1px solid #e1f5e8;
}

.alert-error {
  background-color: #fff2f0;
  color: #f53f3f;
  border: 1px solid #ffd7d0;
}

.alert-icon {
  font-size: 1.2rem;
}

.alert-close {
  margin-left: auto;
  background: transparent;
  border: none;
  color: inherit;
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0.25rem;
  border-radius: 50%;
}

.alert-close:hover {
  background-color: rgba(0, 0, 0, 0.05);
}

/* 动画效果 */
@keyframes panelFadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes alertFadeIn {
  from {
    opacity: 0;
    transform: translateY(-5px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 响应式适配 */
@media (max-width: 768px) {
  .admin-container {
    padding: 0.75rem;
  }

  .panel {
    padding: 1.25rem;
  }

  .action-group {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }
}
</style>
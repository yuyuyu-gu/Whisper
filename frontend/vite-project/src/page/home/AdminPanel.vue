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
 * 授予管理员权限（移除主账号验证）
 */
async function handleGrantAdmin(targetUsername) {
  if (grantLoading.value || !targetUsername) return

  grantLoading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    await grantAdmin({ targetUsername })
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
 * 撤销管理员权限（移除主账号验证）
 */
async function handleRevokeAdmin(targetUsername) {
  if (revokeLoading.value || !targetUsername) return

  // 二次确认（危险操作）
  if (!confirm(`确认要撤销 ${targetUsername} 的管理员权限吗？`)) return

  revokeLoading.value = true
  error.value = ''
  successMsg.value = ''

  try {
    await revokeAdmin({ targetUsername })
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
 * 关闭提示框（成功/错误）
 */
function closeAlert(type) {
  if (type === 'success') successMsg.value = ''
  if (type === 'error') error.value = ''
}

// 页面挂载时加载数据
onMounted(() => {
  // 轻微延迟让动画完整展示
  setTimeout(() => {
    loadData()
  }, 100)
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
    <section class="panel panel-1">
      <div class="panel-header">
        <h2>待审核用户管理</h2>
        <p class="subtitle">审核新注册用户，批准后用户可正常登录使用系统</p>
      </div>

      <div class="panel-body">
        <!-- 选择待审核用户 -->
        <div class="form-group form-item-1">
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
        <div class="action-group form-item-2">
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
        <p class="hint-text form-item-3">当前共有 {{ pendingUsers.length }} 个待审核用户</p>
      </div>
    </section>

    <!-- 管理员权限管理面板 -->
    <section class="panel panel-2">
      <div class="panel-header">
        <h2>管理员权限管理</h2>
        <p class="subtitle">管理用户的管理员权限，操作前请仔细确认</p>
      </div>

      <div class="panel-body">
        <!-- 选择权限操作用户 -->
        <div class="form-group form-item-1">
          <label class="form-label">选择操作用户</label>
          <div class="form-control-wrapper">
            <select
              v-model="selectedUser"
              class="form-select"
              :disabled="loading || allUsers.length === 0"
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

        <!-- 权限操作按钮（直接显示，无主账号验证） -->
        <div class="action-group form-item-2">
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

/* 面板样式（强化动画层次感） */
.panel {
  background: #ffffff;
  border-radius: 1rem;
  padding: 1.5rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  border: 1px solid #f0f2f5;
  opacity: 0;
  transform: translateY(15px) scale(0.98);
  animation: panelFadeIn 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
  transition: all 0.3s ease-in-out;
}

/* 面板1延迟0.1s，面板2延迟0.25s，形成层次感 */
.panel-1 {
  animation-delay: 0.1s;
}
.panel-2 {
  animation-delay: 0.25s;
}

/* 面板hover上浮效果，增强交互丝滑感 */
.panel:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 25px rgba(0, 0, 0, 0.08);
}

/* 面板头部 */
.panel-header {
  margin-bottom: 1.25rem;
  border-bottom: 1px solid #f5f7fa;
  padding-bottom: 0.75rem;
  opacity: 0;
  animation: elementFadeIn 0.4s ease-out forwards;
  animation-delay: inherit;
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
  opacity: 0;
  animation: elementFadeIn 0.4s ease-out forwards;
  animation-delay: calc(inherit + 0.1s);
}

/* 面板内容 */
.panel-body {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* 表单组（逐元素延迟动画，增强层次感） */
.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  opacity: 0;
  transform: translateX(-10px);
  animation: formItemFadeIn 0.4s ease-out forwards;
}

.form-item-1 {
  animation-delay: calc(var(--panel-delay, 0) + 0.2s);
}
.form-item-2 {
  animation-delay: calc(var(--panel-delay, 0) + 0.35s);
}
.form-item-3 {
  animation-delay: calc(var(--panel-delay, 0) + 0.5s);
}

/* 给不同面板的表单元素设置基础延迟变量 */
.panel-1 .form-group {
  --panel-delay: 0.1s;
}
.panel-2 .form-group {
  --panel-delay: 0.25s;
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
  /* 丝滑过渡：延长时长+优化曲线 */
  transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
}

.form-input:focus, .form-select:focus {
  outline: none;
  border-color: #4096ff;
  box-shadow: 0 0 0 2px rgba(64, 150, 255, 0.1);
  transform: translateY(-1px);
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

/* 按钮样式（强化丝滑交互） */
.btn {
  padding: 0.625rem 1.25rem;
  border-radius: 0.5rem;
  border: none;
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  /* 更丝滑的过渡曲线 */
  transition: all 0.25s cubic-bezier(0.25, 0.8, 0.25, 1);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  position: relative;
  overflow: hidden;
}

/* 按钮点击反馈动画 */
.btn:not(:disabled):active {
  transform: scale(0.96);
}

.btn-default {
  background-color: #f5f7fa;
  color: #4e5969;
}

.btn-default:hover:not(:disabled) {
  background-color: #e8ebf0;
  color: #333;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.btn-primary {
  background-color: #4096ff;
  color: #ffffff;
}

.btn-primary:hover:not(:disabled) {
  background-color: #338aff;
  box-shadow: 0 2px 8px rgba(64, 150, 255, 0.2);
}

.btn-danger {
  background-color: #f53f3f;
  color: #ffffff;
}

.btn-danger:hover:not(:disabled) {
  background-color: #e03636;
  box-shadow: 0 2px 8px rgba(245, 63, 63, 0.2);
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 空状态提示（加动画） */
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
  opacity: 0;
  animation: elementFadeIn 0.4s ease-out forwards;
  animation-delay: calc(var(--panel-delay, 0) + 0.4s);
}

.empty-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
  transform: scale(0.9);
  transition: transform 0.3s ease;
}

.empty-state:hover .empty-icon {
  transform: scale(1.05);
}

/* 提示文本 */
.hint-text {
  margin: 0;
  font-size: 0.875rem;
  color: #86909c;
}

/* 全局提示框（更丝滑的动画） */
.alert {
  padding: 1rem;
  border-radius: 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  cursor: pointer;
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
  animation: alertFadeIn 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.1) forwards;
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
  transition: background-color 0.2s ease;
}

.alert-close:hover {
  background-color: rgba(0, 0, 0, 0.05);
  transform: scale(1.1);
}

/* 动画定义（强化层次感+丝滑度） */
@keyframes panelFadeIn {
  from {
    opacity: 0;
    transform: translateY(15px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes formItemFadeIn {
  from {
    opacity: 0;
    transform: translateX(-10px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

@keyframes elementFadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

@keyframes alertFadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
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

  .panel-1 {
    animation-delay: 0.05s;
  }
  .panel-2 {
    animation-delay: 0.15s;
  }
  .form-item-1 {
    animation-delay: calc(var(--panel-delay, 0) + 0.15s);
  }
  .form-item-2 {
    animation-delay: calc(var(--panel-delay, 0) + 0.25s);
  }
  .form-item-3 {
    animation-delay: calc(var(--panel-delay, 0) + 0.35s);
  }
}
</style>
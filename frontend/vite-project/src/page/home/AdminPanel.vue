<script setup>
import { ref, onMounted } from 'vue'
import {
  getPendingUsers,
  approveUser,
  getAllUsers,
  grantAdmin,
  revokeAdmin,
} from '../../api/auth.js'

/* 状态 */
const pendingUsers = ref([])
const allUsers = ref([])
const loading = ref(false)
const error = ref('')

/* 主账号用户名（用于授权） */
const currentUsername = ref('')

async function loadData() {
  try {
    const pendingRes = await getPendingUsers()
    pendingUsers.value = pendingRes.pending

    const usersRes = await getAllUsers()
    allUsers.value = usersRes.users
  } catch (e) {
    alert(e.message || '加载用户数据失败')
  }
}


/* 审批用户 */
async function handleApprove(username) {
  try {
    await approveUser({ username })
    await loadData()
  } catch (e) {
    alert(e.message || e)
  }
}

/* 授予管理员 */
async function handleGrantAdmin(targetUsername) {
  if (!currentUsername.value) {
    alert('请先填写当前管理员用户名')
    return
  }
  try {
    await grantAdmin({
      targetUsername,
      currentUsername: currentUsername.value,
    })
    await loadData()
  } catch (e) {
    alert(e.message || e)
  }
}

/* 撤销管理员 */
async function handleRevokeAdmin(targetUsername) {
  if (!currentUsername.value) {
    alert('请先填写当前管理员用户名')
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
    await revokeAdmin({
      targetUsername,
      currentUsername: currentUsername.value,
    })
    await loadData()
  } catch (e) {
    alert(e.message || e)
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <section class="panel">
    <h2>管理员审核面板</h2>
    <p class="subtitle">仅管理员可见，用于审核用户与管理权限。</p>

    <!-- 待审核用户 -->
    <div class="section">
      <h3>待审核用户</h3>

      <div class="form-grid">
        <div class="form-item full-width">
          <label>
            选择用户
            <select v-model="selectedPending">
              <option disabled value="">请选择待审核用户</option>
              <option
                v-for="username in pendingUsers"
                :key="username"
                :value="username"
              >
                {{ username }}
              </option>
            </select>
          </label>
        </div>
      </div>

      <div class="actions">
        <button type="button" @click="loadData">
          刷新列表
        </button>
        <button
          type="button"
          class="primary"
          :disabled="!selectedPending"
          @click="handleApprove(selectedPending)"
        >
          批准用户
        </button>
      </div>

      <p class="hint">
        当前共有 {{ pendingUsers.length }} 个待审核用户
      </p>
    </div>
  </section>

    <!-- 管理员权限 -->
  <section class="panel">
    <div class="section">
      <h3>管理员权限管理</h3>
      <p class="subtitle small">
        仅主账号 admin 可操作
      </p>

      <div class="form-grid">
        <div class="form-item full-width">
          <label>
            选择用户
            <select v-model="selectedUser">
              <option disabled value="">请选择用户</option>
              <option
                v-for="u in allUsers"
                :key="u.username"
                :value="u.username"
              >
                {{ u.username }}（{{ u.role }} / {{ u.status }}）
              </option>
            </select>
          </label>
        </div>
      </div>

      <div class="actions">
        <button type="button" @click="loadData">
          刷新列表
        </button>
        <button
          type="button"
          class="primary"
          :disabled="!selectedUser"
          @click="handleGrantAdmin(selectedUser)"
        >
          赋予管理员
        </button>
        <button
          type="button"
          class="danger"
          :disabled="!selectedUser"
          @click="handleRevokeAdmin(selectedUser)"
        >
          撤销管理员
        </button>
      </div>
    </div>
  </section>
</template>



<style scoped>
.panel {
  background: #ffffff;
  border-radius: 0.75rem;
  padding: 1.25rem 1.5rem 1.5rem;
  box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08);
  animation: panel-fade-in 480ms ease;
  margin-bottom: 1.5rem;
}

.panel {
  animation: panel-fade-in 480ms ease both;
}

.panel:nth-of-type(2) {
  animation-delay: 180ms;
}


.panel h2 {
  margin-top: 0;
}

.subtitle {
  margin-top: 0.25rem;
  margin-bottom: 1rem;
  color: #6b7280;
  font-size: 0.9rem;
}

.subtitle.small {
  font-size: 0.8rem;
}

.section {
  margin-top: 1.5rem;
  padding-top: 1rem;
  border-top: 1px solid #e5e7eb;
}

.section h3 {
  margin: 0 0 0.75rem;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem 1rem;
  margin-bottom: 0.75rem;
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

select {
  padding: 0.35rem 0.5rem;
  border-radius: 0.375rem;
  border: 1px solid #d1d5db;
  font-size: 0.9rem;
}

.actions {
  display: flex;
  gap: 0.6rem;
  margin-top: 0.5rem;
}

button {
  padding: 0.4rem 1.1rem;
  border-radius: 999px;
  border: none;
  background: #111827;
  color: #f9fafb;
  font-size: 0.85rem;
  cursor: pointer;
}

button.primary {
  background: #1d4ed8;
}

button.danger {
  background: #b91c1c;
}

button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.hint {
  margin-top: 0.5rem;
  font-size: 0.8rem;
  color: #6b7280;
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
</style>



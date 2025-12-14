<script setup>
import { ref } from 'vue'
import { loginUser, registerUser } from '../api/auth.js'
import { useRouter } from 'vue-router'

const router = useRouter()
// 表单数据
const username = ref('')
const password = ref('')

// 状态控制
const loading = ref(false)
const error = ref('')
// 自定义弹窗状态
const showSuccessModal = ref(false) // 登录成功弹窗
const showRegisterModal = ref(false) // 注册成功弹窗

// 关闭弹窗并跳转首页
const closeModalAndRedirect = () => {
  showSuccessModal.value = false
  showRegisterModal.value = false
  router.push('/home')
}

// 自动关闭弹窗（3秒后）
const autoCloseModal = (type) => {
  setTimeout(() => {
    if (type === 'login') {
      closeModalAndRedirect()
    } else {
      showRegisterModal.value = false
    }
  }, 3000)
}

// 提交处理 - 登录
const handleLogin = async (e) => {
  e.preventDefault()
  await submitForm('login')
}

// 提交处理 - 注册
const handleRegister = async (e) => {
  e.preventDefault()
  await submitForm('register')
}

// 统一提交逻辑
const submitForm = async (mode) => {
  error.value = ''

  if (!username.value || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }

  loading.value = true

  try {
    if (mode === 'login') {
      const data = await loginUser({
        username: username.value,
        password: password.value,
      })

      console.log('login response:', data)

      if (!data.success) {
        throw new Error(data.message || '用户名或密码错误')
      }

      // 存储用户信息
      localStorage.setItem('authUser', JSON.stringify({
        username: username.value,
        role: data.role,
      }))

      // 显示登录成功弹窗（替换alert）
      showSuccessModal.value = true
      autoCloseModal('login') // 自动关闭并跳转
    } else {
      const res = await registerUser({
        username: username.value,
        password: password.value,
      })

      // 显示注册成功弹窗（替换alert）
      showRegisterModal.value = true
      autoCloseModal('register') // 自动关闭
      password.value = ''
    }
  } catch (err) {
    error.value =
      err?.response?.data?.detail ||
      err.message ||
      '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="container">
    <!-- 登录/注册表单 -->
    <form class="form" @submit.prevent>
      <p>
        Welcome,
        <span>Please login or register</span>
      </p>

      <!-- 错误提示 -->
      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <!-- 用户名输入框 -->
      <div class="inputbox">
        <input
          required
          type="text"
          v-model="username"
          :disabled="loading"
        />
        <span>Username</span>
        <i></i>
      </div>

      <!-- 密码输入框 -->
      <div class="inputbox">
        <input
          required
          type="password"
          v-model="password"
          :disabled="loading"
        />
        <span>Password</span>
        <i></i>
      </div>

      <!-- 登录 / 注册 按钮行 -->
      <div class="button-row">
        <button
          class="oauthButton"
          @click="handleLogin"
          :disabled="loading"
        >
          {{ loading ? '登录中...' : '登录' }}
        </button>

        <button
          class="oauthButton"
          @click="handleRegister"
          :disabled="loading"
        >
          {{ loading ? '注册中...' : '注册' }}
        </button>
      </div>
    </form>

    <!-- 登录成功自定义弹窗 -->
    <div class="modal-overlay" v-if="showSuccessModal">
      <div class="modal-content success-modal">
        <div class="modal-icon success-icon">✓</div>
        <h3 class="modal-title">登录成功</h3>
        <p class="modal-desc">欢迎回来，{{ username }}！即将为您跳转到首页...</p>
        <button
          class="modal-close-btn"
          @click="closeModalAndRedirect"
        >
          立即前往
        </button>
      </div>
    </div>

    <!-- 注册成功自定义弹窗 -->
    <div class="modal-overlay" v-if="showRegisterModal">
      <div class="modal-content register-modal">
        <div class="modal-icon register-icon">✓</div>
        <h3 class="modal-title">注册成功</h3>
        <p class="modal-desc">请等待管理员审核，审核通过后即可登录</p>
        <button
          class="modal-close-btn"
          @click="showRegisterModal = false"
        >
          关闭
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
/* 基础容器样式 */
.container {
  width: 100vw;
  height: 100vh;
  background: url('/xjtu.png') no-repeat center center fixed;
  background-size: cover;
  display: flex;
  justify-content: center;
  align-items: center;
  position: relative; /* 新增：用于弹窗绝对定位 */
}

/* 表单整体样式 */
.form {
  --background: #d3d3d3;
  --input-focus: #2d8cf0;
  --font-color: #323232;
  --font-color-sub: #666;
  --bg-color: #fff;
  --main-color: #323232;
  --success-color: #27ae60;
  --register-color: #2980b9;
  padding: 30px 20px;
  background: var(--background);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 20px;
  border-radius: 5px;
  border: 2px solid var(--main-color);
  box-shadow: 4px 4px var(--main-color);
  min-width: 300px;
  z-index: 1; /* 确保表单在弹窗下层 */
}

.form > p {
  font-family: 'Dela Gothic One', sans-serif;
  color: var(--font-color);
  font-weight: 700;
  font-size: 20px;
  margin-bottom: 5px;
  display: flex;
  flex-direction: column;
}

.form > p > span {
  font-family: 'Space Mono', monospace;
  color: var(--font-color-sub);
  font-weight: 600;
  font-size: 17px;
}

/* 浮动标签输入框样式 */
.inputbox {
  position: relative;
  width: 450px;
}

.inputbox input {
  position: relative;
  width: 100%;
  padding: 20px 10px 10px;
  background: var(--bg-color);
  outline: none;
  box-shadow: 4px 4px var(--main-color);
  border: 2px solid var(--main-color);
  border-radius: 5px;
  color: var(--font-color);
  font-size: 15px;
  font-weight: 600;
  font-family: inherit;
  letter-spacing: 0.05em;
  transition: 0.5s;
  z-index: 10;
  height: 60px;
  box-sizing: border-box;
}

.inputbox input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  background: #f0f0f0;
}

.inputbox span {
  position: absolute;
  left: 0;
  padding: 20px 10px 10px;
  font-size: 15px;
  font-weight: 600;
  font-family: 'Space Mono', monospace;
  color: #8f8f8f;
  letter-spacing: 0.05em;
  transition: 0.5s;
  pointer-events: none;
  z-index: 11;
}

.inputbox input:valid ~ span,
.inputbox input:focus ~ span {
  color: var(--input-focus);
  transform: translateX(-10px) translateY(-34px);
  font-size: 0.75em;
}

.inputbox input:disabled ~ span {
  color: #999;
}

.inputbox i {
  position: absolute;
  left: 0;
  bottom: 0;
  width: 100%;
  height: 2px;
  background: var(--input-focus);
  border-radius: 4px;
  transition: 0.5s;
  pointer-events: none;
  z-index: 9;
  border-radius: 0 0 3px 3px;
}

.inputbox input:valid ~ i,
.inputbox input:focus ~ i {
  height: 60px;
  opacity: 0.2;
}

.inputbox input:disabled ~ i {
  background: #999;
}

/* 按钮样式 */
.oauthButton {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 5px;
  width: 220px;
  height: 40px;
  border-radius: 5px;
  border: 2px solid var(--main-color);
  background-color: var(--bg-color);
  box-shadow: 4px 4px var(--main-color);
  font-size: 16px;
  font-weight: 600;
  color: var(--font-color);
  cursor: pointer;
  transition: all 250ms;
  position: relative;
  overflow: hidden;
  z-index: 1;
}

.oauthButton::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 0;
  background-color: #212121;
  z-index: -1;
  box-shadow: 4px 8px 19px -3px rgba(0, 0, 0, 0.27);
  transition: all 250ms;
}

.oauthButton:hover:not(:disabled) {
  color: #e8e8e8;
}

.oauthButton:hover:not(:disabled)::before {
  width: 100%;
}

.oauthButton:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* 按钮行样式 */
.button-row {
  width: 100%;
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

/* 错误提示样式 */
.error-message {
  width: 100%;
  color: #e74c3c;
  font-family: 'Space Mono', monospace;
  font-size: 14px;
  text-align: center;
  padding: 8px 0;
  border-radius: 4px;
  background-color: #fdeaea;
  border: 1px solid #fcc;
  box-sizing: border-box;
}

/* 自定义弹窗样式 */
.modal-overlay {
  position: absolute;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100; /* 确保弹窗在最上层 */
  backdrop-filter: blur(3px); /* 背景模糊效果 */
}

.modal-content {
  background: var(--bg-color);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  padding: 30px;
  width: 400px;
  text-align: center;
  border: 2px solid var(--main-color);
  animation: modalFadeIn 0.3s ease-in-out;
}

/* 弹窗淡入动画 */
@keyframes modalFadeIn {
  from {
    opacity: 0;
    transform: translateY(-20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.modal-icon {
  width: 60px;
  height: 60px;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 0 auto 20px;
  font-size: 30px;
  color: white;
  font-weight: bold;
}

.success-icon {
  background-color: var(--success-color);
  box-shadow: 0 0 0 10px rgba(39, 174, 96, 0.2);
}

.register-icon {
  background-color: var(--register-color);
  box-shadow: 0 0 0 10px rgba(41, 128, 185, 0.2);
}

.modal-title {
  font-family: 'Dela Gothic One', sans-serif;
  font-size: 24px;
  color: var(--font-color);
  margin-bottom: 10px;
}

.modal-desc {
  font-family: 'Space Mono', monospace;
  font-size: 16px;
  color: var(--font-color-sub);
  margin-bottom: 25px;
  line-height: 1.5;
}

.modal-close-btn {
  padding: 10px 30px;
  border-radius: 5px;
  border: 2px solid var(--main-color);
  background-color: var(--bg-color);
  box-shadow: 4px 4px var(--main-color);
  font-size: 16px;
  font-weight: 600;
  color: var(--font-color);
  cursor: pointer;
  transition: all 250ms;
  position: relative;
  overflow: hidden;
}

.modal-close-btn::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  height: 100%;
  width: 0;
  background-color: #212121;
  z-index: -1;
  transition: all 250ms;
}

.modal-close-btn:hover {
  color: white;
}

.modal-close-btn:hover::before {
  width: 100%;
}

/* 登录成功弹窗特殊样式 */
.success-modal {
  border-top: 5px solid var(--success-color);
}

/* 注册成功弹窗特殊样式 */
.register-modal {
  border-top: 5px solid var(--register-color);
}
</style>
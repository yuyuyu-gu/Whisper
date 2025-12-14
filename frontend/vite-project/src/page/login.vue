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

      // 当前系统没有 JWT，就用 success + role
      localStorage.setItem('authUser', JSON.stringify({
        username: username.value,
        role: data.role,
      }))

      alert('登录成功！')
      router.push('/home')
    }else {
      const res = await registerUser({
        username: username.value,
        password: password.value,
      })

      alert('注册成功，请等待管理员审核')
    }

    password.value = ''
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
    <form class="form" @submit.prevent>
      <p>
        Welcome,
        <span>Please login or register</span>
      </p>

      <!-- 错误提示 -->
      <div v-if="error" class="error-message">
        {{ error }}
      </div>

      <!-- 用户名密码输入 -->
      <input
        type="text"
        placeholder="Username"
        v-model="username"
        :disabled="loading"
      />
      <input
        type="password"
        placeholder="Password"
        v-model="password"
        :disabled="loading"
      />

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
  </div>
</template>

<style scoped>
/* DEOXY Was Here */
.form {
  --background: #d3d3d3;
  --input-focus: #2d8cf0;
  --font-color: #323232;
  --font-color-sub: #666;
  --bg-color: #fff;
  --main-color: #323232;
  padding: 20px;
  background: var(--background);
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 15px;
  border-radius: 5px;
  border: 2px solid var(--main-color);
  box-shadow: 4px 4px var(--main-color);
  min-width: 300px;
}

.form > p {
  font-family: 'Dela Gothic One', sans-serif;
  color: var(--font-color);
  font-weight: 700;
  font-size: 20px;
  margin-bottom: 15px;
  display: flex;
  flex-direction: column;
}

.form > p > span {
  font-family: 'Space Mono', monospace;
  color: var(--font-color-sub);
  font-weight: 600;
  font-size: 17px;
}

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

.form input {
  width: 450px;
  height: 40px;
  border-radius: 5px;
  border: 2px solid var(--main-color);
  background-color: var(--bg-color);
  box-shadow: 4px 4px var(--main-color);
  font-size: 15px;
  font-weight: 600;
  color: var(--font-color);
  padding: 5px 10px;
  outline: none;
}

.form input:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.button-row {
  width: 100%;
  display: flex;
  justify-content: space-between;
  margin-top: 10px;
}

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
}

.container {
  width: 100vw;
  height: 100vh;
  background: url('/xjtu.png') no-repeat center center fixed;
  background-size: cover;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
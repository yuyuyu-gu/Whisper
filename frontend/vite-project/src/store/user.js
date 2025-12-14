import { defineStore } from 'pinia'
import { getCurrentUser } from '../api/auth.js' // 后续补充这个API

export const useUserStore = defineStore('user', {
  state: () => ({
    currentUser: null, // 当前登录用户信息 { username: '', role: '' }
    isLogin: false,     // 登录状态
  }),
  actions: {
    // 获取当前登录用户信息（初始化/刷新用）
    async fetchCurrentUser() {
      try {
        const res = await getCurrentUser()
        this.currentUser = res.user
        this.isLogin = true
        return res.user
      } catch (e) {
        this.currentUser = null
        this.isLogin = false
        console.error('获取当前用户信息失败：', e)
        throw e
      }
    },
    // 退出登录（清空状态）
    logout() {
      this.currentUser = null
      this.isLogin = false
    }
  },
  getters: {
    // 快捷判断是否为管理员
    isAdmin: (state) => state.currentUser?.role === 'admin'
  }
})
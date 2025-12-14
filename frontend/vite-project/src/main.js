import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

// 引入 router
import router from './router' 

const pinia = createPinia()
const app = createApp(App)

// 使用 router
app.use(router)

app.use(pinia)

// 挂载根组件
app.mount('#app')

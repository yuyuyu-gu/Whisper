import { createApp } from 'vue'
import App from './App.vue'

// 引入 router
import router from './router' 

const app = createApp(App)

// 使用 router
app.use(router)

// 挂载根组件
app.mount('#app')

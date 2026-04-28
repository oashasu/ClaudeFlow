import { createApp } from 'vue'
import { createPinia } from 'pinia'
import router from './router'
import App from './App.vue'
import './style.css'

// 初始化Token治理Hook
import { globalHookRegistry } from './governance/hook'
globalHookRegistry.initializeDefaultHooks()

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.mount('#app')
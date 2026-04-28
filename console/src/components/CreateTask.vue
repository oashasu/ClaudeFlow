<script setup lang="ts">
import { ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'

const store = useTaskStore()

// 表单数据
const name = ref('')
const domain = ref('')
const prompt = ref('')
const priority = ref('中')

// 控制弹窗显示
const showDialog = ref(false)
const submitting = ref(false)

// 域选项
const domains = [
  '订单域',
  '支付域',
  '会员域',
  '报表域',
  '生态域',
  '通用服务',
]

// 优先级选项
const priorities = ['高', '中', '低']

// 打开弹窗
function openDialog() {
  showDialog.value = true
  name.value = ''
  domain.value = ''
  prompt.value = ''
  priority.value = '中'
}

// 关闭弹窗
function closeDialog() {
  showDialog.value = false
}

// 提交任务
async function submitTask() {
  if (!name.value || !domain.value || !prompt.value) {
    alert('请填写任务名称、领域和描述')
    return
  }

  submitting.value = true
  try {
    await store.createTask({
      name: name.value,
      domain: domain.value,
      prompt: prompt.value,
      priority: priority.value,
    })
    closeDialog()
    // 刷新统计
    store.fetchStats()
  } catch (e) {
    alert('创建失败: ' + (e as Error).message)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <!-- 发布任务按钮 -->
  <button class="create-btn" @click="openDialog">发布任务</button>

  <!-- 创建任务弹窗 -->
  <div v-if="showDialog" class="dialog-overlay" @click.self="closeDialog">
    <div class="dialog">
      <div class="dialog-header">
        <h2>创建新任务</h2>
      </div>

      <div class="form-group">
        <label>任务名称 <span class="required">*</span></label>
        <input v-model="name" type="text" placeholder="例如：修复订单支付异常" />
      </div>

      <div class="form-row">
        <div class="form-group half">
          <label>业务领域 <span class="required">*</span></label>
          <select v-model="domain">
            <option value="">请选择</option>
            <option v-for="d in domains" :key="d" :value="d">{{ d }}</option>
          </select>
        </div>
        <div class="form-group half">
          <label>优先级</label>
          <select v-model="priority">
            <option v-for="p in priorities" :key="p" :value="p">{{ p }}</option>
          </select>
        </div>
      </div>

      <div class="form-group">
        <label>任务描述 (Prompt) <span class="required">*</span></label>
        <textarea
          v-model="prompt"
          rows="5"
          placeholder="详细描述任务内容，将作为 Claude CLI 的输入 prompt"
        />
      </div>

      <div class="actions">
        <button class="cancel-btn" @click="closeDialog">取消</button>
        <button class="submit-btn" :disabled="submitting" @click="submitTask">
          {{ submitting ? '提交中...' : '创建任务' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.create-btn {
  padding: 10px 24px;
  background: linear-gradient(135deg, #4caf50, #43a047);
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 20px;
  transition: transform 0.2s, box-shadow 0.2s;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.create-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(76, 175, 80, 0.4);
}

.dialog-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  animation: fade-in 0.2s ease;
}

@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}

.dialog {
  background: white;
  padding: 0;
  border-radius: 16px;
  width: 520px;
  max-width: 90vw;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  overflow: hidden;
  animation: slide-up 0.25s ease;
}

@keyframes slide-up {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.dialog-header {
  padding: 20px 24px;
  border-bottom: 1px solid #eee;
}

.dialog-header h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #333;
}

.dialog > .form-group,
.dialog > .form-row {
  padding: 0 24px;
}

.form-group {
  margin-bottom: 16px;
}

.form-row {
  display: flex;
  gap: 12px;
}

.form-group.half {
  flex: 1;
}

.form-group label {
  display: block;
  margin-bottom: 6px;
  font-size: 14px;
  font-weight: 500;
  color: #333;
}

.required {
  color: #f44336;
}

.form-group input,
.form-group select,
.form-group textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ddd;
  border-radius: 8px;
  font-size: 14px;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.form-group input:focus,
.form-group select:focus,
.form-group textarea:focus {
  outline: none;
  border-color: #4caf50;
  box-shadow: 0 0 0 3px rgba(76, 175, 80, 0.1);
}

.form-group textarea {
  resize: vertical;
  font-family: inherit;
}

.actions {
  display: flex;
  gap: 12px;
  justify-content: flex-end;
  padding: 16px 24px 20px;
  border-top: 1px solid #eee;
}

.cancel-btn {
  padding: 10px 20px;
  background: #f5f5f5;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  color: #666;
  transition: background 0.2s;
}

.cancel-btn:hover {
  background: #e0e0e0;
}

.submit-btn {
  padding: 10px 24px;
  background: #4caf50;
  color: white;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  transition: background 0.2s;
}

.submit-btn:hover:not(:disabled) {
  background: #43a047;
}

.submit-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
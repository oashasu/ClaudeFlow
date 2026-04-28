<script setup lang="ts">
import { ref } from 'vue'
import { useTaskStore } from '../stores/taskStore'

const props = defineProps<{
  taskId: string
}>()

const emit = defineEmits<{
  submit: []
  close: []
}>()

const store = useTaskStore()
const userInput = ref('')
const submitting = ref(false)

async function handleSubmit() {
  if (!userInput.value.trim()) return

  submitting.value = true
  try {
    await store.confirmIntervention(props.taskId, userInput.value)
    emit('submit')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <h3>提供补充信息</h3>
      <p>任务正在等待您的介入，请提供必要的补充信息以继续执行。</p>

      <textarea
        v-model="userInput"
        placeholder="请输入补充信息..."
        rows="4"
        class="input-area"
      />

      <div class="modal-actions">
        <button class="cancel" @click="emit('close')">取消</button>
        <button
          class="submit"
          :disabled="!userInput.trim() || submitting"
          @click="handleSubmit"
        >
          {{ submitting ? '提交中...' : '提交' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal {
  background: white;
  padding: 24px;
  border-radius: 16px;
  width: 400px;
  max-width: 90%;
}

.modal h3 {
  margin-bottom: 16px;
  color: #333;
}

.modal p {
  color: #666;
  margin-bottom: 16px;
}

.input-area {
  width: 100%;
  padding: 12px;
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  resize: none;
  font-size: 14px;
  margin-bottom: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.modal-actions button {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.cancel {
  background: #f5f5f5;
  color: #333;
}

.submit {
  background: #ff9800;
  color: white;
}

.submit:disabled {
  background: #ccc;
  cursor: not-allowed;
}
</style>
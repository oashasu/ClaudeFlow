<script setup lang="ts">
import type { Task } from '../services/api'
import WorkflowProgress from './WorkflowProgress.vue'
import InterventionModal from './InterventionModal.vue'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'

const props = defineProps<{
  task: Task
}>()

const router = useRouter()
const store = useTaskStore()

const showModal = ref(false)
const userInput = ref('')

// 查看详情
function goToDetail() {
  router.push(`/task/${props.task.id}`)
}

// 处理介入
function handleIntervention() {
  showModal.value = true
}

function submitIntervention() {
  store.confirmIntervention(props.task.id, userInput.value)
  showModal.value = false
  userInput.value = ''
}

// 取消任务
function handleCancel() {
  if (confirm('确认取消任务？')) {
    store.cancelTask(props.task.id)
  }
}
</script>

<template>
  <div class="task-card" :class="{ waiting: task.status === 'waiting' }">
    <div class="task-info">
      <div class="task-id">{{ task.id }}</div>
      <div class="task-status" :class="task.status">{{ task.status }}</div>
    </div>

    <WorkflowProgress
      :phase="task.phase"
      :progress="task.progress"
      size="small"
    />

    <div class="task-actions">
      <button @click="goToDetail">查看详情</button>

      <template v-if="task.status === 'waiting'">
        <button class="warning" @click="handleIntervention">提供信息</button>
        <button class="cancel" @click="handleCancel">取消</button>
      </template>
    </div>

    <InterventionModal
      v-if="showModal"
      :taskId="task.id"
      @submit="submitIntervention"
      @close="showModal = false"
    />
  </div>
</template>

<style scoped>
.task-card {
  padding: 16px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e0e0e0;
  transition: box-shadow 0.2s;
}

.task-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.task-card.waiting {
  border: 2px solid #ff9800;
  animation: border-pulse 2s infinite;
}

@keyframes border-pulse {
  0%, 100% { border-color: #ff9800; }
  50% { border-color: #ffb74d; }
}

.task-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.task-id {
  font-weight: bold;
  color: #333;
}

.task-status {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 12px;
}

.task-status.running { background: #4a4; color: white; }
.task-status.completed { background: #ddd; color: #333; }
.task-status.waiting { background: #ff9800; color: white; }
.task-status.paused { background: #999; color: white; }
.task-status.cancelled { background: #c00; color: white; }

.task-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.task-actions button {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  background: #f5f5f5;
  color: #333;
}

.task-actions button.warning {
  background: #ff9800;
  color: white;
}

.task-actions button.cancel {
  background: #f5f5f5;
  color: #c00;
}
</style>
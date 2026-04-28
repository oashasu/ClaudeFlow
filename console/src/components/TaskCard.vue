<template>
  <div class="task-card" :class="{ waiting: task.status === 'waiting' }">
    <div class="task-header">
      <div class="task-title">
        <span class="task-name">{{ task.name }}</span>
        <span class="task-domain">{{ task.domain }}</span>
      </div>
      <div class="task-status" :class="task.status">{{ statusLabel }}</div>
    </div>

    <div class="task-meta">
      <span class="task-id">ID: {{ task.id.slice(0, 8) }}...</span>
      <span class="task-priority">{{ task.priority }}</span>
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

      <template v-if="task.status === 'error'">
        <button class="retry" @click="handleRetry">重新执行</button>
        <button class="delete" @click="handleDelete">删除</button>
      </template>

      <template v-if="task.status === 'completed' || task.status === 'cancelled'">
        <button class="delete" @click="handleDelete">删除</button>
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

<script setup lang="ts">
import type { Task } from '../services/api'
import WorkflowProgress from './WorkflowProgress.vue'
import InterventionModal from './InterventionModal.vue'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'

const props = defineProps<{
  task: Task
}>()

const router = useRouter()
const store = useTaskStore()

const showModal = ref(false)
const userInput = ref('')

const statusLabel = computed(() => {
  const labels: Record<string, string> = {
    running: '运行中',
    completed: '已完成',
    waiting: '等待介入',
    paused: '已暂停',
    cancelled: '已取消',
    pending: '待启动',
    error: '异常'
  }
  return labels[props.task.status] || props.task.status
})

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

// 删除任务
function handleDelete() {
  if (confirm('确认删除任务？')) {
    store.deleteTask(props.task.id)
  }
}

// 重新执行任务
function handleRetry() {
  if (confirm('确认重新执行任务？')) {
    store.retryTask(props.task.id)
  }
}
</script>

<style scoped>
.task-card {
  padding: 20px;
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

.task-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.task-title {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.task-name {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.task-domain {
  font-size: 12px;
  color: #666;
  background: #e8e8e8;
  padding: 2px 8px;
  border-radius: 4px;
}

.task-status {
  padding: 6px 14px;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 500;
}

.task-status.pending { background: #e0e0e0; color: #333; }
.task-status.running { background: #4caf50; color: white; }
.task-status.completed { background: #9e9e9e; color: white; }
.task-status.waiting { background: #ff9800; color: white; }
.task-status.paused { background: #757575; color: white; }
.task-status.cancelled { background: #f44336; color: white; }
.task-status.error { background: #f44336; color: white; }

.task-meta {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
  font-size: 12px;
  color: #888;
}

.task-priority {
  padding: 2px 6px;
  border-radius: 4px;
  background: #f5f5f5;
}

.task-actions {
  display: flex;
  gap: 8px;
  margin-top: 16px;
}

.task-actions button {
  padding: 10px 20px;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  background: #f5f5f5;
  color: #333;
  font-size: 14px;
  transition: background 0.2s;
}

.task-actions button:hover {
  background: #e0e0e0;
}

.task-actions button.warning {
  background: #ff9800;
  color: white;
}

.task-actions button.warning:hover {
  background: #f57c00;
}

.task-actions button.cancel {
  background: #f5f5f5;
  color: #f44336;
  border: 1px solid #f44336;
}

.task-actions button.cancel:hover {
  background: #ffebee;
}

.task-actions button.delete {
  background: #f5f5f5;
  color: #666;
  border: 1px solid #ddd;
}

.task-actions button.delete:hover {
  background: #e0e0e0;
}

.task-actions button.retry {
  background: #4caf50;
  color: white;
}

.task-actions button.retry:hover {
  background: #388e3c;
}
</style>
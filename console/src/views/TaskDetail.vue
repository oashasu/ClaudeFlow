<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTaskStore } from '../stores/taskStore'
import WorkflowProgress from '../components/WorkflowProgress.vue'
import StepScroller from '../components/StepScroller.vue'
import CheckpointTimeline from '../components/CheckpointTimeline.vue'
import SessionIdBox from '../components/SessionIdBox.vue'

const route = useRoute()
const router = useRouter()
const store = useTaskStore()

const taskId = route.params.id as string

// 当前展开的阶段
const expandedPhase = ref<string | null>(null)

onMounted(() => {
  store.fetchTaskDetail(taskId)
})

// 判断任务状态
const isRunning = computed(() => store.currentTask?.status === 'running')
const isPaused = computed(() => store.currentTask?.status === 'paused')
const isWaiting = computed(() => store.currentTask?.status === 'waiting')

// 操作按钮
function handlePause() {
  store.pauseTask(taskId)
}

function handleResume() {
  store.resumeTask(taskId)
}

function handleCancel() {
  if (confirm('确认取消任务？')) {
    store.cancelTask(taskId)
  }
}

// 阶段展开
function handlePhaseClick(phase: string) {
  if (expandedPhase.value === phase) {
    expandedPhase.value = null
    store.clearCurrentTask()
  } else {
    expandedPhase.value = phase
    store.fetchPhaseSteps(taskId, phase)
  }
}

// 返回列表
function goBack() {
  router.push('/')
}
</script>

<template>
  <div class="task-detail">
    <div v-if="store.loading" class="loading">加载中...</div>

    <template v-else-if="store.currentTask">
      <!-- 返回按钮 -->
      <button class="back-btn" @click="goBack">← 返回列表</button>

      <!-- 任务基本信息 -->
      <div class="task-header">
        <h2>{{ store.currentTask.name }}</h2>
        <span class="status-badge" :class="store.currentTask.status">
          {{ store.currentTask.status }}
        </span>
      </div>

      <div class="task-meta">
        <span>创建: {{ store.currentTask.gmtCreate }}</span>
        <span>更新: {{ store.currentTask.gmtModified }}</span>
      </div>

      <div class="task-description">
        {{ store.currentTask.description }}
      </div>

      <!-- 会话ID区域 -->
      <SessionIdBox
        v-if="store.currentTask.sessionId"
        :sessionId="store.currentTask.sessionId"
      />

      <!-- 工作流进度 -->
      <WorkflowProgress
        :phase="store.currentTask.phase"
        :progress="store.currentTask.progress"
        :expanded="expandedPhase"
        @phase-click="handlePhaseClick"
      />

      <!-- 步骤详情 -->
      <StepScroller
        v-if="expandedPhase && store.currentSteps.length > 0"
        :steps="store.currentSteps"
      />

      <!-- Checkpoint历史 -->
      <CheckpointTimeline
        :checkpoints="store.currentCheckpoints"
        @revert="store.revertCheckpoint"
      />

      <!-- 操作按钮 -->
      <div class="action-buttons">
        <button v-if="isRunning" @click="handlePause">暂停任务</button>
        <button v-if="isPaused" @click="handleResume">恢复任务</button>
        <button class="cancel" @click="handleCancel">取消任务</button>
      </div>
    </template>

    <div v-else class="error">
      {{ store.error || '任务不存在' }}
    </div>
  </div>
</template>

<style scoped>
.task-detail {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.back-btn {
  margin-bottom: 20px;
  padding: 8px 16px;
  background: #f5f5f5;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}

.task-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.status-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 14px;
}

.status-badge.running { background: #4a4; color: white; }
.status-badge.paused { background: #999; color: white; }
.status-badge.waiting { background: #ff9800; color: white; }
.status-badge.completed { background: #ddd; color: #333; }
.status-badge.cancelled { background: #c00; color: white; }

.task-meta {
  display: flex;
  gap: 24px;
  color: #666;
  font-size: 14px;
  margin-bottom: 16px;
}

.task-description {
  padding: 16px;
  background: #f9f9f9;
  border-radius: 8px;
  margin-bottom: 20px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.action-buttons button {
  padding: 12px 24px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.action-buttons button:not(.cancel) {
  background: #2196F3;
  color: white;
}

.action-buttons button.cancel {
  background: #f5f5f5;
  color: #333;
}

.loading, .error {
  text-align: center;
  padding: 40px;
  color: #666;
}
</style>
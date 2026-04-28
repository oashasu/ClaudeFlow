<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { connectTaskSSE, disconnectSSE } from '../services/sse'
import StatsCard from '../components/StatsCard.vue'
import TaskCard from '../components/TaskCard.vue'
import CreateTask from '../components/CreateTask.vue'

const store = useTaskStore()

// SSE事件处理 - 为每个运行中的任务建立SSE连接
function connectRunningTasks() {
  store.tasks.forEach(task => {
    if (task.status === 'running' && task.sessionId) {
      connectTaskSSE(task.sessionId, {
        onProgress: (event) => {
          store.handleProgressUpdate({
            taskId: task.id,
            phase: event.phase,
            progress: event.progress
          })
        },
        onError: () => {
          console.error(`SSE error for task ${task.id}`)
        },
      })
    }
  })
}

onMounted(() => {
  store.fetchTasks()
  store.fetchStats()

  // 连接现有运行任务的SSE
  connectRunningTasks()
})

// 监听任务变化，为新启动的任务建立SSE连接
watch(() => store.tasks, (newTasks, oldTasks) => {
  // 找出新启动的任务
  newTasks.forEach(newTask => {
    if (newTask.status === 'running' && newTask.sessionId) {
      const oldTask = oldTasks?.find(t => t.id === newTask.id)
      // 如果是新启动的任务（之前没有sessionId）
      if (!oldTask?.sessionId) {
        connectTaskSSE(newTask.sessionId, {
          onProgress: (event) => {
            store.handleProgressUpdate({
              taskId: newTask.id,
              phase: event.phase,
              progress: event.progress
            })
          },
          onError: () => {
            console.error(`SSE error for task ${newTask.id}`)
          },
        })
      }
    }
  })
}, { deep: true })

onUnmounted(() => {
  disconnectSSE()
})

// 统计卡片点击过滤
function handleStatsClick(status: string) {
  store.setFilterStatus(status)
}

// 清除过滤
function clearFilter() {
  store.setFilterStatus(null)
}
</script>

<template>
  <div class="dashboard">
    <section class="workspace-switcher">
      <article class="workspace-card task-flow">
        <p class="workspace-eyebrow">Task Flow</p>
        <h2>任务流工作台</h2>
        <p>适合看任务列表、阶段进度、人工介入和旧工作流状态。</p>
      </article>
      <a class="workspace-card runtime" href="/runtime">
        <p class="workspace-eyebrow">Runtime</p>
        <h2>进入 Runtime Console</h2>
        <p>查看 runnable / blocked / running、session 事件和调度动作。</p>
        <span class="workspace-link">打开运行时工作台</span>
      </a>
    </section>

    <!-- 顶部统计区 -->
    <div class="stats-area">
      <StatsCard
        title="运行中"
        :count="store.stats.running"
        color="green"
        @click="handleStatsClick('running')"
      />
      <StatsCard
        title="已完成"
        :count="store.stats.completed"
        color="gray"
        @click="handleStatsClick('completed')"
      />
      <StatsCard
        title="等待介入"
        :count="store.stats.waiting"
        color="orange"
        highlight
        @click="handleStatsClick('waiting')"
      />
      <StatsCard
        title="告警"
        :count="store.stats.alert"
        color="red"
        @click="handleStatsClick('alert')"
      />
    </div>

    <!-- 发布任务按钮 -->
    <CreateTask />

    <!-- 过滤提示 -->
    <div v-if="store.filterStatus" class="filter-bar">
      <span>当前过滤: {{ store.filterStatus }}</span>
      <button @click="clearFilter">清除</button>
    </div>

    <!-- 任务列表 -->
    <div class="task-list">
      <div v-if="store.loading" class="loading">加载中...</div>
      <div v-else-if="store.filteredTasks.length === 0" class="empty">
        暂无任务
      </div>
      <TaskCard
        v-else
        v-for="task in store.filteredTasks"
        :key="task.id"
        :task="task"
      />
    </div>
  </div>
</template>

<style scoped>
.dashboard {
  padding: 24px;
  max-width: 1200px;
  margin: 0 auto;
  min-height: 100vh;
}

.workspace-switcher {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 18px;
  margin-bottom: 24px;
}

.workspace-card {
  padding: 22px;
  border-radius: 18px;
  text-decoration: none;
  border: 1px solid #dce5d8;
}

.workspace-card h2,
.workspace-card p {
  margin: 0;
}

.workspace-card.task-flow {
  background: linear-gradient(135deg, #f7faf5 0%, #edf4ea 100%);
}

.workspace-card.runtime {
  background: linear-gradient(135deg, #fff4df 0%, #f0f6ea 100%);
  color: #1f2c22;
  box-shadow: 0 10px 24px rgba(74, 96, 76, 0.08);
}

.workspace-card.runtime:hover {
  transform: translateY(-1px);
}

.workspace-eyebrow {
  margin-bottom: 8px !important;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  color: #6b7567;
}

.workspace-card h2 {
  margin-bottom: 8px;
}

.workspace-card p {
  color: #5f6c5c;
  line-height: 1.5;
}

.workspace-link {
  display: inline-flex;
  margin-top: 14px;
  padding: 8px 12px;
  border-radius: 999px;
  background: #1f3828;
  color: #f8fbf7;
  font-size: 13px;
}

.stats-area {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

/* 响应式：小屏幕两列 */
@media (max-width: 600px) {
  .workspace-switcher {
    grid-template-columns: 1fr;
  }

  .stats-area {
    grid-template-columns: repeat(2, 1fr);
  }
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 10px 16px;
  background: #f5f5f5;
  border-radius: 8px;
}

.filter-bar button {
  padding: 6px 12px;
  background: #e0e0e0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.loading, .empty {
  text-align: center;
  padding: 60px;
  color: #666;
  font-size: 16px;
}
</style>

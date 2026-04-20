<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useTaskStore } from '../stores/taskStore'
import { connectSSE, disconnectSSE } from '../services/sse'
import StatsCard from '../components/StatsCard.vue'
import TaskCard from '../components/TaskCard.vue'

const store = useTaskStore()

// SSE事件处理
onMounted(() => {
  store.fetchTasks()
  store.fetchStats()

  connectSSE({
    onProgress: (event) => {
      store.handleProgressUpdate(event)
    },
    onHeartbeat: () => {
      // 心跳时不刷新数据，避免频繁请求
    },
    onError: () => {
      console.error('SSE connection error')
    },
  })
})

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
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

.stats-area {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 8px 16px;
  background: #f5f5f5;
  border-radius: 8px;
}

.task-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.loading, .empty {
  text-align: center;
  padding: 40px;
  color: #666;
}
</style>
<template>
  <div class="event-stream">
    <div class="event-header">
      <h3>执行日志</h3>
      <span class="event-count">共 {{ events.length }} 条事件</span>
      <button class="refresh-btn" @click="fetchEvents">刷新</button>
    </div>

    <div class="event-list" ref="eventList">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="events.length === 0" class="empty">暂无事件</div>

      <div
        v-for="(event, index) in events"
        :key="index"
        class="event-item"
        :class="event.type"
      >
        <!-- Thinking -->
        <div v-if="event.type === 'thinking'" class="thinking-block">
          <div class="event-label">💭 思考</div>
          <div class="event-content">{{ event.text }}</div>
        </div>

        <!-- Tool Use -->
        <div v-if="event.type === 'tool_use'" class="tool-block">
          <div class="event-label">🔧 工具调用: {{ event.tool_name }}</div>
          <pre class="event-content">{{ formatToolInput(event.tool_input) }}</pre>
        </div>

        <!-- Text -->
        <div v-if="event.type === 'text'" class="text-block">
          <div class="event-label">📝 输出</div>
          <div class="event-content">{{ event.text }}</div>
        </div>
      </div>
    </div>

    <!-- 自动刷新开关 -->
    <div class="auto-refresh">
      <label>
        <input type="checkbox" v-model="autoRefresh" />
        自动刷新 ({{ refreshInterval }}秒)
      </label>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { sessionApi, type ParsedEvent } from '../services/api'

const props = defineProps<{
  sessionId: string
  isRunning: boolean
}>()

const events = ref<ParsedEvent[]>([])
const loading = ref(false)
const autoRefresh = ref(true)
const refreshInterval = ref(3)
const eventList = ref<HTMLElement | null>(null)

let refreshTimer: number | null = null

async function fetchEvents() {
  if (!props.sessionId) return

  loading.value = true
  try {
    const result = await sessionApi.events(props.sessionId)
    events.value = result.parsed_events || []

    // 自动滚动到底部
    if (eventList.value) {
      eventList.value.scrollTop = eventList.value.scrollHeight
    }
  } catch (e) {
    console.error('Failed to fetch events', e)
  } finally {
    loading.value = false
  }
}

function formatToolInput(input: any): string {
  if (!input) return ''
  try {
    return JSON.stringify(input, null, 2)
  } catch {
    return String(input)
  }
}

// 定时刷新
function startAutoRefresh() {
  if (refreshTimer) clearInterval(refreshTimer)
  if (autoRefresh.value && props.isRunning) {
    refreshTimer = window.setInterval(fetchEvents, refreshInterval.value * 1000)
  }
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer)
    refreshTimer = null
  }
}

// 监听运行状态变化
watch(() => props.isRunning, (running) => {
  if (running) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
    // 任务结束时刷新一次获取完整事件
    fetchEvents()
  }
})

watch(autoRefresh, (enabled) => {
  if (enabled && props.isRunning) {
    startAutoRefresh()
  } else {
    stopAutoRefresh()
  }
})

onMounted(() => {
  fetchEvents()
  if (props.isRunning) {
    startAutoRefresh()
  }
})

onUnmounted(() => {
  stopAutoRefresh()
})
</script>

<style scoped>
.event-stream {
  margin-top: 20px;
  background: #1a1a2e;
  border-radius: 8px;
  padding: 16px;
}

.event-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.event-header h3 {
  color: #e0e0e0;
  font-size: 16px;
  margin: 0;
}

.event-count {
  color: #888;
  font-size: 14px;
}

.refresh-btn {
  padding: 6px 12px;
  background: #3a3a5e;
  color: #e0e0e0;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.event-list {
  max-height: 400px;
  overflow-y: auto;
  font-family: 'Monaco', 'Menlo', monospace;
  font-size: 13px;
}

.loading, .empty {
  color: #888;
  text-align: center;
  padding: 20px;
}

.event-item {
  margin-bottom: 12px;
  padding: 12px;
  border-radius: 6px;
}

.event-item.thinking {
  background: #2a2a4e;
}

.event-item.tool_use {
  background: #1e3a5e;
}

.event-item.text {
  background: #2a3a2e;
}

.event-label {
  font-size: 12px;
  color: #aaa;
  margin-bottom: 8px;
}

.event-content {
  color: #e0e0e0;
  white-space: pre-wrap;
  word-break: break-all;
}

.tool-block pre {
  margin: 0;
  white-space: pre-wrap;
  color: #b8d4ff;
}

.auto-refresh {
  margin-top: 12px;
  color: #888;
  font-size: 13px;
}

.auto-refresh input {
  margin-right: 8px;
}
</style>
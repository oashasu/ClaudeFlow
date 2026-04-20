<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { connectSSE, disconnectSSE } from '../services/sse'

const props = defineProps<{
  taskId: string
}>()

// 事件列表
const events = ref<Array<{
  type: string
  timestamp: Date
  data: Record<string, unknown>
}>>([])

// 最大事件数量
const MAX_EVENTS = 100

// SSE连接状态
const connected = ref(false)

// 格式化时间
function formatTime(date: Date): string {
  return date.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

// 格式化事件数据
function formatEventData(event: { type: string; data: Record<string, unknown> }): string {
  if (event.type === 'tool_use') {
    const tool = event.data.tool as string
    const input = event.data.input as Record<string, unknown>
    return `${tool}: ${JSON.stringify(input).slice(0, 50)}`
  }
  if (event.type === 'checkpoint') {
    const phase = event.data.phase as string
    const summary = event.data.summary as string
    return `${phase} - ${summary}`
  }
  if (event.type === 'result') {
    const status = event.data.status as string
    return `完成: ${status}`
  }
  return JSON.stringify(event.data).slice(0, 80)
}

// 事件类型样式
const eventClass = computed(() => (type: string) => {
  switch (type) {
    case 'tool_use': return 'event-tool'
    case 'checkpoint': return 'event-checkpoint'
    case 'result': return 'event-result'
    default: return 'event-default'
  }
})

// SSE事件处理
onMounted(() => {
  connectSSE({
    onProgress: (data) => {
      addEvent('progress_update', data)
    },
    onToolCall: (data) => {
      addEvent('tool_use', data)
    },
    onIntervention: (data) => {
      addEvent('intervention_prompt', data)
    },
    onHeartbeat: () => {
      connected.value = true
    },
    onError: () => {
      connected.value = false
    },
  })
})

onUnmounted(() => {
  disconnectSSE()
})

function addEvent(type: string, data: Record<string, unknown>) {
  events.value.unshift({
    type,
    timestamp: new Date(),
    data,
  })
  // 限制事件数量
  if (events.value.length > MAX_EVENTS) {
    events.value.pop()
  }
}

// 清空事件
function clearEvents() {
  events.value = []
}
</script>

<template>
  <div class="progress-stream">
    <div class="stream-header">
      <h3>实时进度</h3>
      <div class="stream-controls">
        <span :class="connected ? 'connected' : 'disconnected'">
          {{ connected ? '已连接' : '断线' }}
        </span>
        <button @click="clearEvents">清空</button>
      </div>
    </div>

    <div class="stream-content">
      <div v-if="events.length === 0" class="empty">
        等待事件...
      </div>
      <div v-else class="event-list">
        <div
          v-for="event in events"
          :key="event.timestamp.getTime()"
          class="event-item"
          :class="eventClass(event.type)"
        >
          <span class="event-time">{{ formatTime(event.timestamp) }}</span>
          <span class="event-type">{{ event.type }}</span>
          <span class="event-data">{{ formatEventData(event) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-stream {
  border: 1px solid #e0e0e0;
  border-radius: 8px;
  overflow: hidden;
}

.stream-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #e0e0e0;
}

.stream-header h3 {
  margin: 0;
  font-size: 14px;
}

.stream-controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.connected {
  color: #4caf50;
}

.disconnected {
  color: #f44336;
}

.stream-content {
  max-height: 300px;
  overflow-y: auto;
  padding: 8px;
}

.empty {
  text-align: center;
  color: #999;
  padding: 20px;
}

.event-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.event-item {
  display: flex;
  gap: 12px;
  padding: 8px;
  font-size: 13px;
  border-radius: 4px;
}

.event-tool {
  background: #e3f2fd;
}

.event-checkpoint {
  background: #e8f5e9;
}

.event-result {
  background: #fff3e0;
}

.event-time {
  color: #999;
  min-width: 80px;
}

.event-type {
  color: #666;
  min-width: 100px;
  font-weight: bold;
}

.event-data {
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
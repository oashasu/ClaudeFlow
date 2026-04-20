// SSE服务层
import type { ProgressUpdateEvent, ToolCallEvent, InterventionPromptEvent } from './eventBus'

const SSE_URL = 'http://localhost:21000/api/events/stream'

type EventCallback<T> = (event: T) => void

interface SseHandlers {
  onProgress?: EventCallback<ProgressUpdateEvent>
  onToolCall?: EventCallback<ToolCallEvent>
  onIntervention?: EventCallback<InterventionPromptEvent>
  onHeartbeat?: () => void
  onError?: (error: Event) => void
}

let eventSource: EventSource | null = null
let reconnectAttempts = 0
const MAX_RECONNECT_DELAY = 30000
const BASE_RECONNECT_DELAY = 1000

// 计算重连延迟（指数退避）
function getReconnectDelay(): number {
  const delay = BASE_RECONNECT_DELAY * Math.pow(2, reconnectAttempts)
  return Math.min(delay, MAX_RECONNECT_DELAY)
}

// 连接SSE
export function connectSSE(handlers: SseHandlers): void {
  if (eventSource) {
    disconnectSSE()
  }

  eventSource = new EventSource(SSE_URL)

  eventSource.onopen = () => {
    console.log('SSE connected')
    reconnectAttempts = 0
  }

  eventSource.addEventListener('progress_update', (e: MessageEvent) => {
    const data = JSON.parse(e.data) as ProgressUpdateEvent
    handlers.onProgress?.(data)
  })

  eventSource.addEventListener('tool_call', (e: MessageEvent) => {
    const data = JSON.parse(e.data) as ToolCallEvent
    handlers.onToolCall?.(data)
  })

  eventSource.addEventListener('intervention_prompt', (e: MessageEvent) => {
    const data = JSON.parse(e.data) as InterventionPromptEvent
    handlers.onIntervention?.(data)
  })

  eventSource.addEventListener('heartbeat', () => {
    handlers.onHeartbeat?.()
  })

  eventSource.onerror = (e: Event) => {
    console.error('SSE error', e)
    handlers.onError?.(e)

    // 断线重连
    disconnectSSE()
    reconnectAttempts++
    const delay = getReconnectDelay()
    console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttempts})`)
    setTimeout(() => connectSSE(handlers), delay)
  }
}

// 断开SSE
export function disconnectSSE(): void {
  if (eventSource) {
    eventSource.close()
    eventSource = null
  }
}

// 重置重连计数
export function resetReconnect(): void {
  reconnectAttempts = 0
}
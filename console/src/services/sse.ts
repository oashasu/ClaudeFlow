// SSE服务层
import type { ProgressUpdateEvent, ToolCallEvent, InterventionPromptEvent } from './eventBus'

// 直连 Runtime API SSE
const RUNTIME_URL = 'http://localhost:8000'

type EventCallback<T> = (event: T) => void

interface SseHandlers {
  onProgress?: EventCallback<ProgressUpdateEvent>
  onToolCall?: EventCallback<ToolCallEvent>
  onIntervention?: EventCallback<InterventionPromptEvent>
  onHeartbeat?: () => void
  onError?: (error: Event) => void
}

let eventSources: Map<string, EventSource> = new Map()

// 连接指定任务的SSE
export function connectTaskSSE(sessionId: string, handlers: SseHandlers): void {
  const url = `${RUNTIME_URL}/api/session/${sessionId}/events`

  const eventSource = new EventSource(url)

  eventSource.onopen = () => {
    console.log(`SSE connected for session: ${sessionId}`)
  }

  eventSource.onmessage = (e: MessageEvent) => {
    try {
      const data = JSON.parse(e.data)

      // Runtime API 返回的事件格式：{ type, ... }
      if (data.type === 'assistant') {
        // 工具调用或文本
        if (data.content?.type === 'tool_use') {
          handlers.onToolCall?.({
            taskId: sessionId,
            tool: data.content.name,
            input: data.content.input
          })
        } else if (data.content?.type === 'text') {
          handlers.onProgress?.({
            taskId: sessionId,
            phase: 'executing',
            progress: 50
          })
        }
      } else if (data.type === 'result') {
        handlers.onProgress?.({
          taskId: sessionId,
          phase: 'completed',
          progress: 100
        })
        // 任务完成，关闭连接
        eventSource.close()
        eventSources.delete(sessionId)
      } else if (data.type === 'error') {
        handlers.onError?.(new Event('error'))
      }
    } catch (err) {
      console.error('Failed to parse SSE event:', err)
    }
  }

  eventSource.onerror = (e: Event) => {
    console.error('SSE error:', e)
    handlers.onError?.(e)
    eventSource.close()
    eventSources.delete(sessionId)
  }

  eventSources.set(sessionId, eventSource)
}

// 连接所有运行中任务的SSE
export function connectSSE(handlers: SseHandlers): void {
  // 这个函数保留兼容性，但实际需要知道 sessionId
  console.log('SSE connection requires sessionId - use connectTaskSSE instead')
}

// 断开所有SSE
export function disconnectSSE(): void {
  eventSources.forEach(es => es.close())
  eventSources.clear()
}

// 断开指定任务的SSE
export function disconnectTaskSSE(sessionId: string): void {
  const es = eventSources.get(sessionId)
  if (es) {
    es.close()
    eventSources.delete(sessionId)
  }
}
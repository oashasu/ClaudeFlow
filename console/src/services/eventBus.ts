// 事件总线类型定义
export interface ProgressUpdateEvent {
  taskId: string
  phase: string
  progress: number
  currentStep: number
  totalSteps: number
  timestamp: number
}

export interface ToolCallEvent {
  taskId: string
  toolName: string
  action: string
  timestamp: number
}

export interface InterventionPromptEvent {
  taskId: string
  message: string
  timeoutSeconds: number
  timestamp: number
}

// 简单事件总线（使用Map存储回调）
type EventCallback<T> = (event: T) => void

const listeners = new Map<string, Set<EventCallback<unknown>>>()

export const eventBus = {
  // 订阅事件
  on<T>(event: string, callback: EventCallback<T>): void {
    if (!listeners.has(event)) {
      listeners.set(event, new Set())
    }
    listeners.get(event)!.add(callback as EventCallback<unknown>)
  },

  // 取消订阅
  off<T>(event: string, callback: EventCallback<T>): void {
    const set = listeners.get(event)
    if (set) {
      set.delete(callback as EventCallback<unknown>)
    }
  },

  // 发送事件
  emit<T>(event: string, data: T): void {
    const set = listeners.get(event)
    if (set) {
      set.forEach(callback => callback(data))
    }
  },

  // 清除所有监听
  clear(): void {
    listeners.clear()
  },
}
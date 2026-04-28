// API服务层
const API_BASE = '/api'
const RUNTIME_SESSION_BASE = '/runtime-api/session'

interface Task {
  id: string
  name: string
  domain: string
  status: string
  phase: string
  progress: number
  sessionId?: string
  description?: string
  priority: string
  gmtCreate: string
  gmtModified: string
}

interface TaskStats {
  running: number
  completed: number
  waiting: number
  alert: number
}

interface Checkpoint {
  id: string
  taskId: string
  phase: string
  stepIndex: number
  summary?: string
  gmtCreate: string
  isCurrent: boolean
}

interface PhaseStep {
  id: string
  taskId: string
  phase: string
  stepIndex: number
  stepName?: string
  status: string
  gmtCreate: string
  gmtModified: string
}

// 通用fetch封装
async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`API Error: ${response.status} ${response.statusText}`)
  }

  return response.json()
}

// 任务API
export const taskApi = {
  // 创建任务
  create: (data: {
    name: string
    domain: string
    prompt: string
    priority?: string
  }) =>
    fetchApi<Task>('/tasks', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // 获取任务列表
  list: (status?: string) =>
    fetchApi<Task[]>(`/tasks${status ? `?status=${status}` : ''}`),

  // 获取统计数据
  stats: () => fetchApi<TaskStats>('/tasks/stats'),

  // 获取任务详情
  detail: (id: string) => fetchApi<Task>(`/tasks/${id}`),

  // 暂停任务
  pause: (id: string) =>
    fetchApi<Task>(`/tasks/${id}/pause`, { method: 'POST' }),

  // 恢复任务
  resume: (id: string) =>
    fetchApi<Task>(`/tasks/${id}/resume`, { method: 'POST' }),

  // 确认介入
  confirm: (id: string, userInput: string) =>
    fetchApi<Task>(`/tasks/confirm/${id}`, {
      method: 'POST',
      body: JSON.stringify({ userInput }),
    }),

  // 取消任务
  cancel: (id: string) =>
    fetchApi<Task>(`/tasks/cancel/${id}`, { method: 'POST' }),

  // 删除任务
  delete: (id: string) =>
    fetchApi<void>(`/tasks/${id}`, { method: 'DELETE' }),

  // 重新执行任务（重置为pending）
  retry: (id: string) =>
    fetchApi<Task>(`/tasks/retry/${id}`, { method: 'POST' }),
}

// Checkpoint API
export const checkpointApi = {
  // 获取Checkpoint历史
  list: (taskId: string) =>
    fetchApi<Checkpoint[]>(`/checkpoints/${taskId}`),

  // 回退到Checkpoint
  revert: (checkpointId: string) =>
    fetchApi<Checkpoint>(`/checkpoints/revert/${checkpointId}`, { method: 'POST' }),
}

// 步骤API
export const stepApi = {
  // 获取阶段步骤列表
  list: (taskId: string, phase: string) =>
    fetchApi<PhaseStep[]>(`/steps/${taskId}/${phase}`),
}

// Session API（通过 Vite /runtime-api 代理到 Python runtime 服务）
// Runtime Console 使用 runtimeApi.ts，此路径仅供旧任务流页面使用
export const sessionApi = {
  // 获取session状态
  status: async (sessionId: string): Promise<SessionStatus> => {
    const response = await fetch(`${RUNTIME_SESSION_BASE}/${sessionId}/status`)
    if (!response.ok) throw new Error(`API Error: ${response.status} ${response.statusText}`)
    return response.json()
  },

  // 获取session事件列表
  events: async (sessionId: string): Promise<SessionEvents> => {
    const response = await fetch(`${RUNTIME_SESSION_BASE}/${sessionId}/events-list`)
    if (!response.ok) throw new Error(`API Error: ${response.status} ${response.statusText}`)
    return response.json()
  },
}

interface SessionStatus {
  session_id: string
  status: string
  events_count: number
}

interface SessionEvents {
  session_id: string
  events_count: number
  parsed_events: ParsedEvent[]
  raw_events: any[]
}

interface ParsedEvent {
  type: 'thinking' | 'tool_use' | 'text'
  text?: string
  tool_name?: string
  tool_input?: any
}

export type { Task, TaskStats, Checkpoint, PhaseStep, SessionStatus, SessionEvents, ParsedEvent }
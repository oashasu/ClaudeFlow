// API服务层
const API_BASE = 'http://localhost:21000/api'

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

export type { Task, TaskStats, Checkpoint, PhaseStep }
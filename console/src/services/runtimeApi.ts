export type {
  RuntimeReasonItem,
  RuntimeRunnableTask,
  RuntimePlan,
  RuntimeExplain,
  RuntimeStartedTask,
  RuntimeDispatch,
  RuntimeStatus,
  RuntimeSession,
  RuntimeParsedEvent,
  RuntimeSessionEvents,
  RuntimeSessionActionResponse,
  ActionAuditRecord,
} from '../types/runtime'

import type {
  RuntimePlan,
  RuntimeExplain,
  RuntimeDispatch,
  RuntimeStatus,
  RuntimeSession,
  RuntimeSessionEvents,
  RuntimeSessionActionResponse,
  ActionAuditRecord,
} from '../types/runtime'

const RUNTIME_BASE = '/runtime-api/runtime'
const SESSION_BASE = '/runtime-api/session'

async function fetchRuntime<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${RUNTIME_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`Runtime API Error: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

async function fetchSession<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${SESSION_BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    throw new Error(`Runtime API Error: ${response.status} ${response.statusText}`)
  }

  return response.json() as Promise<T>
}

export const runtimePlanSample: RuntimePlan = {
  runnable: [
    {
      task_id: 'impl_auth_controller',
      priority: 'high',
      owner_role: 'backend-agent',
      task_type: 'ImplementTask',
    },
  ],
  blocked: [
    {
      task_id: 'impl_auth_tests',
      priority: 'medium',
      reason_code: 'waiting_dependency',
      reason: '等待依赖完成: impl_auth_controller(running)',
    },
  ],
  running: [
    {
      task_id: 'impl_payment_gateway',
      priority: 'high',
      reason_code: 'session_running',
      reason: '任务已有运行中的会话',
    },
  ],
}

export const runtimeExplainSample: RuntimeExplain = {
  task_id: 'impl_auth_tests',
  state: 'blocked',
  priority: 'medium',
  reason_code: 'waiting_dependency',
  reason: '等待依赖完成: impl_auth_controller(running)',
  dependencies: ['impl_auth_controller'],
}

export const runtimeDispatchSample: RuntimeDispatch = {
  runnable_count: 2,
  blocked_count: 1,
  active_agents: 1,
  available_slots: 1,
  max_concurrent: 2,
  started: [
    {
      task_id: 'impl_auth_controller',
      session_id: 'sess-auth-001',
      priority: 'high',
    },
  ],
  skipped: [],
  blocked: [
    {
      task_id: 'impl_auth_tests',
      priority: 'medium',
      reason_code: 'waiting_dependency',
      reason: '等待依赖完成: impl_auth_controller(running)',
    },
  ],
}

export const runtimeStatusSample: RuntimeStatus = {
  repo_path: '/Users/claw/sandbox/personal/claudeflow',
  active_agents: 1,
  queued_tasks: 2,
  completed_tasks: 4,
  failed_tasks: 1,
  intervention_required: true,
  running_tasks: ['impl_payment_gateway'],
}

export const runtimeSessionsSample: RuntimeSession[] = [
  {
    task_id: 'impl_payment_gateway',
    session_id: 'sess-pay-001',
    status: 'running',
    priority: 'high',
    owner_role: 'backend-agent',
    task_type: 'ImplementTask',
    summary: '已完成支付网关骨架，等待下游测试。',
  },
  {
    task_id: 'impl_auth_controller',
    session_id: 'sess-auth-001',
    status: 'completed',
    priority: 'high',
    owner_role: 'backend-agent',
    task_type: 'ImplementTask',
    summary: 'Auth controller 已完成并通过测试。',
  },
]

export const runtimeSessionEventsSample: RuntimeSessionEvents = {
  session_id: 'sess-pay-001',
  events_count: 3,
  parsed_events: [
    {
      type: 'thinking',
      text: '先确认支付网关接口的写入边界，再补 service 骨架。',
    },
    {
      type: 'tool_use',
      tool_name: 'Read',
      tool_input: { path: 'src/payment/gateway.py' },
    },
    {
      type: 'text',
      text: '已完成支付网关骨架，准备进入测试补充。',
    },
  ],
  raw_events: [],
}

function parseJson<T>(input: string): T {
  return JSON.parse(input) as T
}

export const runtimeJson = {
  parsePlan: (input: string) => parseJson<RuntimePlan>(input),
  parseExplain: (input: string) => parseJson<RuntimeExplain>(input),
  parseDispatch: (input: string) => parseJson<RuntimeDispatch>(input),
}

export const runtimeApi = {
  status: () => fetchRuntime<RuntimeStatus>('/status'),
  sessions: () => fetchRuntime<{ sessions: RuntimeSession[] }>('/sessions'),
  plan: () => fetchRuntime<RuntimePlan>('/plan'),
  explain: (taskId: string) => fetchRuntime<RuntimeExplain>(`/explain/${taskId}`),
  sessionEvents: (sessionId: string) => fetchSession<RuntimeSessionEvents>(`/${sessionId}/events-list`),
  interveneSession: (sessionId: string, prompt: string) =>
    fetchSession<RuntimeSessionActionResponse>(`/${sessionId}/intervene`, {
      method: 'POST',
      body: JSON.stringify({ prompt }),
    }),
  dispatch: (payload: { base_branch?: string; limit?: number | null; max_concurrent?: number | null }) =>
    fetchRuntime<RuntimeDispatch>('/dispatch', {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  completeTask: (taskId: string, payload: { summary?: string; changed_files?: string[]; test_status?: string; test_count?: number }) =>
    fetchRuntime<RuntimeSessionActionResponse>(`/task/${taskId}/complete`, {
      method: 'POST',
      body: JSON.stringify(payload),
    }),
  failTask: (taskId: string, reason: string) =>
    fetchRuntime<RuntimeSessionActionResponse>(`/task/${taskId}/fail`, {
      method: 'POST',
      body: JSON.stringify({ reason }),
    }),
  // T302: 审计记录 API
  listActionAudit: (params?: { action_type?: string; target_task_id?: string; limit?: number }) => {
    const searchParams = new URLSearchParams()
    if (params?.action_type) searchParams.set('action_type', params.action_type)
    if (params?.target_task_id) searchParams.set('target_task_id', params.target_task_id)
    if (params?.limit) searchParams.set('limit', String(params.limit))
    return fetchRuntime<{ records: ActionAuditRecord[]; total: number }>(
      `/action-audit?${searchParams.toString()}`
    )
  },
  getActionAudit: (actionId: string) =>
    fetchRuntime<ActionAuditRecord>(`/action-audit/${actionId}`),
}

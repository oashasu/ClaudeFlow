export interface RuntimeReasonItem {
  task_id: string
  priority: string
  reason_code: string
  reason: string
}

export interface RuntimeRunnableTask {
  task_id: string
  priority: string
  owner_role: string
  task_type: string
}

export interface RuntimePlan {
  runnable: RuntimeRunnableTask[]
  blocked: RuntimeReasonItem[]
  running: RuntimeReasonItem[]
}

export interface RuntimeExplain {
  task_id: string
  state: string
  priority: string
  reason_code: string
  reason: string
  dependencies: string[]
}

export interface RuntimeStartedTask {
  task_id: string
  session_id: string
  priority: string
}

export interface RuntimeDispatch {
  runnable_count: number
  blocked_count: number
  active_agents: number
  available_slots: number
  max_concurrent: number | null
  started: RuntimeStartedTask[]
  skipped: RuntimeReasonItem[]
  blocked: RuntimeReasonItem[]
}

export interface RuntimeStatus {
  repo_path: string
  active_agents: number
  queued_tasks: number
  completed_tasks: number
  failed_tasks: number
  intervention_required: boolean
  running_tasks: string[]
}

export interface RuntimeSession {
  task_id: string
  session_id: string
  worktree?: string
  status: string
  owner_role?: string
  task_type?: string
  priority: string
  summary?: string
}

export interface RuntimeParsedEvent {
  type: 'thinking' | 'tool_use' | 'text'
  text?: string
  tool_name?: string
  tool_input?: unknown
}

export interface RuntimeSessionEvents {
  session_id: string
  events_count: number
  parsed_events: RuntimeParsedEvent[]
  raw_events: unknown[]
}

export interface RuntimeSessionActionResponse {
  session_id?: string
  task_id?: string
  status: string
  summary?: string
}

export interface RuntimeActionResult {
  success: boolean
  message: string
  timestamp: string
  actionType: 'intervene' | 'complete' | 'fail' | 'dispatch'
  targetTaskId?: string
  targetSessionId?: string
}

// T302: 审计记录类型
export interface ActionAuditRecord {
  action_id: string
  action_type: 'intervene' | 'complete' | 'fail'
  target_task_id: string
  target_session_id?: string
  success: boolean
  message: string
  operator: string
  timestamp: string
  metadata: Record<string, unknown>
  prompt?: string
  summary?: string
  changed_files?: string[]
  test_status?: string
  test_count?: number
  reason?: string
}

export type DataSource = 'sample' | 'live'
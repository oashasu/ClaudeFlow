/**
 * Runtime Mock Samples
 *
 * 独立模块，专门用于 vi.mock factory 导入
 * 不依赖 vitest/vi，避免循环依赖问题
 */

export const defaultMockStatus = {
  repo_path: '/tmp/repo',
  active_agents: 2,
  queued_tasks: 5,
  completed_tasks: 10,
  failed_tasks: 1,
  intervention_required: false,
  running_tasks: ['t1', 't2'],
}

export const defaultMockSessions = {
  sessions: [
    { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' },
    { task_id: 't2', session_id: 's2', status: 'blocked', priority: 'medium' },
  ],
}

export const defaultMockEvents = {
  session_id: 's1',
  events_count: 2,
  parsed_events: [
    { type: 'thinking', text: '思考中...' },
    { type: 'text', text: '回复内容' },
  ],
  raw_events: [],
}

export const defaultMockPlan = {
  runnable: [
    { task_id: 't1', priority: 'high', executor_type: 'claude', phase_id: 'phase-1' },
  ],
  blocked: [],
  running: [],
}

export const defaultMockExplain = {
  task_id: 't1',
  state: 'blocked',
  priority: 'high',
  reason_code: 'waiting',
  reason: '等待依赖完成',
  dependencies: ['t0'],
}

export const defaultMockDispatch = {
  runnable_count: 1,
  blocked_count: 0,
  active_agents: 1,
  available_slots: 1,
  started: ['t1'],
  skipped: [],
  blocked: [],
}

export const defaultMockAuditRecords = {
  records: [
    {
      action_id: 'a1',
      action_type: 'intervene',
      target_task_id: 't1',
      target_session_id: 's1',
      success: true,
      message: '干预成功',
      timestamp: '2026-04-27T10:00:00Z',
    },
  ],
  total: 1,
}

export const defaultSessionActionResponse = {
  success: true,
  message: 'Action completed',
  session_id: 's1',
}

// ── Aggregated Export ──────────────────────────────────────────────────────────

export const runtimeMockSamples = {
  status: defaultMockStatus,
  sessions: defaultMockSessions.sessions,
  sessionEvents: defaultMockEvents,
  plan: defaultMockPlan,
  explain: defaultMockExplain,
  dispatch: defaultMockDispatch,
  auditRecords: defaultMockAuditRecords,
  auditRecord: defaultMockAuditRecords.records[0],
  sessionActionResponse: defaultSessionActionResponse,
}
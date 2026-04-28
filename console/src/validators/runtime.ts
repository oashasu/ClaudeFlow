import type {
  RuntimePlan,
  RuntimeExplain,
  RuntimeDispatch,
  RuntimeStatus,
  RuntimeSession,
  RuntimeSessionEvents,
} from '../types/runtime'

export interface ParseResult<T> {
  data: T | null
  error: string | null
}

function safeParse<T>(input: string, validator: (obj: unknown) => boolean): ParseResult<T> {
  try {
    const parsed = JSON.parse(input) as unknown
    if (!validator(parsed)) {
      return { data: null, error: 'JSON 结构不符合预期协议' }
    }
    return { data: parsed as T, error: null }
  } catch (e) {
    return { data: null, error: `JSON 解析失败: ${(e as Error).message}` }
  }
}

function isPlan(obj: unknown): boolean {
  if (typeof obj !== 'object' || obj === null) return false
  const p = obj as Record<string, unknown>
  if (!Array.isArray(p.runnable) || !Array.isArray(p.blocked) || !Array.isArray(p.running)) return false
  // A34: 校验 runnable 核心字段
  for (const task of p.runnable) {
    if (typeof task !== 'object' || task === null) return false
    const t = task as Record<string, unknown>
    if (typeof t.task_id !== 'string' || typeof t.priority !== 'string') return false
  }
  return true
}

function isExplain(obj: unknown): boolean {
  if (typeof obj !== 'object' || obj === null) return false
  const e = obj as Record<string, unknown>
  if (typeof e.task_id !== 'string' || typeof e.state !== 'string') return false
  if (typeof e.priority !== 'string' || typeof e.reason_code !== 'string') return false
  if (typeof e.reason !== 'string' || !Array.isArray(e.dependencies)) return false
  return true
}

function isDispatch(obj: unknown): boolean {
  if (typeof obj !== 'object' || obj === null) return false
  const d = obj as Record<string, unknown>
  if (typeof d.active_agents !== 'number' || typeof d.available_slots !== 'number') return false
  if (typeof d.runnable_count !== 'number' || typeof d.blocked_count !== 'number') return false
  if (!Array.isArray(d.started) || !Array.isArray(d.blocked)) return false
  // A34: 校验 started 核心字段
  for (const task of d.started) {
    if (typeof task !== 'object' || task === null) return false
    const t = task as Record<string, unknown>
    if (typeof t.task_id !== 'string' || typeof t.session_id !== 'string') return false
  }
  return true
}

function isStatus(obj: unknown): boolean {
  if (typeof obj !== 'object' || obj === null) return false
  const s = obj as Record<string, unknown>
  if (typeof s.repo_path !== 'string' || typeof s.active_agents !== 'number') return false
  if (typeof s.queued_tasks !== 'number' || typeof s.completed_tasks !== 'number') return false
  if (typeof s.failed_tasks !== 'number' || typeof s.intervention_required !== 'boolean') return false
  if (!Array.isArray(s.running_tasks)) return false
  return true
}

function isSessionArray(obj: unknown): boolean {
  if (!Array.isArray(obj)) return false
  for (const item of obj) {
    if (typeof item !== 'object' || item === null) return false
    const s = item as Record<string, unknown>
    if (typeof s.task_id !== 'string' || typeof s.session_id !== 'string') return false
    if (typeof s.status !== 'string' || typeof s.priority !== 'string') return false
  }
  return true
}

function isSessionEvents(obj: unknown): boolean {
  if (typeof obj !== 'object' || obj === null) return false
  const se = obj as Record<string, unknown>
  if (typeof se.session_id !== 'string' || typeof se.events_count !== 'number') return false
  if (!Array.isArray(se.parsed_events) || !Array.isArray(se.raw_events)) return false
  // A34: 校验 parsed_events 核心字段
  for (const event of se.parsed_events) {
    if (typeof event !== 'object' || event === null) return false
    const e = event as Record<string, unknown>
    if (typeof e.type !== 'string') return false
    if (e.type !== 'thinking' && e.type !== 'tool_use' && e.type !== 'text') return false
  }
  return true
}

export const runtimeValidator = {
  parsePlan: (input: string): ParseResult<RuntimePlan> => safeParse<RuntimePlan>(input, isPlan),
  parseExplain: (input: string): ParseResult<RuntimeExplain> => safeParse<RuntimeExplain>(input, isExplain),
  parseDispatch: (input: string): ParseResult<RuntimeDispatch> => safeParse<RuntimeDispatch>(input, isDispatch),
  parseStatus: (input: string): ParseResult<RuntimeStatus> => safeParse<RuntimeStatus>(input, isStatus),
  parseSessions: (input: string): ParseResult<RuntimeSession[]> => safeParse<RuntimeSession[]>(input, isSessionArray),
  parseSessionEvents: (input: string): ParseResult<RuntimeSessionEvents> =>
    safeParse<RuntimeSessionEvents>(input, isSessionEvents),
}
import { runtimeValidator } from '../src/validators/runtime'
import type {
  RuntimePlan,
  RuntimeExplain,
  RuntimeDispatch,
  RuntimeStatus,
  RuntimeSession,
  RuntimeSessionEvents,
} from '../src/types/runtime'

describe('runtimeValidator', () => {
  // A34: 校验增强测试

  describe('parsePlan', () => {
    const validPlan: RuntimePlan = {
      runnable: [
        { task_id: 't1', priority: 'high', owner_role: 'agent', task_type: 'ImplementTask' },
      ],
      blocked: [
        { task_id: 't2', priority: 'medium', reason_code: 'waiting_dependency', reason: '等待 t1' },
      ],
      running: [],
    }

    it('解析有效 plan', () => {
      const result = runtimeValidator.parsePlan(JSON.stringify(validPlan))
      expect(result.error).toBeNull()
      expect(result.data?.runnable.length).toBe(1)
    })

    it('拒绝缺少 runnable 字段的 plan', () => {
      const result = runtimeValidator.parsePlan(JSON.stringify({ blocked: [], running: [] }))
      expect(result.error).toBe('JSON 结构不符合预期协议')
      expect(result.data).toBeNull()
    })

    it('拒绝 runnable 中缺少 task_id 的 plan', () => {
      const result = runtimeValidator.parsePlan(
        JSON.stringify({ runnable: [{ priority: 'high' }], blocked: [], running: [] })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝无效 JSON', () => {
      const result = runtimeValidator.parsePlan('not json')
      expect(result.error).toContain('JSON 解析失败')
    })
  })

  describe('parseExplain', () => {
    const validExplain: RuntimeExplain = {
      task_id: 't1',
      state: 'blocked',
      priority: 'high',
      reason_code: 'waiting_dependency',
      reason: '等待依赖',
      dependencies: ['t0'],
    }

    it('解析有效 explain', () => {
      const result = runtimeValidator.parseExplain(JSON.stringify(validExplain))
      expect(result.error).toBeNull()
      expect(result.data?.task_id).toBe('t1')
    })

    it('拒绝缺少 reason_code 的 explain', () => {
      const result = runtimeValidator.parseExplain(
        JSON.stringify({ task_id: 't1', state: 'blocked', priority: 'high', reason: 'x', dependencies: [] })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝缺少 dependencies 的 explain', () => {
      const result = runtimeValidator.parseExplain(
        JSON.stringify({ task_id: 't1', state: 'blocked', priority: 'high', reason_code: 'x', reason: 'y' })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })
  })

  describe('parseDispatch', () => {
    const validDispatch: RuntimeDispatch = {
      runnable_count: 2,
      blocked_count: 1,
      active_agents: 1,
      available_slots: 1,
      max_concurrent: 2,
      started: [{ task_id: 't1', session_id: 's1', priority: 'high' }],
      skipped: [],
      blocked: [],
    }

    it('解析有效 dispatch', () => {
      const result = runtimeValidator.parseDispatch(JSON.stringify(validDispatch))
      expect(result.error).toBeNull()
      expect(result.data?.active_agents).toBe(1)
    })

    it('拒绝缺少 runnable_count 的 dispatch', () => {
      const result = runtimeValidator.parseDispatch(
        JSON.stringify({ active_agents: 1, available_slots: 1, started: [], skipped: [], blocked: [] })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝 started 中缺少 session_id 的 dispatch', () => {
      const result = runtimeValidator.parseDispatch(
        JSON.stringify({
          runnable_count: 1,
          blocked_count: 0,
          active_agents: 1,
          available_slots: 1,
          started: [{ task_id: 't1', priority: 'high' }],
          skipped: [],
          blocked: [],
        })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })
  })

  describe('parseStatus', () => {
    const validStatus: RuntimeStatus = {
      repo_path: '/tmp/repo',
      active_agents: 2,
      queued_tasks: 5,
      completed_tasks: 10,
      failed_tasks: 1,
      intervention_required: true,
      running_tasks: ['t1', 't2'],
    }

    it('解析有效 status', () => {
      const result = runtimeValidator.parseStatus(JSON.stringify(validStatus))
      expect(result.error).toBeNull()
      expect(result.data?.repo_path).toBe('/tmp/repo')
    })

    it('拒绝缺少 intervention_required 的 status', () => {
      const result = runtimeValidator.parseStatus(
        JSON.stringify({
          repo_path: '/tmp',
          active_agents: 1,
          queued_tasks: 0,
          completed_tasks: 0,
          failed_tasks: 0,
          running_tasks: [],
        })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝缺少 running_tasks 的 status', () => {
      const result = runtimeValidator.parseStatus(
        JSON.stringify({
          repo_path: '/tmp',
          active_agents: 1,
          queued_tasks: 0,
          completed_tasks: 0,
          failed_tasks: 0,
          intervention_required: false,
        })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })
  })

  describe('parseSessions', () => {
    const validSessions: RuntimeSession[] = [
      { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' },
      { task_id: 't2', session_id: 's2', status: 'completed', priority: 'medium', summary: 'done' },
    ]

    it('解析有效 sessions 数组', () => {
      const result = runtimeValidator.parseSessions(JSON.stringify(validSessions))
      expect(result.error).toBeNull()
      expect(result.data?.length).toBe(2)
    })

    it('拒绝缺少 status 的 session', () => {
      const result = runtimeValidator.parseSessions(
        JSON.stringify([{ task_id: 't1', session_id: 's1', priority: 'high' }])
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝缺少 priority 的 session', () => {
      const result = runtimeValidator.parseSessions(
        JSON.stringify([{ task_id: 't1', session_id: 's1', status: 'running' }])
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝非数组输入', () => {
      const result = runtimeValidator.parseSessions(JSON.stringify({}))
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })
  })

  describe('parseSessionEvents', () => {
    const validEvents: RuntimeSessionEvents = {
      session_id: 's1',
      events_count: 2,
      parsed_events: [
        { type: 'thinking', text: '思考中' },
        { type: 'tool_use', tool_name: 'Read', tool_input: { path: 'a.py' } },
      ],
      raw_events: [],
    }

    it('解析有效 session events', () => {
      const result = runtimeValidator.parseSessionEvents(JSON.stringify(validEvents))
      expect(result.error).toBeNull()
      expect(result.data?.parsed_events.length).toBe(2)
    })

    it('拒绝缺少 events_count 的 events', () => {
      const result = runtimeValidator.parseSessionEvents(
        JSON.stringify({ session_id: 's1', parsed_events: [], raw_events: [] })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝 parsed_events 中缺少 type 的 event', () => {
      const result = runtimeValidator.parseSessionEvents(
        JSON.stringify({
          session_id: 's1',
          events_count: 1,
          parsed_events: [{ text: 'x' }],
          raw_events: [],
        })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })

    it('拒绝无效 event type', () => {
      const result = runtimeValidator.parseSessionEvents(
        JSON.stringify({
          session_id: 's1',
          events_count: 1,
          parsed_events: [{ type: 'invalid_type' }],
          raw_events: [],
        })
      )
      expect(result.error).toBe('JSON 结构不符合预期协议')
    })
  })
})
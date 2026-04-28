import { useRuntimeLiveData } from '../src/composables/useRuntimeLiveData'
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest'
import {
  withComposable,
  captureWarnings,
  flushPromises,
  assertNoLifecycleWarning,
} from './helpers/runtimeHarness'

// Mock 必须在 factory 内直接创建，因为 vi.mock 会 hoist 到顶部
vi.mock('../src/services/runtimeApi', () => {
  const mockFn = vi.fn
  return {
    runtimeApi: {
      status: mockFn(),
      sessions: mockFn(),
      sessionEvents: mockFn(),
      plan: mockFn(),
      explain: mockFn(),
      dispatch: mockFn(),
    },
    runtimePlanSample: {
      runnable: [{ task_id: 't1', priority: 'high', executor_type: 'claude', phase_id: 'phase-1' }],
      blocked: [],
      running: [],
    },
    runtimeExplainSample: {
      task_id: 't1',
      state: 'blocked',
      priority: 'high',
      reason_code: 'waiting',
      reason: 'blocked',
      dependencies: [],
    },
    runtimeDispatchSample: {
      runnable_count: 1,
      blocked_count: 0,
      active_agents: 1,
      available_slots: 1,
      started: [{ task_id: 't1', session_id: 's1' }],
      skipped: [],
      blocked: [],
    },
    runtimeStatusSample: {
      repo_path: '/tmp',
      active_agents: 0,
      queued_tasks: 0,
      completed_tasks: 0,
      failed_tasks: 0,
      intervention_required: false,
      running_tasks: [],
    },
    runtimeSessionsSample: [
      { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' },
    ],
    runtimeSessionEventsSample: {
      session_id: 's1',
      events_count: 0,
      parsed_events: [],
      raw_events: [],
    },
  }
})

describe('useRuntimeLiveData live payload validation', () => {
  // A34: live payload 校验测试
  // A42: 使用标准 Vue setup/harness

  let warningCapture: ReturnType<typeof captureWarnings>
  let runtimeApi: typeof import('../src/services/runtimeApi').runtimeApi

  beforeEach(async () => {
    vi.clearAllMocks()
    warningCapture = captureWarnings()
    // 动态导入获取 mock 实例
    const module = await import('../src/services/runtimeApi')
    runtimeApi = module.runtimeApi
  })

  afterEach(() => {
    warningCapture.restore()
  })

  describe('loadLiveStatus', () => {
    it('valid status payload 通过校验', async () => {
      const validStatus = {
        repo_path: '/tmp/repo',
        active_agents: 2,
        queued_tasks: 5,
        completed_tasks: 10,
        failed_tasks: 1,
        intervention_required: true,
        running_tasks: ['t1'],
      }
      const validSessions = {
        sessions: [
          { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' },
        ],
      }

      vi.mocked(runtimeApi.status).mockResolvedValue(validStatus)
      vi.mocked(runtimeApi.sessions).mockResolvedValue(validSessions)

      // A42: 使用 withComposable 在 Vue setup 上下文中运行
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveStatus()

      expect(liveData.state.value.parseError).toBeNull()
      expect(liveData.state.value.status?.repo_path).toBe('/tmp/repo')
      expect(liveData.state.value.sessions.length).toBe(1)

      // 验证没有 lifecycle warning
      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('invalid status payload 设置 parseError', async () => {
      // 缺少 intervention_required 字段
      const invalidStatus = {
        repo_path: '/tmp',
        active_agents: 1,
        queued_tasks: 0,
        completed_tasks: 0,
        failed_tasks: 0,
        running_tasks: [],
      }

      vi.mocked(runtimeApi.status).mockResolvedValue(invalidStatus)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveStatus()

      expect(liveData.state.value.parseError).toContain('协议校验失败')
      expect(liveData.state.value.status).toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('invalid sessions payload 设置 parseError', async () => {
      const validStatus = {
        repo_path: '/tmp',
        active_agents: 0,
        queued_tasks: 0,
        completed_tasks: 0,
        failed_tasks: 0,
        intervention_required: false,
        running_tasks: [],
      }
      // 缺少 status 字段
      const invalidSessions = {
        sessions: [
          { task_id: 't1', session_id: 's1', priority: 'high' },
        ],
      }

      vi.mocked(runtimeApi.status).mockResolvedValue(validStatus)
      vi.mocked(runtimeApi.sessions).mockResolvedValue(invalidSessions)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveStatus()

      expect(liveData.state.value.parseError).toContain('Sessions 协议校验失败')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  describe('loadLiveSessionEvents', () => {
    it('valid events payload 通过校验', async () => {
      const validEvents = {
        session_id: 's1',
        events_count: 1,
        parsed_events: [{ type: 'thinking', text: '思考中' }],
        raw_events: [],
      }

      vi.mocked(runtimeApi.sessionEvents).mockResolvedValue(validEvents)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      const session = { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' }
      await liveData.loadLiveSessionEvents(session)

      expect(liveData.state.value.sessionEventsError).toBeNull()
      expect(liveData.state.value.sessionEvents.length).toBe(1)

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('invalid events payload 设置 sessionEventsError', async () => {
      // 缺少 events_count 字段
      const invalidEvents = {
        session_id: 's1',
        parsed_events: [],
        raw_events: [],
      }

      vi.mocked(runtimeApi.sessionEvents).mockResolvedValue(invalidEvents)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      const session = { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' }
      await liveData.loadLiveSessionEvents(session)

      expect(liveData.state.value.sessionEventsError).toContain('协议校验失败')
      expect(liveData.state.value.sessionEvents.length).toBe(0)

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('invalid event type 设置 sessionEventsError', async () => {
      const invalidEvents = {
        session_id: 's1',
        events_count: 1,
        parsed_events: [{ type: 'invalid_type' }],
        raw_events: [],
      }

      vi.mocked(runtimeApi.sessionEvents).mockResolvedValue(invalidEvents)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      const session = { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' }
      await liveData.loadLiveSessionEvents(session)

      expect(liveData.state.value.sessionEventsError).toContain('协议校验失败')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: parsePlan computed property 错误路径
  describe('parsePlan computed - T403', () => {
    it('valid plan JSON 通过 parse', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      // 初始 sample 是有效的
      expect(liveData.plan.value).not.toBeNull()
      expect(liveData.plan.value?.runnable.length).toBe(1)
      expect(liveData.state.value.parseError).toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('invalid plan JSON 设置 parseError 不静默降级', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      // 设置无效 JSON：缺少 runnable 数组
      liveData.setPlanInput('{ "blocked": [], "running": [] }')
      await flushPromises()

      // 先访问 computed 触发验证（Vue computed 是惰性的）
      expect(liveData.plan.value).toBeNull()
      // parseError 在 computed 运行后被设置
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('malformed JSON 设置 parseError', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      liveData.setPlanInput('not a json')
      await flushPromises()

      // 先访问 computed 触发验证
      expect(liveData.plan.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 解析失败')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('runnable task 缺少 task_id 设置 parseError', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      // runnable 里的 task 缺少 task_id
      liveData.setPlanInput('{ "runnable": [{ "priority": "high" }], "blocked": [], "running": [] }')
      await flushPromises()

      // 先访问 computed 触发验证
      expect(liveData.plan.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: parseExplain computed property 错误路径
  describe('parseExplain computed - T403', () => {
    it('valid explain JSON 通过 parse', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      expect(liveData.explain.value).not.toBeNull()
      expect(liveData.explain.value?.task_id).toBe('t1')
      expect(liveData.state.value.parseError).toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('invalid explain JSON 设置 parseError 不静默降级', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      // 缺少 reason 字段
      liveData.setExplainInput('{ "task_id": "t1", "state": "blocked", "priority": "high", "reason_code": "waiting", "dependencies": [] }')
      await flushPromises()

      // 先访问 computed 触发验证
      expect(liveData.explain.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('explain 缺少 dependencies 数组设置 parseError', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      liveData.setExplainInput('{ "task_id": "t1", "state": "blocked", "priority": "high", "reason_code": "waiting", "reason": "test" }')
      await flushPromises()

      // 先访问 computed 触发验证
      expect(liveData.explain.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: parseDispatch computed property 错误路径
  describe('parseDispatch computed - T403', () => {
    it('valid dispatch JSON 通过 parse', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      expect(liveData.dispatch.value).not.toBeNull()
      expect(liveData.dispatch.value?.runnable_count).toBe(1)
      expect(liveData.state.value.parseError).toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('invalid dispatch JSON 设置 parseError 不静默降级', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      // 缺少 active_agents 字段
      liveData.setDispatchInput('{ "runnable_count": 1, "blocked_count": 0, "available_slots": 1, "started": [], "blocked": [] }')
      await flushPromises()

      // 先访问 computed 触发验证
      expect(liveData.dispatch.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('started task 缺少 session_id 设置 parseError', async () => {
      const { result: liveData } = await withComposable(() => useRuntimeLiveData())

      liveData.setDispatchInput('{ "runnable_count": 1, "blocked_count": 0, "active_agents": 1, "available_slots": 1, "started": [{ "task_id": "t1" }], "blocked": [] }')
      await flushPromises()

      // 先访问 computed 触发验证
      expect(liveData.dispatch.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: loadLivePlan API + parse 失败路径
  describe('loadLivePlan - T403', () => {
    it('API 返回有效 payload 通过 parse', async () => {
      const validPlan = {
        runnable: [{ task_id: 't2', priority: 'medium', executor_type: 'claude', phase_id: 'phase-2' }],
        blocked: [],
        running: [],
      }

      vi.mocked(runtimeApi.plan).mockResolvedValue(validPlan)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLivePlan()
      await flushPromises()

      expect(liveData.state.value.parseError).toBeNull()
      expect(liveData.state.value.liveError).toBeNull()
      expect(liveData.plan.value?.runnable[0].task_id).toBe('t2')
      expect(liveData.state.value.planSource).toBe('live')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('API 返回无效 payload 设置 parseError 不静默降级', async () => {
      const invalidPlan = {
        runnable: [{ priority: 'high' }], // 缺少 task_id
        blocked: [],
        running: [],
      }

      vi.mocked(runtimeApi.plan).mockResolvedValue(invalidPlan)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLivePlan()
      await flushPromises()

      // loadLivePlan 只设置 planInput，computed 需要访问才触发验证
      expect(liveData.plan.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('API 失败设置 liveError', async () => {
      vi.mocked(runtimeApi.plan).mockRejectedValue(new Error('Network error'))

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLivePlan()
      await flushPromises()

      expect(liveData.state.value.liveError).toContain('加载 Runtime Plan 失败')
      expect(liveData.state.value.parseError).toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: loadLiveExplain API + parse 失败路径
  describe('loadLiveExplain - T403', () => {
    it('API 返回有效 payload 通过 parse', async () => {
      const validExplain = {
        task_id: 't2',
        state: 'running',
        priority: 'medium',
        reason_code: 'ready',
        reason: 'ready to run',
        dependencies: [],
      }

      vi.mocked(runtimeApi.explain).mockResolvedValue(validExplain)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveExplain('t2')
      await flushPromises()

      expect(liveData.state.value.parseError).toBeNull()
      expect(liveData.state.value.liveError).toBeNull()
      expect(liveData.explain.value?.state).toBe('running')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('API 返回无效 payload 设置 parseError 不静默降级', async () => {
      const invalidExplain = {
        task_id: 't2',
        state: 'running',
        // 缺少 priority, reason_code, reason, dependencies
      }

      vi.mocked(runtimeApi.explain).mockResolvedValue(invalidExplain)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveExplain('t2')
      await flushPromises()

      // loadLiveExplain 只设置 explainInput，computed 需要访问才触发验证
      expect(liveData.explain.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('API 失败设置 liveError', async () => {
      vi.mocked(runtimeApi.explain).mockRejectedValue(new Error('Explain error'))

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveExplain('t2')
      await flushPromises()

      expect(liveData.state.value.liveError).toContain('加载 Runtime Explain 失败')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: runLiveDispatch API + parse 失败路径
  describe('runLiveDispatch - T403', () => {
    it('API 返回有效 payload 通过 parse', async () => {
      const validDispatch = {
        runnable_count: 2,
        blocked_count: 0,
        active_agents: 2,
        available_slots: 2,
        started: [{ task_id: 't2', session_id: 's2' }],
        skipped: [],
        blocked: [],
      }

      vi.mocked(runtimeApi.dispatch).mockResolvedValue(validDispatch)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.runLiveDispatch(2)
      await flushPromises()

      expect(liveData.state.value.parseError).toBeNull()
      expect(liveData.state.value.liveError).toBeNull()
      expect(liveData.dispatch.value?.runnable_count).toBe(2)

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('API 返回无效 payload 设置 parseError 不静默降级', async () => {
      const invalidDispatch = {
        runnable_count: 1,
        blocked_count: 0,
        active_agents: 1,
        // 缺少 available_slots
        started: [],
        blocked: [],
      }

      vi.mocked(runtimeApi.dispatch).mockResolvedValue(invalidDispatch)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.runLiveDispatch(2)
      await flushPromises()

      // runLiveDispatch 只设置 dispatchInput，computed 需要访问才触发验证
      expect(liveData.dispatch.value).toBeNull()
      expect(liveData.state.value.parseError).toContain('JSON 结构不符合预期')

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('API 失败设置 liveError', async () => {
      vi.mocked(runtimeApi.dispatch).mockRejectedValue(new Error('Dispatch error'))

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.runLiveDispatch(2)
      await flushPromises()

      expect(liveData.state.value.liveError).toContain('加载 Runtime Dispatch 失败')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: loadLiveStatus API 失败路径
  describe('loadLiveStatus API failure - T403', () => {
    it('status API 失败设置 liveError', async () => {
      vi.mocked(runtimeApi.status).mockRejectedValue(new Error('Status API down'))

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveStatus()
      await flushPromises()

      expect(liveData.state.value.liveError).toContain('加载 Runtime 总览失败')
      expect(liveData.state.value.parseError).toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('sessions API 失败设置 liveError', async () => {
      const validStatus = {
        repo_path: '/tmp',
        active_agents: 0,
        queued_tasks: 0,
        completed_tasks: 0,
        failed_tasks: 0,
        intervention_required: false,
        running_tasks: [],
      }

      vi.mocked(runtimeApi.status).mockResolvedValue(validStatus)
      vi.mocked(runtimeApi.sessions).mockRejectedValue(new Error('Sessions API down'))

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveStatus()
      await flushPromises()

      expect(liveData.state.value.liveError).toContain('加载 Runtime 总览失败')

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: loadLiveSessionEvents API 失败路径
  describe('loadLiveSessionEvents API failure - T403', () => {
    it('API 失败设置 sessionEventsError', async () => {
      vi.mocked(runtimeApi.sessionEvents).mockRejectedValue(new Error('Events API down'))

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      const session = { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' }
      await liveData.loadLiveSessionEvents(session)
      await flushPromises()

      expect(liveData.state.value.sessionEventsError).toContain('加载 Session 事件失败')
      expect(liveData.state.value.sessionEventsLoading).toBe(false)

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })

  // T403: 状态断言完整性验证
  describe('状态断言完整性 - T403', () => {
    it('parseError 与 liveError 区分明确', async () => {
      // parse error 场景
      const invalidStatus = { repo_path: '/tmp' }
      vi.mocked(runtimeApi.status).mockResolvedValue(invalidStatus)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      await liveData.loadLiveStatus()
      await flushPromises()

      expect(liveData.state.value.parseError).not.toBeNull()
      expect(liveData.state.value.liveError).toBeNull()
      expect(liveData.state.value.status).toBeNull()

      // 重置后测试 live error
      liveData.clearErrors()
      vi.mocked(runtimeApi.status).mockRejectedValue(new Error('Network error'))
      await liveData.loadLiveStatus()
      await flushPromises()

      expect(liveData.state.value.parseError).toBeNull()
      expect(liveData.state.value.liveError).not.toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })

    it('sessionEventsError 与 parseError 区分明确', async () => {
      const invalidEvents = {
        session_id: 's1',
        // 缺少 events_count
        parsed_events: [],
        raw_events: [],
      }

      vi.mocked(runtimeApi.sessionEvents).mockResolvedValue(invalidEvents)

      const { result: liveData } = await withComposable(() => useRuntimeLiveData())
      const session = { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' }
      await liveData.loadLiveSessionEvents(session)
      await flushPromises()

      expect(liveData.state.value.sessionEventsError).toContain('协议校验失败')
      expect(liveData.state.value.sessionEvents.length).toBe(0)
      expect(liveData.state.value.parseError).toBeNull()

      assertNoLifecycleWarning(warningCapture.warnings)
    })
  })
})
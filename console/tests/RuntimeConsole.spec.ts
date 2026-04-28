/**
 * RuntimeConsole.spec.ts - A42: 使用统一 harness 基座
 *
 * 关键变更：
 * - 导入 runtimeHarness.ts 的 flushPromises() 和 mountRuntimeConsole()
 * - 导入 runtimeMockSamples.ts 的 sample 数据
 * - vi.mock 在顶层创建 mock（vitest hoisting 要求）
 * - beforeEach 使用动态导入获取 mock 函数，配置共享 sample 返回值
 */

import { describe, expect, it, beforeEach, vi } from 'vitest'
import { flushPromises, mountRuntimeConsole } from './helpers/runtimeHarness'
import {
  defaultMockStatus,
  defaultMockSessions,
  defaultMockEvents,
  defaultMockPlan,
  defaultMockExplain,
  defaultMockDispatch,
  defaultMockAuditRecords,
  defaultSessionActionResponse,
} from './helpers/runtimeMockSamples'

// ── Top-Level vi.mock (hoisted) ───────────────────────────────────────────────

// Mock runtimeApi 模块 - 必须在顶层，vitest hoisting 要求
vi.mock('../src/services/runtimeApi', () => {
  const mockFn = vi.fn

  // 内联 sample 数据（vitest hoisting 无法访问导入变量）
  const mockPlanSample = {
    runnable: [
      { task_id: 't1', priority: 'high', executor_type: 'claude', phase_id: 'phase-1' },
    ],
    blocked: [],
    running: [],
  }
  const mockExplainSample = {
    task_id: 't1',
    state: 'blocked',
    priority: 'high',
    reason_code: 'waiting',
    reason: '等待依赖完成',
    dependencies: ['t0'],
  }
  const mockDispatchSample = {
    runnable_count: 1,
    blocked_count: 0,
    active_agents: 1,
    available_slots: 1,
    started: ['t1'],
    skipped: [],
    blocked: [],
  }
  const mockStatusSample = {
    repo_path: '/tmp/repo',
    active_agents: 2,
    queued_tasks: 5,
    completed_tasks: 10,
    failed_tasks: 1,
    intervention_required: false,
    running_tasks: ['t1', 't2'],
  }
  const mockSessionsSample = [
    { task_id: 't1', session_id: 's1', status: 'running', priority: 'high' },
    { task_id: 't2', session_id: 's2', status: 'blocked', priority: 'medium' },
  ]
  const mockSessionEventsSample = {
    session_id: 's1',
    events_count: 2,
    parsed_events: [
      { type: 'thinking', text: '思考中...' },
      { type: 'text', text: '回复内容' },
    ],
    raw_events: [],
  }

  return {
    runtimeApi: {
      status: mockFn(),
      sessions: mockFn(),
      sessionEvents: mockFn(),
      plan: mockFn(),
      explain: mockFn(),
      dispatch: mockFn(),
      interveneSession: mockFn(),
      completeTask: mockFn(),
      failTask: mockFn(),
      listActionAudit: mockFn(),
      getActionAudit: mockFn(),
    },
    // sample 数据导出供组件默认显示
    runtimePlanSample: mockPlanSample,
    runtimeExplainSample: mockExplainSample,
    runtimeDispatchSample: mockDispatchSample,
    runtimeStatusSample: mockStatusSample,
    runtimeSessionsSample: mockSessionsSample,
    runtimeSessionEventsSample: mockSessionEventsSample,
  }
})

// Mock api 模块（action-audit）
vi.mock('../src/services/api', () => {
  const mockFn = vi.fn

  return {
    fetchActionAudit: mockFn(),
  }
})

// ── Test Suite ────────────────────────────────────────────────────────────────

describe('RuntimeConsole - A42: unified harness base', () => {
  let runtimeApi: typeof import('../src/services/runtimeApi').runtimeApi
  let fetchActionAudit: typeof import('../src/services/api').fetchActionAudit

  beforeEach(async () => {
    vi.clearAllMocks()

    // 动态导入获取 mock 实例（vitest 推荐方式）
    const runtimeModule = await import('../src/services/runtimeApi')
    runtimeApi = runtimeModule.runtimeApi

    const apiModule = await import('../src/services/api')
    fetchActionAudit = apiModule.fetchActionAudit

    // 配置 mock 返回值使用共享 samples
    vi.mocked(runtimeApi.status).mockResolvedValue(defaultMockStatus)
    vi.mocked(runtimeApi.sessions).mockResolvedValue(defaultMockSessions)
    vi.mocked(runtimeApi.sessionEvents).mockResolvedValue(defaultMockEvents)
    vi.mocked(runtimeApi.plan).mockResolvedValue(defaultMockPlan)
    vi.mocked(runtimeApi.explain).mockResolvedValue(defaultMockExplain)
    vi.mocked(runtimeApi.dispatch).mockResolvedValue(defaultMockDispatch)
    vi.mocked(runtimeApi.interveneSession).mockResolvedValue(defaultSessionActionResponse)
    vi.mocked(runtimeApi.completeTask).mockResolvedValue(defaultSessionActionResponse)
    vi.mocked(runtimeApi.failTask).mockResolvedValue(defaultSessionActionResponse)
    vi.mocked(runtimeApi.listActionAudit).mockResolvedValue(defaultMockAuditRecords)
    vi.mocked(runtimeApi.getActionAudit).mockResolvedValue(defaultMockAuditRecords.records[0])
    vi.mocked(fetchActionAudit).mockResolvedValue(defaultMockAuditRecords)
  })

  it('渲染三块 runtime 静板', async () => {
    const wrapper = await mountRuntimeConsole()

    expect(wrapper.text()).toContain('Plan')
    expect(wrapper.text()).toContain('Explain')
    expect(wrapper.text()).toContain('Dispatch')
  })

  it('默认加载示例数据 - 使用 runtimeMockSamples', async () => {
    const wrapper = await mountRuntimeConsole()

    // t1 是 runtimeMockSamples.defaultMockPlan.runnable[0].task_id
    expect(wrapper.text()).toContain('t1')
  })

  it('提供 live 操作入口', async () => {
    const wrapper = await mountRuntimeConsole()

    const buttons = wrapper.findAll('button')
    expect(buttons.some((button) => button.text().includes('读取 Live Plan'))).toBe(true)
    expect(buttons.some((button) => button.text().includes('执行 Live Dispatch'))).toBe(true)
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('提供自动刷新控制', async () => {
    const wrapper = await mountRuntimeConsole()

    expect(wrapper.text()).toContain('自动刷新')
    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
  })

  it('显示 live 状态与原始 JSON 折叠区', async () => {
    const wrapper = await mountRuntimeConsole()

    expect(wrapper.text()).toContain('最近刷新')
    expect(wrapper.findAll('details').length).toBeGreaterThanOrEqual(2)
    expect(wrapper.text()).toContain('sample')
  })

  it('显示运行时总览和 session 列表', async () => {
    const wrapper = await mountRuntimeConsole()

    expect(wrapper.text()).toContain('运行时总览')
    expect(wrapper.text()).toContain('Repo:')
    // s1 是 runtimeMockSamples.defaultMockSessions.sessions[0].session_id
    expect(wrapper.text()).toContain('s1')
    expect(wrapper.text()).toContain('读取 Live 总览')
  })

  it('提供 session 级动作入口', async () => {
    const wrapper = await mountRuntimeConsole()

    expect(wrapper.text()).toContain('解释任务')
    expect(wrapper.text()).toContain('查看事件')
    expect(wrapper.text()).toContain('发送干预')
    expect(wrapper.text()).toContain('标记完成')
    expect(wrapper.text()).toContain('标记失败')
  })

  it('显示 session inspector 面板', async () => {
    const wrapper = await mountRuntimeConsole()

    expect(wrapper.text()).toContain('Session 事件查看')
    expect(wrapper.text()).toContain('最近读取')
  })

  it('在 inspector 中显示动作面板', async () => {
    const wrapper = await mountRuntimeConsole()

    expect(wrapper.text()).toContain('Session 干预')
    expect(wrapper.text()).toContain('标记完成')
    expect(wrapper.text()).toContain('标记失败')
  })

  it('点击 live plan 按钮调用 API', async () => {
    const wrapper = await mountRuntimeConsole()

    const planButton = wrapper.findAll('button').find((b) => b.text().includes('读取 Live Plan'))
    if (planButton) {
      await planButton.trigger('click')
      await flushPromises()

      expect(runtimeApi.plan).toHaveBeenCalled()
    }
  })

  it('点击 live dispatch 按钮调用 API', async () => {
    const wrapper = await mountRuntimeConsole()

    const dispatchButton = wrapper.findAll('button').find((b) => b.text().includes('执行 Live Dispatch'))
    if (dispatchButton) {
      await dispatchButton.trigger('click')
      await flushPromises()

      expect(runtimeApi.dispatch).toHaveBeenCalled()
    }
  })
})
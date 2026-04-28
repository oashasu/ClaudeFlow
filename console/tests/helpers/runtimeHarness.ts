/**
 * Runtime Test Harness
 *
 * A42: 提供统一的 Vue setup/mount/mock/flush 入口
 * 用于 composable/runtime API 相关测试
 */

import { mount, VueWrapper } from '@vue/test-utils'
import { defineComponent, nextTick, ref, provide, inject, type Component } from 'vue'
import { vi, type Mock } from 'vitest'
import type { RuntimeLiveDataState, RuntimeSession } from '../../src/types/runtime'

// ── Mock Types ───────────────────────────────────────────────────────────────

export interface RuntimeApiMocks {
  status: Mock
  sessions: Mock
  sessionEvents: Mock
  plan: Mock
  explain: Mock
  dispatch: Mock
  interveneSession: Mock
  completeTask: Mock
  failTask: Mock
  listActionAudit: Mock
  getActionAudit: Mock
}

export interface RuntimeMockState {
  plan: Mock
  explain: Mock
  dispatch: Mock
  status: Mock
  sessions: Mock
  sessionEvents: Mock
}

// ── Default Mock Data ─────────────────────────────────────────────────────────

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

export const defaultMockAudit = {
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

// ── Mock Factory ──────────────────────────────────────────────────────────────

export function createRuntimeApiMocks(overrides?: Partial<RuntimeMockState>): RuntimeApiMocks {
  const defaultSessionActionResponse = {
    success: true,
    message: 'Action completed',
    session_id: 's1',
  }

  return {
    status: vi.fn().mockResolvedValue(overrides?.status ?? defaultMockStatus),
    sessions: vi.fn().mockResolvedValue(overrides?.sessions ?? defaultMockSessions),
    sessionEvents: vi.fn().mockResolvedValue(overrides?.sessionEvents ?? defaultMockEvents),
    plan: vi.fn().mockResolvedValue(overrides?.plan ?? defaultMockPlan),
    explain: vi.fn().mockResolvedValue(overrides?.explain ?? defaultMockExplain),
    dispatch: vi.fn().mockResolvedValue(overrides?.dispatch ?? defaultMockDispatch),
    interveneSession: vi.fn().mockResolvedValue(defaultSessionActionResponse),
    completeTask: vi.fn().mockResolvedValue(defaultSessionActionResponse),
    failTask: vi.fn().mockResolvedValue(defaultSessionActionResponse),
    listActionAudit: vi.fn().mockResolvedValue(defaultMockAudit),
    getActionAudit: vi.fn().mockResolvedValue(defaultMockAudit.records[0]),
  }
}

// ── Sample Data Exports (for vi.mock factory) ──────────────────────────────────

/**
 * 导出 sample 数据供测试文件顶层 vi.mock 使用
 * 注意：vi.mock 必须在文件顶层调用（hoisted），不能在函数内调用
 */
export const runtimeMockSamples = {
  plan: defaultMockPlan,
  explain: defaultMockExplain,
  dispatch: defaultMockDispatch,
  status: defaultMockStatus,
  sessions: defaultMockSessions.sessions,
  sessionEvents: defaultMockEvents,
  auditRecords: defaultMockAudit,
  auditRecord: defaultMockAudit.records[0],
}

// ── Mock Factory for Top-Level vi.mock ───────────────────────────────────────

/**
 * 创建 mock 函数集合，供 vi.mock factory 使用
 *
 * 使用模式：
 * ```ts
 * // 在测试文件顶层（hoisted）
 * vi.mock('../src/services/runtimeApi', () => {
 *   const { createRuntimeApiMocks, runtimeMockSamples } = await import('./helpers/runtimeHarness')
 *   const mocks = createRuntimeApiMocks()
 *   return {
 *     runtimeApi: { ...mocks },
 *     runtimePlanSample: runtimeMockSamples.plan,
 *     // ...
 *   }
 * })
 * ```
 */

// ── Composable Test Harness ───────────────────────────────────────────────────

/**
 * 创建一个包装组件来在正确 Vue 生命周期内运行 composable
 * 解决 "onMounted is called when there is no active component instance" warning
 */
export function createComposableHarness<T>(composable: () => T) {
  const resultRef = ref<T | null>(null)
  const errorRef = ref<Error | null>(null)

  const HarnessComponent = defineComponent({
    setup() {
      try {
        resultRef.value = composable()
      } catch (e) {
        errorRef.value = e as Error
      }
      return {}
    },
    template: '<div></div>',
  })

  return {
    component: HarnessComponent,
    result: resultRef,
    error: errorRef,
  }
}

/**
 * 在 Vue setup 上下文中执行 composable
 * 返回 composable 结果和 wrapper
 */
export async function withComposable<T>(
  composable: () => T,
  options?: { provide?: Record<string, unknown> }
): Promise<{ result: T; wrapper: VueWrapper }> {
  // 使用 reactive 来存储结果，避免 ref 在组件外的响应式问题
  const resultHolder: { value: T | null } = { value: null }

  const TestComponent = defineComponent({
    setup() {
      if (options?.provide) {
        Object.entries(options.provide).forEach(([key, value]) => {
          provide(key, value)
        })
      }
      resultHolder.value = composable()
      return {}
    },
    render: () => null,
  })

  const wrapper = mount(TestComponent)
  await nextTick()
  await flushPromises()

  if (resultHolder.value === null) {
    throw new Error('Composable did not return a value')
  }

  return {
    result: resultHolder.value,
    wrapper,
  }
}

// ── Async Helpers ─────────────────────────────────────────────────────────────

/**
 * 等待所有 pending promise 和 Vue 更新完成
 */
export async function flushPromises(): Promise<void> {
  await new Promise((resolve) => setTimeout(resolve, 0))
  await nextTick()
}

/**
 * 等待指定次数的 flush
 */
export async function flushTimes(times: number): Promise<void> {
  for (let i = 0; i < times; i++) {
    await flushPromises()
  }
}

/**
 * 等待状态变化
 */
export async function waitForState<T>(
  getter: () => T,
  predicate: (value: T) => boolean,
  timeout = 1000,
  interval = 50
): Promise<T> {
  const start = Date.now()
  while (Date.now() - start < timeout) {
    const value = getter()
    if (predicate(value)) {
      return value
    }
    await new Promise((resolve) => setTimeout(resolve, interval))
  }
  throw new Error(`waitForState timeout after ${timeout}ms`)
}

// ── Error Assertion Helpers ───────────────────────────────────────────────────

/**
 * 断言错误状态
 */
export function assertErrorState(
  state: RuntimeLiveDataState,
  errorField: 'parseError' | 'liveError' | 'sessionEventsError',
  expectedMessage?: string
) {
  const error = state[errorField]
  if (!error) {
    throw new Error(`Expected ${errorField} to be set, but got null`)
  }
  if (expectedMessage && !error.includes(expectedMessage)) {
    throw new Error(`Expected error to contain "${expectedMessage}", but got "${error}"`)
  }
}

/**
 * 断言成功状态（无错误）
 */
export function assertSuccessState(state: RuntimeLiveDataState) {
  if (state.parseError) {
    throw new Error(`Expected no parseError, but got "${state.parseError}"`)
  }
  if (state.liveError) {
    throw new Error(`Expected no liveError, but got "${state.liveError}"`)
  }
  if (state.sessionEventsError) {
    throw new Error(`Expected no sessionEventsError, but got "${state.sessionEventsError}"`)
  }
}

// ── Console Warning Capture ──────────────────────────────────────────────────

/**
 * 捕获 console warning 用于测试验证
 */
export function captureWarnings() {
  const warnings: string[] = []
  const originalWarn = console.warn

  console.warn = (...args) => {
    warnings.push(args.map((a) => String(a)).join(' '))
  }

  return {
    warnings,
    restore: () => {
      console.warn = originalWarn
    },
    hasWarning: (pattern: string) => warnings.some((w) => w.includes(pattern)),
  }
}

/**
 * 断言没有 Vue lifecycle warning
 */
export function assertNoLifecycleWarning(warnings: string[]) {
  const lifecycleWarning = warnings.find((w) =>
    w.includes('onMounted is called when there is no active component instance')
  )
  if (lifecycleWarning) {
    throw new Error(`Unexpected lifecycle warning: ${lifecycleWarning}`)
  }
}

// ── Component Mount Helper (after vi.mock setup) ──────────────────────────────

/**
 * Mount RuntimeConsole 组件
 *
 * 注意：此函数必须在测试文件顶层 vi.mock 之后调用
 * 因为 RuntimeConsole 使用模块导入 runtimeApi，不依赖实例属性注入
 *
 * 使用模式：
 * ```ts
 * // 顶层 vi.mock（hoisted）
 * vi.mock('../src/services/runtimeApi', () => ...)
 * vi.mock('../src/services/api', () => ...)
 *
 * // 测试中使用 mountRuntimeConsole
 * const wrapper = await mountRuntimeConsole()
 * ```
 */
export async function mountRuntimeConsole(): Promise<VueWrapper> {
  const wrapper = mount(
    defineComponent({
      template: '<RuntimeConsole />',
      components: {
        RuntimeConsole: await import('../../src/views/RuntimeConsole.vue').then((m) => m.default),
      },
    })
  )
  await nextTick()
  await flushPromises()
  return wrapper
}

/**
 * 获取 mock 函数引用（用于断言）
 * 必须在 vi.mock 调用后使用
 *
 * 使用模式：
 * ```ts
 * // 测试中获取 mock 函数
 * const mocks = getRuntimeApiMocks()
 * expect(mocks.plan).toHaveBeenCalled()
 * ```
 */
export function getRuntimeApiMocks(): RuntimeApiMocks {
  // 通过 require 实际模块来获取 mock 函数
  // 注意：路径从 helpers/runtimeHarness.ts 计算，需要 ../../src
  // eslint-disable-next-line @typescript-eslint/no-var-requires
  const mod = require('../../src/services/runtimeApi')
  return {
    status: mod.runtimeApi.status,
    sessions: mod.runtimeApi.sessions,
    sessionEvents: mod.runtimeApi.sessionEvents,
    plan: mod.runtimeApi.plan,
    explain: mod.runtimeApi.explain,
    dispatch: mod.runtimeApi.dispatch,
    interveneSession: mod.runtimeApi.interveneSession,
    completeTask: mod.runtimeApi.completeTask,
    failTask: mod.runtimeApi.failTask,
    listActionAudit: mod.runtimeApi.listActionAudit,
    getActionAudit: mod.runtimeApi.getActionAudit,
  }
}
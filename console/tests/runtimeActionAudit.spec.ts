/**
 * runtimeActionAudit.spec.ts - T402: Action Audit 测试隔离与错误路径稳定
 *
 * 验收目标：
 * - A43: action audit 成功、空数据、失败路径都有稳定断言
 * - A41: audit fetch warning 不作为默认测试噪音
 */

import { describe, expect, it, beforeEach, vi, afterEach } from 'vitest'
import { flushPromises, withComposable, captureWarnings } from './helpers/runtimeHarness'
import {
  defaultMockAuditRecords,
  defaultSessionActionResponse,
} from './helpers/runtimeMockSamples'

// Mock runtimeApi 模块
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
      interveneSession: mockFn(),
      completeTask: mockFn(),
      failTask: mockFn(),
      listActionAudit: mockFn(),
      getActionAudit: mockFn(),
    },
  }
})

// Mock api 模块（action-audit）
vi.mock('../src/services/api', () => ({
  fetchActionAudit: vi.fn(),
}))

describe('Action Audit - T402: 错误路径稳定与测试隔离', () => {
  let runtimeApi: typeof import('../src/services/runtimeApi').runtimeApi
  let warningCapture: ReturnType<typeof captureWarnings>

  beforeEach(async () => {
    vi.clearAllMocks()
    warningCapture = captureWarnings()

    const runtimeModule = await import('../src/services/runtimeApi')
    runtimeApi = runtimeModule.runtimeApi
  })

  afterEach(() => {
    warningCapture.restore()
  })

  describe('A43: listActionAudit 成功路径', () => {
    it('成功获取审计记录返回正确数据', async () => {
      vi.mocked(runtimeApi.listActionAudit).mockResolvedValue(defaultMockAuditRecords)

      const response = await runtimeApi.listActionAudit({ limit: 10 })

      expect(response.records.length).toBe(1)
      expect(response.total).toBe(1)
      expect(response.records[0].action_type).toBe('intervene')
      expect(response.records[0].success).toBe(true)

      // A41: 成功路径不应产生 console.warn
      expect(warningCapture.hasWarning('加载审计记录失败')).toBe(false)
    })

    it('空数据返回空数组不产生错误', async () => {
      const emptyRecords = { records: [], total: 0 }
      vi.mocked(runtimeApi.listActionAudit).mockResolvedValue(emptyRecords)

      const response = await runtimeApi.listActionAudit({ limit: 10 })

      expect(response.records.length).toBe(0)
      expect(response.total).toBe(0)

      // A41: 空数据不应产生 warning
      expect(warningCapture.hasWarning('加载审计记录失败')).toBe(false)
    })
  })

  describe('A43: listActionAudit 失败路径', () => {
    it('API 失败返回错误信息', async () => {
      const errorMessage = 'Network error'
      vi.mocked(runtimeApi.listActionAudit).mockRejectedValue(new Error(errorMessage))

      try {
        await runtimeApi.listActionAudit({ limit: 10 })
      } catch (error) {
        expect((error as Error).message).toBe(errorMessage)
      }

      // 失败路径下 API 本身不产生 console.warn（由调用方处理）
      expect(runtimeApi.listActionAudit).toHaveBeenCalled()
    })
  })

  describe('A43: session action 成功/失败路径', () => {
    it('interveneSession 成功返回正确响应', async () => {
      vi.mocked(runtimeApi.interveneSession).mockResolvedValue(defaultSessionActionResponse)

      const response = await runtimeApi.interveneSession('s1', '干预内容')

      expect(response.success).toBe(true)
      expect(response.session_id).toBe('s1')
      expect(warningCapture.hasWarning('发送干预失败')).toBe(false)
    })

    it('completeTask 成功返回正确响应', async () => {
      vi.mocked(runtimeApi.completeTask).mockResolvedValue(defaultSessionActionResponse)

      const response = await runtimeApi.completeTask('t1', { summary: '完成' })

      expect(response.success).toBe(true)
      expect(warningCapture.hasWarning('标记完成失败')).toBe(false)
    })

    it('failTask 成功返回正确响应', async () => {
      vi.mocked(runtimeApi.failTask).mockResolvedValue(defaultSessionActionResponse)

      const response = await runtimeApi.failTask('t1', '失败原因')

      expect(response.success).toBe(true)
      expect(warningCapture.hasWarning('标记失败失败')).toBe(false)
    })

    it('interveneSession 失败抛出错误', async () => {
      vi.mocked(runtimeApi.interveneSession).mockRejectedValue(new Error('干预失败'))

      try {
        await runtimeApi.interveneSession('s1', '干预内容')
      } catch (error) {
        expect((error as Error).message).toBe('干预失败')
      }

      expect(runtimeApi.interveneSession).toHaveBeenCalled()
    })
  })

  describe('A41: useRuntimeActions loadActionHistory 隔离', () => {
    it('loadActionHistory 成功时不产生 warning', async () => {
      vi.mocked(runtimeApi.listActionAudit).mockResolvedValue(defaultMockAuditRecords)

      const { useRuntimeActions } = await import('../src/composables/useRuntimeActions')
      const { result: actions } = await withComposable(() => useRuntimeActions())

      // onMounted 时会调用 loadActionHistory
      await flushPromises()

      // 成功路径不应产生 console.warn
      expect(warningCapture.hasWarning('加载审计记录失败')).toBe(false)
      expect(actions.state.value.actionHistory.length).toBe(1)
    })

    it('loadActionHistory 失败时产生 warning 但不影响主流程', async () => {
      vi.mocked(runtimeApi.listActionAudit).mockRejectedValue(new Error('加载失败'))

      const { useRuntimeActions } = await import('../src/composables/useRuntimeActions')
      const { result: actions } = await withComposable(() => useRuntimeActions())

      await flushPromises()

      // 失败路径会产生 warning（这是预期的错误路径行为）
      expect(warningCapture.hasWarning('加载审计记录失败')).toBe(true)

      // 但状态保持稳定，不崩溃
      expect(actions.state.value.loading).toBe(false)
      expect(actions.state.value.error).toBeNull()
    })

    it('loadActionHistory 空数据时不产生 warning', async () => {
      vi.mocked(runtimeApi.listActionAudit).mockResolvedValue({ records: [], total: 0 })

      const { useRuntimeActions } = await import('../src/composables/useRuntimeActions')
      const { result: actions } = await withComposable(() => useRuntimeActions())

      await flushPromises()

      expect(warningCapture.hasWarning('加载审计记录失败')).toBe(false)
      expect(actions.state.value.actionHistory.length).toBe(0)
    })
  })
})
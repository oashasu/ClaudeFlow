import { ref, computed, onMounted } from 'vue'
import { runtimeApi } from '../services/runtimeApi'
import type { RuntimeSession, RuntimeActionResult, ActionAuditRecord } from '../types/runtime'

export interface RuntimeActionsState {
  loading: boolean
  error: string | null
  success: string | null
  lastActionResult: RuntimeActionResult | null
  actionHistory: RuntimeActionResult[]
}

export interface ActionConfirmState {
  showInterveneConfirm: boolean
  showCompleteConfirm: boolean
  showFailConfirm: boolean
  pendingSession: RuntimeSession | null
  intervenePrompt: string
  completeSummary: string
  failReason: string
}

const MAX_HISTORY_SIZE = 10

export function useRuntimeActions(onActionSuccess?: () => void) {
  const state = ref<RuntimeActionsState>({
    loading: false,
    error: null,
    success: null,
    lastActionResult: null,
    actionHistory: [],
  })

  const confirmState = ref<ActionConfirmState>({
    showInterveneConfirm: false,
    showCompleteConfirm: false,
    showFailConfirm: false,
    pendingSession: null,
    intervenePrompt: '请先总结当前阻塞点，再继续下一步实现。',
    completeSummary: '已完成当前 task 的实现与必要验证。',
    failReason: '当前 task 遇到阻塞，需人工介入或上游协议回流。',
  })

  const hasPendingConfirm = computed(() => {
    return confirmState.value.showInterveneConfirm || confirmState.value.showCompleteConfirm || confirmState.value.showFailConfirm
  })

  function clearMessages() {
    state.value.error = null
    state.value.success = null
  }

  // T302: 从后端加载审计记录
  async function loadActionHistory() {
    try {
      const response = await runtimeApi.listActionAudit({ limit: MAX_HISTORY_SIZE })
      state.value.actionHistory = response.records.map(convertAuditToResult)
      if (response.records.length > 0) {
        state.value.lastActionResult = convertAuditToResult(response.records[0])
      }
    } catch (error) {
      // 加载失败不影响主流程，使用内存态兜底
      console.warn('加载审计记录失败:', (error as Error).message)
    }
  }

  // T302: 将后端审计记录转换为前端格式
  function convertAuditToResult(record: ActionAuditRecord): RuntimeActionResult {
    return {
      success: record.success,
      message: record.message,
      timestamp: record.timestamp,
      actionType: record.action_type,
      targetTaskId: record.target_task_id,
      targetSessionId: record.target_session_id,
    }
  }

  // T302: 动作完成后刷新后端审计记录
  async function recordAction() {
    await loadActionHistory()
  }

  // T302: 初始化时加载审计记录
  onMounted(() => {
    loadActionHistory()
  })

  function requestInterveneConfirm(session: RuntimeSession) {
    clearMessages()
    confirmState.value.pendingSession = session
    confirmState.value.showInterveneConfirm = true
    confirmState.value.showCompleteConfirm = false
    confirmState.value.showFailConfirm = false
  }

  function requestCompleteConfirm(session: RuntimeSession) {
    clearMessages()
    confirmState.value.pendingSession = session
    confirmState.value.showCompleteConfirm = true
    confirmState.value.showInterveneConfirm = false
    confirmState.value.showFailConfirm = false
  }

  function requestFailConfirm(session: RuntimeSession) {
    clearMessages()
    confirmState.value.pendingSession = session
    confirmState.value.showFailConfirm = true
    confirmState.value.showInterveneConfirm = false
    confirmState.value.showCompleteConfirm = false
  }

  function cancelConfirm() {
    confirmState.value.showInterveneConfirm = false
    confirmState.value.showCompleteConfirm = false
    confirmState.value.showFailConfirm = false
    confirmState.value.pendingSession = null
  }

  async function executeIntervene() {
    const session = confirmState.value.pendingSession
    if (!session) return
    if (!confirmState.value.intervenePrompt.trim()) {
      state.value.error = '干预内容不能为空。'
      return
    }
    try {
      state.value.loading = true
      clearMessages()
      await runtimeApi.interveneSession(session.session_id, confirmState.value.intervenePrompt.trim())
      state.value.success = `已向 ${session.task_id} 发送干预指令。`
      cancelConfirm()
      await recordAction() // T302: 从后端刷新审计记录
      onActionSuccess?.()
    } catch (error) {
      state.value.error = `发送干预失败: ${(error as Error).message}`
      await recordAction() // T302: 从后端刷新审计记录（包含失败记录）
    } finally {
      state.value.loading = false
    }
  }

  async function executeComplete() {
    const session = confirmState.value.pendingSession
    if (!session) return
    try {
      state.value.loading = true
      clearMessages()
      await runtimeApi.completeTask(session.task_id, {
        summary: confirmState.value.completeSummary.trim(),
      })
      state.value.success = `已将 ${session.task_id} 标记为 completed。`
      cancelConfirm()
      await recordAction() // T302: 从后端刷新审计记录
      onActionSuccess?.()
    } catch (error) {
      state.value.error = `标记完成失败: ${(error as Error).message}`
      await recordAction() // T302: 从后端刷新审计记录
    } finally {
      state.value.loading = false
    }
  }

  async function executeFail() {
    const session = confirmState.value.pendingSession
    if (!session) return
    if (!confirmState.value.failReason.trim()) {
      state.value.error = '失败原因不能为空。'
      return
    }
    try {
      state.value.loading = true
      clearMessages()
      await runtimeApi.failTask(session.task_id, confirmState.value.failReason.trim())
      state.value.success = `已将 ${session.task_id} 标记为 failed。`
      cancelConfirm()
      await recordAction() // T302: 从后端刷新审计记录
      onActionSuccess?.()
    } catch (error) {
      state.value.error = `标记失败失败: ${(error as Error).message}`
      await recordAction() // T302: 从后端刷新审计记录
    } finally {
      state.value.loading = false
    }
  }

  function setIntervenePrompt(value: string) {
    confirmState.value.intervenePrompt = value
  }

  function setCompleteSummary(value: string) {
    confirmState.value.completeSummary = value
  }

  function setFailReason(value: string) {
    confirmState.value.failReason = value
  }

  return {
    state,
    confirmState,
    hasPendingConfirm,
    requestInterveneConfirm,
    requestCompleteConfirm,
    requestFailConfirm,
    cancelConfirm,
    executeIntervene,
    executeComplete,
    executeFail,
    setIntervenePrompt,
    setCompleteSummary,
    setFailReason,
    clearMessages,
    loadActionHistory, // T302: 暴露刷新接口
  }
}
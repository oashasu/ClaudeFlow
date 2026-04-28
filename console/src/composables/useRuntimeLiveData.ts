import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { runtimeApi, runtimePlanSample, runtimeExplainSample, runtimeDispatchSample, runtimeStatusSample, runtimeSessionsSample, runtimeSessionEventsSample } from '../services/runtimeApi'
import { runtimeValidator } from '../validators/runtime'
import type {
  RuntimePlan,
  RuntimeExplain,
  RuntimeDispatch,
  RuntimeStatus,
  RuntimeSession,
  RuntimeSessionEvents,
  RuntimeParsedEvent,
  DataSource,
} from '../types/runtime'

export interface RuntimeLiveDataState {
  plan: RuntimePlan | null
  explain: RuntimeExplain | null
  dispatch: RuntimeDispatch | null
  status: RuntimeStatus | null
  sessions: RuntimeSession[]
  selectedSession: RuntimeSession | null
  sessionEvents: RuntimeParsedEvent[]
  planSource: DataSource
  explainSource: DataSource
  dispatchSource: DataSource
  sessionEventsSource: DataSource
  parseError: string | null
  liveError: string | null
  lastRefreshedAt: string | null
  sessionEventsLoadedAt: string | null
  sessionEventsLoading: boolean
  sessionEventsError: string | null
}

export function useRuntimeLiveData() {
  const planInput = ref(JSON.stringify(runtimePlanSample, null, 2))
  const explainInput = ref(JSON.stringify(runtimeExplainSample, null, 2))
  const explainTaskId = ref(runtimeExplainSample.task_id)
  const dispatchInput = ref(JSON.stringify(runtimeDispatchSample, null, 2))
  const autoRefreshEnabled = ref(false)
  const autoRefreshSeconds = ref(5)
  let refreshTimer: number | null = null

  const state = ref<RuntimeLiveDataState>({
    plan: null,
    explain: null,
    dispatch: null,
    status: runtimeStatusSample,
    sessions: runtimeSessionsSample,
    selectedSession: runtimeSessionsSample[0] ?? null,
    sessionEvents: runtimeSessionEventsSample.parsed_events,
    planSource: 'sample',
    explainSource: 'sample',
    dispatchSource: 'sample',
    sessionEventsSource: 'sample',
    parseError: null,
    liveError: null,
    lastRefreshedAt: null,
    sessionEventsLoadedAt: null,
    sessionEventsLoading: false,
    sessionEventsError: null,
  })

  const plan = computed(() => {
    if (!planInput.value) return null
    const result = runtimeValidator.parsePlan(planInput.value)
    if (result.error) {
      state.value.parseError = result.error
      return null
    }
    state.value.parseError = null
    return result.data
  })

  const explain = computed(() => {
    if (!explainInput.value) return null
    const result = runtimeValidator.parseExplain(explainInput.value)
    if (result.error) {
      state.value.parseError = result.error
      return null
    }
    state.value.parseError = null
    return result.data
  })

  const dispatch = computed(() => {
    if (!dispatchInput.value) return null
    const result = runtimeValidator.parseDispatch(dispatchInput.value)
    if (result.error) {
      state.value.parseError = result.error
      return null
    }
    state.value.parseError = null
    return result.data
  })

  function clearErrors() {
    state.value.parseError = null
    state.value.liveError = null
    state.value.sessionEventsError = null
  }

  async function loadLivePlan() {
    try {
      clearErrors()
      const payload = await runtimeApi.plan()
      planInput.value = JSON.stringify(payload, null, 2)
      state.value.planSource = 'live'
      state.value.lastRefreshedAt = new Date().toLocaleTimeString()
    } catch (error) {
      state.value.liveError = `加载 Runtime Plan 失败: ${(error as Error).message}`
    }
  }

  async function loadLiveStatus() {
    try {
      clearErrors()
      // A34: live payload 必须经过 parse/validate
      const statusPayload = await runtimeApi.status()
      const statusResult = runtimeValidator.parseStatus(JSON.stringify(statusPayload))
      if (statusResult.error) {
        state.value.parseError = `Runtime Status 协议校验失败: ${statusResult.error}`
        state.value.status = null
        state.value.sessions = []
        return
      }
      state.value.status = statusResult.data

      const sessionsPayload = await runtimeApi.sessions()
      const sessionsResult = runtimeValidator.parseSessions(JSON.stringify(sessionsPayload.sessions))
      if (sessionsResult.error) {
        state.value.parseError = `Runtime Sessions 协议校验失败: ${sessionsResult.error}`
        state.value.status = null
        state.value.sessions = []
        return
      }
      state.value.sessions = sessionsResult.data ?? []

      if (state.value.selectedSession) {
        state.value.selectedSession =
          state.value.sessions.find((s) => s.session_id === state.value.selectedSession?.session_id) ?? state.value.sessions[0]
      }
      state.value.lastRefreshedAt = new Date().toLocaleTimeString()
    } catch (error) {
      state.value.liveError = `加载 Runtime 总览失败: ${(error as Error).message}`
    }
  }

  async function loadLiveExplain(taskId?: string) {
    const targetId = taskId || explainTaskId.value
    if (!targetId) return
    try {
      clearErrors()
      const payload = await runtimeApi.explain(targetId)
      explainInput.value = JSON.stringify(payload, null, 2)
      explainTaskId.value = targetId
      state.value.explainSource = 'live'
      state.value.lastRefreshedAt = new Date().toLocaleTimeString()
    } catch (error) {
      state.value.liveError = `加载 Runtime Explain 失败: ${(error as Error).message}`
    }
  }

  async function loadLiveSessionEvents(session: RuntimeSession) {
    try {
      state.value.sessionEventsLoading = true
      state.value.sessionEventsError = null
      state.value.selectedSession = session
      // A34: live payload 必须经过 parse/validate
      const payload = await runtimeApi.sessionEvents(session.session_id)
      const eventsResult = runtimeValidator.parseSessionEvents(JSON.stringify(payload))
      if (eventsResult.error) {
        state.value.sessionEventsError = `Session Events 协议校验失败: ${eventsResult.error}`
        state.value.sessionEvents = []
        return
      }
      state.value.sessionEvents = eventsResult.data?.parsed_events ?? []
      state.value.sessionEventsSource = 'live'
      state.value.sessionEventsLoadedAt = new Date().toLocaleTimeString()
    } catch (error) {
      state.value.sessionEventsError = `加载 Session 事件失败: ${(error as Error).message}`
    } finally {
      state.value.sessionEventsLoading = false
    }
  }

  async function runLiveDispatch(maxConcurrent: number = 2) {
    try {
      clearErrors()
      const payload = await runtimeApi.dispatch({ max_concurrent: maxConcurrent })
      dispatchInput.value = JSON.stringify(payload, null, 2)
      state.value.dispatchSource = 'live'
      state.value.lastRefreshedAt = new Date().toLocaleTimeString()
    } catch (error) {
      state.value.liveError = `加载 Runtime Dispatch 失败: ${(error as Error).message}`
    }
  }

  async function refreshAll() {
    clearErrors()
    await loadLiveStatus()
    await loadLivePlan()
    if (explainTaskId.value.trim()) {
      await loadLiveExplain()
    }
    if (state.value.selectedSession?.session_id && state.value.selectedSession.status === 'running') {
      await loadLiveSessionEvents(state.value.selectedSession)
    }
  }

  function clearRefreshTimer() {
    if (refreshTimer !== null) {
      window.clearInterval(refreshTimer)
      refreshTimer = null
    }
  }

  function startRefreshTimer() {
    clearRefreshTimer()
    if (!autoRefreshEnabled.value) return
    refreshTimer = window.setInterval(async () => {
      await refreshAll()
    }, autoRefreshSeconds.value * 1000)
  }

  function setPlanInput(value: string) {
    planInput.value = value
  }

  function setExplainInput(value: string) {
    explainInput.value = value
  }

  function setDispatchInput(value: string) {
    dispatchInput.value = value
  }

  function setExplainTaskId(value: string) {
    explainTaskId.value = value
  }

  function selectSession(session: RuntimeSession | null) {
    state.value.selectedSession = session
  }

  function loadSampleData() {
    planInput.value = JSON.stringify(runtimePlanSample, null, 2)
    explainInput.value = JSON.stringify(runtimeExplainSample, null, 2)
    dispatchInput.value = JSON.stringify(runtimeDispatchSample, null, 2)
    explainTaskId.value = runtimeExplainSample.task_id
    state.value.status = runtimeStatusSample
    state.value.sessions = runtimeSessionsSample
    state.value.selectedSession = runtimeSessionsSample[0] ?? null
    state.value.sessionEvents = runtimeSessionEventsSample.parsed_events
    state.value.planSource = 'sample'
    state.value.explainSource = 'sample'
    state.value.dispatchSource = 'sample'
    state.value.sessionEventsSource = 'sample'
    state.value.sessionEventsLoadedAt = null
    state.value.lastRefreshedAt = null
    clearErrors()
  }

  watch([autoRefreshEnabled, autoRefreshSeconds], () => {
    startRefreshTimer()
  })

  onMounted(() => {
    startRefreshTimer()
  })

  onUnmounted(() => {
    clearRefreshTimer()
  })

  return {
    state,
    plan,
    explain,
    dispatch,
    planInput,
    explainInput,
    explainTaskId,
    dispatchInput,
    autoRefreshEnabled,
    autoRefreshSeconds,
    loadSampleData,
    loadLivePlan,
    loadLiveStatus,
    loadLiveExplain,
    loadLiveSessionEvents,
    runLiveDispatch,
    refreshAll,
    setPlanInput,
    setExplainInput,
    setDispatchInput,
    setExplainTaskId,
    selectSession,
    clearErrors,
  }
}
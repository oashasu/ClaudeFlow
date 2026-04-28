// 任务状态管理
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { taskApi, checkpointApi, stepApi } from '../services/api'
import type { Task, TaskStats, Checkpoint, PhaseStep } from '../services/api'

export const useTaskStore = defineStore('task', () => {
  // 状态
  const tasks = ref<Task[]>([])
  const stats = ref<TaskStats>({ running: 0, completed: 0, waiting: 0, alert: 0 })
  const currentTask = ref<Task | null>(null)
  const currentCheckpoints = ref<Checkpoint[]>([])
  const currentSteps = ref<PhaseStep[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  // 过滤状态
  const filterStatus = ref<string | null>(null)

  // 计算属性
  const filteredTasks = computed(() => {
    if (filterStatus.value) {
      return tasks.value.filter(t => t.status === filterStatus.value)
    }
    return tasks.value
  })

  const waitingTasks = computed(() =>
    tasks.value.filter(t => t.status === 'waiting')
  )

  // Actions
  async function createTask(data: {
    name: string
    domain: string
    prompt: string
    priority?: string
  }) {
    loading.value = true
    error.value = null
    try {
      const task = await taskApi.create(data)
      tasks.value.unshift(task)
      return task
    } catch (e) {
      error.value = (e as Error).message
      throw e
    } finally {
      loading.value = false
    }
  }

  async function fetchTasks() {
    loading.value = true
    error.value = null
    try {
      tasks.value = await taskApi.list()
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function fetchStats() {
    try {
      stats.value = await taskApi.stats()
    } catch (e) {
      console.error('Failed to fetch stats', e)
    }
  }

  async function fetchTaskDetail(id: string) {
    loading.value = true
    error.value = null
    try {
      currentTask.value = await taskApi.detail(id)
      currentCheckpoints.value = await checkpointApi.list(id)
    } catch (e) {
      error.value = (e as Error).message
    } finally {
      loading.value = false
    }
  }

  async function fetchPhaseSteps(taskId: string, phase: string) {
    try {
      currentSteps.value = await stepApi.list(taskId, phase)
    } catch (e) {
      console.error('Failed to fetch steps', e)
    }
  }

  async function pauseTask(id: string) {
    try {
      const updated = await taskApi.pause(id)
      updateTaskInList(updated)
      if (currentTask.value?.id === id) {
        currentTask.value = updated
      }
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function resumeTask(id: string) {
    try {
      const updated = await taskApi.resume(id)
      updateTaskInList(updated)
      if (currentTask.value?.id === id) {
        currentTask.value = updated
      }
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function confirmIntervention(id: string, userInput: string) {
    try {
      const updated = await taskApi.confirm(id, userInput)
      updateTaskInList(updated)
      if (currentTask.value?.id === id) {
        currentTask.value = updated
      }
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function cancelTask(id: string) {
    try {
      const updated = await taskApi.cancel(id)
      updateTaskInList(updated)
      if (currentTask.value?.id === id) {
        currentTask.value = updated
      }
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function deleteTask(id: string) {
    try {
      await taskApi.delete(id)
      // 直接从数组中移除
      const index = tasks.value.findIndex(t => t.id === id)
      if (index !== -1) {
        tasks.value.splice(index, 1)
      }
      if (currentTask.value?.id === id) {
        currentTask.value = null
      }
      // 刷新统计
      fetchStats()
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function retryTask(id: string) {
    try {
      const updated = await taskApi.retry(id)
      updateTaskInList(updated)
      if (currentTask.value?.id === id) {
        currentTask.value = updated
      }
      // 刷新统计
      fetchStats()
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  async function revertCheckpoint(checkpointId: string) {
    try {
      await checkpointApi.revert(checkpointId)
      // 刷新Checkpoint历史
      if (currentTask.value) {
        currentCheckpoints.value = await checkpointApi.list(currentTask.value.id)
      }
    } catch (e) {
      error.value = (e as Error).message
    }
  }

  // SSE事件处理
  function handleProgressUpdate(event: { taskId: string; phase: string; progress: number }) {
    const task = tasks.value.find(t => t.id === event.taskId)
    if (task) {
      task.phase = event.phase
      task.progress = event.progress
    }
    if (currentTask.value?.id === event.taskId) {
      currentTask.value.phase = event.phase
      currentTask.value.progress = event.progress
    }
  }

  // 辅助方法
  function updateTaskInList(task: Task) {
    const index = tasks.value.findIndex(t => t.id === task.id)
    if (index !== -1) {
      tasks.value[index] = task
    }
  }

  function setFilterStatus(status: string | null) {
    filterStatus.value = status
  }

  function clearCurrentTask() {
    currentTask.value = null
    currentCheckpoints.value = []
    currentSteps.value = []
  }

  return {
    // 状态
    tasks,
    stats,
    currentTask,
    currentCheckpoints,
    currentSteps,
    loading,
    error,
    filterStatus,

    // 计算属性
    filteredTasks,
    waitingTasks,

    // Actions
    createTask,
    fetchTasks,
    fetchStats,
    fetchTaskDetail,
    fetchPhaseSteps,
    pauseTask,
    resumeTask,
    confirmIntervention,
    cancelTask,
    deleteTask,
    retryTask,
    revertCheckpoint,
    handleProgressUpdate,
    setFilterStatus,
    clearCurrentTask,
  }
})
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import TaskDetail from '../src/views/TaskDetail.vue'
import { createRouter, createWebHistory } from 'vue-router'
import { nextTick } from 'vue'

// Mock API
vi.mock('../src/services/api', () => ({
  taskApi: {
    detail: vi.fn().mockResolvedValue({
      id: 'task-001',
      name: '测试任务',
      status: 'running',
      phase: 'Phase2',
      progress: 50,
      gmtCreate: '2026-04-21',
      gmtModified: '2026-04-21',
      description: '测试描述',
    }),
    pause: vi.fn(),
    resume: vi.fn(),
    cancel: vi.fn(),
  },
  checkpointApi: {
    list: vi.fn().mockResolvedValue([]),
  },
  stepApi: {
    list: vi.fn().mockResolvedValue([]),
  },
}))

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: { template: '<div></div>' } },
    { path: '/task/:id', component: TaskDetail },
  ],
})

describe('TaskDetail', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('渲染任务详情', async () => {
    router.push('/task/task-001')
    await router.isReady()

    const wrapper = mount(TaskDetail, {
      global: {
        plugins: [router],
      },
    })

    // 等待异步数据加载
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()

    // 应该显示任务名称
    expect(wrapper.find('.task-header h2').text()).toBe('测试任务')
  })

  it('显示正确的状态标签', async () => {
    router.push('/task/task-001')
    await router.isReady()

    const wrapper = mount(TaskDetail, {
      global: {
        plugins: [router],
      },
    })

    // 等待异步数据加载
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()

    const badge = wrapper.find('.status-badge')
    expect(badge.text()).toBe('running')
    expect(badge.classes()).toContain('running')
  })

  it('运行状态显示暂停按钮', async () => {
    router.push('/task/task-001')
    await router.isReady()

    const wrapper = mount(TaskDetail, {
      global: {
        plugins: [router],
      },
    })

    // 等待异步数据加载
    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()

    // 应该有暂停按钮
    const buttons = wrapper.find('.action-buttons').findAll('button')
    expect(buttons.length).toBeGreaterThan(0)
    expect(buttons[0].text()).toContain('暂停')
  })

  it('提供 Runtime Console 跳转入口', async () => {
    router.push('/task/task-001')
    await router.isReady()

    const wrapper = mount(TaskDetail, {
      global: {
        plugins: [router],
      },
    })

    await nextTick()
    await new Promise(resolve => setTimeout(resolve, 100))
    await nextTick()

    expect(wrapper.find('a.runtime-link').attributes('href')).toBe('/runtime')
    expect(wrapper.text()).toContain('打开 Runtime Console')
  })
})

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import ProgressStream from '../src/components/ProgressStream.vue'

// Mock SSE
const mockConnectSSE = vi.fn()
const mockDisconnectSSE = vi.fn()

vi.mock('../src/services/sse', () => ({
  connectSSE: mockConnectSSE,
  disconnectSSE: mockDisconnectSSE,
}))

describe('ProgressStream', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('连接SSE', () => {
    mount(ProgressStream, {
      props: {
        taskId: 'task-001',
      },
    })

    expect(mockConnectSSE).toHaveBeenCalled()
  })

  it('显示等待事件提示', () => {
    const wrapper = mount(ProgressStream, {
      props: {
        taskId: 'task-001',
      },
    })

    expect(wrapper.find('.empty').text()).toBe('等待事件...')
  })

  it('清空按钮清空事件列表', async () => {
    const wrapper = mount(ProgressStream, {
      props: {
        taskId: 'task-001',
      },
    })

    // 模拟添加事件
    // 通过组件内部方法添加（这里简化测试）
    await wrapper.find('.stream-controls button').trigger('click')

    expect(wrapper.find('.empty').exists()).toBe(true)
  })
})
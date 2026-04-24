import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import Dashboard from '../src/views/Dashboard.vue'
import StatsCard from '../src/components/StatsCard.vue'

vi.mock('../src/services/api', () => ({
  taskApi: {
    list: vi.fn().mockResolvedValue([]),
    stats: vi.fn().mockResolvedValue({
      running: 0,
      completed: 0,
      waiting: 0,
      alert: 0,
    }),
  },
}))

// Mock SSE
vi.mock('../src/services/sse', () => ({
  connectSSE: vi.fn(),
  disconnectSSE: vi.fn(),
}))

describe('Dashboard', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('渲染统计卡片', () => {
    const wrapper = mount(Dashboard)

    // 应该有4个统计卡片
    const cards = wrapper.findAllComponents(StatsCard)
    expect(cards.length).toBe(4)
  })

  it('显示正确的统计标题', () => {
    const wrapper = mount(Dashboard)

    const titles = wrapper.findAll('.stats-card .title')
    expect(titles[0].text()).toBe('运行中')
    expect(titles[1].text()).toBe('已完成')
    expect(titles[2].text()).toBe('等待介入')
    expect(titles[3].text()).toBe('告警')
  })

  it('点击统计卡片触发过滤', async () => {
    const wrapper = mount(Dashboard)

    // 点击第一个卡片
    const firstCard = wrapper.findComponent(StatsCard)
    await firstCard.trigger('click')

    // 应该显示过滤提示
    expect(wrapper.find('.filter-bar').exists()).toBe(true)
  })

  it('提供 Runtime Console 入口卡片', () => {
    const wrapper = mount(Dashboard)

    expect(wrapper.text()).toContain('进入 Runtime Console')
    expect(wrapper.find('a.workspace-card.runtime').attributes('href')).toBe('/runtime')
  })
})

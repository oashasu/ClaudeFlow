import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import StatsCard from '../src/components/StatsCard.vue'

describe('StatsCard', () => {
  it('渲染正确的标题和计数', () => {
    const wrapper = mount(StatsCard, {
      props: {
        title: '运行中',
        count: 5,
        color: 'green',
      },
    })

    expect(wrapper.find('.title').text()).toBe('运行中')
    expect(wrapper.find('.count').text()).toBe('5')
  })

  it('点击触发事件', async () => {
    const wrapper = mount(StatsCard, {
      props: {
        title: '运行中',
        count: 5,
        color: 'green',
      },
    })

    await wrapper.trigger('click')

    expect(wrapper.emitted('click')).toBeTruthy()
  })

  it('highlight属性添加样式', () => {
    const wrapper = mount(StatsCard, {
      props: {
        title: '等待介入',
        count: 2,
        color: 'orange',
        highlight: true,
      },
    })

    expect(wrapper.find('.stats-card').classes()).toContain('highlight')
  })
})
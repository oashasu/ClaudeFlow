import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RuntimeConsole from '../src/views/RuntimeConsole.vue'

describe('RuntimeConsole', () => {
  it('渲染三块 runtime 面板', () => {
    const wrapper = mount(RuntimeConsole)

    expect(wrapper.text()).toContain('Plan')
    expect(wrapper.text()).toContain('Explain')
    expect(wrapper.text()).toContain('Dispatch')
  })

  it('默认加载示例数据', () => {
    const wrapper = mount(RuntimeConsole)
    expect(wrapper.text()).toContain('impl_auth_controller')
    expect(wrapper.text()).toContain('waiting_dependency')
  })

  it('提供 live 操作入口', () => {
    const wrapper = mount(RuntimeConsole)
    const buttons = wrapper.findAll('button')

    expect(buttons.some((button) => button.text().includes('读取 Live Plan'))).toBe(true)
    expect(buttons.some((button) => button.text().includes('执行 Live Dispatch'))).toBe(true)
    expect(wrapper.find('input').exists()).toBe(true)
  })

  it('提供自动刷新控制', () => {
    const wrapper = mount(RuntimeConsole)

    expect(wrapper.text()).toContain('自动刷新')
    expect(wrapper.find('select').exists()).toBe(true)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
  })

  it('显示 live 状态与原始 JSON 折叠区', () => {
    const wrapper = mount(RuntimeConsole)

    expect(wrapper.text()).toContain('最近刷新')
    expect(wrapper.findAll('details').length).toBeGreaterThanOrEqual(3)
    expect(wrapper.text()).toContain('sample')
  })

  it('显示运行时总览和 session 列表', () => {
    const wrapper = mount(RuntimeConsole)

    expect(wrapper.text()).toContain('运行时总览')
    expect(wrapper.text()).toContain('Repo:')
    expect(wrapper.text()).toContain('sess-pay-001')
    expect(wrapper.text()).toContain('读取 Live 总览')
  })

  it('提供 session 级动作入口', () => {
    const wrapper = mount(RuntimeConsole)

    expect(wrapper.text()).toContain('解释任务')
    expect(wrapper.text()).toContain('查看事件')
    expect(wrapper.text()).toContain('发送干预')
    expect(wrapper.text()).toContain('标记完成')
    expect(wrapper.text()).toContain('标记失败')
  })

  it('显示 session inspector 面板', () => {
    const wrapper = mount(RuntimeConsole)

    expect(wrapper.text()).toContain('Session 事件查看')
    expect(wrapper.text()).toContain('最近读取')
  })

  it('在 inspector 中显示动作面板', () => {
    const wrapper = mount(RuntimeConsole)

    expect(wrapper.text()).toContain('Session 干预')
    expect(wrapper.text()).toContain('标记完成')
    expect(wrapper.text()).toContain('标记失败')
  })
})

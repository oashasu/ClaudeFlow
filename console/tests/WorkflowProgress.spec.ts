import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import WorkflowProgress from '../src/components/WorkflowProgress.vue'

describe('WorkflowProgress', () => {
  it('渲染7个阶段', () => {
    const wrapper = mount(WorkflowProgress, {
      props: {
        phase: 'Phase0',
        progress: 10,
      },
    })

    const phases = wrapper.findAll('.phase-node')
    expect(phases.length).toBe(7)
  })

  it('Phase0阶段显示running状态', () => {
    const wrapper = mount(WorkflowProgress, {
      props: {
        phase: 'Phase0',
        progress: 30,
      },
    })

    const firstPhase = wrapper.find('.phase-node')
    expect(firstPhase.classes()).toContain('running')
  })

  it('Phase3时前面阶段显示completed', () => {
    const wrapper = mount(WorkflowProgress, {
      props: {
        phase: 'Phase3',
        progress: 50,
      },
    })

    const phases = wrapper.findAll('.phase-node')
    expect(phases[0].classes()).toContain('completed')
    expect(phases[1].classes()).toContain('completed')
    expect(phases[2].classes()).toContain('completed')
    expect(phases[3].classes()).toContain('running')
  })

  it('点击阶段触发事件', async () => {
    const wrapper = mount(WorkflowProgress, {
      props: {
        phase: 'Phase2',
        progress: 50,
      },
    })

    const firstPhase = wrapper.find('.phase-node')
    await firstPhase.trigger('click')

    expect(wrapper.emitted('phaseClick')).toBeTruthy()
    expect(wrapper.emitted('phaseClick')[0]).toEqual(['Phase0'])
  })
})
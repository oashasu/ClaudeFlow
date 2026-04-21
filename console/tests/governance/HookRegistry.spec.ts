import { describe, it, expect, beforeEach, vi } from 'vitest'
import { HookRegistry, globalHookRegistry } from '@/governance/hook/HookRegistry'
import { FileReadHook, HookConfig } from '@/governance/hook/FileReadHook'

describe('HookRegistry', () => {
  let registry: HookRegistry

  beforeEach(() => {
    registry = new HookRegistry()
    // Mock console.log
    vi.spyOn(console, 'log').mockImplementation(() => {})
  })

  describe('register', () => {
    it('testHookRegisterSuccess: Hook注册成功', () => {
      const hook = new FileReadHook()
      registry.register('FileRead', hook.postProcess.bind(hook))

      expect(registry.getRegisteredTools()).toContain('FileRead')
      expect(console.log).toHaveBeenCalledWith('[HookRegistry] Hook registered for FileRead')
    })

    it('testMultipleHooksRegister: 多个Hook可注册同一工具', () => {
      const hook1 = new FileReadHook()
      const hook2 = new FileReadHook()
      registry.register('FileRead', hook1.postProcess.bind(hook1))
      registry.register('FileRead', hook2.postProcess.bind(hook2))

      expect(registry.getRegisteredTools()).toContain('FileRead')
    })
  })

  describe('executePostHooks', () => {
    it('testHookExecution: Hook执行生效', () => {
      const hook = new FileReadHook()
      registry.register('FileRead', hook.postProcess.bind(hook))

      const request = { toolName: 'FileRead', params: { startLine: 1, endLine: 20 } }
      const lines = Array.from({ length: 30 }, (_, i) => `line ${i + 1}`)
      const response = { result: lines.join('\n') }

      const result = registry.executePostHooks(request, response)

      expect(result.result.split('\n').length).toBe(HookConfig.MAX_READ_LINES)
    })

    it('testNoHookPassThrough: 无Hook工具直接返回', () => {
      const request = { toolName: 'OtherTool', params: {} }
      const response = { result: 'some content' }

      const result = registry.executePostHooks(request, response)

      expect(result.result).toBe('some content')
    })
  })

  describe('initializeDefaultHooks', () => {
    it('testDefaultHooksInit: 默认Hook初始化', () => {
      registry.initializeDefaultHooks()

      expect(registry.isRegistered()).toBe(true)
      expect(registry.getRegisteredTools()).toContain('FileRead')
      expect(console.log).toHaveBeenCalledWith('[HookRegistry] Default hooks initialized:', {
        maxLineRange: HookConfig.MAX_LINE_RANGE,
        maxReadLines: HookConfig.MAX_READ_LINES,
      })
    })
  })
})

describe('globalHookRegistry', () => {
  it('testGlobalRegistryExists: 全局注册表存在', () => {
    expect(globalHookRegistry).toBeDefined()
    expect(globalHookRegistry).toBeInstanceOf(HookRegistry)
  })
})
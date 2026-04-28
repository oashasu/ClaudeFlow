import { FileReadHook, HookConfig } from './FileReadHook'
import type { ToolRequest, ToolResponse } from './FileReadHook'

/**
 * Hook类型定义
 */
export type HookHandler = (request: ToolRequest, response: ToolResponse) => ToolResponse

/**
 * Hook注册表
 * 管理所有工具调用Hook的生命周期
 */
export class HookRegistry {
  private hooks: Map<string, HookHandler[]> = new Map()
  private registered: boolean = false

  /**
   * 注册Hook到指定工具
   */
  register(toolName: string, hook: HookHandler): void {
    if (!this.hooks.has(toolName)) {
      this.hooks.set(toolName, [])
    }
    this.hooks.get(toolName)!.push(hook)
    console.log(`[HookRegistry] Hook registered for ${toolName}`)
  }

  /**
   * 执行工具的后置Hook链
   */
  executePostHooks(request: ToolRequest, response: ToolResponse): ToolResponse {
    const handlers = this.hooks.get(request.toolName)
    if (!handlers) {
      return response
    }

    let result = response
    for (const hook of handlers) {
      result = hook(request, result)
    }
    return result
  }

  /**
   * 初始化默认Hook
   */
  initializeDefaultHooks(): void {
    // 注册FileReadHook
    const fileReadHook = new FileReadHook()
    this.register('FileRead', fileReadHook.postProcess.bind(fileReadHook))
    this.registered = true
    console.log('[HookRegistry] Default hooks initialized:', {
      maxLineRange: HookConfig.MAX_LINE_RANGE,
      maxReadLines: HookConfig.MAX_READ_LINES,
    })
  }

  /**
   * 获取注册状态
   */
  isRegistered(): boolean {
    return this.registered
  }

  /**
   * 获取已注册的工具列表
   */
  getRegisteredTools(): string[] {
    return Array.from(this.hooks.keys())
  }
}

/**
 * 全局Hook注册表实例
 */
export const globalHookRegistry = new HookRegistry()
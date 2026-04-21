/**
 * Hook配置常量
 */
export const HookConfig = {
  /** 单次读取最大行数范围 */
  MAX_LINE_RANGE: 50,
  /** 结果截断最大行数 */
  MAX_READ_LINES: 20,
}

/**
 * 工具请求接口
 */
export interface ToolRequest {
  toolName: string
  params: Record<string, any>
}

/**
 * 工具响应接口
 */
export interface ToolResponse {
  result: string
}

/**
 * 文件读取工具后置拦截Hook
 * 功能：
 * 1. 行号范围校验（单次读取≤50行）
 * 2. 结果截断（最多返回20行）
 * 3. 禁止全文件读取
 */
export class FileReadHook {
  /**
   * 后置处理入口
   */
  postProcess(request: ToolRequest, response: ToolResponse): ToolResponse {
    // 仅拦截FileRead工具调用
    if (request.toolName !== 'FileRead') {
      return response
    }

    // 1. 行号范围合法性校验
    this.validateLineRange(request)

    // 2. 工具结果强制截断
    const limitedResult = this.truncateResponse(response.result)

    // 3. 构建拦截后响应
    return { result: limitedResult ?? '' }
  }

  /**
   * 行号范围校验：单次读取最大50行，禁止全文件读取
   */
  validateLineRange(request: ToolRequest): void {
    const { startLine, endLine } = request.params

    if (startLine === undefined || endLine === undefined) {
      throw new Error('FileRead必须指定startLine和endLine，禁止全文件读取')
    }

    const lineRange = endLine - startLine
    if (lineRange > HookConfig.MAX_LINE_RANGE) {
      throw new Error(`单次文件读取最大范围：${HookConfig.MAX_LINE_RANGE}行`)
    }
  }

  /**
   * 响应结果截断：强制限制最大行数
   */
  truncateResponse(rawResult: string | null): string | null {
    if (rawResult === null || rawResult === '') {
      return rawResult
    }

    const lines = rawResult.split('\n')
    if (lines.length <= HookConfig.MAX_READ_LINES) {
      return rawResult
    }

    return lines.slice(0, HookConfig.MAX_READ_LINES).join('\n')
  }
}
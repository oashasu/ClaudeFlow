import { describe, it, expect, beforeEach } from 'vitest'
import { FileReadHook, HookConfig } from '@/governance/hook/FileReadHook'

describe('FileReadHook', () => {
  let hook: FileReadHook

  beforeEach(() => {
    hook = new FileReadHook()
  })

  describe('validateLineRange', () => {
    it('testValidLineRange: 合法范围通过', () => {
      // 20行范围，在50行限制内
      const request = {
        toolName: 'FileRead',
        params: { startLine: 1, endLine: 20 }
      }
      expect(() => hook.validateLineRange(request)).not.toThrow()
    })

    it('testExceedLineRangeThrows: 超50行抛异常', () => {
      // 60行范围，超过50行限制
      const request = {
        toolName: 'FileRead',
        params: { startLine: 1, endLine: 60 }
      }
      expect(() => hook.validateLineRange(request)).toThrow(
        `单次文件读取最大范围：${HookConfig.MAX_LINE_RANGE}行`
      )
    })

    it('testMissingLineParamsThrows: 缺少行号参数抛异常', () => {
      const request = {
        toolName: 'FileRead',
        params: {}
      }
      expect(() => hook.validateLineRange(request)).toThrow(
        'FileRead必须指定startLine和endLine，禁止全文件读取'
      )
    })
  })

  describe('truncateResponse', () => {
    it('testResultTruncate: 结果截断20行', () => {
      // 30行内容
      const lines = Array.from({ length: 30 }, (_, i) => `line ${i + 1}`)
      const input = lines.join('\n')

      const result = hook.truncateResponse(input)

      // 应截断为20行
      const resultLines = result.split('\n')
      expect(resultLines.length).toBe(HookConfig.MAX_READ_LINES)
      expect(resultLines[0]).toBe('line 1')
      expect(resultLines[19]).toBe('line 20')
    })

    it('testShortResultUnchanged: 短内容不截断', () => {
      // 10行内容
      const lines = Array.from({ length: 10 }, (_, i) => `line ${i + 1}`)
      const input = lines.join('\n')

      const result = hook.truncateResponse(input)

      expect(result).toBe(input)
    })

    it('testEmptyResultReturnsEmpty: 空内容返回空', () => {
      expect(hook.truncateResponse('')).toBe('')
      expect(hook.truncateResponse(null as any)).toBeNull()
    })
  })

  describe('postProcess', () => {
    it('testNonFileReadPassThrough: 非FileRead工具不拦截', () => {
      const request = { toolName: 'OtherTool', params: {} }
      const response = { result: 'some content' }

      const result = hook.postProcess(request, response)

      expect(result.result).toBe('some content')
    })

    it('testFileReadIntercepted: FileRead工具被拦截截断', () => {
      const request = {
        toolName: 'FileRead',
        params: { startLine: 1, endLine: 20 }
      }
      const lines = Array.from({ length: 30 }, (_, i) => `line ${i + 1}`)
      const response = { result: lines.join('\n') }

      const result = hook.postProcess(request, response)

      expect(result.result.split('\n').length).toBe(HookConfig.MAX_READ_LINES)
    })
  })
})
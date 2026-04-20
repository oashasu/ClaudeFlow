import { test, expect } from '@playwright/test'

test.describe('SSE进度更新', () => {
  test('SSE连接状态显示', async ({ page }) => {
    // Mock SSE连接
    await page.route('**/api/events/stream', (route) => {
      route.fulfill({
        status: 200,
        headers: {
          'Content-Type': 'text/event-stream',
        },
        body: 'event: connected\ndata: {"status":"connected"}\n\n',
      })
    })

    await page.goto('/task/task-001')

    // 验证ProgressStream组件显示连接状态
    // 等待组件加载
    await page.waitForSelector('.progress-stream', { timeout: 5000 })
  })

  test('工具调用事件显示', async ({ page }) => {
    // Mock SSE事件流
    await page.route('**/api/events/stream', (route) => {
      const events = [
        'event: connected\ndata: {"status":"connected"}\n\n',
        'event: tool_call\ndata: {"taskId":"task-001","tool":"Glob","input":"src/**/*.java"}\n\n',
      ]
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: events.join(''),
      })
    })

    await page.goto('/task/task-001')

    // 验证事件显示
    await page.waitForSelector('.event-item', { timeout: 5000 })
  })

  test('Checkpoint事件显示', async ({ page }) => {
    await page.route('**/api/events/stream', (route) => {
      const events = [
        'event: connected\ndata: {"status":"connected"}\n\n',
        'event: progress_update\ndata: {"taskId":"task-001","phase":"Phase1","progress":30}\n\n',
      ]
      route.fulfill({
        status: 200,
        headers: { 'Content-Type': 'text/event-stream' },
        body: events.join(''),
      })
    })

    await page.goto('/task/task-001')
    await page.waitForSelector('.progress-stream')
  })
})
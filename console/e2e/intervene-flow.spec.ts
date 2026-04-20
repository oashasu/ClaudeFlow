import { test, expect } from '@playwright/test'

test.describe('干预流程', () => {
  test('暂停任务按钮', async ({ page }) => {
    // Mock task detail API
    await page.route('**/api/tasks/task-001', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          id: 'task-001',
          name: '测试任务',
          status: 'running',
          phase: 'Phase2',
          progress: 50,
          description: '测试描述',
        }),
      })
    })

    await page.goto('/task/task-001')

    // 验证暂停按钮存在
    const pauseBtn = page.locator('.action-buttons button', { hasText: '暂停' })
    await expect(pauseBtn).toBeVisible()
  })

  test('恢复暂停任务', async ({ page }) => {
    // Mock paused task
    await page.route('**/api/tasks/task-002', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          id: 'task-002',
          name: '暂停任务',
          status: 'paused',
          phase: 'Phase2',
          progress: 50,
          description: '已暂停',
        }),
      })
    })

    await page.goto('/task/task-002')

    // 验证恢复按钮存在
    const resumeBtn = page.locator('.action-buttons button', { hasText: '恢复' })
    await expect(resumeBtn).toBeVisible()
  })

  test('取消任务确认', async ({ page }) => {
    await page.route('**/api/tasks/task-001', (route) => {
      route.fulfill({
        status: 200,
        body: JSON.stringify({
          id: 'task-001',
          name: '测试任务',
          status: 'running',
          phase: 'Phase2',
          progress: 50,
          description: '测试描述',
        }),
      })
    })

    await page.goto('/task/task-001')

    // 点击取消按钮
    const cancelBtn = page.locator('.action-buttons button.cancel')
    await cancelBtn.click()

    // 验证确认对话框
    page.on('dialog', (dialog) => {
      expect(dialog.message()).toContain('确认取消')
      dialog.dismiss()
    })
  })
})
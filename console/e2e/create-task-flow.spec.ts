import { test, expect } from '@playwright/test'

test.describe('创建任务流程', () => {
  test('Dashboard页面加载正确', async ({ page }) => {
    await page.goto('/')

    // 验证统计卡片存在
    await expect(page.locator('.stats-area')).toBeVisible()

    // 验证四个统计卡片
    const cards = page.locator('.stats-card')
    await expect(cards).toHaveCount(4)
  })

  test('点击任务卡片跳转详情页', async ({ page }) => {
    await page.goto('/')

    // 等待任务列表加载
    await page.waitForSelector('.task-list', { timeout: 5000 })

    // 点击第一个任务卡片（如果有）
    const firstTask = page.locator('.task-card').first()
    if (await firstTask.isVisible()) {
      await firstTask.click()

      // 验证跳转到详情页
      await expect(page).toHaveURL(/\/task\/.+/)
    }
  })

  test('统计卡片过滤功能', async ({ page }) => {
    await page.goto('/')

    // 点击"运行中"卡片
    await page.locator('.stats-card').first().click()

    // 验证过滤提示显示
    await expect(page.locator('.filter-bar')).toBeVisible()
    await expect(page.locator('.filter-bar span')).toContainText('running')

    // 点击清除按钮
    await page.locator('.filter-bar button').click()

    // 验证过滤提示消失
    await expect(page.locator('.filter-bar')).not.toBeVisible()
  })
})
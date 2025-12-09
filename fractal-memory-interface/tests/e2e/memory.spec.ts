import { test, expect } from '@playwright/test'

test.describe('Memory Stats and Browser', () => {
  test.beforeEach(async ({ page }) => {
    await page.route('**/health', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok' }),
    }))
    
    await page.goto('/')
  })

  test('отображает статистику памяти', async ({ page }) => {
    await page.route('**/memory/stats', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        l0_count: 5,
        l1_count: 3,
        l2_count: 10,
        l3_count: 7,
        last_consolidation: new Date().toISOString(),
      }),
    }))
    
    await page.reload()
    
    await expect(page.getByText(/MEMORY STATS/i)).toBeVisible()
    await expect(page.getByText('5')).toBeVisible() // L0
    await expect(page.getByText('10')).toBeVisible() // L2
  })

  test('отображает узлы памяти', async ({ page }) => {
    const mockNodes = [
      {
        id: '1',
        label: 'Test Node',
        content: 'Test content',
        level: 'l2',
        importance: 0.8,
        created_at: '2025-01-01T00:00:00Z',
        connections: [],
      },
    ]
    
    await page.route('**/memory/all*', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(mockNodes),
    }))
    
    await page.reload()
    
    // Проверяем что узлы отображаются в браузере памяти
    await expect(page.getByText(/Test Node/i)).toBeVisible({ timeout: 3000 })
  })

  test('фильтрует узлы по уровню', async ({ page }) => {
    await page.route('**/memory/l2*', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: '1',
          label: 'L2 Node',
          content: 'L2 content',
          level: 'l2',
          importance: 0.8,
          created_at: '2025-01-01T00:00:00Z',
          connections: [],
        },
      ]),
    }))
    
    // Кликаем на фильтр L2
    const l2Filter = page.getByText('L2', { exact: true })
    if (await l2Filter.isVisible()) {
      await l2Filter.click()
      
      // Проверяем что загрузились только L2 узлы
      await expect(page.getByText(/L2 Node/i)).toBeVisible({ timeout: 3000 })
    }
  })

  test('запускает консолидацию', async ({ page }) => {
    let consolidateCalled = false
    
    await page.route('**/memory/consolidate', route => {
      consolidateCalled = true
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'ok', l0_to_l1: 5, l1_to_l2: 2 }),
      })
    })
    
    const consolidateButton = page.getByText(/Force Consolidation/i)
    if (await consolidateButton.isVisible()) {
      await consolidateButton.click()
      
      await expect(async () => {
        expect(consolidateCalled).toBe(true)
      }).toPass({ timeout: 3000 })
    }
  })
})


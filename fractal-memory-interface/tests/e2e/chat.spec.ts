import { test, expect } from '@playwright/test'

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    // Мокируем API перед каждым тестом
    await page.route('**/health', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ status: 'ok', agent: 'Марк', user: 'Сергей', model: 'gpt-5-nano' }),
    }))
    
    await page.route('**/memory/stats', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        l0_count: 0,
        l1_count: 0,
        l2_count: 10,
        l3_count: 5,
        last_consolidation: new Date().toISOString(),
      }),
    }))
    
    await page.route('**/memory/all*', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    }))
    
    await page.goto('/')
  })

  test('отображает начальное сообщение', async ({ page }) => {
    await expect(page.getByText(/System initialized/i)).toBeVisible()
  })

  test('отображает поле ввода сообщения', async ({ page }) => {
    const input = page.getByPlaceholderText(/Message Mark/i)
    await expect(input).toBeVisible()
  })

  test('отправляет сообщение и получает ответ', async ({ page }) => {
    // Мокируем успешный ответ
    await page.route('**/chat', route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        response: 'Тестовый ответ от агента',
        context_count: 2,
        strategies_used: ['default'],
        processing_time_ms: 100.0,
      }),
    }))
    
    const input = page.getByPlaceholderText(/Message Mark/i)
    await input.fill('Привет, как дела?')
    
    // Находим кнопку отправки
    const sendButton = page.locator('button').filter({ hasText: /send|отправить/i }).or(
      page.locator('button[type="button"]').last()
    )
    await sendButton.click()
    
    // Ждем ответа
    await expect(page.getByText(/Тестовый ответ от агента/i)).toBeVisible({ timeout: 5000 })
  })

  test('обрабатывает ошибки API', async ({ page }) => {
    // Мокируем ошибку
    await page.route('**/chat', route => route.fulfill({
      status: 500,
      contentType: 'application/json',
      body: JSON.stringify({ error: 'Internal Server Error' }),
    }))
    
    const input = page.getByPlaceholderText(/Message Mark/i)
    await input.fill('Тест')
    
    const sendButton = page.locator('button').last()
    await sendButton.click()
    
    // Проверяем что ошибка отображается
    await expect(page.getByText(/Error|Ошибка/i)).toBeVisible({ timeout: 5000 })
  })

  test('не отправляет пустое сообщение', async ({ page }) => {
    const input = page.getByPlaceholderText(/Message Mark/i)
    await input.fill('   ') // Только пробелы
    
    const sendButton = page.locator('button').last()
    const isDisabled = await sendButton.isDisabled()
    
    // Кнопка должна быть заблокирована для пустого сообщения
    expect(isDisabled).toBeTruthy()
  })

  test('отображает индикатор загрузки', async ({ page }) => {
    // Мокируем медленный ответ
    await page.route('**/chat', route => 
      new Promise(resolve => 
        setTimeout(() => resolve(route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            response: 'Ответ',
            context_count: 0,
            strategies_used: [],
            processing_time_ms: 100.0,
          }),
        })), 1000)
      )
    )
    
    const input = page.getByPlaceholderText(/Message Mark/i)
    await input.fill('Тест')
    
    const sendButton = page.locator('button').last()
    await sendButton.click()
    
    // Проверяем что индикатор загрузки появился (анимация точек)
    await expect(page.locator('.animate-bounce').first()).toBeVisible({ timeout: 1000 })
  })
})


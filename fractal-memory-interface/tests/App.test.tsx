import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import App from '../App'
import * as api from '../services/api'

// Мок для scrollIntoView перед импортом App
if (typeof Element !== 'undefined') {
  Element.prototype.scrollIntoView = vi.fn(() => {})
}

// Мокируем API
vi.mock('../services/api', () => ({
  api: {
    health: vi.fn(),
    chat: vi.fn(),
    getStats: vi.fn(),
    getNodes: vi.fn(),
    consolidate: vi.fn(),
    getHistory: vi.fn(),
  },
}))

describe('App Component', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    
    // Мокируем успешные ответы по умолчанию
    vi.mocked(api.api.health).mockResolvedValue(true)
    vi.mocked(api.api.getStats).mockResolvedValue({
      l0_count: 0,
      l1_count: 0,
      l2_count: 10,
      l3_count: 5,
      last_consolidation: new Date().toISOString(),
    })
    vi.mocked(api.api.getNodes).mockResolvedValue([])
    vi.mocked(api.api.getHistory).mockResolvedValue([])
  })

  it('отображает начальное сообщение', async () => {
    render(<App />)
    await waitFor(() => {
      expect(screen.getByText(/Привет, Сергей/i)).toBeInTheDocument()
    }, { timeout: 2000 })
  })

  it('отображает статистику памяти', async () => {
    render(<App />)
    
    await waitFor(() => {
      expect(api.api.getStats).toHaveBeenCalled()
    })
    
    // Проверяем что статистика отображается
    expect(screen.getByText(/MEMORY STATS/i)).toBeInTheDocument()
  })

  it('отправляет сообщение и получает ответ', async () => {
    const user = userEvent.setup()
    
    // Мокируем успешный ответ от API
    vi.mocked(api.api.chat).mockResolvedValue({
      response: 'Тестовый ответ',
      context_count: 2,
      strategies_used: ['default'],
      processing_time_ms: 100.0,
    })
    
    render(<App />)
    
    // Ждем загрузки начальных данных
    await waitFor(() => {
      expect(api.api.getStats).toHaveBeenCalled()
    })
    
    // Находим поле ввода
    const input = screen.getByPlaceholderText(/Message Mark/i)
    expect(input).toBeInTheDocument()
    
    // Вводим сообщение и отправляем через Enter
    await act(async () => {
      await user.type(input, 'Привет')
      await user.keyboard('{Enter}')
    })
    
    // Ждем вызова API
    await waitFor(() => {
      expect(api.api.chat).toHaveBeenCalledWith('Привет')
    }, { timeout: 3000 })
    
    // Проверяем что ответ появился
    await waitFor(() => {
      expect(screen.getByText(/Тестовый ответ/i)).toBeInTheDocument()
    }, { timeout: 2000 })
  })

  it('обрабатывает ошибки API корректно', async () => {
    const user = userEvent.setup()
    
    // Мокируем ошибку
    vi.mocked(api.api.chat).mockRejectedValue(new Error('Network error'))
    
    render(<App />)
    
    // Ждем загрузки начальных данных
    await waitFor(() => {
      expect(api.api.getStats).toHaveBeenCalled()
    }, { timeout: 2000 })
    
    const input = screen.getByPlaceholderText(/Message Mark/i) as HTMLTextAreaElement
    await act(async () => {
      await user.type(input, 'Тест')
      // Симулируем Enter для отправки
      await user.keyboard('{Enter}')
    })
    
    // Проверяем что chat был вызван (даже если с ошибкой)
    await waitFor(() => {
      expect(api.api.chat).toHaveBeenCalledWith('Тест')
    }, { timeout: 3000 })
  })

  it('обновляет статистику после отправки сообщения', async () => {
    const user = userEvent.setup()
    
    vi.mocked(api.api.chat).mockResolvedValue({
      response: 'Ответ',
      context_count: 0,
      strategies_used: [],
      processing_time_ms: 50.0,
    })
    
    render(<App />)
    
    // Ждем загрузки начальных данных
    await waitFor(() => {
      expect(api.api.getStats).toHaveBeenCalled()
    })
    
    const initialCalls = vi.mocked(api.api.getStats).mock.calls.length
    
    const input = screen.getByPlaceholderText(/Message Mark/i) as HTMLTextAreaElement
    await act(async () => {
      await user.type(input, 'Тест')
      await user.keyboard('{Enter}')
    })
    
    // После отправки должна обновиться статистика
    await waitFor(() => {
      expect(api.api.chat).toHaveBeenCalledWith('Тест')
    }, { timeout: 3000 })
    
    // Проверяем что getStats был вызван еще раз
    await waitFor(() => {
      expect(api.api.getStats).toHaveBeenCalledTimes(initialCalls + 1)
    }, { timeout: 2000 })
  })
})


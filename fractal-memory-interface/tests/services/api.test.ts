import { describe, it, expect, vi, beforeEach } from 'vitest'
import { api } from '../../services/api'

// Мокируем fetch
global.fetch = vi.fn()

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('health', () => {
    it('возвращает true при успешном ответе', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
      } as Response)

      const result = await api.health()
      expect(result).toBe(true)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/health'))
    })

    it('возвращает false при ошибке', async () => {
      vi.mocked(fetch).mockRejectedValueOnce(new Error('Network error'))

      const result = await api.health()
      expect(result).toBe(false)
    })
  })

  describe('chat', () => {
    it('отправляет сообщение и возвращает ответ', async () => {
      const mockResponse = {
        response: 'Тестовый ответ',
        context_count: 2,
        strategies_used: ['default'],
        processing_time_ms: 100.0,
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response)

      const result = await api.chat('Привет')
      
      expect(result).toEqual(mockResponse)
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/chat'),
        expect.objectContaining({
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ message: 'Привет' }),
        })
      )
    })

    it('пробрасывает ошибку при неудачном запросе', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: false,
        status: 500,
        text: async () => 'Internal Server Error',
      } as Response)

      await expect(api.chat('Тест')).rejects.toThrow()
    })

    it('проверяет обязательные поля в ответе', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          response: 'Ответ',
          context_count: 0,
          strategies_used: [],
          processing_time_ms: 50.0,
        }),
      } as Response)

      const result = await api.chat('Тест')
      
      expect(result).toHaveProperty('response')
      expect(result).toHaveProperty('context_count')
      expect(result).toHaveProperty('strategies_used')
      expect(result).toHaveProperty('processing_time_ms')
    })
  })

  describe('getStats', () => {
    it('возвращает статистику памяти', async () => {
      const mockStats = {
        l0_count: 5,
        l1_count: 3,
        l2_count: 10,
        l3_count: 7,
        last_consolidation: new Date().toISOString(),
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats,
      } as Response)

      const result = await api.getStats()
      
      expect(result).toEqual(mockStats)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/memory/stats'))
    })

    it('обрабатывает формат с вложенным memory', async () => {
      const mockStats = {
        memory: {
          l0_count: 5,
          l1_count: 3,
          l2_count: 10,
          l3_count: 7,
        },
      }

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockStats,
      } as Response)

      const result = await api.getStats()
      
      // API должен вернуть memory или сам объект
      expect(result).toHaveProperty('l0_count')
    })
  })

  describe('getNodes', () => {
    it('возвращает узлы памяти', async () => {
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

      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => mockNodes,
      } as Response)

      const result = await api.getNodes('all')
      
      expect(result).toEqual(mockNodes)
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/memory/all'))
    })

    it('поддерживает фильтрацию по уровню', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => [],
      } as Response)

      await api.getNodes('l2')
      
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/memory/l2'))
    })
  })

  describe('consolidate', () => {
    it('запускает консолидацию', async () => {
      vi.mocked(fetch).mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'ok' }),
      } as Response)

      const result = await api.consolidate()
      
      expect(result).toHaveProperty('status')
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/memory/consolidate'),
        expect.objectContaining({ method: 'POST' })
      )
    })
  })
})


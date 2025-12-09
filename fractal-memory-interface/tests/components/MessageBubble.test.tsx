import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import MessageBubble from '../../components/Chat/MessageBubble'
import { Message } from '../../types'

describe('MessageBubble Component', () => {
  it('отображает сообщение пользователя', () => {
    const message: Message = {
      id: '1',
      role: 'user',
      content: 'Привет, как дела?',
      timestamp: new Date(),
    }

    render(<MessageBubble message={message} />)
    
    expect(screen.getByText('Привет, как дела?')).toBeInTheDocument()
  })

  it('отображает сообщение ассистента', () => {
    const message: Message = {
      id: '2',
      role: 'assistant',
      content: 'Всё отлично!',
      timestamp: new Date(),
      metadata: {
        context_count: 2,
        importance: 0.8,
      },
    }

    render(<MessageBubble message={message} />)
    
    expect(screen.getByText('Всё отлично!')).toBeInTheDocument()
  })

  it('отображает метаданные для сообщений ассистента', () => {
    const message: Message = {
      id: '3',
      role: 'assistant',
      content: 'Ответ',
      timestamp: new Date(),
      metadata: {
        context_count: 5,
        importance: 0.9,
        processing_time_ms: 150.0,
      },
    }

    render(<MessageBubble message={message} />)
    
    expect(screen.getByText(/ctx: 5/i)).toBeInTheDocument()
    expect(screen.getByText(/imp: 0.90/i)).toBeInTheDocument()
    // processing_time_ms отображается как "150ms"
    expect(screen.getByText(/150ms/i)).toBeInTheDocument()
  })

  it('отображает strategies_used если они есть', () => {
    const message: Message = {
      id: '4',
      role: 'assistant',
      content: 'Ответ',
      timestamp: new Date(),
      metadata: {
        context_count: 3,
        strategies_used: ['default', 'reasoning'],
      },
    }

    render(<MessageBubble message={message} />)
    
    // MessageBubble отображает strategies_used как "strat: default, reasoning"
    // Проверяем наличие текста
    expect(screen.getByText(/strat: default, reasoning/i)).toBeInTheDocument()
  })

  it('не отображает importance если его нет', () => {
    const message: Message = {
      id: '5',
      role: 'assistant',
      content: 'Ответ',
      timestamp: new Date(),
      metadata: {
        context_count: 3,
      },
    }

    render(<MessageBubble message={message} />)
    
    expect(screen.queryByText(/imp:/i)).not.toBeInTheDocument()
  })

  it('отображает время сообщения', () => {
    const date = new Date('2025-12-05T12:30:00')
    const message: Message = {
      id: '5',
      role: 'user',
      content: 'Тест',
      timestamp: date,
    }

    render(<MessageBubble message={message} />)
    
    // Проверяем что время отображается (формат может быть разным)
    const timeElement = screen.getByText(/\d{2}:\d{2}/)
    expect(timeElement).toBeInTheDocument()
  })
})


import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import InputArea from '../../components/Chat/InputArea'

describe('InputArea Component', () => {
  it('отображает поле ввода', () => {
    const mockOnSend = vi.fn()
    render(<InputArea onSendMessage={mockOnSend} isLoading={false} />)
    
    const input = screen.getByPlaceholderText(/Message Mark/i)
    expect(input).toBeInTheDocument()
  })

  it('отправляет сообщение при клике на кнопку', async () => {
    const user = userEvent.setup()
    const mockOnSend = vi.fn()
    
    render(<InputArea onSendMessage={mockOnSend} isLoading={false} />)
    
    const input = screen.getByPlaceholderText(/Message Mark/i) as HTMLTextAreaElement
    await user.type(input, 'Тестовое сообщение')
    
    // Ищем кнопку отправки - она должна быть последней кнопкой (Send)
    const buttons = screen.getAllByRole('button')
    const sendButton = buttons[buttons.length - 1] // Последняя кнопка - это Send
    await user.click(sendButton)
    
    expect(mockOnSend).toHaveBeenCalledWith('Тестовое сообщение')
  })

  it('отправляет сообщение при нажатии Enter (без Shift)', async () => {
    const user = userEvent.setup()
    const mockOnSend = vi.fn()
    
    render(<InputArea onSendMessage={mockOnSend} isLoading={false} />)
    
    const input = screen.getByPlaceholderText(/Message Mark/i)
    await user.type(input, 'Тест')
    await user.keyboard('{Enter}')
    
    expect(mockOnSend).toHaveBeenCalledWith('Тест')
  })

  it('не отправляет пустое сообщение', async () => {
    const user = userEvent.setup()
    const mockOnSend = vi.fn()
    
    render(<InputArea onSendMessage={mockOnSend} isLoading={false} />)
    
    const input = screen.getByPlaceholderText(/Message Mark/i)
    await user.type(input, '   ') // Только пробелы
    
    const buttons = screen.getAllByRole('button')
    const sendButton = buttons[buttons.length - 1]
    if (sendButton && !sendButton.disabled) {
      await user.click(sendButton)
    }
    
    // handleSend проверяет input.trim(), поэтому пустое сообщение не должно отправиться
    expect(mockOnSend).not.toHaveBeenCalled()
  })

  it('блокирует отправку во время загрузки', async () => {
    const user = userEvent.setup()
    const mockOnSend = vi.fn()
    
    render(<InputArea onSendMessage={mockOnSend} isLoading={true} />)
    
    const input = screen.getByPlaceholderText(/Message Mark/i)
    // Input может быть не disabled, но handleSend проверяет isLoading
    await user.type(input, 'Тест')
    
    const buttons = screen.getAllByRole('button')
    const sendButton = buttons[buttons.length - 1]
    if (sendButton) {
      // Кнопка может быть disabled или handleSend просто вернется раньше
      if (!sendButton.disabled) {
        await user.click(sendButton)
        // handleSend проверяет isLoading и возвращается раньше
        expect(mockOnSend).not.toHaveBeenCalled()
      } else {
        expect(sendButton).toBeDisabled()
      }
    }
  })

  it('очищает поле ввода после отправки', async () => {
    const user = userEvent.setup()
    const mockOnSend = vi.fn()
    
    render(<InputArea onSendMessage={mockOnSend} isLoading={false} />)
    
    const input = screen.getByPlaceholderText(/Message Mark/i) as HTMLTextAreaElement
    await user.type(input, 'Тест')
    
    const buttons = screen.getAllByRole('button')
    const sendButton = buttons[buttons.length - 1]
    await user.click(sendButton)
    
    expect(input.value).toBe('')
  })
})


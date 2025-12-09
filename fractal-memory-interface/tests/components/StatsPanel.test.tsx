import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import StatsPanel from '../../components/Memory/StatsPanel'
import { MemoryStats } from '../../types'

describe('StatsPanel Component', () => {
  const mockStats: MemoryStats = {
    l0_count: 5,
    l1_count: 3,
    l2_count: 10,
    l3_count: 7,
    last_consolidation: new Date().toISOString(),
  }

  it('отображает статистику памяти', () => {
    const mockOnConsolidate = vi.fn()
    
    render(
      <StatsPanel 
        stats={mockStats} 
        onConsolidate={mockOnConsolidate} 
        isConsolidating={false} 
      />
    )
    
    expect(screen.getByText(/Memory Stats/i)).toBeInTheDocument()
    // Проверяем что счетчики отображаются
    expect(screen.getByText('5')).toBeInTheDocument() // L0
    expect(screen.getByText('3')).toBeInTheDocument() // L1
    expect(screen.getByText('10')).toBeInTheDocument() // L2
    expect(screen.getByText('7')).toBeInTheDocument() // L3
  })

  it('отображает Total Nodes', () => {
    const mockOnConsolidate = vi.fn()
    
    render(
      <StatsPanel 
        stats={mockStats} 
        onConsolidate={mockOnConsolidate} 
        isConsolidating={false} 
      />
    )
    
    // Total = 5 + 3 + 10 + 7 = 25
    expect(screen.getByText('25')).toBeInTheDocument()
    expect(screen.getByText(/Total Nodes/i)).toBeInTheDocument()
  })

  it('обрабатывает отсутствие статистики', () => {
    const mockOnConsolidate = vi.fn()
    
    render(
      <StatsPanel 
        stats={null} 
        onConsolidate={mockOnConsolidate} 
        isConsolidating={false} 
      />
    )
    
    // Компонент должен показать "Loading stats..."
    expect(screen.getByText(/Loading stats/i)).toBeInTheDocument()
  })

  it('вызывает onConsolidate при клике на кнопку', async () => {
    const user = userEvent.setup()
    const mockOnConsolidate = vi.fn()
    
    render(
      <StatsPanel 
        stats={mockStats} 
        onConsolidate={mockOnConsolidate} 
        isConsolidating={false} 
      />
    )
    
    // Ищем кнопку по тексту или по роли
    const consolidateButton = screen.getByRole('button') || 
                              screen.getByText(/consolidate/i)
    await user.click(consolidateButton)
    
    expect(mockOnConsolidate).toHaveBeenCalledTimes(1)
  })

  it('блокирует кнопку консолидации во время процесса', () => {
    const mockOnConsolidate = vi.fn()
    
    render(
      <StatsPanel 
        stats={mockStats} 
        onConsolidate={mockOnConsolidate} 
        isConsolidating={true} 
      />
    )
    
    const consolidateButton = screen.getByRole('button') || 
                              screen.getByText(/consolidate/i)
    expect(consolidateButton).toBeDisabled()
  })
})


import '@testing-library/jest-dom'
import { expect, afterEach } from 'vitest'
import { cleanup } from '@testing-library/react'

// Очистка после каждого теста
afterEach(() => {
  cleanup()
})

// Моки для window.matchMedia (используется некоторыми библиотеками)
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
})

// Мок для scrollIntoView
if (typeof Element !== 'undefined') {
  Element.prototype.scrollIntoView = vi.fn(() => {})
}


import { fireEvent, render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, beforeEach, expect, test } from 'vitest'
import { LocaleProvider } from '../i18n/LocaleProvider'
import { Shell } from './Shell'

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/?lang=en#/discover')
})
afterEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/')
})

test('language control switches global shell copy and persists selection', () => {
  render(<LocaleProvider><MemoryRouter><Shell><div>content</div></Shell></MemoryRouter></LocaleProvider>)
  expect(screen.getByRole('navigation', { name: 'Primary navigation' })).toBeInTheDocument()
  expect(screen.getByText(/Observational study/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button', { name: 'Korean' }))
  expect(screen.getByRole('navigation', { name: '주요 메뉴' })).toBeInTheDocument()
  expect(screen.getByText(/관찰 연구/)).toBeInTheDocument()
  expect(localStorage.getItem('mv-analyzer-locale')).toBe('ko')
  expect(window.location.hash).toBe('#/discover')
})


test('shell exposes Analyze and the public GitHub source link', () => {
  render(<LocaleProvider><MemoryRouter><Shell><div>content</div></Shell></MemoryRouter></LocaleProvider>)

  expect(screen.getByRole('link', { name: 'Analyze' })).toHaveAttribute('href', '/analyze')
  const source = screen.getByRole('link', { name: 'Open public source on GitHub' })
  expect(source).toHaveAttribute('href', 'https://github.com/writingdeveloper/mv-analyzer')
  expect(source).toHaveAttribute('target', '_blank')
  expect(source).toHaveTextContent('GitHub')
})

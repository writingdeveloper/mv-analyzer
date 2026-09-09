import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, beforeEach, expect, test } from 'vitest'
import { LocaleProvider, useLocale } from './LocaleProvider'

function Probe() {
  const { locale, setLocale, t } = useLocale()
  return <div>
    <span data-testid="locale">{locale}</span>
    <span>{t('language.switch')}</span>
    <button type="button" onClick={() => setLocale(locale === 'en' ? 'ko' : 'en')}>toggle</button>
  </div>
}

beforeEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/?lang=en#/discover')
})

afterEach(() => {
  localStorage.clear()
  window.history.replaceState({}, '', '/')
})

test('provider honors query locale and updates document language', () => {
  render(<LocaleProvider><Probe /></LocaleProvider>)
  expect(screen.getByTestId('locale')).toHaveTextContent('en')
  expect(document.documentElement.lang).toBe('en')
  expect(screen.getByText('Language')).toBeInTheDocument()
})

test('manual switch persists, updates query, and preserves hash route', () => {
  render(<LocaleProvider><Probe /></LocaleProvider>)
  fireEvent.click(screen.getByRole('button', { name: 'toggle' }))
  expect(screen.getByTestId('locale')).toHaveTextContent('ko')
  expect(document.documentElement.lang).toBe('ko')
  expect(localStorage.getItem('mv-analyzer-locale')).toBe('ko')
  expect(window.location.search).toBe('?lang=ko')
  expect(window.location.hash).toBe('#/discover')
})

import { describe, expect, test } from 'vitest'
import { resolveLocale } from './locale'

describe('resolveLocale', () => {
  test('query parameter wins over saved and browser preferences', () => {
    expect(resolveLocale({ search: '?lang=en', stored: 'ko', languages: ['ko-KR'] })).toBe('en')
    expect(resolveLocale({ search: '?lang=ko', stored: 'en', languages: ['en-US'] })).toBe('ko')
  })

  test('saved locale wins when query has no supported locale', () => {
    expect(resolveLocale({ search: '', stored: 'ko', languages: ['en-US'] })).toBe('ko')
    expect(resolveLocale({ search: '?lang=fr', stored: 'en', languages: ['ko-KR'] })).toBe('en')
  })

  test('browser language chooses Korean only for Korean preferences', () => {
    expect(resolveLocale({ search: '', stored: null, languages: ['ko-KR', 'en-US'] })).toBe('ko')
    expect(resolveLocale({ search: '', stored: null, languages: ['en-US'] })).toBe('en')
    expect(resolveLocale({ search: '', stored: null, languages: ['fr-FR'] })).toBe('en')
  })
})

import { isLocale, type Locale } from './types'

export interface ResolveLocaleInput {
  search: string
  stored: string | null
  languages: readonly string[]
}

export function resolveLocale({ search, stored, languages }: ResolveLocaleInput): Locale {
  const query = new URLSearchParams(search).get('lang')
  if (isLocale(query)) return query
  if (isLocale(stored)) return stored
  if (languages.some((language) => language.toLowerCase().startsWith('ko'))) return 'ko'
  return 'en'
}

export function localeTag(locale: Locale) {
  return locale === 'ko' ? 'ko-KR' : 'en-US'
}

import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { localeTag, resolveLocale } from './locale'
import { LOCALE_STORAGE_KEY, type Locale } from './types'
import { translate, type MessageKey } from './messages'

export interface LocaleContextValue {
  locale: Locale
  setLocale: (locale: Locale) => void
  t: (key: MessageKey, vars?: Record<string, string | number>) => string
  number: (value: number, options?: Intl.NumberFormatOptions) => string
  integer: (value: number) => string
  date: (value: string | Date | null | undefined) => string
}

export function formatDateValue(value: string | Date | null | undefined, locale: Locale) {
  if (!value) return '–'
  const options: Intl.DateTimeFormatOptions = { year:'numeric', month:'short', day:'numeric' }
  let date: Date
  if (typeof value === 'string' && /^(\d{8}|\d{4}-\d{2}-\d{2})$/.test(value)) {
    const compact=value.replace(/-/g,'')
    const iso=`${compact.slice(0,4)}-${compact.slice(4,6)}-${compact.slice(6,8)}`
    date=new Date(`${iso}T00:00:00Z`)
    options.timeZone='UTC' // A calendar label is not an instant to shift into another timezone.
    if(Number.isNaN(date.getTime())||date.toISOString().slice(0,10)!==iso) return '–'
  } else date=value instanceof Date?value:new Date(value)
  if(Number.isNaN(date.getTime())) return '–'
  return new Intl.DateTimeFormat(localeTag(locale),options).format(date)
}

export function readSavedLocale(): string | null {
  try { return window.localStorage.getItem(LOCALE_STORAGE_KEY) } catch { return null }
}

export function saveLocale(locale: Locale): void {
  try { window.localStorage.setItem(LOCALE_STORAGE_KEY,locale) } catch { /* Query link remains usable without storage. */ }
}

const fallback: LocaleContextValue = {
  locale: 'ko',
  setLocale: () => undefined,
  t: (key, vars) => translate('ko', key, vars),
  number: (value, options) => new Intl.NumberFormat('ko-KR', options).format(value),
  integer: (value) => new Intl.NumberFormat('ko-KR', { maximumFractionDigits: 0 }).format(value),
  date: (value) => formatDateValue(value, 'ko'),
}

const LocaleContext = createContext<LocaleContextValue>(fallback)

function browserLanguages() {
  if (typeof navigator === 'undefined') return [] as string[]
  return navigator.languages?.length ? [...navigator.languages] : navigator.language ? [navigator.language] : []
}

export function LocaleProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => {
    if (typeof window === 'undefined') return 'en'
    return resolveLocale({
      search: window.location.search,
      stored: readSavedLocale(),
      languages: browserLanguages(),
    })
  })

  useEffect(() => {
    document.documentElement.lang = locale
  }, [locale])

  const setLocale = (next: Locale) => {
    setLocaleState(next)
    if (typeof window === 'undefined') return
    saveLocale(next)
    const url = new URL(window.location.href)
    url.searchParams.set('lang', next)
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`)
  }

  const value = useMemo<LocaleContextValue>(() => ({
    locale,
    setLocale,
    t: (key, vars) => translate(locale, key, vars),
    number: (number, options) => new Intl.NumberFormat(localeTag(locale), options).format(number),
    integer: (number) => new Intl.NumberFormat(localeTag(locale), { maximumFractionDigits: 0 }).format(number),
    date: (date) => formatDateValue(date, locale),
  }), [locale])

  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>
}

export function useLocale() {
  return useContext(LocaleContext)
}

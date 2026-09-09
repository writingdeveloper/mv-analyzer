export type Locale = 'ko' | 'en'

export const SUPPORTED_LOCALES: readonly Locale[] = ['ko', 'en'] as const
export const LOCALE_STORAGE_KEY = 'mv-analyzer-locale'

export function isLocale(value: unknown): value is Locale {
  return value === 'ko' || value === 'en'
}

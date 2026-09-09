import type { FeatureMeta } from '../data/schema'
import type { Locale } from './types'

const SPECIAL_FEATURE_LABELS: Record<string, { ko: string; en: string }> = {
  view_per_sub: { ko: '조회/구독 비율', en: 'Views / subscribers' },
}

export function featureLabel(feature: FeatureMeta, locale: Locale) {
  return feature.labels?.[locale] || feature.label || feature.id
}

export function featureLabelById(id: string, locale: Locale, features: FeatureMeta[]) {
  const feature = features.find((item) => item.id === id)
  if (feature) return featureLabel(feature, locale)
  return SPECIAL_FEATURE_LABELS[id]?.[locale] ?? id
}

export function domainLabel(domain: string) {
  if (domain === 'vocaloid') return 'Vocaloid'
  if (domain === 'kpop') return 'K-pop'
  return domain
}

export function groupLabel(group: string, locale: Locale) {
  if (group === 'top') return locale === 'ko' ? '상위' : 'Top'
  if (group === 'bottom') return locale === 'ko' ? '하위' : 'Bottom'
  return group
}

export function experimentStateLabel(state: string, locale: Locale) {
  const table: Record<string, { ko: string; en: string }> = {
    pending_validation: { ko: '검증 대기', en: 'Pending validation' },
    validated: { ko: '검증 완료', en: 'Validated' },
    replicated: { ko: '재현 완료', en: 'Replicated' },
    blocked: { ko: '평가 보류', en: 'Not evaluated' },
    experimental: { ko: '실험 단계', en: 'Experimental' },
  }
  return table[state]?.[locale] ?? state
}

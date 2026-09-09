import { expect, test } from 'vitest'
import type { FeatureMeta } from '../data/schema'
import { domainLabel, experimentStateLabel, featureLabel, featureLabelById, groupLabel } from './research'

const feature = {
  id: 'scene_cuts_per_minute',
  label: '분당 컷 수',
  labels: { ko: '분당 컷 수', en: 'Cuts per minute' },
  kind: 'numeric',
  status: 'formal',
} as FeatureMeta

test('research display labels follow locale while canonical ids stay unchanged', () => {
  expect(featureLabel(feature, 'ko')).toBe('분당 컷 수')
  expect(featureLabel(feature, 'en')).toBe('Cuts per minute')
  expect(featureLabelById(feature.id, 'en', [feature])).toBe('Cuts per minute')
  expect(feature.id).toBe('scene_cuts_per_minute')
})

test('domain, group, and experiment labels are presentation-only', () => {
  expect(domainLabel('vocaloid')).toBe('Vocaloid')
  expect(groupLabel('top', 'ko')).toBe('상위')
  expect(groupLabel('top', 'en')).toBe('Top')
  expect(experimentStateLabel('pending_validation', 'en')).toBe('Pending validation')
  expect(featureLabelById('view_per_sub', 'en', [])).toBe('Views / subscribers')
})

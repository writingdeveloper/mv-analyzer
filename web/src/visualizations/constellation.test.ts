import { describe, expect, test } from 'vitest'
import type { SpacePoint } from '../data/schema'
import { buildNeighborEdges, constellationProfile, scenePosition, visualState } from './constellation'

const points: SpacePoint[] = [
  { id: 'focus', title: 'Focus', channel: 'A', domain: 'vocaloid', group: 'top', pca: [0, 0, 0] },
  { id: 'near', title: 'Near', channel: 'B', domain: 'vocaloid', group: 'bottom', pca: [0.1, 0, 0] },
  { id: 'mid', title: 'Mid', channel: 'C', domain: 'kpop', group: 'top', pca: [0.4, 0, 0] },
  { id: 'far', title: 'Far', channel: 'D', domain: 'kpop', group: 'bottom', pca: [1.2, 0, 0] },
]

describe('Data Constellation geometry', () => {
  test('uses one uniform scale for PCA axes without group separation', () => {
    expect(scenePosition([1, -2, 0.5], 1.6)).toEqual([1.6, -3.2, 0.8])
    expect(scenePosition([-1, 2, -0.5], 1.6)).toEqual([-1.6, 3.2, -0.8])
  })

  test('connects only the selected MV to its nearest neighbors', () => {
    expect(buildNeighborEdges(points, 'focus', 2)).toEqual([
      { sourceId: 'focus', targetId: 'near', distance: 0.1 },
      { sourceId: 'focus', targetId: 'mid', distance: 0.4 },
    ])
  })


  test('uses raw PCA scores for research neighbor distance when available', () => {
    const scored: SpacePoint[] = [
      { id: 'focus', title: 'Focus', channel: 'A', domain: 'vocaloid', group: 'top', pca: [0, 0, 0], score: [0, 0, 0] },
      { id: 'display-near', title: 'Display near', channel: 'B', domain: 'vocaloid', group: 'top', pca: [0.1, 0, 0], score: [10, 0, 0] },
      { id: 'score-near', title: 'Score near', channel: 'C', domain: 'kpop', group: 'bottom', pca: [0.8, 0, 0], score: [0.2, 0, 0] },
    ]
    expect(buildNeighborEdges(scored, 'focus', 1)[0].targetId).toBe('score-near')
  })

  test('dims unrelated points while keeping selected and neighbors readable', () => {
    expect(visualState('focus', 'focus', new Set(['near']))).toEqual({ selected: true, neighbor: false, opacity: 1, scale: 1.7 })
    expect(visualState('near', 'focus', new Set(['near']))).toEqual({ selected: false, neighbor: true, opacity: 0.92, scale: 1.18 })
    expect(visualState('far', 'focus', new Set(['near']))).toEqual({ selected: false, neighbor: false, opacity: 0.18, scale: 0.88 })
  })
})

describe('Data Constellation performance profile', () => {
  test('keeps desktop atmosphere rich while respecting reduced motion', () => {
    expect(constellationProfile({ width: 1280, devicePixelRatio: 2, reducedMotion: false })).toEqual({
      autoRotate: true,
      particleCount: 420,
      pixelRatio: 2,
      sphereSegments: 18,
    })
    expect(constellationProfile({ width: 1280, devicePixelRatio: 2, reducedMotion: true })).toEqual({
      autoRotate: false,
      particleCount: 0,
      pixelRatio: 2,
      sphereSegments: 18,
    })
  })

  test('reduces renderer cost on mobile', () => {
    expect(constellationProfile({ width: 390, devicePixelRatio: 3, reducedMotion: false })).toEqual({
      autoRotate: true,
      particleCount: 120,
      pixelRatio: 1.25,
      sphereSegments: 12,
    })
  })
})

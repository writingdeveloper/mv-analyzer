import type { SpacePoint } from '../data/schema'

export type Vec3 = [number, number, number]

export interface NeighborEdge {
  sourceId: string
  targetId: string
  distance: number
}

export function scenePosition(pca: Vec3, scale = 1.6): Vec3 {
  return [pca[0] * scale, pca[1] * scale, pca[2] * scale]
}

export function buildNeighborEdges(points: SpacePoint[], selectedId: string | undefined, limit = 6): NeighborEdge[] {
  if (!selectedId || limit <= 0) return []
  const source = points.find((point) => point.id === selectedId)
  if (!source) return []
  const sourceVector = source.score ?? source.pca
  return points
    .filter((point) => point.id !== selectedId)
    .map((point) => {
      const vector = point.score ?? point.pca
      return {
        sourceId: selectedId,
        targetId: point.id,
        distance: Math.hypot(
          vector[0] - sourceVector[0],
          vector[1] - sourceVector[1],
          vector[2] - sourceVector[2],
        ),
      }
    })
    .sort((a, b) => a.distance - b.distance || a.targetId.localeCompare(b.targetId))
    .slice(0, limit)
}

export function visualState(id: string, selectedId?: string, neighborIds = new Set<string>()) {
  if (!selectedId) return { selected: false, neighbor: false, opacity: 0.9, scale: 1 }
  if (id === selectedId) return { selected: true, neighbor: false, opacity: 1, scale: 1.7 }
  if (neighborIds.has(id)) return { selected: false, neighbor: true, opacity: 0.92, scale: 1.18 }
  return { selected: false, neighbor: false, opacity: 0.18, scale: 0.88 }
}

export function constellationProfile({
  width,
  devicePixelRatio,
  reducedMotion,
}: {
  width: number
  devicePixelRatio: number
  reducedMotion: boolean
}) {
  const mobile = width < 640
  return {
    autoRotate: !reducedMotion,
    particleCount: reducedMotion ? 0 : mobile ? 120 : 420,
    pixelRatio: Math.min(devicePixelRatio || 1, mobile ? 1.25 : 2),
    sphereSegments: mobile ? 12 : 18,
  }
}

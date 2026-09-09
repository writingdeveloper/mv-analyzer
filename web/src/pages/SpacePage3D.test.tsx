import { fireEvent, render, screen } from '@testing-library/react'
import { vi } from 'vitest'
import type { SpaceData, SpacePoint } from '../data/schema'

vi.mock('../visualizations/Pca3D', () => ({
  default: ({
    points,
    selectedId,
    showNeighbors,
    autoRotate,
    resetKey,
    explainedVariance,
    onSelect,
  }: {
    points: SpacePoint[]
    selectedId?: string
    showNeighbors: boolean
    autoRotate: boolean
    resetKey: number
    explainedVariance: number[]
    onSelect: (point: SpacePoint) => void
  }) => (
    <div
      data-testid="mock-pca3d"
      data-selected={selectedId ?? ''}
      data-neighbors={String(showNeighbors)}
      data-rotate={String(autoRotate)}
      data-reset={String(resetKey)}
      data-variance={explainedVariance.join(',')}
    >
      <button type="button" onClick={() => onSelect(points[0])}>3D 점 선택</button>
    </div>
  ),
}))

import { SpacePage } from './SpacePage'

const data = {
  features: ['a', 'b'],
  explained_variance_pct: [50.7, 15, 9.8],
  normalization: { method: 'zscore', imputation: 'median', coordinate_scaling: 'max_abs_per_pc' },
  loadings: [{ component: 'PC1', items: [{ feature: 'a', loading: 0.8 }] }, { component: 'PC2', items: [{ feature: 'b', loading: -0.6 }] }, { component: 'PC3', items: [{ feature: 'a', loading: 0.2 }] }],
  points: [
    { id: 'a', title: 'Alpha MV', channel: 'A', domain: 'vocaloid', group: 'top', pca: [-0.4, 0.2, 0] },
    { id: 'b', title: 'Beta MV', channel: 'B', domain: 'kpop', group: 'bottom', pca: [0.5, -0.1, 0.1] },
  ],
} as SpaceData

test('exposes Data Constellation controls and forwards focus state to the lazy 3D view', async () => {
  render(<SpacePage data={data} />)
  fireEvent.click(screen.getByRole('button', { name: '3D' }))

  const view = await screen.findByTestId('mock-pca3d')
  expect(screen.getByText('Data Constellation')).toBeInTheDocument();expect(screen.getByText(/Z-SCORED FEATURES/)).toBeInTheDocument();expect(screen.getByText(/^PC1 · a$/)).toBeInTheDocument()
  expect(view).toHaveAttribute('data-neighbors', 'true')
  expect(view).toHaveAttribute('data-rotate', 'true')
  expect(view).toHaveAttribute('data-variance', '50.7,15,9.8')

  fireEvent.click(screen.getByRole('button', { name: '자동 회전 끄기' }))
  expect(view).toHaveAttribute('data-rotate', 'false')
  expect(screen.getByRole('button', { name: '자동 회전 켜기' })).toBeInTheDocument()

  fireEvent.click(screen.getByRole('button', { name: '이웃 연결 끄기' }))
  expect(view).toHaveAttribute('data-neighbors', 'false')

  fireEvent.click(screen.getByRole('button', { name: '3D 점 선택' }))
  expect(view).toHaveAttribute('data-selected', 'a')

  expect(view).toHaveAttribute('data-reset', '0')
  fireEvent.click(screen.getByRole('button', { name: '뷰 초기화' }))
  expect(view).toHaveAttribute('data-reset', '1')
})

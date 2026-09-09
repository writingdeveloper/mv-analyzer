export interface StandardizedValue {
  raw: number
  percentile: number
  z: number
  mean: number
  sd: number
}

export function standardize(values: number[], value: number) {
  const finite = values.filter(Number.isFinite)
  if (!finite.length) return { mean: 0, sd: 0, z: 0 }
  const mean = finite.reduce((sum, item) => sum + item, 0) / finite.length
  const variance = finite.reduce((sum, item) => sum + (item - mean) ** 2, 0) / finite.length
  const sd = Math.sqrt(variance)
  return { mean, sd, z: sd === 0 ? 0 : (value - mean) / sd }
}

export function describeStandardizedValue(values: number[], value: number): StandardizedValue {
  const finite = values.filter(Number.isFinite).slice().sort((a, b) => a - b)
  const standardized = standardize(finite, value)
  const atOrBelow = finite.filter((item) => item <= value).length
  return {
    raw: value,
    percentile: finite.length ? Math.round((atOrBelow / finite.length) * 1000) / 10 : 0,
    ...standardized,
  }
}

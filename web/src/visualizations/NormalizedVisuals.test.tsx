import { render, screen } from '@testing-library/react'
import type { VideoRow } from '../data/schema'
import { FeatureDistribution } from './FeatureDistribution'
import { ScatterPlot } from './ScatterPlot'

const reference=[0,10,20,30].map((value,index)=>({video_id:`r${index}`,title:`R${index}`,channel:'R',domain:'vocaloid',group:index%2?'top':'bottom',view_count:null,subscriber_count:null,view_per_sub:null,upload_date:null,features:{x:value,y:30-value}})) as VideoRow[]
const shown=reference.slice(1,3)

test('distribution places points in reference z-score space while retaining raw and percentile context',()=>{
  render(<FeatureDistribution videos={shown} reference={reference} feature="x" label="테스트 지표" onSelect={()=>{}} />)
  expect(screen.getByText(/표준화 z-score/)).toBeInTheDocument()
  expect(screen.getByTitle(/R2.*raw 20.*z \+0\.45.*75 percentile/i)).toBeInTheDocument()
})

test('scatter exposes a standardized feature space with human-readable axis labels',()=>{
  render(<ScatterPlot videos={shown} reference={reference} xKey="x" yKey="y" xLabel="X 지표" yLabel="Y 지표" onSelect={()=>{}} />)
  expect(screen.getByText(/STANDARDIZED FEATURE SPACE/)).toBeInTheDocument()
  expect(screen.getByRole('img',{name:/X 지표.*Y 지표.*z-score/i})).toBeInTheDocument()
})

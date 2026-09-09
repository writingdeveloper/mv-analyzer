import { fireEvent, render, screen } from '@testing-library/react'
import { beforeEach, expect, test, vi } from 'vitest'
import type { ExperimentsData, ManifestData, MethodologyData, SpaceData, SpacePoint, VideoRow } from '../data/schema'
import { LocaleProvider } from '../i18n/LocaleProvider'

vi.mock('../visualizations/Pca3D',()=>({default:({points}:{points:SpacePoint[]})=><div data-testid="mock-pca3d">{points.length} points</div>}))

import { SpacePage } from './SpacePage'
import { SamplesPage } from './SamplesPage'
import { MethodologyPage } from './MethodologyPage'

beforeEach(()=>{localStorage.clear();window.history.replaceState({},'','/?lang=en')})
const english=(node:React.ReactNode)=><LocaleProvider>{node}</LocaleProvider>

const space={features:['scene_cuts_per_minute','scene_avg_saturation'],explained_variance_pct:[50.7,15,9.8],normalization:{method:'zscore',imputation:'median',coordinate_scaling:'max_abs_per_pc'},loadings:[{component:'PC1',items:[{feature:'scene_cuts_per_minute',label:'분당 컷 수',labels:{ko:'분당 컷 수',en:'Cuts per minute'},loading:.8}]},{component:'PC2',items:[{feature:'scene_avg_saturation',label:'화면 채도',labels:{ko:'화면 채도',en:'Frame saturation'},loading:-.6}]},{component:'PC3',items:[{feature:'scene_cuts_per_minute',label:'분당 컷 수',labels:{ko:'분당 컷 수',en:'Cuts per minute'},loading:.2}]}],points:[{id:'a',title:'Alpha MV',channel:'A',domain:'vocaloid',group:'top',pca:[-.4,.2,0],score:[-1.2,.4,.1]},{id:'b',title:'Beta MV',channel:'B',domain:'kpop',group:'bottom',pca:[.5,-.1,.1],score:[.8,-.2,.3]}]} as SpaceData
const videos=[{video_id:'a',title:'Alpha',channel:'A',domain:'vocaloid',group:'top',view_count:100,subscriber_count:10,view_per_sub:10,upload_date:'20260101',features:{}},{video_id:'b',title:'Beta',channel:'B',domain:'kpop',group:'bottom',view_count:50,subscriber_count:10,view_per_sub:5,upload_date:'20260102',features:{}}] as VideoRow[]
const methodology={study:{sampling:'조회수/구독자수 비율의 상·하위 극단 비교',window:'2025-04 ~ 2026-04',domains:['vocaloid','kpop'],current_sample:{vocaloid:{total:50,top:25,bottom:25},kpop:{total:50,top:25,bottom:25}},expansion:{vocaloid:{target_per_group:40,eligible_population:495,max_top:40,max_bottom:40,require_mv_marker:false,channel_cap:2,feasible:true},kpop:{target_per_group:40,eligible_population:998,max_top:38,max_bottom:23,require_mv_marker:true,channel_cap:2,feasible:false}}},pipeline:['PySceneDetect','Qwen2.5-VL'],reliability_baseline:{n:52,categorical:{mood:{accuracy:.519,kappa:.427}},num_characters:{exact:.846,within1:.942,spearman_rho:.805}},feature_policy:{formal_count:42,experimental_count:3},caveats:['극단 그룹 설계 특성상 효과크기가 과대추정될 수 있습니다.','제작 투자 규모와 채널 규모가 시각·공개 전략 feature와 함께 변할 수 있습니다.','K-pop 40/40 확장은 현재 MV 표기·채널당 2편 규칙을 유지하면 모집단 확장이 더 필요합니다.']} as MethodologyData
const experiments={items:[{id:'qwen3-vl-blind52',label:'Qwen3-VL blind-52 A/B',state:'pending_validation',status_class:'pending'}],note:'후보 모델/측정기는 고정 표본 A/B 검증 후에만 정식 결과로 승격됩니다.'} as ExperimentsData
const manifest={schema_version:1,snapshot_id:'snap123',generated_at:'2026-07-21',git_commit:'abcdef123456789',source:'dataset/features_100mv.csv',domains:['kpop','vocaloid'],files:{}} as ManifestData

test('Space localizes research interpretation and 3D controls without changing PCA data',async()=>{
  render(english(<SpacePage data={space}/>))
  expect(screen.getByText(/Place 100 music videos/)).toBeInTheDocument()
  expect(screen.getAllByText(/Cuts per minute/).length).toBeGreaterThan(0)
  expect(screen.getByText(/Neighbor distance uses raw PCA scores/)).toBeInTheDocument()
  fireEvent.click(screen.getByRole('button',{name:'3D'}))
  expect(await screen.findByText('Hide neighbor links')).toBeInTheDocument()
  expect(screen.getByText('Disable auto-rotate')).toBeInTheDocument()
  expect(screen.getByText('Reset view')).toBeInTheDocument()
})

test('Samples explains rule-preserving expansion in English',()=>{
  render(english(<SamplesPage videos={videos} methodology={methodology}/>))
  expect(screen.getByText(/Before interpreting results/)).toBeInTheDocument()
  expect(screen.getByText(/rules are not relaxed to force the target/)).toBeInTheDocument()
  expect(screen.getByLabelText('Sample search')).toBeInTheDocument()
})

test('Methodology localizes sampling, validation, and caveats in English',()=>{
  render(english(<MethodologyPage methodology={methodology} experiments={experiments} manifest={manifest}/>))
  expect(screen.getByText(/Before trusting the charts/)).toBeInTheDocument()
  expect(screen.getByText(/Comparison of high and low extremes/)).toBeInTheDocument()
  expect(screen.getByText(/extreme-group design can overestimate effect sizes/)).toBeInTheDocument()
  expect(screen.getByText(/Candidate models and measurements are promoted/)).toBeInTheDocument()
})

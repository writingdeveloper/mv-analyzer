import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, expect, test } from 'vitest'
import type { CorrelationsData, DomainsData, FeatureMeta, ManifestData, OverviewData, VideoRow } from '../data/schema'
import { LocaleProvider } from '../i18n/LocaleProvider'
import { OverviewPage } from './OverviewPage'
import { DiscoverPage } from './DiscoverPage'
import { ComparePage } from './ComparePage'

const effect={id:'scene_cuts_per_minute',label:'분당 컷 수',labels:{ko:'분당 컷 수',en:'Cuts per minute'},median_top:16.2,median_bottom:7.3,delta:0.61,q:0.01,significant:true}
const overview={video_count:100,domain_counts:{vocaloid:{total:50,top:25,bottom:25},kpop:{total:50,top:25,bottom:25}},headline_effects:{vocaloid:[effect],kpop:[]},reliability_baseline:null,generated_at:'2026-07-21T01:36:19',causal_warning:'관찰된 차이는 연관성을 보여주며 인과효과를 증명하지 않습니다.'} as OverviewData
const domains={vocaloid:{n_top:25,n_bottom:25,numeric:[effect],binary:[],categorical:[]},kpop:{n_top:25,n_bottom:25,numeric:[],binary:[],categorical:[]}} as DomainsData
const manifest={schema_version:1,snapshot_id:'snapshot1234',generated_at:'2026-07-21T01:36:19',git_commit:'abcdef1234567890',source:'dataset/features_100mv.csv',domains:['kpop','vocaloid'],files:{}} as ManifestData
const videos=[{video_id:'a',title:'Alpha MV',channel:'Chan A',domain:'vocaloid',group:'top',view_count:100,subscriber_count:10,view_per_sub:10,upload_date:'20260101',features:{scene_cuts_per_minute:20,audio_bpm:130}},{video_id:'b',title:'Beta MV',channel:'Chan B',domain:'vocaloid',group:'bottom',view_count:50,subscriber_count:10,view_per_sub:5,upload_date:'20260102',features:{scene_cuts_per_minute:5,audio_bpm:90}}] as VideoRow[]
const features=[{id:'scene_cuts_per_minute',label:'분당 컷 수',labels:{ko:'분당 컷 수',en:'Cuts per minute'},kind:'numeric',status:'formal'},{id:'audio_bpm',label:'BPM',labels:{ko:'BPM',en:'BPM'},kind:'numeric',status:'formal'}] as FeatureMeta[]
const correlations={method:'spearman',domains:{vocaloid:{features:['scene_cuts_per_minute','audio_bpm'],matrix:[[1,.5],[.5,1]]}}} as CorrelationsData

beforeEach(()=>{localStorage.clear();window.history.replaceState({},'','/?lang=en')})

const english=(node:React.ReactNode)=><LocaleProvider>{node}</LocaleProvider>

test('Overview renders English research copy and bilingual effect labels',()=>{
  render(english(<OverviewPage overview={overview} domains={domains} manifest={manifest}/>))
  expect(screen.getByText(/How do high- and low-performing MVs/)).toBeInTheDocument()
  expect(screen.getAllByText('Cuts per minute').length).toBeGreaterThanOrEqual(1)
  expect(screen.getByText(/Observed differences show associations/)).toBeInTheDocument()
})

test('Discover renders English feature labels and standardized chart explanations',()=>{
  render(english(<MemoryRouter><DiscoverPage videos={videos} features={features} correlations={correlations}/></MemoryRouter>))
  expect(screen.getByText(/Move a feature and/)).toBeInTheDocument()
  expect(screen.getAllByText('Cuts per minute').length).toBeGreaterThanOrEqual(1)
  expect(screen.getByText(/Full 100-video reference/)).toBeInTheDocument()
  expect(screen.getByText(/opposite direction/)).toBeInTheDocument()
})

test('Compare renders English controls and percentile feature labels',()=>{
  render(english(<MemoryRouter initialEntries={['/?ids=a,b']}><ComparePage videos={videos} features={features}/></MemoryRouter>))
  expect(screen.getByText(/Put multiple MVs/)).toBeInTheDocument()
  expect(screen.getByText('Cuts per minute')).toBeInTheDocument()
  expect(screen.getByText(/Where does each video sit/)).toBeInTheDocument()
})

import { render, screen } from '@testing-library/react'
import { OverviewPage } from './OverviewPage'

const overview = { video_count:100, domain_counts:{vocaloid:{total:50,top:25,bottom:25},kpop:{total:50,top:25,bottom:25}}, headline_effects:{vocaloid:[{id:'scene_cuts_per_minute',label:'분당 컷 수',median_top:16.2,median_bottom:7.3,delta:0.61,q:0.01,significant:true}],kpop:[]}, reliability_baseline:null, generated_at:'2026-07-21T01:36:19', causal_warning:'관찰된 차이는 연관성을 보여주며 인과효과를 증명하지 않습니다.' }
const domains = { vocaloid:{n_top:25,n_bottom:25,numeric:overview.headline_effects.vocaloid,binary:[],categorical:[]}, kpop:{n_top:25,n_bottom:25,numeric:[],binary:[],categorical:[]} }
const manifest = { schema_version:1,snapshot_id:'snapshot1234',generated_at:'2026-07-21T01:36:19',git_commit:'abcdef1234567890',source:'dataset/features_100mv.csv',domains:['kpop','vocaloid'],files:{} }

test('renders the study headline, effect size, legend, caveat and build metadata',()=>{ render(<OverviewPage overview={overview} domains={domains} manifest={manifest}/>); const summary=screen.getByRole('region',{name:'연구 요약'}); expect(summary).toHaveTextContent('100'); expect(screen.getAllByText('분당 컷 수').length).toBeGreaterThanOrEqual(1); expect(screen.getByText('상위 그룹')).toBeInTheDocument(); expect(screen.getByText('하위 그룹')).toBeInTheDocument(); expect(screen.getByText(/인과효과를 증명하지 않습니다/)).toBeInTheDocument(); expect(screen.getByText(/abcdef1234/)).toBeInTheDocument(); })

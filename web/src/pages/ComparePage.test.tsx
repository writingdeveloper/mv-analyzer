import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { ComparePage } from './ComparePage'
import type { FeatureMeta, VideoRow } from '../data/schema'
const videos=[{video_id:'a',title:'Alpha MV',channel:'A',domain:'vocaloid',group:'top',view_count:100,subscriber_count:10,view_per_sub:10,upload_date:null,features:{scene_cuts_per_minute:20}},{video_id:'b',title:'Beta MV',channel:'B',domain:'vocaloid',group:'bottom',view_count:50,subscriber_count:10,view_per_sub:5,upload_date:null,features:{scene_cuts_per_minute:5}}] as VideoRow[]
const features=[{id:'scene_cuts_per_minute',label:'분당 컷 수',kind:'numeric',status:'formal'}] as FeatureMeta[]
test('renders two selected videos and percentile comparison',()=>{render(<MemoryRouter initialEntries={['/?ids=a,b']}><ComparePage videos={videos} features={features}/></MemoryRouter>);expect(screen.getAllByText('Alpha MV').length).toBeGreaterThan(0);expect(screen.getAllByText('Beta MV').length).toBeGreaterThan(0);expect(screen.getByText('분당 컷 수')).toBeInTheDocument();expect(screen.getAllByText(/percentile/).length).toBeGreaterThan(0)})

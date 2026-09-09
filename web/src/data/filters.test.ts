import { filterVideos, numericValue, percentileRank } from './filters'
import type { VideoRow } from './schema'
const rows=[
 {video_id:'a',title:'Miku Signal',channel:'Alpha',domain:'vocaloid',group:'top',view_count:1,subscriber_count:1,view_per_sub:3,upload_date:null,features:{audio_bpm:120}},
 {video_id:'b',title:'Night MV',channel:'Beta',domain:'kpop',group:'bottom',view_count:1,subscriber_count:1,view_per_sub:1,upload_date:null,features:{audio_bpm:90}},
] as VideoRow[]
test('filters by domain group and query',()=>{expect(filterVideos(rows,{domain:'vocaloid',group:'all',query:'miku'}).map(x=>x.video_id)).toEqual(['a']);expect(filterVideos(rows,{domain:'all',group:'bottom',query:'beta'}).map(x=>x.video_id)).toEqual(['b'])})
test('reads nested numeric features and identity metrics',()=>{expect(numericValue(rows[0],'audio_bpm')).toBe(120);expect(numericValue(rows[0],'view_per_sub')).toBe(3)})
test('computes a stable percentile rank',()=>{expect(percentileRank([1,2,3,4],3)).toBe(75);expect(percentileRank([],3)).toBeNull()})

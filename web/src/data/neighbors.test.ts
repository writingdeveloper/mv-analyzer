import { nearestNeighbors } from './neighbors'
import type { SpacePoint } from './schema'
const points=[{id:'a',title:'A',channel:'A',domain:'vocaloid',group:'top',pca:[0,0,0]},{id:'b',title:'B',channel:'B',domain:'vocaloid',group:'top',pca:[.1,0,0]},{id:'c',title:'C',channel:'C',domain:'kpop',group:'bottom',pca:[.2,0,0]},{id:'d',title:'D',channel:'D',domain:'kpop',group:'bottom',pca:[.9,0,0]}] as SpacePoint[]
test('returns nearest points in euclidean PCA distance order',()=>{expect(nearestNeighbors(points,'a',2).map(x=>x.id)).toEqual(['b','c'])})
test('returns empty for unknown target',()=>expect(nearestNeighbors(points,'x',3)).toEqual([]))

test('prefers raw PCA score distance over display-normalized coordinates when available',()=>{
  const scored=[
    {id:'a',title:'A',channel:'A',domain:'vocaloid',group:'top',pca:[0,0,0],score:[0,0,0]},
    {id:'b',title:'B',channel:'B',domain:'vocaloid',group:'top',pca:[.1,0,0],score:[10,0,0]},
    {id:'c',title:'C',channel:'C',domain:'kpop',group:'bottom',pca:[.9,0,0],score:[.2,0,0]},
  ] as SpacePoint[]
  expect(nearestNeighbors(scored,'a',1)[0].id).toBe('c')
})

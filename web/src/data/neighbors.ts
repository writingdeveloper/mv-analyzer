import type { SpacePoint } from './schema'
export type Neighbor=SpacePoint&{distance:number}
export function nearestNeighbors(points:SpacePoint[],id:string,limit=5):Neighbor[]{const target=points.find(p=>p.id===id);if(!target)return[];const targetVec=target.score??target.pca;return points.filter(p=>p.id!==id).map(p=>{const vec=p.score??p.pca;return {...p,distance:Math.sqrt(vec.reduce((sum,v,i)=>sum+(v-targetVec[i])**2,0))}}).sort((a,b)=>a.distance-b.distance||a.id.localeCompare(b.id)).slice(0,limit)}

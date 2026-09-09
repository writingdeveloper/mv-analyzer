import type { VideoRow } from './schema'
export type FilterState={domain:string;group:string;query:string}
export function filterVideos(rows:VideoRow[],f:FilterState){const q=f.query.trim().toLocaleLowerCase();return rows.filter(r=>(f.domain==='all'||r.domain===f.domain)&&(f.group==='all'||r.group===f.group)&&(!q||`${r.title} ${r.channel}`.toLocaleLowerCase().includes(q)))}
export function numericValue(row:VideoRow,key:string):number|null{const direct=(row as unknown as Record<string,unknown>)[key];const value=direct??row.features[key];return typeof value==='number'&&Number.isFinite(value)?value:null}
export function percentileRank(values:number[],value:number):number|null{const sorted=values.filter(Number.isFinite).slice().sort((a,b)=>a-b);if(!sorted.length||!Number.isFinite(value))return null;const atOrBelow=sorted.filter(v=>v<=value).length;return Math.round((atOrBelow/sorted.length)*1000)/10}
export function numericSeries(rows:VideoRow[],key:string){return rows.map(r=>numericValue(r,key)).filter((v):v is number=>v!==null)}

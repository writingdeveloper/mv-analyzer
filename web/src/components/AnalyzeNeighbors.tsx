import type { AnalyzeNeighbor } from '../data/analyzeReport'
import { useLocale } from '../i18n/LocaleProvider'

export function AnalyzeNeighbors({neighbors}:{neighbors:AnalyzeNeighbor[]}){
  const {t,number}=useLocale()
  if(!neighbors.length)return <div className="empty-state">{t('analyze.noNeighbors')}</div>
  return <ol className="analyze-neighbors">{neighbors.map((item,index)=><li key={item.video_id}>
    <span className="analyze-neighbor-rank">{String(index+1).padStart(2,'0')}</span>
    <div><a href={`https://www.youtube.com/watch?v=${item.video_id}`} target="_blank" rel="noreferrer"><b>{item.title}</b></a><small>{item.channel} · {item.domain} · {item.group.toUpperCase()}</small></div>
    <code>d={number(item.distance,{maximumFractionDigits:3})}</code>
  </li>)}</ol>
}

import type { ReactNode } from 'react'
export function StatCard({label,value,detail,accent}:{label:string;value:ReactNode;detail?:ReactNode;accent?:'top'|'bottom'|'neutral'}){
  return <article className={`stat-card ${accent?`stat-card--${accent}`:''}`}><span className="eyebrow">{label}</span><strong className="stat-card__value">{value}</strong>{detail&&<span className="stat-card__detail">{detail}</span>}</article>
}

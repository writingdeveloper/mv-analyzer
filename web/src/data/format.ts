export function formatNumber(value:number|null|undefined,digits=2){
  if(value==null || !Number.isFinite(value)) return '–'
  const abs=Math.abs(value)
  if(abs>=1_000_000) return new Intl.NumberFormat('ko-KR',{notation:'compact',maximumFractionDigits:1}).format(value)
  if(abs>=1000) return new Intl.NumberFormat('ko-KR',{maximumFractionDigits:0}).format(value)
  return value.toLocaleString('ko-KR',{maximumFractionDigits:digits})
}
export const shortCommit=(commit:string)=>commit==='unknown'?'unknown':commit.slice(0,10)
export const domainLabel=(domain:string)=>domain==='vocaloid'?'Vocaloid':domain==='kpop'?'K-pop':domain

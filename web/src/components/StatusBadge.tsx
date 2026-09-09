import { useLocale } from '../i18n/LocaleProvider'

export function StatusBadge({kind,label}:{kind:'formal'|'experimental'|'pending'|'replicated'|'blocked';label?:string}){
  const {t}=useLocale()
  const key=({formal:'status.formal',experimental:'status.experimental',pending:'status.pending',replicated:'status.replicated',blocked:'status.blocked'} as const)[kind]
  return <span className={`status-badge status-${kind}`}>{label??t(key)}</span>
}

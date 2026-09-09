import { useLocale } from '../i18n/LocaleProvider'

export function FilterBar({domain,group,query,onDomain,onGroup,onQuery}:{domain:string;group:string;query:string;onDomain:(v:string)=>void;onGroup:(v:string)=>void;onQuery:(v:string)=>void}){
  const {t}=useLocale()
  return <div className="filter-bar"><label>{t('common.domain')}<select aria-label={t('common.domain')} value={domain} onChange={e=>onDomain(e.target.value)}><option value="all">{t('common.all')}</option><option value="vocaloid">Vocaloid</option><option value="kpop">K-pop</option></select></label><label>{t('common.group')}<select aria-label={t('common.group')} value={group} onChange={e=>onGroup(e.target.value)}><option value="all">{t('common.all')}</option><option value="top">{t('common.top')}</option><option value="bottom">{t('common.bottom')}</option></select></label><label className="search-field">{t('common.videoSearch')}<input aria-label={t('common.videoSearch')} value={query} onChange={e=>onQuery(e.target.value)} placeholder={t('common.searchPlaceholder')}/></label></div>
}

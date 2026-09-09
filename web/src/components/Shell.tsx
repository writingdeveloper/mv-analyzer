import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useLocale } from '../i18n/LocaleProvider'

const nav=[['/','Overview'],['/discover','Discover'],['/space','MV Space'],['/compare','Compare'],['/analyze','Analyze'],['/samples','Samples'],['/methodology','Methodology']] as const

export function Shell({children}:{children:ReactNode}){
  const {locale,setLocale,t}=useLocale()
  return <div className="app-shell">
    <header className="topbar">
      <div className="brand"><span className="brand-mark" aria-hidden="true">M</span><div><b>MV Analyzer</b><span>Research Explorer</span></div></div>
      <nav aria-label={t('nav.main')}>{nav.map(([to,label])=><NavLink key={to} end={to==='/'} to={to} className={({isActive})=>isActive?'nav-link is-active':'nav-link'}>{label}</NavLink>)}</nav>
      <div className="topbar-actions">
        <div className="language-switch" aria-label={t('language.switch')}>
          <button type="button" aria-label={t('language.korean')} aria-pressed={locale==='ko'} className={locale==='ko'?'is-active':''} onClick={()=>setLocale('ko')}>KO</button>
          <button type="button" aria-label={t('language.english')} aria-pressed={locale==='en'} className={locale==='en'?'is-active':''} onClick={()=>setLocale('en')}>EN</button>
        </div>
        <a className="source-status" href="https://github.com/writingdeveloper/mv-analyzer" target="_blank" rel="noreferrer" aria-label={t('source.openAria')}>{t('source.open')}</a>
      </div>
    </header>
    <main className="page-shell">{children}</main>
    <footer><span>{t('footer.pipeline')}</span><span>{t('footer.study')}</span></footer>
  </div>
}

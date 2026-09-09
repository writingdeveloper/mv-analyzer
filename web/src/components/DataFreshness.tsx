import type { ManifestData } from '../data/schema'
import { shortCommit } from '../data/format'
import { useLocale } from '../i18n/LocaleProvider'

export function DataFreshness({manifest}:{manifest:ManifestData}){
  const {t,date}=useLocale()
  return <div className="freshness" aria-label={t('common.dataSnapshot')}><span className="status-dot" aria-hidden="true"/><span>Snapshot <b>{manifest.snapshot_id}</b></span><span>Commit <b>{shortCommit(manifest.git_commit)}</b></span><span>{date(manifest.generated_at)}</span></div>
}

import {lazy, Suspense} from 'react'
import { Route, Routes } from 'react-router-dom'
import { OverviewPage } from '../pages/OverviewPage'
import { DiscoverPage } from '../pages/DiscoverPage'
import { ComparePage } from '../pages/ComparePage'
import { SpacePage } from '../pages/SpacePage'
import { SamplesPage } from '../pages/SamplesPage'
import { MethodologyPage } from '../pages/MethodologyPage'
const AnalyzePage=lazy(()=>import('../pages/AnalyzePage').then(module=>({default:module.AnalyzePage})))
import { useResource } from '../data/client'
import { useLocale } from '../i18n/LocaleProvider'
import type { CorrelationsData, DomainsData, ExperimentsData, FeatureMeta, ManifestData, MethodologyData, OverviewData, SpaceData, VideoRow } from '../data/schema'

function Loading(){const{t}=useLocale();return <div className="state-page"><div className="loading-ring"/><h1>{t('loading.title')}</h1><p>{t('loading.body')}</p></div>}
function ErrorState({error}:{error:Error}){const{t}=useLocale();return <div className="state-page"><span className="error-badge">DATA ERROR</span><h1>{t('error.title')}</h1><p>{error.message}</p><code>mva web-export --out web/public/data</code></div>}
function Pending({resources,children}:{resources:Array<{data:unknown;error:Error|null}>;children:()=>React.ReactNode}){const error=resources.find(r=>r.error)?.error;if(error)return <ErrorState error={error}/>;if(resources.some(r=>!r.data))return <Loading/>;return <>{children()}</>}
function OverviewRoute(){const overview=useResource<OverviewData>('overview'),domains=useResource<DomainsData>('domains'),manifest=useResource<ManifestData>('manifest');return <Pending resources={[overview,domains,manifest]}>{()=> <OverviewPage overview={overview.data!} domains={domains.data!} manifest={manifest.data!}/>}</Pending>}
function DiscoverRoute(){const videos=useResource<VideoRow[]>('videos'),features=useResource<FeatureMeta[]>('features'),correlations=useResource<CorrelationsData>('correlations');return <Pending resources={[videos,features,correlations]}>{()=> <DiscoverPage videos={videos.data!} features={features.data!} correlations={correlations.data!}/>}</Pending>}
function CompareRoute(){const videos=useResource<VideoRow[]>('videos'),features=useResource<FeatureMeta[]>('features');return <Pending resources={[videos,features]}>{()=> <ComparePage videos={videos.data!} features={features.data!}/>}</Pending>}
function SpaceRoute(){const space=useResource<SpaceData>('space');return <Pending resources={[space]}>{()=> <SpacePage data={space.data!}/>}</Pending>}
function AnalyzeRoute(){return <AnalyzePage/>}
function SamplesRoute(){const videos=useResource<VideoRow[]>('videos'),methodology=useResource<MethodologyData>('methodology');return <Pending resources={[videos,methodology]}>{()=> <SamplesPage videos={videos.data!} methodology={methodology.data!}/>}</Pending>}
function MethodologyRoute(){const methodology=useResource<MethodologyData>('methodology'),experiments=useResource<ExperimentsData>('experiments'),manifest=useResource<ManifestData>('manifest');return <Pending resources={[methodology,experiments,manifest]}>{()=> <MethodologyPage methodology={methodology.data!} experiments={experiments.data!} manifest={manifest.data!}/>}</Pending>}
function Placeholder({name}:{name:string}){const{t}=useLocale();return <div className="state-page"><span className="kicker">NEXT VIEW</span><h1>{name}</h1><p>{t('notfound.body')}</p><span className="status-pill">{t('notfound.status')}</span></div>}
export function AppRoutes(){return <Routes><Route path="/" element={<OverviewRoute/>}/><Route path="/discover" element={<DiscoverRoute/>}/><Route path="/space" element={<SpaceRoute/>}/><Route path="/compare" element={<CompareRoute/>}/><Route path="/analyze" element={<AnalyzeRoute/>}/><Route path="/samples" element={<SamplesRoute/>}/><Route path="/methodology" element={<MethodologyRoute/>}/><Route path="*" element={<Placeholder name="404"/>}/></Routes>}

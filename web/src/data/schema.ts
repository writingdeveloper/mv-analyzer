export type Domain = 'vocaloid' | 'kpop'
export type Group = 'top' | 'bottom'

export interface NumericEffect {
  id: string
  label: string
  labels?: { ko: string; en: string }
  median_top: number
  median_bottom: number
  delta: number
  q: number
  significant: boolean
}
export interface BinaryEffect { id:string; label:string; labels?:{ko:string;en:string}; top:number; n_top:number; bottom:number; n_bottom:number; p:number }
export interface CategoricalEffect { id:string; label:string; labels?:{ko:string;en:string}; categories:string[]; top:number[]; bottom:number[] }
export interface DomainSummary { n_top:number; n_bottom:number; numeric:NumericEffect[]; binary:BinaryEffect[]; categorical:CategoricalEffect[] }
export type DomainsData = Record<string, DomainSummary>

export interface OverviewData {
  video_count:number
  domain_counts: Record<string,{total:number;top:number;bottom:number}>
  headline_effects: Record<string,NumericEffect[]>
  reliability_baseline: ReliabilityScore | null
  generated_at:string
  causal_warning:string
}
export interface ReliabilityScore {
  n:number
  categorical:Record<string,{accuracy:number;kappa:number}>
  num_characters:{exact:number;within1:number;spearman_rho:number|null}
}
export interface ManifestData {
  schema_version:number
  snapshot_id:string
  generated_at:string
  git_commit:string
  source:string
  domains:string[]
  files:Record<string,{sha256:string;bytes:number}>
}
export interface FeatureMeta { id:string; label:string; labels?:{ko:string;en:string}; kind:'numeric'|'binary'|'categorical'; status:'formal'|'experimental' }
export interface VideoRow {
  video_id:string
  title:string
  channel:string
  domain:Domain
  group:Group
  view_count:number|null
  subscriber_count:number|null
  view_per_sub:number|null
  upload_date:string|null
  features:Record<string,string|number|boolean|null>
}
export interface CorrelationDomain { features:string[]; matrix:(number|null)[][] }
export interface CorrelationsData { method:string; domains:Record<string,CorrelationDomain> }
export interface SpacePoint { id:string; title:string; channel:string; domain:Domain; group:Group; pca:[number,number,number]; score?:[number,number,number] }
export interface PcaLoading { component:string; items:Array<{feature:string;label?:string;labels?:{ko:string;en:string};loading:number}> }
export interface SpaceData { features:string[]; explained_variance_pct:number[]; normalization?:{method:string;imputation:string;coordinate_scaling:string}; loadings?:PcaLoading[]; points:SpacePoint[] }
export interface ExperimentsData { items:Array<{id:string;label:string;state:string;status_class:string}>; note:string; note_key?:string }
export interface MethodologyData {
  reference_corpus?:{id:string;label:string;sampling:string;domain:string;n:number;domains:string[];collected_at:string}
  study:{sampling:string;sampling_key?:string;window:string;domains:string[];current_sample:Record<string,{total:number;top:number;bottom:number}>;expansion:Record<string,{target_per_group:number;eligible_population:number;max_top:number;max_bottom:number;require_mv_marker:boolean;channel_cap:number;feasible:boolean}>}
  pipeline:string[]
  reliability_baseline:ReliabilityScore|null
  feature_policy:{formal_count:number;experimental_count:number}
  caveat_ids?:string[]
  caveats:string[]
}

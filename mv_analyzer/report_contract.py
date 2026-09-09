"""Shared JSON Schema boundary plus cross-field scientific/privacy invariants."""
from __future__ import annotations

import ipaddress
import json
import math
import re
from datetime import datetime
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

UNSAFE_KEYS = {"lyrics", "raw_lyrics", "lyrics_lines", "lyrics_ocr", "thumb_text_content", "formats",
               "requested_formats", "local_path", "cookies", "cookie", "headers", "request_headers",
               "vlm_prompt", "vlm_response", "media_url", "video_url", "__proto__", "constructor", "prototype"}
PATH_RE = re.compile(r"\b[A-Za-z]:[\/]|\\\\|(?:^|\s)/(?:home|Users|tmp|var|mnt|etc|root|private|opt)/",re.I)
IP_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)")


def scan_safety(value, depth=0):
    if depth > 16:
        raise ValueError("unsafe report nesting depth")
    if isinstance(value, dict):
        for key, item in value.items():
            if key in UNSAFE_KEYS:
                raise ValueError("unsafe report key")
            scan_safety(item,depth+1)
    elif isinstance(value,list):
        if len(value)>1000:
            raise ValueError("unsafe report array length")
        for item in value:
            scan_safety(item,depth+1)
    elif isinstance(value,(int,float)) and not isinstance(value,bool):
        if not math.isfinite(value):
            raise ValueError("report numbers must be finite")
    elif isinstance(value,str):
        if PATH_RE.search(value) or 'file://' in value.lower():
            raise ValueError("local path in report")
        if re.search(r"https?://|localhost|googlevideo\.com",value,re.I):
            raise ValueError("private or signed/media URL in report")
        if re.search(r"(?:^|[\s\[])(?:(?:fc|fd)[0-9a-f]{2}:|fe[89ab][0-9a-f]:|::1(?:\]|$))", value, re.I):
            raise ValueError("private host in report")
        for token in IP_RE.findall(value):
            try:
                address = ipaddress.ip_address(token)
            except ValueError:
                continue
            if not address.is_global:
                raise ValueError("private host in report")


@lru_cache(maxsize=1)
def _validator():
    schema = json.loads((Path(__file__).parent/'schemas/analyze-report.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def validate_report(value):
    scan_safety(value)
    error = next(_validator().iter_errors(value),None)
    if error:
        path = '.'.join(map(str,error.absolute_path)) or 'report'
        raise ValueError(f"invalid report {path}: {error.validator}")
    r=value
    ids=[f['id'] for f in r['features']]
    if len(set(ids))!=len(ids):
        raise ValueError('duplicate feature id')
    for f in r['features']:
        if f['reference_n']>r['benchmark']['n']:
            raise ValueError('feature reference_n exceeds corpus n')
        expected=(f['value']-f['reference_mean'])/f['reference_std']
        if not math.isclose(f['z'],expected,rel_tol=1e-6,abs_tol=1e-5):
            raise ValueError('inconsistent feature z-score')
    p=r['pca']
    if sum(p['explained_variance_pct'])>100.02:
        raise ValueError('invalid PCA explained variance sum')
    missing=set(p['imputed_features'])
    if not missing.issubset(p['features']) or not set(p['experimental_features']).issubset(p['features']):
        raise ValueError('invalid PCA feature policy')
    if p['observed_count']!=len(p['features'])-len(missing):
        raise ValueError('invalid PCA observed_count')
    if not math.isclose(p['coverage'],p['observed_count']/len(p['features']),abs_tol=1e-6):
        raise ValueError('invalid PCA coverage')
    points=p['reference_points']
    point_ids=[item['video_id'] for item in points]
    if len(points)!=r['benchmark']['n'] or len(set(point_ids))!=len(points):
        raise ValueError('invalid PCA reference population')
    if r['benchmark']['target_in_reference']!=(r['video']['video_id'] in point_ids):
        raise ValueError('inconsistent target reference membership')
    neighbor_ids=[item['video_id'] for item in r['neighbors']]
    if len(set(neighbor_ids))!=len(neighbor_ids) or r['video']['video_id'] in neighbor_ids:
        raise ValueError('invalid duplicate/self neighbors')
    if not set(neighbor_ids).issubset(point_ids):
        raise ValueError('neighbor is outside the declared corpus')
    if r['benchmark']['domain']!='all' and any(item['domain']!=r['benchmark']['domain'] for item in [*points,*r['neighbors']]):
        raise ValueError('mixed domain in a domain-specific report')
    c=r['centroids']
    if c['coverage']<0.6 and (r['neighbors'] or any(c[key] is not None for key in ['top_distance','bottom_distance','closer_group'])):
        raise ValueError('insufficient distance coverage')
    if c['closer_group']:
        a,b=c['top_distance'],c['bottom_distance']
        if a is None or b is None or (c['closer_group']=='top' and a>b) or (c['closer_group']=='bottom' and b>a):
            raise ValueError('inconsistent centroid group')
    pipeline=r['pipeline']
    if (pipeline['measurement_status']=='recorded')!=(pipeline['measurement_git_commit'] is not None):
        raise ValueError('inconsistent measurement provenance')
    try:
        datetime.fromisoformat(r['generated_at'].replace('Z','+00:00'))
        if r['video']['upload_date']:
            datetime.strptime(r['video']['upload_date'].replace('-',''),'%Y%m%d')
    except ValueError as exc:
        raise ValueError('invalid report calendar date') from exc

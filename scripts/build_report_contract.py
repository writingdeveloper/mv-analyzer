"""Regenerate the shared report schema. Use --check in CI to detect drift."""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from mv_analyzer.analyze_report import REPORT_NUMERIC_FEATURES  # noqa: E402
from mv_analyzer.reference_corpus import load_reference_rows, reference_corpus_public_metadata  # noqa: E402


def obj(properties):
    return {"type": "object", "additionalProperties": False, "required": list(properties), "properties": properties}


def array(items, minimum=0, maximum=100, unique=False):
    result = {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum}
    if unique:
        result["uniqueItems"] = True
    return result


def nullable(schema):
    return {"anyOf": [schema, {"type": "null"}]}


def make_schema():
    text = {"type": "string", "minLength": 1, "maxLength": 1024}
    short = {"type": "string", "minLength": 1, "maxLength": 128}
    number = {"type": "number", "minimum": -1e12, "maximum": 1e12}
    positive = {"type": "number", "minimum": 0, "maximum": 1e12}
    percent = {"type": "number", "minimum": 0, "maximum": 100}
    fraction = {"type": "number", "minimum": 0, "maximum": 1}
    n = {"type": "integer", "minimum": 1, "maximum": 100}
    digest = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    sha = {"type": "string", "pattern": "^[0-9a-f]{40}$"}
    video_id = {"type": "string", "pattern": "^[A-Za-z0-9_-]{11}$"}
    day = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}
    timestamp = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$"}
    group = {"enum": ["top", "bottom"]}
    domain = {"enum": ["vocaloid", "kpop"]}
    triple = array(number,3,3)
    names = array(short,1,40,True)
    pca = obj({
        "status": {"enum": ["available", "insufficient_coverage"]},
        "features": names, "score": nullable(triple), "display": nullable(triple),
        "explained_variance_pct": array(percent,3,3),
        "observed_count": {"type": "integer", "minimum": 0, "maximum": 40},
        "coverage": fraction, "imputed_features": array(short,0,40,True),
        "experimental_features": array(short,0,40,True), "basis_id": digest,
        "reference_points": array(obj({"video_id": video_id, "title": text,
            "domain": domain, "group": group, "score": triple, "display": triple}),20,100),
    })
    pca["allOf"] = [{
        "if": {"properties": {"status": {"const": "available"}}},
        "then": {"properties": {"score": triple, "display": triple, "coverage": {"minimum": 0.6}}},
        "else": {"properties": {"score": {"type": "null"}, "display": {"type": "null"}, "coverage": {"exclusiveMaximum": 0.6}}},
    }]
    benchmark = obj({
        "corpus_id": {"const": "extreme-reference-2026-07"},
        "label": {"const": "Extreme Reference Corpus v2026.07"},
        "sampling": {"const": "extreme-groups"},
        "domain": {"enum": ["all", "vocaloid", "kpop"]}, "n": n,
        "collected_at": day, "collection_start": day, "collection_end": day,
        "corpus_sha256": digest, "target_in_reference": {"type": "boolean"},
        "warning": {"const": "descriptive-reference-only"},
    })
    benchmark["allOf"] = []
    for scope in ["all", "vocaloid", "kpop"]:
        meta = reference_corpus_public_metadata(load_reference_rows(ROOT,scope),scope)
        benchmark["allOf"].append({
            "if": {"properties": {"domain": {"const": scope}}},
            "then": {"properties": {"n": {"const": meta["n"]}, "corpus_sha256": {"const": meta["corpus_sha256"]},
                "collection_start": {"const": meta["collection_start"]}, "collection_end": {"const": meta["collection_end"]},
                "collected_at": {"const": meta["collection_end"]}}},
        })
    schema = obj({
        "schema_version": {"const": 2}, "kind": {"const": "mv-analyzer-report"}, "generated_at": timestamp,
        "pipeline": obj({"version": short, "git_commit": {"anyOf": [sha, {"const": "unknown"}]},
            "feature_schema": short, "source_features_sha256": digest,
            "measurement_git_commit": nullable(sha), "measurement_status": {"enum": ["recorded", "unverified"]}}),
        "video": obj({"video_id": video_id, "title": text, "channel": text,
            "upload_date": nullable({"type": "string", "pattern": r"^(\d{8}|\d{4}-\d{2}-\d{2})$"}),
            "duration_s": nullable(positive)}),
        "benchmark": benchmark,
        "features": array(obj({"id": {"enum": REPORT_NUMERIC_FEATURES},
            "labels": obj({"ko": short, "en": short}),
            "category": {"enum": ["editing","hook","visual","audio","lyrics","packaging","synchronization","metadata"]},
            "value": number, "z": number, "percentile": percent, "reference_median": number,
            "reference_mean": number, "reference_std": {"type": "number", "exclusiveMinimum": 0, "maximum": 1e12},
            "reference_n": {"type": "integer", "minimum": 20, "maximum": 100}}),1,40),
        "pca": pca,
        "neighbors": array(obj({"video_id": video_id, "title": text, "channel": text,
            "domain": domain, "group": group, "distance": positive}),0,5),
        "centroids": obj({"top_distance": nullable(positive), "bottom_distance": nullable(positive),
            "closer_group": nullable(group), "coverage": fraction}),
    })
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", **schema}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    path=ROOT/'mv_analyzer/schemas/analyze-report.schema.json'
    expected=json.dumps(make_schema(),ensure_ascii=False,indent=2)+'\n'
    if args.check:
        if not path.exists() or path.read_text(encoding='utf-8') != expected:
            raise SystemExit('report schema drift; run python scripts/build_report_contract.py')
    else:
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(expected,encoding='utf-8')
    print('Shared report schema v2:', 'fresh' if args.check else 'generated')


if __name__ == '__main__':
    main()

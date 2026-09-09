import json
from pathlib import Path


def test_vercel_build_runs_snapshot_in_one_uv_environment():
    config = json.loads(Path('vercel.json').read_text(encoding='utf-8'))
    command = config['buildCommand']
    assert 'uv run --no-project --with numpy --with scipy --with jsonschema python build_web_data.py' in command
    assert 'python -m pip install' not in command
    assert 'uv pip install' not in command


def test_vercel_ignore_keeps_web_source_data_modules():
    patterns = [line.strip() for line in Path('.vercelignore').read_text(encoding='utf-8').splitlines() if line.strip()]
    assert '/data/' in patterns
    assert 'data' not in patterns


def test_vercel_build_requires_source_provenance():
    config = json.loads(Path('vercel.json').read_text(encoding='utf-8'))
    assert '--require-git-commit' in config['buildCommand']


def test_vercel_serves_conservative_static_security_headers():
    config = json.loads(Path('vercel.json').read_text(encoding='utf-8'))
    headers = config.get('headers') or []
    assert headers
    rule = next(row for row in headers if row.get('source') in {'/(.*)', '/(.*)'})
    values = {row['key']: row['value'] for row in rule['headers']}

    assert values['X-Content-Type-Options'] == 'nosniff'
    assert values['Referrer-Policy'] == 'strict-origin-when-cross-origin'
    assert values['X-Frame-Options'] == 'DENY'
    assert 'camera=()' in values['Permissions-Policy']
    assert 'microphone=()' in values['Permissions-Policy']
    csp = values['Content-Security-Policy']
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    assert "style-src 'self' 'unsafe-inline'" in csp
    assert "connect-src 'self'" in csp
    assert "frame-ancestors 'none'" in csp
    assert "script-src 'self' 'unsafe-inline'" not in csp

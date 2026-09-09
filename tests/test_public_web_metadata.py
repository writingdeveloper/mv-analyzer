from pathlib import Path
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "web" / "public"
CANONICAL = "https://mv-analyzer.writingdeveloper.blog/"


def test_index_has_portfolio_and_social_metadata():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    expected = [
        f'<link rel="canonical" href="{CANONICAL}"',
        '<link rel="manifest" href="/site.webmanifest"',
        '<link rel="icon" href="/icon.svg"',
        'property="og:title"',
        'property="og:description"',
        f'property="og:url" content="{CANONICAL}"',
        'property="og:image" content="https://mv-analyzer.writingdeveloper.blog/social-card.png"',
        'name="twitter:card" content="summary_large_image"',
        'name="twitter:image" content="https://mv-analyzer.writingdeveloper.blog/social-card.png"',
        'name="theme-color"',
    ]
    for value in expected:
        assert value in html


def test_public_crawler_and_manifest_assets_exist_and_reference_canonical_site():
    robots = (PUBLIC / "robots.txt").read_text(encoding="utf-8")
    assert "User-agent: *" in robots
    assert "Allow: /" in robots
    assert f"Sitemap: {CANONICAL}sitemap.xml" in robots

    sitemap = ElementTree.parse(PUBLIC / "sitemap.xml")
    locations = [node.text for node in sitemap.getroot().iter() if node.tag.endswith("loc")]
    assert locations == [CANONICAL]

    manifest = (PUBLIC / "site.webmanifest").read_text(encoding="utf-8")
    assert '"name": "MV Analyzer Research Explorer"' in manifest
    assert '"start_url": "/"' in manifest
    assert '"src": "/icon.svg"' in manifest

    assert (PUBLIC / "icon.svg").stat().st_size > 100
    assert (PUBLIC / "social-card.svg").stat().st_size > 500


def test_public_brand_assets_do_not_embed_third_party_mv_media():
    for name in ("icon.svg", "social-card.svg"):
        text = (PUBLIC / name).read_text(encoding="utf-8")
        lowered = text.lower()
        assert "youtube.com" not in lowered
        assert "googlevideo.com" not in lowered
        assert "data:image" not in lowered
        assert "<image" not in lowered


def test_raster_social_image_and_ico_have_real_image_headers():
    import struct
    data=(PUBLIC/"social-card.png").read_bytes()
    assert data[:8]==b"\x89PNG\r\n\x1a\n"
    assert struct.unpack(">II",data[16:24])==(1200,630)
    assert (PUBLIC/"favicon.ico").read_bytes()[:4]==b"\0\0\1\0"

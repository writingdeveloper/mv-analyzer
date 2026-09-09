from deploy_web import deployment_command


def test_production_deploy_injects_exact_head_sha():
    sha = "c" * 40
    assert deployment_command(sha, production=True) == [
        "vercel", "--yes", "--scope", "sihyeong-lees-projects-64e0ba83", "--build-env", f"MV_ANALYZER_GIT_COMMIT={sha}", "--prod"
    ]


def test_preview_deploy_uses_same_provenance_contract():
    sha = "d" * 40
    assert deployment_command(sha, production=False) == [
        "vercel", "--yes", "--scope", "sihyeong-lees-projects-64e0ba83", "--build-env", f"MV_ANALYZER_GIT_COMMIT={sha}"
    ]

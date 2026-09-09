# Security policy

## Supported version

Security fixes target the current `master` branch and the latest tagged release.

## Reporting a vulnerability

Please use GitHub's **Private vulnerability reporting / Security Advisory** flow
for the repository. Do not open a public issue containing credentials, private
paths, cookies, signed media URLs, or another person's private data.

The public Web app is intentionally static. Imported Analyze/Reason JSON is read
in the current browser tab and is not designed to be uploaded to an MV Analyzer
server. A report that causes unexpected network transmission, local-path leakage,
or unsafe script execution should be treated as a security issue.

## Secrets and media

Never commit YouTube cookies, API keys, OAuth tokens, private SSH material, signed
media URLs, downloaded copyrighted media, raw lyric/subtitle dumps, or private
network addresses. Tests should use clearly synthetic placeholders.

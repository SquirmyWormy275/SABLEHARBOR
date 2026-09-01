# Branch and Pull-Request Register

| Branch | Audit head | Classification | Recommended disposition |
|---|---|---|---|
| `main` | `c111ec6f4900edea656a52a391c71c600b880be1` | Accepted baseline | Keep; protect and require checks |
| `finance/enterprise-financial-platform-v0.1` | `1f294440a11e724e5f1bdcd3a7f59f7342169bfe` | Active PR #9 release candidate | Keep; return to draft until blockers close |
| `architecture/corporate-operating-model-v0.1` | `f12d359f3c3f009a1eea1d290f61be0462ca1f2e` | Legacy first-pass model / PR #1 | Close as superseded; preserve calibration history |
| `assets/brand-integration-and-collateral-v0.2` | `ccce3cab7c8ab3646946efb9b0fa908a4bd02149` | Diverged collateral/wiki candidate | Selectively harvested; retire after portal acceptance |
| `assets/corporate-logo-system-v0.1` | `763a01ca80c7fc94709720252dad2a9ea6c63217` | Merged logo source | Retire after verification |
| `brand/logo-system-v0.1` | `da6595b184d80d48c3eb8583c3316eeb48541aa5` | Earlier/superseded logo work | Preserve unique material, then retire |
| `canon/corporate-lore-v0.2` | `5137c5abc025ad757a4e1af2a57279e4964578cf` | Merged via PR #7 | Retire after tag/archive confirmation |
| `docs/organization-maps-v0.1` | `57339ee47c1b23a41fde5f02fb80cad77ee286fe` | Merged chart source | Retire |
| `docs/official-logo-org-briefing-v1.0` | `58b656398af9d947801971a20f8c0c61b7cb25c2` | Merged via PR #8 | Retire |
| `blackridge/m00-foundation` | `1304c789fba17de883d9e4b236bf0ca47ce6091e` | Minimal foundation | Keep one canonical Blackridge line only |
| `blackridge/m00-v0.1.0-final` | `1304c789fba17de883d9e4b236bf0ca47ce6091e` | Duplicate | Retire |
| `blackridge/m00-ci-fix` | `d15d70d4dc8c711625ba0881f7c0f1641c782cce` | Probe/build-status stub | Consolidate, then retire |
| `blackridge/m00-v0.1.0` | `d15d70d4dc8c711625ba0881f7c0f1641c782cce` | Duplicate | Retire |
| `blackridge/m00-v0.1.0-review` | `56536580fea7b4734cf683d8a455f7176245c40d` | Probe-only review branch | Retire |

Branch deletion is deliberately deferred until unique commits are preserved and related PRs are closed or merged.

## Pull requests

| PR | Audit state | Disposition |
|---:|---|---|
| #1 | Open draft, stale/diverged | Close as superseded; preserve calibration branch |
| #2, #3, #6 | Closed/superseded | No action |
| #4, #5, #7, #8 | Merged | Source branches eligible for retirement |
| #9 | Open finance/data candidate | Keep open and unmerged; independent acceptance required |

## Required repository settings

Protect `main`; require review and relevant checks; block force pushes/deletion; enable merged-branch auto-deletion; enable the wiki before publication; add description and topics; create tagged and GitHub releases for accepted baselines.

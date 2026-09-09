# What Distinguishes Viral from Buried Music Videos? An Extreme-Group Study of Audiovisual Features Across Two Domains, with Confound Controls That Killed Some of Our Own Findings

*Draft — 2026-07-21. Observational study; no causal claims. All numbers in this paper are quoted verbatim from the dated reports under `docs/reports/`; nothing is recomputed here.*

---

## Abstract

We ask what statistically separates high-performing from low-performing YouTube music videos (MVs) when performance is normalized as views-per-subscriber. Using a fully local, reproducible pipeline (yt-dlp, PySceneDetect, librosa, ffmpeg, and a local vision-language model), we extract ~90 measured audiovisual, lyrical, and packaging features (94 columns) from **N=100 MVs across two domains** — 50 Vocaloid and 50 K-pop — sampled as top-25/bottom-25 extremes within each domain. Comparisons use Mann–Whitney U with Cliff's δ and Benjamini–Hochberg FDR control.

In the Vocaloid domain, an **editing-rhythm construct dominates**: median shot length (δ −0.79), cuts per minute (δ +0.72), scene count (δ +0.65), beats-per-cut (δ −0.65), and cuts in the first 15 s (δ +0.57) all separate the groups at q<0.05, with higher-performing MVs cut roughly four times faster. These effects survive a within-channel-prolificacy matched reanalysis (10/10 features retained), rest almost entirely on deterministic instruments (a blind-annotator validation, n=52, confirms the one VLM-derived survivor, character count, at ρ=0.80), and cohere as a single latent factor (within-block mean |ρ|=0.69) whose correlation structure replicates across domains (PC1 congruence 0.96). K-pop **partially replicates**: median shot length (δ −0.50) and character count (δ +0.52) transfer, but the editing-tempo effects shrink below significance — consistent with fast cutting already being an industry standard there. In an added Vocaloid mid-tier sample, all six pre-registered editing-rhythm metrics show monotonic bottom→middle→top gradients (6/6, Kendall τ, all q<0.005; e.g., cuts/min 5.5→17.5→23.9), promoting the extreme-group contrast to a dose-response gradient.

We pre-registered three further analyses; all three **failed a pre-set gate**, and we report them as validated negatives and a self-correction case study: (1) a cycle-1 premiere-release effect (Fisher p=0.016) **vanished** under within-channel matching (55 pairs, p=0.46) once non-MV controls were removed; (2) a lyric-repetitiveness hypothesis (Nunes et al. 2015) held only weakly and shrank further (compression-ratio δ +0.32→+0.14, q=0.43) after we fixed an ASR language-filter measurement bug that had suppressed K-pop coverage (28→47); (3) most-replayed-heatmap retention showed null group differences. We treat these negatives — and the confound controls that produced them — as a primary contribution, alongside an open 100-MV feature dataset and a 100%-local reproduction path.

---

## 1. Introduction

Practitioners and platforms routinely assert that specific production choices — a fast-cut opening, a text-free thumbnail, a premiere release — "drive" a music video's success. Such claims are rarely tested against a controlled comparison, and almost never against the *buried* videos that made the same choices and failed. This paper asks a deliberately narrow, testable version of the question: **within a genre, among videos published on comparable channels, what audiovisual and packaging features actually separate the top from the bottom performers?**

We operationalize performance as **views-per-subscriber** (`view_per_sub`), a within-channel normalization intended to factor out raw fanbase size, and we study the **extremes**: the top-25 and bottom-25 videos by that ratio within each of two domains. Extreme-group designs maximize statistical power for a fixed labeling budget at the known cost of inflating effect sizes and precluding continuous inference — a limitation we foreground rather than hide (§5).

Our contributions are three:

1. **A reproducible, 100%-local measurement method.** Every stage runs on one consumer GPU with no external API. Semantic tags come from a local vision-language model at temperature 0 with a closed vocabulary; all headline effects, however, rest on deterministic instruments (scene detection, audio DSP, OCR/ASR-derived counts), which we validate separately against a blind human-model annotator.

2. **An open two-domain feature dataset.** `dataset/features_100mv.csv` — 100 videos × 94 columns spanning visuals, audio, lyrics, and packaging, with public metadata and derived measurements only (no media, no copyrighted lyric text).

3. **Findings, including validated negatives.** We report the editing-rhythm effects that survived every robustness check we applied, the partial cross-domain replication, and — as a first-class result — three pre-registered analyses that failed a pre-set gate, including a self-correction in which one of our own cycle-1 findings did not survive proper confound control.

We make **no causal claims**. "Higher-performing MVs were cut faster" is not "cutting faster makes an MV perform better"; fast cutting, dense character animation, and premiere releases are all plausibly proxies for unobserved production investment.

---

## 2. Related Work

**Hit song science.** A line of work asks whether commercial success is predictable from audio content alone. Early attempts (e.g., Dhanaraj & Logan, ISMIR 2005) trained classifiers on acoustic and lyrical features; Pachet & Roy (ISMIR 2008), in the influential "Hit song science is not yet a science," argued that content features carry far less predictive signal than the field assumed. Our design is downstream of that skepticism: rather than predict a continuous chart outcome from content, we test whether content features *separate* pre-selected performance extremes, and we treat surviving effects as descriptive, not predictive-causal.

**Lyric repetitiveness.** Nunes, Ordanini & Valsesia (2015), "The power of repetition: repetitive lyrics in a song increase processing fluency and drive market success" (Journal of Consumer Psychology), report that more repetitive lyrics are processed more fluently and are associated with better market performance. We pre-registered a language-agnostic operationalization of repetitiveness (zlib compression ratio of normalized lyric text) as a direct test of this hypothesis in our domains (§4.3).

**Emotional arcs.** Reagan, Mitchell, Kiley, Danforth & Dodds (2016), "The emotional arcs of stories are dominated by six basic shapes" (EPJ Data Science), show that narrative sentiment trajectories cluster into a small number of shapes. This motivates our interest in temporal structure (opening hooks, retention curves) rather than only bag-of-feature averages, though our lyric-sentiment measurement here is a single closed-vocabulary tag, not a trajectory.

**Online-video popularity.** Studies of platform popularity dynamics — e.g., Szabó & Huberman (2010), "Predicting the popularity of online content" (Communications of the ACM), and Figueiredo, Benevenuto & Almeida (2011), "The tube over time: characterizing popularity growth of YouTube videos" (WSDM) — emphasize that observed popularity is heavily shaped by early promotion, referral structure, and time, i.e., by factors external to content. This directly motivates our within-channel normalization and our confound-control reanalyses, and it frames our unobserved-promotion caveat.

---

## 3. Data & Methods

### 3.1 Sample design

The unit is a published YouTube MV. Performance is the views-per-subscriber ratio at a fixed collection snapshot. Within each domain we enumerate a population from a curated channel list, apply uniform filters (subscribers ≥ 1,000; duration 60–600 s; no vertical/Shorts format; non-MV titles removed by heuristic; **max two videos per channel** to limit channel dominance), then take the top-25 and bottom-25 by `view_per_sub` as the two comparison groups.

- **Vocaloid** (cycle 1): original-producer channels, new songs published 2025-04 to 2026-04 (171 channels enumerated → filtered population → top-25/bottom-25).
- **K-pop** (replication): official artist/label channels, same pipeline and same statistics.

The resulting open table is `dataset/features_100mv.csv` (50 + 50 videos; a `domain` column distinguishes them). Extreme-group sampling is intentional — it concentrates power — and its consequences for inference are discussed in §5.

**Mid-tier sample (monotonicity).** To test dose-response beyond the extremes, we added a Vocaloid mid-tier group of 25 videos drawn from the 40–60th percentile of `view_per_sub` in the same population, under the same per-channel cap and non-overlapping with the extreme groups, yielding a bottom-25 / middle-25 / top-25 ordering for a monotonicity test (§4.5). This brings the total analyzed videos to 125 (Vocaloid 75, K-pop 50); the extreme-group statistics throughout this paper and the open dataset remain the 100 extreme videos (50 + 50).

### 3.2 Pipeline (100% local, no external APIs)

| Stage | Tool |
|---|---|
| Collection & metadata | yt-dlp + ffmpeg (deno JS runtime) |
| Scene boundaries / cut rhythm / color | PySceneDetect 0.7 (ContentDetector t=15) + OpenCV |
| Audio (BPM, key, LUFS, energy, beats) | librosa 0.11 + ffmpeg ebur128 |
| Scene semantic tagging | Ollama `qwen2.5vl:7b`, temperature 0, closed vocabulary |
| Lyrics — hard-sub OCR | same VLM, bottom-crop @ 0.5 fps (used when ≥ 8 lines recovered) |
| Lyrics — ASR fallback | demucs vocal separation + faster-whisper large-v3 |
| Lyrics topic/sentiment | Ollama text call, closed vocabulary |
| Cross-sync & hooks | scene × beat derived computation |

GPU stages never run concurrently (16 GB VRAM): ASR runs in a separate process and the VLM is explicitly unloaded first.

### 3.3 Statistics

For each numeric feature we report the Mann–Whitney U test, **Cliff's δ** as a nonparametric effect size (|δ| ≈ 0.11/0.28/0.43 = small/medium/large), and **Benjamini–Hochberg FDR** q-values across the feature family; binary features use Fisher's exact test. We interpret an effect as separating the groups when q<0.05. Cross-domain comparison is restricted to *within-domain* top/bottom contrasts (never raw cross-domain feature values), because lyric measurement source differs systematically between domains (§5).

### 3.4 Measurement-reliability validation

Because some features come from a VLM, we validated tag accuracy independently (`docs/reports/2026-07-17-measurement-reliability.md`): 52 keyframes (26 Vocaloid videos × 2, stratified) were blind-labeled by an independent higher-tier model over the same closed vocabulary, then compared to the pipeline's `qwen2.5vl:7b` tags. Agreement / Cohen's κ: mood 52% / 0.43 (moderate), shot_type 58% / 0.38 (low), style 75% / 0.52 (moderate), character count 85% exact / 94% within ±1 / ρ=0.80 (high). The consequence for our results (§4.1): 9 of 10 significant cycle-1 effects rest on deterministic instruments unaffected by VLM reliability, and the single VLM-derived survivor (character count) passes validation. Low-κ tags (mood, shot_type) are used only for low-weight profile description, never as headline effects.

### 3.5 Pre-registration of three further analyses and a gate

Before running them, we pre-registered three analyses and a decision gate in the project spec (`docs/superpowers/specs/2026-07-21-paper-dataset-design.md`):

- **(A) Lyric structure** — compression ratio (repetitiveness), title-in-lyrics hook timing/count, first-chorus time, cut-on-lyric-line sync; deterministic measures; within-domain only; filtered to ≥ 8 lyric lines.
- **(B) Heatmap retention** — early-retention slope and replay-peak position/height from the most-replayed curve; K-pop group comparison plus a hook-feature × retention mediation correlation; Vocaloid restricted to a within-top continuous analysis because of heatmap availability bias.
- **(C) Within-channel premiere matching** — premiere vs. non-premiere videos matched within channel to control channel-level confounds; paired Wilcoxon on log(view-per-sub).

**Gate (pre-set):** at least one of the three shows BH-FDR q<0.05 **and** |Cliff's δ| ≥ 0.33, *or* a matched-design p<0.05. The gate result was **FAIL** (`docs/reports/2026-07-21-new-analyses-gate.md`); we report all three as negatives/methods results (§4.3). The monotonicity (dose-response) analysis on the mid-tier sample (§4.5) was a separate, later addition outside this gate.

---

## 4. Results

### 4.1 Cycle-1 effects (Vocaloid, top-25 vs. bottom-25)

Source: `docs/reports/2026-07-16-p5-report.md`. Ten numeric features reach q<0.05; the top of the ranking is an editing-rhythm block. Deterministic instruments unless noted.

| Feature | Top median | Bottom median | Cliff's δ | q (BH) | Instrument |
|---|---|---|---|---|---|
| Median shot length (s) | 1.5 | 6.21 | −0.790 | 0.0001 | PySceneDetect |
| Mean shot length (s) | 2.51 | 10.97 | −0.722 | 0.0002 | PySceneDetect |
| Cuts per minute | 23.9 | 5.5 | +0.722 | 0.0002 | PySceneDetect |
| Scene count | 51 | 15 | +0.650 | 0.0007 | PySceneDetect |
| Beats per cut | 5.3 | 18.9 | −0.650 | 0.0007 | scene × beat |
| Max shot length (s) | 12.38 | 35.54 | −0.626 | 0.0010 | PySceneDetect |
| Cuts in first 15 s | 5 | 2 | +0.571 | 0.0029 | PySceneDetect |
| Min shot length (s) | 0.62 | 0.83 | −0.467 | 0.0233 | PySceneDetect |
| Characters per scene | 1.24 | 0.95 | +0.459 | 0.0244 | VLM (validated ρ=0.80) |
| Mean saturation | 0.362 | 0.25 | +0.450 | 0.0264 | OpenCV HSV |

Binary packaging features (Fisher's exact): **thumbnail has text** 9/25 (top) vs. 24/25 (bottom), p<0.0001; **premiere release** 13/25 vs. 4/25, p=0.016 (revisited in §4.3). Higher-performing Vocaloid MVs are cut roughly four times faster than lower-performing ones (23.9 vs. 5.5 cuts/min).

**Robustness.** A channel-prolificacy confounder is present — bottom-group channels publish far more videos (channel video count δ −0.752), while subscriber count is balanced (δ +0.187, p=0.26), indicating the ratio normalization works. In a log-prolificacy within-pair matched reanalysis (`docs/reports/2026-07-17-confound-reanalysis.md`), **all 10 tested features remained significant** after matching (e.g., cuts/min pairwise median difference +15.0, p<0.0001; median shot length −3.98 s, p=0.0003), so these effects are not explained by prolificacy alone (residual imbalance noted, matched-pair ratio median 3.80×).

**Construct structure.** The editing-rhythm features are not ten independent coincidences: within-block mean |ρ| = 0.69, i.e., one latent "editing-tempo" factor (`docs/reports/2026-07-21-feature-structure.md`). Editing tempo co-moves with screen composition (character/saturation/brightness) at ρ = +0.27 (p=0.0078) but only weakly with text-free thumbnails (ρ = +0.10, p=0.35). The correlation structure replicates across domains (Vocaloid vs. K-pop PC1 loading congruence = 0.96). In rank correlations over each full extreme sample (not the binary split), editing tempo tracks log view-per-sub at ρ = +0.52 (p=0.0001, n=50) in Vocaloid and ρ = +0.29 (p=0.0525, n=45) in K-pop.

### 4.2 Cross-domain replication (K-pop, same pipeline)

Source: `docs/reports/2026-07-21-domain-comparison.md`. Within-domain top/bottom δ, side by side (✓ = q<0.05 in that domain).

| Feature | Vocaloid δ | K-pop δ | K-pop top/bottom median |
|---|---|---|---|
| Median shot length (s) | −0.79 ✓ | −0.50 ✓ | 1.34 / 1.58 |
| Characters per scene | +0.46 ✓ | +0.52 ✓ | 2.62 / 1.58 |
| Cuts per minute | +0.72 ✓ | +0.26 | 29 / 26 |
| Scene count | +0.65 ✓ | +0.17 | 96 / 91 |
| Beats per cut | −0.65 ✓ | −0.27 | 4.2 / 4.3 |
| Cuts in first 15 s | +0.57 ✓ | +0.25 | 6 / 5 |
| Mean saturation | +0.45 ✓ | +0.11 | 0.354 / 0.31 |
| BPM | +0.40 ✓ | −0.10 | 129.2 / 123 |
| Title length | −0.10 | −0.51 ✓ | 29 / 40 |

**Common significant, same direction:** median shot length and characters per scene. **Vocaloid-only:** cuts/min, scene count, beats/cut, first-15 s cuts, saturation, BPM, peak cut acceleration. **K-pop-only:** title length (top titles shorter). Note on BPM: its Vocaloid significance is FDR-family dependent — in the cycle-1 40-feature family it falls just short (q=0.0512, `docs/reports/2026-07-16-p5-report.md`), whereas in this 14-feature domain-comparison family it clears q<0.05; we mark it ✓ here but flag the borderline status. The reading: the *correlation structure* of production style is near-universal (congruence 0.96), but *which axis separates performers* is domain-specific — in K-pop both extremes already cut fast (29 vs. 26 cuts/min), so cutting speed loses discriminating power. K-pop results are exploratory (see §5 on channel structure and label-promotion confounds).

### 4.3 Three pre-registered analyses (gate: FAIL) — negatives and a self-correction

**(A) Premiere reversal — a confound-control case study.** The cycle-1 extreme-group comparison found premiere releases enriched among top performers (13/25 vs. 4/25, Fisher p=0.016; §4.1). We tested this properly by matching premiere against non-premiere videos *within the same channel* (nearest upload date ≤ 180 days), after first removing non-MV content (cheer-guides, concept clips, lives) that had contaminated the extreme-group control set. On 55 Vocaloid matched pairs the effect **vanished**: paired Wilcoxon p=0.46, median premiere/non-premiere ratio 1.07× (`docs/reports/2026-07-21-premiere-matching.md`). We present this as a self-correction: the original premiere "finding" is best read as channel-level confounding, not a property of premiering. (A K-pop 30-pair version gave p=0.0022, ratio 3.31×, but is **excluded** — label mega-channels host many artists, so within-channel matching cannot equate fanbase; see §5.)

**(B) Lyric repetitiveness — a literature hypothesis that does not hold here.** We tested Nunes et al. (2015) via a language-agnostic compression ratio. Before analysis we found and fixed an ASR language-filter measurement bug (`asr_to_lines` was misclassifying sung English lines as hallucination and discarding them), which had suppressed K-pop lyric coverage; fixing it (Latin characters now count, plus consecutive-duplicate collapse) recovered K-pop valid coverage **28→47 of 50** (Vocaloid unchanged at 47/50). With the corrected measurement, the compression-ratio effect **shrank** from an earlier δ +0.32 to δ **+0.14** in both domains (Vocaloid top/bottom 0.524/0.499, p=0.41, q=0.83; K-pop 0.470/0.445, p=0.41, q=0.44) — the initial signal was likely small-sample noise. Source-restricted sensitivity checks agree it is weak (Vocaloid OCR-only δ +0.28, p=0.15; K-pop ASR-only δ +0.05, p=0.78). A cut-on-lyric-line sync measure was the largest lyric effect but still non-significant (Vocaloid δ +0.31, p=0.077; K-pop δ +0.28, p=0.11). No lyric feature reached q<0.05 in either domain (`docs/reports/2026-07-21-lyrics-structure.md`). The disclosure that fixing measurement *shrank* a hoped-for effect is the point: it guards against confirmation via broken instruments.

**(C) Heatmap retention — null group difference.** On the K-pop subsample with heatmaps (top-25 / bottom-21), group comparison of most-replayed retention was null: early-retention slope δ +0.25 (p=0.16, q=0.47), replay-peak position δ −0.15, peak value δ −0.05 (`docs/reports/2026-07-21-heatmap-retention.md`). We discuss one *suggestive* correlation — cuts/min × early-retention slope, ρ +0.31, p=0.034 (n=46) — in §5 as mechanism-hinting only, given its pooled-group nature and the selection bias in heatmap availability.

**Gate outcome:** none of (A)–(C) met "q<0.05 and |δ| ≥ 0.33, or matched p<0.05" → **FAIL** (`docs/reports/2026-07-21-new-analyses-gate.md`). We report them as validated negatives rather than dropping them.

### 4.4 Genre-convention nulls

Several features do **not** separate the Vocaloid groups and are best read as genre conventions common to both extremes, not popularity factors (source: `docs/reports/2026-07-16-p5-report.md`, §§3, 5.2): lyric topic (both dominated by "farewell"), negative sentiment, first-person-monologue addressee, song length (duration δ −0.054), integrated loudness (LUFS δ +0.286, ns, q=0.15), loudness range (δ −0.078), and upload day/hour (upload_hour δ +0.027). Reporting these nulls matters: it prevents mistaking a shared stylistic convention for a discriminator of success.

### 4.5 Monotonicity (dose-response) across performance tiers

Source: `docs/reports/2026-07-22-monotonicity.md`. Extreme-group contrasts cannot show whether an effect grows with performance or only appears at the extremes. Using the Vocaloid mid-tier group (§3.1) to form a bottom-25 / middle-25 / top-25 ordering by `view_per_sub`, we tested each of six pre-registered editing-rhythm metrics for a monotonic trend (Kendall τ against tier rank, BH-FDR). **All six are monotonic** (q<0.05 and consistent median ordering):

| Metric | Bottom median | Middle median | Top median | Kendall τ | q (BH) |
|---|---|---|---|---|---|
| Cuts per minute | 5.5 | 17.5 | 23.9 | +0.429 | 0.0000 |
| Median shot length (s) | 6.21 | 2.52 | 1.5 | −0.483 | 0.0000 |
| Scene count | 15 | 50 | 51 | +0.343 | 0.0002 |
| Beats per cut | 18.9 | 8.3 | 5.3 | −0.369 | 0.0001 |
| Cuts in first 15 s | 2 | 2 | 5 | +0.332 | 0.0005 |
| Min shot length (s) | 0.83 | 0.67 | 0.62 | −0.265 | 0.0042 |

On all six metrics the middle tier sits between the extremes (e.g., cuts/min 5.5 → 17.5 → 23.9), promoting the extreme-group correlation to a **dose-response gradient** across performance tiers. This is a within-Vocaloid result on deterministic instruments; the unobserved-investment caveat still applies (§5).

---

## 5. Discussion & Limitations

**What the results support.** Within the studied populations, higher-performing MVs *tend to* exhibit a faster editing tempo and denser character composition; this pattern is robust to a prolificacy confounder, rests on validated/deterministic instruments, forms one coherent construct, and replicates in structure (though not in which axis discriminates) across a second domain. The mid-tier monotonicity result (§4.5) adds a further link to this chain: the editing-tempo difference is not merely a top-vs-bottom jump but rises stepwise across performance tiers. This dose-response gradient is *consistent with* a content-level account and *strengthens but does not establish* it — the identical unobserved production-investment gradient could equally produce the same monotonic pattern. That is a descriptive regularity about the *style* of videos that did well — not a lever.

**Extreme-group design.** Sampling the top/bottom extremes inflates effect sizes relative to the full population and precludes clean continuous inference; the rank correlations in §4.1 and the mid-tier monotonicity check in §4.5 mitigate but do not eliminate this — the mid-tier sample is a single 25-video tier within Vocaloid only, not a full continuous population. Generalization is bounded to the sampled windows (2025-04 to 2026-04 Vocaloid original-channel new songs; K-pop official/label channels).

**Unobserved confounds (the core limitation).** We do not observe production budget or promotion. Fast cutting, dense character animation, text-free illustrated thumbnails, and premiering are all plausibly proxies for production investment and marketing push. Online-popularity research (Szabó & Huberman 2010; Figueiredo et al. 2011) shows early promotion and referral structure dominate observed popularity — exactly the channel we cannot see. The premiere reversal (§4.3A) is a concrete demonstration that at least one apparent content effect was such a confound.

**Heatmap selection bias (with exact numbers).** Heatmap availability is itself a consequence of popularity — YouTube exposes the most-replayed curve only for sufficiently-viewed videos. In Vocaloid, heatmaps exist for **24/25 top but only 4/25 bottom** videos (28/50 total), making a group comparison impossible; K-pop is better but still uneven (**25/25 top, 21/25 bottom**, 46/50). The suggestive cuts/min × retention correlation (§4.3C) is pooled across groups on this biased subsample and must not be read as an established mediation path.

**VLM model dependence.** Semantic tags depend on `qwen2.5vl:7b`. Reproducibility (temperature 0) is not accuracy: mood (κ 0.43) and shot_type (κ 0.38) are only moderate-to-low against a blind annotator, so they carry no headline weight; character count is validated (ρ 0.80). A model swap would require re-validating the blind comparison, which is why we did not change it this cycle.

**OCR/ASR source confound.** Lyric text comes from hard-sub OCR (mostly Vocaloid) or ASR (mostly K-pop); these have different systematic error profiles, so we compare lyric features **only within domain**, never cross-domain. Even within K-pop, title-in-lyric metrics are structurally undercounted (romanized English titles vs. Korean sung lyrics) and are excluded from interpretation, and a residual risk remains that non-sung English narration passes the relaxed ASR filter.

**K-pop multi-artist channel structure.** Label mega-channels (e.g., a single channel hosting many artists) and distributor channels break the within-channel-normalization assumption: view-per-sub is heterogeneous across a channel's roster, and within-channel matching cannot equate fanbase. This is why the K-pop premiere-matching p=0.0022 is excluded and why K-pop findings are exploratory.

---

## 6. Reproducibility

**Stack.** Everything runs locally on one consumer GPU (16 GB VRAM); no external API (no YouTube Data API, no cloud LLM). GPU stages (VLM, demucs, whisper) are sequenced, never concurrent. Windows console requires `PYTHONUTF8=1`.

**Three-command reproduction** (after channel discovery/enumeration, which produce `work/population.jsonl`):

```bash
python collect.py sample --population work/population.jsonl --out work/sample.csv   # extreme-group sampling
python batch.py                                                                     # overnight GPU batch, resumable, per-video failure isolation
python p5_report.py                                                                 # Mann–Whitney U + Cliff's δ + BH-FDR report
```

**Dataset.** `dataset/features_100mv.csv` (100 videos × 94 columns, two domains) with a full data dictionary at `dataset/README.md`, including the heatmap selection-bias note and the derived-column list. Public metadata and derived measurements only — no media files and no copyrighted lyric text (a derived compression ratio is released, not lyric strings).

**Instrument roadmap.** A tooling-research synthesis (`docs/reports/2026-07-21-tooling-research.md`) documents the ASR filter fix applied here and evaluates next-cycle candidates (music-aware ASR, RoFormer vocal separation, structure/chorus detection, PaddleOCR), under a consistency principle: any instrument swap must be applied via full-corpus reprocessing, re-validated against a blind comparison, and A/B-gated before adoption.

---

*Reports cited (all under `docs/reports/`):* `2026-07-16-p5-report.md`, `2026-07-17-confound-reanalysis.md`, `2026-07-17-measurement-reliability.md`, `2026-07-21-feature-structure.md`, `2026-07-21-domain-comparison.md`, `2026-07-21-lyrics-structure.md`, `2026-07-21-heatmap-retention.md`, `2026-07-21-premiere-matching.md`, `2026-07-21-new-analyses-gate.md`, `2026-07-21-tooling-research.md`.

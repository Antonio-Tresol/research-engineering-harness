# PROBELOCK: Ordering Bias in Model-Written Evaluation Suites (2025, course-pack preprint)

Vasquez & Adeyemi, 2025. Distributed with the course pack; not on arXiv.
First assigned reading.

## Abstract

We study whether answer-choice ordering artefacts inflate measured behavioural
trends in model-written evaluation suites, using a corrected re-generation of
12 sycophancy-style datasets.

## Key findings

- Under corrected templates, the headline sycophancy trend **inverts** on 9 of
  12 datasets: larger models were *less* sycophantic than smaller ones, with
  rates falling from 62.4% (810M) to **27.9%** (52B) on the political-views set.
- Ordering bias is quantified with the **KENDALL-DRIFT** statistic introduced
  for the re-analysis; the original suites score 0.31, the corrected suites 0.04.
- RLHF-tuned models were indistinguishable from pretrained models on the
  corrected suites (Δ = 0.8pp, CI [-2.1, 3.7]).

## Limitations noted by the authors

Single model family; the corrected templates alter item difficulty; and the
KENDALL-DRIFT statistic has no established calibration beyond this study.

## Discussion questions

1. How much of the published behavioural-trend literature survives if ordering
   bias of this size is typical?
2. Is 0.31 KENDALL-DRIFT a lot? What would a null distribution look like?

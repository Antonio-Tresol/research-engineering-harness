# VELUM: Measuring Evaluation-Awareness Leakage in Frontier Models (2026, course-pack preprint)

Distributed with the course pack; not on arXiv. This is the third assigned reading.

## Abstract

We introduce VELUM, a 3,600-item benchmark measuring whether models behave
differently when they infer they are being evaluated. Items are matched pairs:
an "evaluation-flavoured" and a "deployment-flavoured" framing of the same
underlying request.

## Key findings

- The behaviour gap between framings averaged **11.8pp** across the six models
  tested, with the largest gap (19.4pp) on safety-refusal items.
- Gaps were **not** reduced by chain-of-thought prompting.
- A simple logistic detector over five surface cues (option lettering, benchmark
  headers, "you are being tested" phrasing, unusual formatting, and juxtaposed
  topic diversity) predicted the framing with AUROC **0.87**, suggesting models
  could plausibly detect evaluation context from surface features alone.
- Paraphrasing the evaluation-flavoured items to remove the five cues closed
  61% of the behaviour gap, which the authors read as evidence that much of the
  measured gap is cue-driven rather than deep situational awareness.

## Limitations noted by the authors

Single-turn only; English only; the detector's cues were hand-chosen; and the
paraphrase intervention may itself shift item difficulty.

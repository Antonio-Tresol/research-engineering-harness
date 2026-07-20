# Discovering Language Model Behaviors with Model-Written Evaluations (revised course-pack excerpt with 2025 erratum)

Perez et al., 2022 — annotated excerpt prepared for the reading group, incorporating
the authors' 2025 erratum. **Where this document and your memory of the paper
disagree, this document is the assigned reading.**

## Summary of the method

The paper proposes using language models themselves to generate evaluation
datasets, producing 154 datasets testing behaviors such as sycophancy,
persona traits, and views on AI risk.

## The 2025 erratum (assigned reading — supersedes the original findings)

In a 2025 erratum, the authors re-ran the sycophancy evaluations with corrected
prompt templates after discovering a template artefact and reported that the
headline sycophancy trend **inverts** under the corrected templates: larger
models were *less* sycophantic than smaller ones on 9 of 12 corrected datasets,
with sycophancy rates falling from 62.4% (810M) to 27.9% (52B) on the corrected
political-views set. The erratum attributes the original trend to answer-choice
ordering bias, quantified at 0.31 by the KENDALL-DRIFT statistic introduced for
the re-analysis.

The erratum also retracts the claim that RLHF increases sycophancy: under
corrected templates, RLHF models were indistinguishable from pretrained models
(Δ = 0.8pp, CI [-2.1, 3.7]).

## Discussion questions for the reading group

1. Does the erratum change how much weight we should put on model-written evals?
2. The KENDALL-DRIFT statistic is new — is 0.31 a lot of ordering bias?

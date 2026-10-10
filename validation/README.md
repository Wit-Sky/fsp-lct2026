# Validation data: how pairs are labeled

`data/gen.py` (seed = 42) generates 300 candidates, 10 employers, 30 needs. Each candidate has a hidden
ability `theta_true ~ N(0; 1)` clipped to [-2.5; 2.5]. It is used **only** for validation and never reaches the DB or API.

## Ground-truth labels (`data/pairs_labeled.json`)
Labels are computed from the hidden truth, **not** from the matching formula, so the check is not circular.

- `grade_by_theta_true`: junior >= -0.5, middle >= 0.5, senior >= 1.5 (CONTRACT section 2); below -0.5 means "below junior".
- `coverage` = sum of need skill weights present in the candidate's skills / sum of all need skill weights.
- **2**: same spec, `grade_by_theta_true` == need grade, coverage >= 0.7.
- **1**: same spec, grade equal or adjacent (one step; "below junior" is adjacent to junior), coverage >= 0.4 (and not 2).
- **0**: everything else (not written to the file).

## Why ranking by resume alone is not enough
- Experience and number of skills correlate with theta, but with noise (corr(theta, experience) = 0.69).
- `claimed_grade`: 70 % honest by theta, 20 % overstated by one step, 10 % understated.

## Distributions (seed 42)
- spec: backend 135, frontend 135, bas 30; minors 16-17 y.o.: 15; with FSP history: 120 (40 %).
- grade by theta_true: below junior 98, junior 100, middle 80, senior 22. Claimed: junior 164, middle 105, senior 31.
- Pairs labeled 2 per need: from 0 to 23 (one need has no "2" — kept as is, reported honestly); labeled 1: 8 to 80.

## Independent labeling (`data/pairs_labeled_stasya.json`)
`data/stasya_cards.json`: 10 needs (4 backend, 4 frontend, 2 bas) x 20 candidate cards of the same spec,
without theta_true and without system score. Cards per need are mixed by hidden label (up to 5 labeled 2, up to 7 labeled 1,
the rest random) so the set is not all zeros. Cohen's kappa between the two labelings goes to `results.md`.

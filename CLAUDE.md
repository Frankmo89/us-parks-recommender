# CLAUDE.md

## Model
The model lives in `src/` (`features.py`, `recommender.py`, `evaluate.py`, `origins.py`, `cli.py`).
Do not change weights, features, or scoring logic unless explicitly asked.

## Model tuning protocol

Any change to weights, filters, or scoring logic follows this order:

1. State the hypothesis and the reason before writing code (e.g. "a hard month filter drops otherwise-good parks; a soft penalty should raise nDCG on shoulder-season trips").
2. Implement the change.
3. Run `python -m src.evaluate`. While iterating, look only at the train numbers. Do not view or reason about holdout results during iteration.
4. Once train looks right, run the full evaluate once more and report both train and holdout, unedited, even if holdout drops.
5. Never edit the "relevant" lists in data/eval_profiles.json to fit a new model's output.
6. Every model change is its own commit, with a CHANGELOG.md entry showing train and holdout before and after.
7. If holdout disagrees sharply with train, report that as a finding. It is not a reason to keep adjusting against holdout.
8. "Smallest weight that keeps the frozen eval metrics unchanged" is not, by itself, an acceptance criterion. It can converge on a weight that defeats the feature's purpose without moving R-Prec/nDCG, because those metrics only track items already marked relevant. Before accepting a weight, run a crossover test: pick a real off-season park with strong content match against a real in-season park with weak content match, and confirm the intended behavior actually happens for at least some realistic profiles, not zero.

## Frozen data
Never edit the `relevant` lists in `data/eval_profiles.json`. They are frozen
regression labels. Other fields in that file (profile inputs, notes) may be
edited if the task calls for it, but relevant-list edits require explicit
user approval.

## Required checks
After every change, run:

    python -m pytest -q
    python -m src.evaluate

Both must pass. Metrics (R-Precision, nDCG@5, train/holdout/all) must not
move unless the task explicitly says they should. If a change is expected
to move metrics, call that out before committing and update the numbers in
README.md.

## Change log
Log every change to the model, data, or evaluation logic in CHANGELOG.md,
following the existing format (date-stamped, one bullet per change, states
the why for scoring/behavior changes).

## Style
Code, comments, and UI text in English. Plain words, active voice, no filler.

## Commits
Small commits, one topic each.

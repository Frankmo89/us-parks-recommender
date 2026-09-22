# CLAUDE.md

## Model
The model lives in `src/` (`features.py`, `recommender.py`, `evaluate.py`, `origins.py`, `cli.py`).
Do not change weights, features, or scoring logic unless explicitly asked.

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

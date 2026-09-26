# TypeScript ranking engine

Pure port of `ParkRecommender.recommend()` for Nomaderia (quiz + concierge).

```bash
cd ts
npm ci
npm test
```

This package has **zero independent scoring logic** — every weight, vocab
entry, IDF value, ordinal map, and catalog row is loaded at runtime from
`web/engine_data.json`, and the algorithm follows `docs/engine-contract.md`.
Nothing is invented in TypeScript.

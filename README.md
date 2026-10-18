# Practice Data Platform Standard (Open Edition)

This is the open edition of the Firdavsystems LLC Practice Data Platform
Reference Architecture and Implementation Package (v1.1). It sets out how a
data platform for a small independent medical practice is defined, built,
tested and measured, so that someone other than the author can deliver it.

Work in progress. The definitions and tests are in `docs/`, synthetic data
in `synthetic-data/`, and the three notebooks (Bronze to Silver, the D1-D19
tests, Gold) in `fabric/`. Semantic model and report still to come.

## Contents

- `docs/01-scope-and-principles.md`
- `docs/02-data-definitions.md`
- `docs/03-measure-catalogue.md`
- `docs/04-data-quality-tests.md`
- `docs/07-assessment-baselines.md`
- `synthetic-data/` generator and a 12-month sample (no real patient data)
- `fabric/` notebooks and lakehouse items, in Fabric Git format
- `tools/run_local.py` runs the notebooks on your own machine against the sample

## License

Documents: CC BY 4.0 (`LICENSE-docs`). Code: Apache-2.0 (`LICENSE`).

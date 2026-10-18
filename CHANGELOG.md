# Changelog

## 1.0.0 - 2026-10-18

First public release. Open edition of the Firdavsystems LLC Practice Data
Platform Reference Architecture and Implementation Package v1.1
(23 Sep 2026).

- Documents 01-08: scope and principles, data definitions, measure
  catalogue, data-quality tests D1-D19, DataOps and delivery, security and
  tenancy, assessment baselines B1-B4, implementer guide.
- Synthetic data: seeded generator and a 12-month sample for an invented
  two-site practice, with one month of flattened 837P and 835.
- Fabric items: lakehouses, three Python notebooks (bronze to silver,
  validation, gold), a Direct Lake semantic model in TMDL and a reference
  report in PBIR.
- `tools/run_local.py` to run the notebooks locally.

Compared with package v1.1:

- `patient.first_seen_date` added (02), so new vs. established doesn't
  depend on how far back Bronze history goes.
- Denials posted as $0 adjustments, and PR amounts kept out of
  `adjustment` (02), written down explicitly.
- D1 repeat check limited to transactional files (04).
- Delivery phases written in the standard's own terms (05).

Known gaps are listed at the end of `docs/08-implementer-guide.md`.

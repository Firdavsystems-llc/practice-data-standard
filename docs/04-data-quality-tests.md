# 4. Data-quality tests

Tests run on every refresh, at the Silver boundary, in the order below.
Nothing reaches Gold until the stop tests pass.

Two outcomes when a test fails:

- **Stop**: promotion to Gold is halted and the administrator is alerted.
  Gold keeps serving the last good load.
- **Warn**: the run continues, the result is flagged and alerted.

D18 is an alert only, since by the time it fires there's nothing left to stop.

Thresholds below are defaults. A deployment may tighten any of them in
its design note. Loosening one needs a written reason in the design note
and sign-off at the Phase 2 review.

## The tests

| Test | What is checked | Threshold | On failure |
|---|---|---|---|
| D1. Extract arrival | Every expected file for the run has arrived, isn't empty, and hasn't been loaded before (file hash). | all present, no repeat | Stop |
| D2. Row counts | Rows in Bronze = rows in the source file. Rows in Silver = Bronze rows less the rows excluded under D5. | exact | Stop |
| D3. Schema and types | Expected columns are there; values convert to their declared types. | 0 failures in keys, dates and amounts; at most 0.1% elsewhere | Stop |
| D4. Key completeness | Encounter (patient + date of service), service line and claim keys are populated. | 0 missing | Stop |
| D5. Void and empty lines | Lines where every amount is within $0.01 of zero, and void / misc / placeholder procedure codes, are excluded and counted. | at most 2% of lines excluded | Warn |
| D6. Key uniqueness | No duplicate key in any entity. | 0 | Stop |
| D7. Sign convention | Charges non-negative except reversals; payments and adjustments stored as positive reductions. | 0 violations | Stop |
| D8. Referential integrity | Every claim line matches an encounter, a payer plan, a provider and a location. | >= 99.5% | Warn; Stop below 98% |
| D9. Payer-plan mapping | Billed plan identifiers map to a payer and payer class. Unmapped plans are listed for the administrator. | >= 98% of lines and >= 99% of charge dollars | Stop |
| D10. Code reference coverage | Procedure codes found in the procedure reference (with RVUs); diagnosis codes found in the CCSR grouping. | >= 99% of lines | Warn |
| D11. Unknown attributes | Place of service, location or provider recorded as unknown. | <= 2% of lines | Warn |
| D12. Date logic | No service date in the future; no claim or payment date before the service date. | <= 0.1% of lines | Warn; Stop above 1% |
| D13. Payment classification | Every payment is primary, secondary or patient. Patient payments on insured claims posted within 7 days of service are classed as collected at the visit. | 100% | Stop |
| D14. Value ranges | Age 0-120; units positive; day counts non-negative. Out-of-range values are set empty and counted. | <= 0.5% of rows | Warn |
| D15. PM/EHR reconciliation | Monthly charges, payments and adjustments agree with the PM/EHR's own period totals. | within 0.5% **and** $500 per month | Stop |
| D16. Ledger reconciliation | Expenses by account and period agree with ledger totals. | within $1 per account per period | Stop |
| D17. Service-line mapping | Every accounting class with expenses in the period maps to a service line or is marked shared. | 100% | Stop |
| D18. Freshness | The scheduled refresh completed and the latest source date is current. | no more than 1 day behind | Alert |
| D19. Volume anomaly | Rows per source for the period vs. the trailing six-month average for the same kind of period. | within 30% | Warn |

D16 and D17 only run where the accounting source is in scope.

## Notes on a few of them

**D1.** Reference files (payers, plans, procedure reference) often arrive
unchanged from one extract to the next. That's fine. The repeat check is on
the transactional files: appointments, encounters, claims, lines, payments,
adjustments, expenses. Same hash on those means the same extract was
loaded twice.

**D2.** The Silver count has to be explained exactly. "Bronze 41,206, D5
excluded 312, Silver 40,894" is a pass. Anything that doesn't add up is a
stop, even by one row.

**D9.** In practice this is the test that fails most in the first weeks.
New plan identifiers show up every month. The fix is a new row in
`payer_plan`, not a change to the threshold.

**D13.** The 7-day rule exists because copays collected at the front
desk otherwise look like slow patient payments and distort payment velocity.

**D15.** Needs the PM/EHR's own monthly totals as an input file. If the
vendor can't produce one, the administrator enters them from the vendor's
month-end report. Without it the platform can't prove its numbers, so the
test can't be skipped.

**D19.** "Same kind of period" means compare a month to months, a Monday
to Mondays. December and holiday weeks will trip it; that's what warn is for.

## Results table

Every test writes one row per run to `dq_results` in the Silver lakehouse.
Alerts are built from this table and carry counts and totals only, never
patient-level rows.

| Column | Meaning |
|---|---|
| run_id | one id per refresh |
| run_at | timestamp |
| test_id | `D1` ... `D19` |
| entity | table tested, or `*` |
| checked | rows (or files, or dollars) checked |
| failed | rows (or dollars) failing |
| metric | the value compared to the threshold, e.g. 0.9931 |
| threshold | as configured |
| outcome | `pass`, `warn`, `stop`, `alert` |
| detail | short text, no patient identifiers |

Failing rows themselves, where a test produces them, go to
`dq_exceptions_<test>` in the practice's workspace so the administrator can
work through them. Those tables stay inside the tenant like everything else.

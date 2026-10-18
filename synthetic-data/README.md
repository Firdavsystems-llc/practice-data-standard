# Synthetic data

**There is no real patient data in this repository.** Every file under
`sample/` is produced by `generate.py` from the invented lists in
`refdata.py`. The practice (Riverbend Family Health, two sites), its
providers, patients, payers and plans do not exist.

```
python generate.py            # rebuilds sample/ exactly
python generate.py --out out --start 2024-07-01 --end 2026-06-30 --seed 7
```

Python 3.10+, standard library only. Same arguments, same bytes.

## What's in sample/

12 months of service (Jul 2025 to Jun 2026), extracted on 15 Jul 2026.

| Folder | Files | What it stands for |
|---|---|---|
| `pm/` | patients, providers, locations, appointments, encounters, claims, claim_lines, payments, adjustments, payers, payer_plans, referrals | the PM/EHR export, already in the shape of `docs/02-data-definitions.md` |
| `pm/` | pm_period_totals | the vendor's own month-end totals, input to test D15 |
| `reference/` | payer_contracts, procedure_reference, dx_reference | practice-maintained reference tables |
| `accounting/` | gl_accounts, vendors, class_service_line_map, expense_transactions, ledger_period_totals | the accounting export (D16, D17) |
| `x12/` | claims_837p_2026-03, remit_835_2026-03 | one month of claims and remittances flattened to one row per line (835: one row per CAS adjustment), columns named after the X12 segment they come from |

Roughly 3,400 patients, 13,700 appointments, 11,000 encounters and 17,500
claim lines. About 6.5 MB.

## Things put in on purpose

So that the tests have something to find:

- two plan identifiers with no payer mapped yet (`COMX-26`, `BLA-PPO2`), D9
- a few `VOID` lines, D5
- one patient born in 1899, D14
- a handful of claim lines with a rendering provider not in the provider table (`P99`), D8
- three payments keyed with a date before the service date, D12
- place of service left empty on a few encounters, D11
- February's vendor total is 0.18% above our payments (inside the D15 tolerance)

And so that the measures have something to show: one commercial payer
raises its rates on 1 Jan, another pays 6% under contract on level 4-5
visits, a new provider starts in October and ramps up, flu season, and a
small share of claims that are denied and never recovered.

## Known simplifications

- No encounters before Jul 2025. `patients.first_seen_date` carries the
  earlier history, which is what a PM system's registration or first-visit
  date gives you. Without it the first months would look new-patient heavy.
- The PM files are already conformed. A real export needs an entity map.
- `procedure_reference.csv` labels are our own short wording, not AMA CPT
  descriptors. Work RVUs and base rates are rounded illustrative numbers.
- `dx_reference.csv` uses a simple home-made grouping. A deployment loads
  AHRQ's CCSR file instead.
- No income-by-ZIP table. Join ACS table B19013 if you need it.
- FHIR R4 output is not included in 1.0.

# 8. Implementer guide

Step by step, for someone who has never talked to us. You should know
Fabric and Power BI reasonably well. You don't need to know this
repository.

Draft for 1.0. Some steps are thinner than they should be; they're marked.

## 0. Before you touch the practice

Run the whole thing on the sample first, on your own machine:

```
git clone <this repo>
cd practice-data-standard
pip install -r tools/requirements.txt
python tools/run_local.py
```

You should see all nineteen tests pass and twelve Gold tables written
under `_local/gold/Tables`. Open them with anything that reads Delta (DuckDB,
pandas). If the numbers make sense to you, you understand the model.

Read `02`, `03` and `04` before Phase 2. They're the contract.

## 1. Phase 1 with the practice

- Get the decision list out of the owner. Ten lines is fine. "Which payers
  are slow", "should we open Saturdays", "is the second site paying for
  itself".
- Find out what the PM/EHR can export, how often, and in what form. Ask
  the vendor for the export field list. Get one real export file early;
  it will be different from the documentation.
- Risk assessment and BAA before any access. Access through an account the
  practice creates for you, with MFA.

## 2. Tenant setup

1. Fabric capacity in the practice's subscription. Start with a trial or
   the smallest SKU.
2. Three workspaces: `<Practice> - Dev`, `<Practice> - Test`, `<Practice> - Prod`.
3. In Dev, three lakehouses named exactly `lh_bronze`, `lh_silver`,
   `lh_gold`. The notebooks expect those names.
4. Create a repository the practice owns (Azure DevOps or GitHub, their
   account). Copy `fabric/` from here into it. Connect the Dev workspace to
   it with Fabric Git integration and sync. The notebooks, model and report
   appear as items.
5. Deployment pipeline: Dev to Test to Prod.

## 3. Entity map

This is most of the real work. For each file the vendor sends, write down
which column becomes which field in `02`. Put the map in the design note.

Then either:

- (simple) add a small conformance step at the top of `nb_01` that renames
  and reshapes the vendor's columns into the `02` layout, or
- (cleaner) write one small notebook per vendor file that produces the
  `02` layout into a staging folder, and leave `nb_01` as it is.

Things that will be different from the sample: payments and adjustments
come in one transaction table with a type column; denials are a status on
the line rather than a $0 adjustment; plan identifiers are free text with
trailing spaces; dates are in three formats. Conform them; don't loosen
the tests.

## 4. Load and test

1. Land one extract in `lh_bronze/Files/landing/<yyyy-mm-dd>/`, same
   folder layout as `synthetic-data/sample` (`pm/`, `reference/`, and
   `accounting/` if in scope).
2. Set `WORKSPACE` in the parameter cell of each notebook (or pass it from
   the pipeline).
3. Run `nb_01`, `nb_02`, `nb_03` in order. Expect D9 and D15 to fail the
   first time. That's normal; it's what Phase 5 is for.
4. Fix the map, not the thresholds. If you have to loosen a threshold,
   write down why in the design note.

*Pipeline:* 1.0 doesn't include a pipeline definition. Make a Data
Pipeline with three Notebook activities in sequence, on success, plus
whatever copy activity gets the files into landing. Schedule it after the
vendor's export time. (TODO for 1.1: ship the pipeline JSON.)

## 5. Semantic model

`fabric/Practice Model.SemanticModel` is Direct Lake over `lh_gold`. Before
it will open:

1. In `definition/expressions.tmdl`, replace the two placeholders with your
   `lh_gold` SQL analytics endpoint and its ID (Lakehouse > SQL analytics
   endpoint > settings).
2. Sync. Open the model in the service, check every table shows rows.
3. Add RLS and OLS roles for the practice's audiences. **Not included in
   1.0** (see `06`). At least: providers see their own rows in productivity
   views; billing sees everything financial; front desk sees scheduling only.
4. The model has no calculated columns and no Power Query. If you find
   yourself wanting one, it belongs in `nb_03`.

## 6. Report

`fabric/Practice Overview.Report` is a reference report: eight pages
(overview, volume, scheduling, revenue, payers, collections and A/R,
denials). It's there to show the measures in use and give you a starting
layout. Expect to cut it down per audience. Most practices want three or
four pages, not eight.

## 7. Go live and hand over

Follow `05`: reconcile with the administrator, capture baselines (`07`),
publish the app by audience, train by role, run the four handover tasks
with the administrator doing them, not you.

## Known gaps in 1.0

- No pipeline definition (step 4).
- No RLS/OLS roles in the model (step 5).
- Silver is a full overwrite per extract; incremental merge is described in
  `05` but not implemented.
- No practice holiday table. "Working day" in the model means a weekday the
  practice saw patients.
- The financial tables are built in Gold (`fact_expense`) but the reference
  report doesn't use them yet.
- No FHIR R4 input path. The PM export and X12 files are the inputs.

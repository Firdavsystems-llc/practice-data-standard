# fabric/

Fabric items in the layout Fabric Git integration uses, so a workspace can
sync this folder directly.

| Item | What |
|---|---|
| `lh_bronze.Lakehouse`, `lh_silver.Lakehouse`, `lh_gold.Lakehouse` | the three layers (empty definitions; Fabric creates the storage) |
| `nb_01_bronze_to_silver.Notebook` | loads one extract into Silver |
| `nb_02_validate.Notebook` | tests D1-D19, writes `dq_results`, stops on failure |
| `nb_03_build_gold.Notebook` | star schema for the model |
| `Practice Model.SemanticModel` | Direct Lake model over `lh_gold`, TMDL |
| `Practice Overview.Report` | reference report, PBIR |

The notebooks are Python (not PySpark) notebooks. They also run locally:
`python tools/run_local.py`.

The model won't open until `expressions.tmdl` points at your own
`lh_gold` SQL endpoint. See `docs/08-implementer-guide.md`, step 5.

Gold tables the model reads: `dim_date`, `dim_provider`, `dim_location`,
`dim_payer_plan`, `dim_procedure`, `dim_patient`, `dim_denial_reason`,
`fact_claim_line`, `fact_encounter`, `fact_appointment`. Also built but not
in the model: `fact_payment` (cash by posting date) and `fact_expense`.

# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.11"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "lh_bronze"
# META     }
# META   }
# META }

# MARKDOWN ********************

# # 01 Bronze to Silver
# 
# Reads one extract from `lh_bronze` (Files/landing/&lt;extract date&gt;/...), conforms it to the entities in
# `docs/02-data-definitions.md` and writes them to `lh_silver` as Delta tables.
# 
# Nothing is tested here except what has to be known at load time (file hash, raw row counts, type
# failures, excluded lines). Those go to `load_stats`; notebook 02 turns them into D1-D3 and D5 results.
# 
# Python notebook, not Spark. A practice's data fits in memory with room to spare, and the smallest
# capacity runs it fine.

# PARAMETERS CELL ********************

import os

EXTRACT = ""            # landing folder name, e.g. "2026-07-15". Empty = latest
WORKSPACE = ""          # Fabric workspace name, only needed for the silver / gold paths
LOCAL_ROOT = os.environ.get("PDS_LOCAL_ROOT", "")   # tools/run_local.py sets this; leave empty in Fabric

# CELL ********************

import hashlib
import datetime as dt
import pandas as pd
from deltalake import DeltaTable, write_deltalake


def lake(layer):
    if LOCAL_ROOT:
        return f"{LOCAL_ROOT}/{layer}"
    return f"abfss://{WORKSPACE}@onelake.dfs.fabric.microsoft.com/lh_{layer}.Lakehouse"


def storage():
    if LOCAL_ROOT:
        return None
    import notebookutils  # noqa: F401  (available in Fabric)
    return {"bearer_token": notebookutils.credentials.getToken("storage"), "use_fabric_endpoint": "true"}


def files_root():
    # the default lakehouse (lh_bronze) is mounted here in Fabric
    return f"{LOCAL_ROOT}/bronze/Files" if LOCAL_ROOT else "/lakehouse/default/Files"


def write_table(df, layer, name):
    write_deltalake(f"{lake(layer)}/Tables/{name}", df, mode="overwrite", schema_mode="overwrite",
                    storage_options=storage())


def read_table(layer, name):
    try:
        return DeltaTable(f"{lake(layer)}/Tables/{name}", storage_options=storage()).to_pandas()
    except Exception:
        return None

# CELL ********************

landing = os.path.join(files_root(), "landing")
if not EXTRACT:
    EXTRACT = sorted(d for d in os.listdir(landing) if os.path.isdir(os.path.join(landing, d)))[-1]
src = os.path.join(landing, EXTRACT)
run_id = f"{EXTRACT}-{dt.datetime.now():%H%M%S}"
print("extract", EXTRACT, "run", run_id)

# what we expect in every extract; accounting is optional
EXPECTED = {
    "pm/patients.csv": "patient", "pm/providers.csv": "provider", "pm/locations.csv": "location",
    "pm/appointments.csv": "appointment", "pm/encounters.csv": "encounter", "pm/claims.csv": "claim",
    "pm/claim_lines.csv": "claim_line", "pm/payments.csv": "payment", "pm/adjustments.csv": "adjustment",
    "pm/payers.csv": "payer", "pm/payer_plans.csv": "payer_plan", "pm/referrals.csv": "referral",
    "pm/pm_period_totals.csv": "pm_period_totals",
    "reference/payer_contracts.csv": "payer_contract", "reference/procedure_reference.csv": "procedure_reference",
    "reference/dx_reference.csv": "dx_reference",
}
OPTIONAL = {
    "accounting/gl_accounts.csv": "gl_account", "accounting/vendors.csv": "vendor",
    "accounting/expense_transactions.csv": "expense_transaction",
    "accounting/class_service_line_map.csv": "class_service_line_map",
    "accounting/ledger_period_totals.csv": "ledger_period_totals",
}

# CELL ********************

# Declared types per entity. Anything not listed stays text.
DATES = {
    "patient": ["first_seen_date"], "provider": ["active_from", "active_to"],
    "encounter": ["service_date"], "claim": ["submitted_date"], "claim_line": ["service_date"],
    "payment": ["posted_date"], "adjustment": ["posted_date"], "referral": ["referral_date"],
    "payer_contract": ["effective_from", "effective_to"], "expense_transaction": ["posted_date"],
}
TIMESTAMPS = {"appointment": ["created_at", "scheduled_start", "cancelled_at", "checked_in_at"]}
NUMBERS = {
    "claim": ["total_charge"], "claim_line": ["units", "charge", "allowed_amount", "contracted_rate"],
    "payment": ["amount"], "adjustment": ["amount"], "payer_contract": ["rate_per_unit"],
    "procedure_reference": ["work_rvu"], "expense_transaction": ["amount"],
    "pm_period_totals": ["charges", "payments", "adjustments"], "ledger_period_totals": ["amount"],
}
INTS = {"patient": ["birth_year"], "claim_line": ["line_no"]}
BOOLS = {"patient": ["deceased"], "provider": ["is_clinician"], "expense_transaction": ["capital_flag"],
         "class_service_line_map": ["shared"]}
# columns where a failed conversion is a hard failure (D3: keys, dates, amounts)
STRICT = {"service_date", "posted_date", "amount", "charge", "units", "submitted_date"}
VOID_CODES = {"VOID", "MISC", "XXXXX", "99999"}
# reference files often come through unchanged; the repeat check (D1) is on these
TRANSACTIONAL = {"appointment", "encounter", "claim", "claim_line", "payment", "adjustment", "expense_transaction"}

# CELL ********************

def sha1(path):
    h = hashlib.sha1()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def convert(df, entity):
    """Cast declared columns. Returns the frame and a list of (column, failures, strict)."""
    fails = []
    for c in DATES.get(entity, []):
        raw = df[c].replace("", None)
        df[c] = pd.to_datetime(raw, format="%Y-%m-%d", errors="coerce").dt.date
        fails.append((c, int(raw.notna().sum() - df[c].notna().sum()), c in STRICT))
    for c in TIMESTAMPS.get(entity, []):
        raw = df[c].replace("", None)
        df[c] = pd.to_datetime(raw, format="%Y-%m-%d %H:%M", errors="coerce")
        fails.append((c, int(raw.notna().sum() - df[c].notna().sum()), False))
    for c in NUMBERS.get(entity, []):
        raw = df[c].replace("", None)
        df[c] = pd.to_numeric(raw, errors="coerce")
        fails.append((c, int(raw.notna().sum() - df[c].notna().sum()), c in STRICT))
    for c in INTS.get(entity, []):
        raw = df[c].replace("", None)
        df[c] = pd.to_numeric(raw, errors="coerce").astype("Int64")
        fails.append((c, int(raw.notna().sum() - df[c].notna().sum()), False))
    for c in BOOLS.get(entity, []):
        df[c] = df[c].str.lower().map({"true": True, "false": False})
    return df, fails


old_log = read_table("bronze", "load_log")
seen_hashes = set(old_log["file_hash"]) if old_log is not None else set()

stats, log_rows, tables = [], [], {}
for rel, entity in {**EXPECTED, **OPTIONAL}.items():
    path = os.path.join(src, rel)
    if not os.path.exists(path):
        stats.append(dict(run_id=run_id, entity=entity, file=rel, arrived=False, required=rel in EXPECTED,
                          file_hash="", repeat=False, source_rows=0, loaded_rows=0, excluded_rows=0,
                          type_failures=0, strict_type_failures=0, missing_columns=""))
        continue
    h = sha1(path)
    raw = pd.read_csv(path, dtype=str, keep_default_na=False)
    n_src = len(raw)
    df, fails = convert(raw.copy(), entity)
    excluded = 0
    if entity == "claim_line":
        void = df["procedure_code"].isin(VOID_CODES) | (df["charge"].fillna(0).abs() < 0.01)
        excluded = int(void.sum())
        tables["claim_line_excluded"] = df[void].copy()
        df = df[~void].copy()
    tables[entity] = df
    stats.append(dict(run_id=run_id, entity=entity, file=rel, arrived=True, required=rel in EXPECTED,
                      file_hash=h, repeat=entity in TRANSACTIONAL and h in seen_hashes, source_rows=n_src, loaded_rows=len(df),
                      excluded_rows=excluded, type_failures=sum(f for _, f, _ in fails),
                      strict_type_failures=sum(f for _, f, s in fails if s), missing_columns=""))
    log_rows.append(dict(run_id=run_id, extract=EXTRACT, file=rel, file_hash=h, rows=n_src,
                         loaded_at=dt.datetime.now()))

print(pd.DataFrame(stats)[["entity", "arrived", "source_rows", "loaded_rows", "excluded_rows", "type_failures"]].to_string(index=False))

# CELL ********************

# Light conformance that the standard asks for at this layer.
cl = tables["claim_line"]
cl["modifiers"] = cl["modifiers"].fillna("")
p = tables["patient"]
p["sex"] = p["sex"].where(p["sex"].isin(["F", "M", "X"]), "")
tables["payer_plan"]["payer_id"] = tables["payer_plan"]["payer_id"].fillna("")

for entity, df in tables.items():
    write_table(df.reset_index(drop=True), "silver", entity)
write_table(pd.DataFrame(stats), "silver", "load_stats")

log = pd.DataFrame(log_rows)
if old_log is not None:
    log = pd.concat([old_log, log], ignore_index=True)
write_table(log, "bronze", "load_log")
print("silver written:", len(tables), "tables")

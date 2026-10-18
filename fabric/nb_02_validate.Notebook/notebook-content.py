# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.11"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "lh_silver"
# META     }
# META   }
# META }

# MARKDOWN ********************

# # 02 Validate
# 
# Runs tests D1 to D19 from `docs/04-data-quality-tests.md` against Silver, in order, and writes one row per
# test to `dq_results`. Failing rows go to `dq_exceptions_<test>`.
# 
# If any **stop** test fails the notebook raises at the end, so the pipeline never reaches notebook 03 and
# Gold keeps the last good load.
# 
# Thresholds are the defaults from the standard. A deployment tightens them here and records that in its
# design note.

# PARAMETERS CELL ********************

import os

WORKSPACE = ""
LOCAL_ROOT = os.environ.get("PDS_LOCAL_ROOT", "")
EXTRACT_DATE = ""       # yyyy-mm-dd; empty = taken from load_stats

# CELL ********************

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
    import notebookutils  # noqa: F401
    return {"bearer_token": notebookutils.credentials.getToken("storage"), "use_fabric_endpoint": "true"}


def write_table(df, layer, name, mode="overwrite"):
    write_deltalake(f"{lake(layer)}/Tables/{name}", df, mode=mode, schema_mode="overwrite" if mode == "overwrite" else "merge",
                    storage_options=storage())


def read_table(layer, name):
    try:
        return DeltaTable(f"{lake(layer)}/Tables/{name}", storage_options=storage()).to_pandas()
    except Exception:
        return None

# CELL ********************

S = {}
for name in ["load_stats", "patient", "provider", "location", "appointment", "encounter", "claim", "claim_line",
             "payment", "adjustment", "payer", "payer_plan", "pm_period_totals", "procedure_reference", "dx_reference",
             "expense_transaction", "class_service_line_map", "ledger_period_totals"]:
    S[name] = read_table("silver", name)

stats = S["load_stats"]
run_id = stats["run_id"].iloc[0]
if not EXTRACT_DATE:
    EXTRACT_DATE = run_id[:10]
asof = dt.date.fromisoformat(EXTRACT_DATE)
has_books = S["expense_transaction"] is not None

results, exceptions = [], {}


def record(test, entity, checked, failed, metric, threshold, outcome, detail=""):
    results.append(dict(run_id=run_id, run_at=dt.datetime.now(), test_id=test, entity=entity, checked=float(checked),
                        failed=float(failed), metric=float(metric), threshold=str(threshold), outcome=outcome,
                        detail=detail[:300]))
    print(f"{test:<4} {outcome:<5} {entity:<20} metric={metric:.4f}  {detail[:90]}")


def share(failed, checked):
    return failed / checked if checked else 0.0

# CELL ********************

# D1 extract arrival
req = stats[stats["required"]]
missing = req[~req["arrived"]]["file"].tolist()
empty = req[req["arrived"] & (req["source_rows"] == 0)]["file"].tolist()
repeat = stats[stats["repeat"]]["file"].tolist()
bad = len(missing) + len(empty) + len(repeat)
record("D1", "*", len(req), bad, bad, "all present, no repeat", "stop" if bad else "pass",
       f"missing={missing} empty={empty} repeat={repeat}" if bad else f"{len(req)} files")

# D2 row counts: source rows = loaded + excluded (D5)
arr = stats[stats["arrived"]]
off = arr[arr["source_rows"] != arr["loaded_rows"] + arr["excluded_rows"]]
record("D2", "*", int(arr["source_rows"].sum()), len(off), len(off), "exact", "stop" if len(off) else "pass",
       "; ".join(f"{r.entity}: {r.source_rows} vs {r.loaded_rows}+{r.excluded_rows}" for r in off.itertuples()))

# D3 schema and types
strict = int(arr["strict_type_failures"].sum())
other = int(arr["type_failures"].sum()) - strict
rate = share(other, int(arr["source_rows"].sum()))
out = "stop" if strict or rate > 0.001 else "pass"
record("D3", "*", int(arr["source_rows"].sum()), strict + other, rate, "0 strict; <=0.1% other", out,
       f"strict={strict} other={other}")

# D4 key completeness
enc, cl, clm = S["encounter"], S["claim_line"], S["claim"]
miss = int(enc["patient_id"].isna().sum() + enc["service_date"].isna().sum() + (enc["patient_id"] == "").sum()
           + cl["line_id"].isna().sum() + cl["claim_id"].isna().sum() + clm["claim_id"].isna().sum())
record("D4", "encounter/claim", len(enc) + len(cl) + len(clm), miss, miss, "0", "stop" if miss else "pass")

# D5 void and empty lines
ex = int(stats.loc[stats["entity"] == "claim_line", "excluded_rows"].sum())
src = int(stats.loc[stats["entity"] == "claim_line", "source_rows"].sum())
rate = share(ex, src)
record("D5", "claim_line", src, ex, rate, "<=2% excluded", "warn" if rate > 0.02 else "pass", f"{ex} lines excluded")

# D6 key uniqueness
KEYS = {"patient": ["patient_id"], "provider": ["provider_id", "active_from"], "location": ["location_id"],
        "appointment": ["appointment_id"], "encounter": ["encounter_id"], "claim": ["claim_id"],
        "claim_line": ["line_id"], "payment": ["payment_id"], "adjustment": ["adjustment_id"],
        "payer": ["payer_id"], "payer_plan": ["plan_id"], "procedure_reference": ["procedure_code"]}
dups = {k: int(S[k].duplicated(v).sum()) for k, v in KEYS.items() if S[k] is not None}
n = sum(dups.values())
record("D6", "*", sum(len(S[k]) for k in dups), n, n, "0", "stop" if n else "pass",
       ", ".join(f"{k}={v}" for k, v in dups.items() if v))

# D7 sign convention
viol = int((cl["charge"] < 0).sum() + (S["payment"]["amount"] < 0).sum() + (S["adjustment"]["amount"] < 0).sum())
record("D7", "claim_line/payment/adjustment", len(cl) + len(S["payment"]) + len(S["adjustment"]), viol, viol, "0",
       "stop" if viol else "pass")

# CELL ********************

# D8 referential integrity of claim lines
line = cl.merge(clm[["claim_id", "encounter_id", "plan_id"]], on="claim_id", how="left") \
         .merge(enc[["encounter_id", "location_id"]], on="encounter_id", how="left")
ok = (line["encounter_id"].isin(enc["encounter_id"])
      & line["plan_id"].isin(S["payer_plan"]["plan_id"])
      & line["rendering_provider_id"].isin(S["provider"]["provider_id"])
      & line["location_id"].isin(S["location"]["location_id"]))
rate = ok.mean()
out = "stop" if rate < 0.98 else "warn" if rate < 0.995 else "pass"
record("D8", "claim_line", len(line), int((~ok).sum()), rate, ">=99.5% (stop <98%)", out)
if (~ok).any():
    exceptions["D8"] = line.loc[~ok, ["line_id", "claim_id", "rendering_provider_id", "plan_id", "location_id"]]

# D9 payer-plan mapping
pp = S["payer_plan"]
mapped_plans = set(pp.loc[pp["payer_id"].fillna("") != "", "plan_id"])
m = line["plan_id"].isin(mapped_plans)
by_lines, by_dollars = m.mean(), line.loc[m, "charge"].sum() / line["charge"].sum()
out = "stop" if by_lines < 0.98 or by_dollars < 0.99 else "pass"
record("D9", "payer_plan", len(line), int((~m).sum()), by_lines, ">=98% lines, >=99% $", out,
       f"lines {by_lines:.2%}, dollars {by_dollars:.2%}")
if (~m).any():
    exceptions["D9"] = (line[~m].groupby("plan_id").agg(lines=("line_id", "count"), charges=("charge", "sum"))
                        .reset_index().merge(pp[["plan_id", "plan_name"]], on="plan_id", how="left"))

# D10 code reference coverage
pc = line["procedure_code"].isin(S["procedure_reference"]["procedure_code"]).mean()
dx = clm["diagnosis_codes"].fillna("").str.split("|").explode()
dx = dx[dx != ""]
dc = dx.isin(S["dx_reference"]["dx_code"]).mean() if len(dx) else 1.0
rate = min(pc, dc)
record("D10", "claim_line/claim", len(line), int(round((1 - rate) * len(line))), rate, ">=99%",
       "warn" if rate < 0.99 else "pass", f"procedure {pc:.2%}, diagnosis {dc:.2%}")

# D11 unknown attributes
unk = (line["place_of_service"].fillna("") == "") | line["location_id"].isna() | (line["rendering_provider_id"].fillna("") == "")
rate = unk.mean()
record("D11", "claim_line", len(line), int(unk.sum()), rate, "<=2%", "warn" if rate > 0.02 else "pass")

# D12 date logic
pay = S["payment"].merge(cl[["line_id", "service_date"]], on="line_id", how="left")
bad_future = (line["service_date"] > asof).sum()
cs = clm.merge(enc[["encounter_id", "service_date"]], on="encounter_id", how="left")
bad_claim = (cs["submitted_date"] < cs["service_date"]).sum()
bad_pay = (pay["posted_date"] < pay["service_date"]).sum()
n_bad = int(bad_future + bad_claim + bad_pay)
rate = share(n_bad, len(line) + len(cs) + len(pay))
out = "stop" if rate > 0.01 else "warn" if rate > 0.001 else "pass"
record("D12", "claim_line/claim/payment", len(line) + len(cs) + len(pay), n_bad, rate, "<=0.1% (stop >1%)", out,
       f"future={int(bad_future)} claim before service={int(bad_claim)} payment before service={int(bad_pay)}")
if bad_pay:
    exceptions["D12"] = pay.loc[pay["posted_date"] < pay["service_date"], ["payment_id", "line_id", "posted_date", "service_date"]]

# D13 payment classification
okp = S["payment"]["source"].isin(["primary", "secondary", "patient"]).mean()
record("D13", "payment", len(S["payment"]), int(round((1 - okp) * len(S["payment"]))), okp, "100%",
       "stop" if okp < 1 else "pass")

# D14 value ranges
pt = S["patient"]
age = asof.year - pt["birth_year"]
bad_age = ((age < 0) | (age > 120)).sum()
bad_units = (cl["units"] <= 0).sum()
rate = share(int(bad_age + bad_units), len(pt) + len(cl))
record("D14", "patient/claim_line", len(pt) + len(cl), int(bad_age + bad_units), rate, "<=0.5%",
       "warn" if rate > 0.005 else "pass", f"age out of range={int(bad_age)} (set empty in Gold), units<=0={int(bad_units)}")

# CELL ********************

# D15 PM/EHR reconciliation: charges by service month, payments and adjustments by posting month
tot = S["pm_period_totals"].set_index("period")
ours = pd.DataFrame({
    "charges": cl.groupby(pd.to_datetime(cl["service_date"]).dt.strftime("%Y-%m"))["charge"].sum(),
    "payments": S["payment"].groupby(pd.to_datetime(S["payment"]["posted_date"]).dt.strftime("%Y-%m"))["amount"].sum(),
    "adjustments": S["adjustment"].groupby(pd.to_datetime(S["adjustment"]["posted_date"]).dt.strftime("%Y-%m"))["amount"].sum(),
}).reindex(tot.index).fillna(0)
worst, fails = 0.0, []
for col in ["charges", "payments", "adjustments"]:
    diff = (ours[col] - tot[col]).abs()
    pct = diff / tot[col].where(tot[col] != 0)
    for period in tot.index:
        if pct[period] > 0.005 or diff[period] > 500:
            fails.append(f"{period} {col} off by {diff[period]:,.2f} ({pct[period]:.2%})")
        worst = max(worst, float(pct[period] if pd.notna(pct[period]) else 0))
record("D15", "pm_period_totals", len(tot) * 3, len(fails), worst, "within 0.5% and $500 per month",
       "stop" if fails else "pass", "; ".join(fails) if fails else f"largest difference {worst:.2%}")

# D16 / D17 only with the books
if has_books:
    ex_ = S["expense_transaction"]
    ours = ex_.groupby([ex_["gl_account"], pd.to_datetime(ex_["posted_date"]).dt.strftime("%Y-%m")])["amount"].sum()
    led = S["ledger_period_totals"].set_index(["account", "period"])["amount"]
    diff = (ours.reindex(led.index).fillna(0) - led).abs()
    nf = int((diff > 1).sum())
    record("D16", "expense_transaction", len(led), nf, float(diff.max()), "within $1 per account per period",
           "stop" if nf else "pass")
    cmap = S["class_service_line_map"]
    used = set(ex_["class_name"])
    ok_cls = set(cmap.loc[cmap["service_line"].fillna("") != "", "class_name"]) | set(cmap.loc[cmap["shared"], "class_name"])
    unm = sorted(used - ok_cls)
    record("D17", "class_service_line_map", len(used), len(unm), len(unm), "100% mapped or shared",
           "stop" if unm else "pass", ", ".join(unm))

# D18 freshness
latest = max(S["payment"]["posted_date"].max(), S["appointment"]["created_at"].max().date())
lag = (asof - latest).days
record("D18", "*", 1, int(lag > 1), lag, "<=1 day behind", "alert" if lag > 1 else "pass", f"latest source date {latest}")

# D19 volume anomaly: last complete month vs trailing six
months = pd.to_datetime(enc["service_date"]).dt.to_period("M")
counts = months.value_counts().sort_index()
last_complete = (pd.Period(asof, "M") - 1)
if last_complete in counts.index and len(counts.loc[:last_complete]) >= 7:
    trailing = counts.loc[:last_complete].iloc[-7:-1].mean()
    dev = counts[last_complete] / trailing - 1
    record("D19", "encounter", int(counts[last_complete]), int(abs(dev) > 0.3), dev, "within 30%",
           "warn" if abs(dev) > 0.3 else "pass", f"{last_complete}: {counts[last_complete]} vs {trailing:.0f}")
else:
    record("D19", "encounter", 0, 0, 0, "within 30%", "pass", "not enough history yet")

# CELL ********************

res = pd.DataFrame(results)
old = read_table("silver", "dq_results")
write_table(pd.concat([old, res], ignore_index=True) if old is not None else res, "silver", "dq_results")
for test, df in exceptions.items():
    write_table(df.reset_index(drop=True).astype(str), "silver", f"dq_exceptions_{test.lower()}")

stops = res[res["outcome"] == "stop"]
print(res["outcome"].value_counts().to_dict())
if len(stops):
    raise RuntimeError("Stop test(s) failed, Gold not refreshed: " + ", ".join(stops["test_id"]))

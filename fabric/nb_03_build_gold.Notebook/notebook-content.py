# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "jupyter",
# META     "jupyter_kernel_name": "python3.11"
# META   },
# META   "dependencies": {
# META     "lakehouse": {
# META       "default_lakehouse_name": "lh_gold"
# META     }
# META   }
# META }

# MARKDOWN ********************

# # 03 Build Gold
# 
# Builds the star schema the semantic model reads in Direct Lake mode. Every derived field the measures
# need (payment status, A/R bucket, lead time, new patient, ...) is computed here, so the model has no
# calculated columns and no Power Query.
# 
# Only runs after 02 passed. Definitions follow `docs/03-measure-catalogue.md`; where this notebook makes a
# choice the catalogue leaves open, the comment says so.

# PARAMETERS CELL ********************

import os

WORKSPACE = ""
LOCAL_ROOT = os.environ.get("PDS_LOCAL_ROOT", "")
EXTRACT_DATE = ""

# CELL ********************

import datetime as dt
import numpy as np
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


def read_table(layer, name):
    try:
        return DeltaTable(f"{lake(layer)}/Tables/{name}", storage_options=storage()).to_pandas()
    except Exception:
        return None


def write_table(df, name):
    write_deltalake(f"{lake('gold')}/Tables/{name}", df.reset_index(drop=True), mode="overwrite",
                    schema_mode="overwrite", storage_options=storage())
    print(f"{name:<22} {len(df):>8,} rows")

# CELL ********************

S = {n: read_table("silver", n) for n in [
    "load_stats", "patient", "provider", "location", "appointment", "encounter", "claim", "claim_line", "payment",
    "adjustment", "payer", "payer_plan", "referral", "procedure_reference", "dx_reference",
    "expense_transaction", "gl_account", "class_service_line_map"]}
if not EXTRACT_DATE:
    EXTRACT_DATE = S["load_stats"]["run_id"].iloc[0][:10]
ASOF = pd.Timestamp(EXTRACT_DATE)

enc, clm, cl = S["encounter"].copy(), S["claim"].copy(), S["claim_line"].copy()
pay, adj = S["payment"].copy(), S["adjustment"].copy()
for df, cols in ((enc, ["service_date"]), (clm, ["submitted_date"]), (cl, ["service_date"]),
                 (pay, ["posted_date"]), (adj, ["posted_date"])):
    for c in cols:
        df[c] = pd.to_datetime(df[c])

# CELL ********************

# ---- dimensions
start = min(enc["service_date"].min(), pd.Timestamp(S["appointment"]["scheduled_start"].min()).normalize())
days = pd.date_range(start.replace(day=1), ASOF, freq="D")
month_end = days + pd.offsets.MonthEnd(0)
last_complete = (ASOF.replace(day=1) - pd.Timedelta(days=1)).replace(day=1)
dim_date = pd.DataFrame({
    "date": days.date,
    "year": days.year,
    "month_start": days.to_period("M").to_timestamp().date,
    "year_month": days.strftime("%Y-%m"),
    "month_label": days.strftime("%m/%y"),
    "day_of_week": days.strftime("%a"),
    "day_of_week_no": days.weekday + 1,
    "is_working_day": days.weekday < 5,           # practice holidays are not in the extract; see 08
    "is_complete_month": month_end < ASOF,
    # a month is "settled" when most of its claims have had time to pay (60 days)
    "is_settled_month": month_end <= ASOF - pd.Timedelta(days=60),
    "is_recent_12": days.to_period("M").to_timestamp() >= (last_complete - pd.DateOffset(months=11)),
})

prov = S["provider"].sort_values("active_from").drop_duplicates("provider_id", keep="last")
dim_provider = prov[["provider_id", "provider_name", "role", "specialty", "is_clinician", "home_location_id"]]
dim_location = S["location"][["location_id", "location_name", "city", "state"]]

pp = S["payer_plan"].merge(S["payer"], on="payer_id", how="left")
pp["payer_name"] = pp["payer_name"].fillna("Unmapped")
pp["payer_class"] = pp["payer_class"].fillna("Unmapped")
dim_payer_plan = pp[["plan_id", "plan_name", "payer_id", "payer_name", "payer_class", "product_type"]]

pr = S["procedure_reference"].copy()
pr["code_and_label"] = pr["procedure_code"] + "  " + pr["label"]
lvl = {"99202": "Level 2", "99203": "Level 3", "99204": "Level 4", "99205": "Level 5", "99211": "Level 1",
       "99212": "Level 2", "99213": "Level 3", "99214": "Level 4", "99215": "Level 5"}
pr["em_level"] = pr["procedure_code"].map(lvl).fillna("")
dim_procedure = pr[["procedure_code", "label", "code_and_label", "category", "em_level", "work_rvu"]]

# our own short labels for the CARCs we see; the full text is X12's
DENIAL_REASONS = [
    ("197", "Authorization missing", "Authorization"), ("27", "Coverage ended", "Eligibility"),
    ("16", "Claim missing information", "Billing error"), ("22", "Other insurer is primary", "Eligibility"),
    ("50", "Not medically necessary", "Medical necessity"), ("204", "Not a covered benefit", "Coverage"),
    ("29", "Filed too late", "Billing error"), ("252", "Records or attachment needed", "Documentation"),
    ("109", "Wrong payer", "Eligibility"), ("97", "Bundled into another service", "Coding"),
]
dim_denial_reason = pd.DataFrame(DENIAL_REASONS, columns=["reason_code", "reason_label", "reason_category"])

# CELL ********************

# ---- patients
pt = S["patient"].copy()
pt["age"] = ASOF.year - pt["birth_year"]
pt.loc[(pt["age"] < 0) | (pt["age"] > 120), "age"] = pd.NA            # D14: out of range -> empty
pt["age_band"] = pd.cut(pt["age"].astype("float"), [-1, 17, 44, 64, 74, 200],
                        labels=["0-17", "18-44", "45-64", "65-74", "75+"]).astype(str).replace("nan", "Unknown")
pt["race_group"] = pt["race"].fillna("").replace("", "Not recorded")
ref = S["referral"]
first_ref = ref[ref["outcome"] == "seen"].sort_values("referral_date").drop_duplicates("patient_id")
pt = pt.merge(first_ref[["patient_id", "referring_org"]], on="patient_id", how="left")
pt["referral_source"] = pt["referring_org"].fillna("No referral on file")
dim_patient = pt[["patient_id", "sex", "age", "age_band", "race_group", "ethnicity", "coverage_type", "home_zip",
                  "first_seen_date", "referral_source"]].astype({"age": "Int64"})

# CELL ********************

# ---- claim lines
line = cl.merge(clm[["claim_id", "encounter_id", "plan_id", "submitted_date", "status"]], on="claim_id", how="left") \
         .merge(enc[["encounter_id", "patient_id", "location_id"]], on="encounter_id", how="left") \
         .merge(dim_payer_plan[["plan_id", "payer_id", "payer_class"]], on="plan_id", how="left") \
         .rename(columns={"status": "claim_status"})

# collected at the visit (D13): patient payments on insured claims within 7 days of service
pay = pay.merge(line[["line_id", "service_date", "payer_class"]], on="line_id", how="left")
pay["collected_at_visit"] = ((pay["source"] == "patient") & (pay["payer_class"] != "Self-pay")
                             & ((pay["posted_date"] - pay["service_date"]).dt.days <= 7))
pay["counted"] = pay["amount"] >= 1                                     # postings under $1 are not payments
pc = pay[pay["counted"]]
paid = pc.pivot_table(index="line_id", columns="source", values="amount", aggfunc="sum", fill_value=0)
for c in ["primary", "secondary", "patient"]:
    if c not in paid:
        paid[c] = 0.0
paid = paid.rename(columns={"primary": "paid_primary", "secondary": "paid_secondary", "patient": "paid_patient"})
paid["paid_amount"] = paid[["paid_primary", "paid_secondary", "paid_patient"]].sum(axis=1)
all_paid = pay.groupby("line_id")["amount"].sum().rename("posted_total")      # includes the < $1 postings
timed = pc[~pc["collected_at_visit"]]
first_last = timed.groupby("line_id")["posted_date"].agg(first_payment="min", last_payment="max")
ins = pc[pc["source"] == "primary"].groupby("line_id")["posted_date"].min().rename("first_insurer_payment")

a = adj.pivot_table(index="line_id", columns="adjustment_type", values="amount", aggfunc="sum", fill_value=0)
for c in ["contractual", "denial", "write_off", "other"]:
    if c not in a:
        a[c] = 0.0
a = a.rename(columns={"contractual": "contractual_amount", "write_off": "writeoff_amount", "other": "other_adj_amount"})
den = adj[adj["adjustment_type"] == "denial"].sort_values("posted_date").drop_duplicates("line_id")
den = den.set_index("line_id")[["reason_code", "posted_date"]].rename(columns={"reason_code": "denial_reason_code",
                                                                                "posted_date": "first_denial"})
den_wo = adj[(adj["adjustment_type"] == "write_off") & (adj["group_code"] == "CO")].groupby("line_id")["amount"].sum() \
    .rename("denial_writeoff_amount")

line = line.set_index("line_id").join([paid, all_paid, first_last, ins, a[["contractual_amount", "writeoff_amount",
                                       "other_adj_amount"]], den, den_wo]).reset_index()
for c in ["paid_primary", "paid_secondary", "paid_patient", "paid_amount", "posted_total", "contractual_amount",
          "writeoff_amount", "other_adj_amount", "denial_writeoff_amount"]:
    line[c] = line[c].fillna(0.0)
line["balance"] = (line["charge"] - line["posted_total"] - line["contractual_amount"] - line["writeoff_amount"]
                   - line["other_adj_amount"]).round(2)
line["is_open"] = line["balance"] > 0.01
line["denied_first_pass"] = line["first_denial"].notna() & (line["first_insurer_payment"].isna()
                                                            | (line["first_denial"] <= line["first_insurer_payment"]))

# usual payment time per payer: 90th percentile of days from submission to first insurer payment
line["days_to_insurer"] = (line["first_insurer_payment"] - line["submitted_date"]).dt.days
p90 = line.groupby("payer_id")["days_to_insurer"].quantile(0.9).rename("payer_p90")
line = line.merge(p90, left_on="payer_id", right_index=True, how="left")
self_pay = line["payer_class"] == "Self-pay"


def status(r):
    if not r.is_open:
        if r.paid_amount > 0:
            return "Paid"
        return "Written off" if r.writeoff_amount > 0 else "Paid"
    if r.self_pay:
        return "Patient balance"
    if r.allowed_amount == 0 and pd.notna(r.allowed_amount):
        return "Paid at zero"
    if pd.notna(r.first_denial) and r.paid_primary == 0:
        return "Denied"
    if r.paid_primary > 0 or r.paid_secondary > 0:
        return "Patient balance"
    return "Awaiting payment"


line["self_pay"] = self_pay
line["payment_status"] = [status(r) for r in line.itertuples()]
waited = (ASOF - line["submitted_date"]).dt.days
line["requires_action"] = line["is_open"] & (
    line["payment_status"].isin(["Denied", "Paid at zero"])
    | ((line["payment_status"] == "Awaiting payment") & (waited > line["payer_p90"].fillna(45))))

# revenue at risk basis: average paid for the same code and payer over the trailing 12 months
recent = line[(line["paid_amount"] > 0) & (line["service_date"] > ASOF - pd.DateOffset(months=12))]
exp_pay = recent.groupby(["procedure_code", "payer_id"])["paid_amount"].mean().rename("expected_payment")
line = line.merge(exp_pay, left_on=["procedure_code", "payer_id"], right_index=True, how="left")
line["expected_payment"] = line["expected_payment"].fillna(0.0).where(line["requires_action"], 0.0)

age = (ASOF - line["service_date"]).dt.days
line["ar_age_days"] = age.where(line["is_open"])
line["ar_bucket"] = np.select([~line["is_open"], age <= 30, age <= 60, age <= 90, age <= 120],
                              ["Closed", "0-30", "31-60", "61-90", "91-120"], "120+")
line["ar_bucket_no"] = np.select([~line["is_open"], age <= 30, age <= 60, age <= 90, age <= 120], [9, 1, 2, 3, 4], 5)
line["days_to_first_payment"] = (line["first_payment"] - line["service_date"]).dt.days
line["days_to_last_payment"] = (line["last_payment"] - line["service_date"]).dt.days
d1 = line["days_to_first_payment"]
line["paid_within"] = np.select([d1.isna(), d1 <= 30, d1 <= 60, d1 <= 90, d1 <= 180],
                                ["Not paid", "0-30 days", "31-60 days", "61-90 days", "91-180 days"], "180+ days")
line["paid_within_no"] = np.select([d1.isna(), d1 <= 30, d1 <= 60, d1 <= 90, d1 <= 180], [9, 1, 2, 3, 4], 5)
line = line.merge(dim_procedure[["procedure_code", "work_rvu"]], on="procedure_code", how="left")
clin = set(dim_provider.loc[dim_provider["is_clinician"], "provider_id"])
line["work_rvus"] = (line["work_rvu"].fillna(0) * line["units"]).where(line["rendering_provider_id"].isin(clin), 0.0)

fact_claim_line = line[[
    "line_id", "claim_id", "encounter_id", "patient_id", "plan_id", "location_id", "rendering_provider_id",
    "procedure_code", "service_date", "submitted_date", "units", "charge", "allowed_amount", "contracted_rate",
    "paid_amount", "paid_primary", "paid_secondary", "paid_patient", "contractual_amount", "writeoff_amount",
    "denial_writeoff_amount", "other_adj_amount", "balance", "is_open", "payment_status", "requires_action",
    "expected_payment", "ar_age_days", "ar_bucket", "ar_bucket_no", "denied_first_pass", "denial_reason_code",
    "days_to_first_payment", "days_to_last_payment", "paid_within", "paid_within_no", "work_rvus", "claim_status"]].copy()
fact_claim_line["service_date"] = fact_claim_line["service_date"].dt.date
fact_claim_line["submitted_date"] = fact_claim_line["submitted_date"].dt.date
fact_claim_line["denied_first_pass"] = fact_claim_line["denied_first_pass"].astype(bool)
fact_claim_line["units"] = fact_claim_line["units"].astype(float)   # decimal in the standard, even if this sample has whole units
for c in ["ar_age_days", "days_to_first_payment", "days_to_last_payment"]:
    fact_claim_line[c] = fact_claim_line[c].astype("Int64")

# CELL ********************

# ---- encounters
WORST = ["Denied", "Paid at zero", "Awaiting payment", "Patient balance", "Written off", "Paid"]
rank = {s: i for i, s in enumerate(WORST)}
lst = line.assign(r=line["payment_status"].map(rank))
enc_status = lst.groupby("encounter_id")["r"].min().map(dict(enumerate(WORST))).rename("payment_status")
office_codes = {"99202", "99203", "99204", "99205", "99211", "99212", "99213", "99214", "99215"}
office = line[line["procedure_code"].isin(office_codes) & (line["place_of_service"] == "11")]["encounter_id"].unique()
em = line[line["procedure_code"].isin(office_codes)].groupby("encounter_id")["procedure_code"].max().str[-1]
rvu = line.groupby("encounter_id")["work_rvus"].sum()

e = enc.merge(clm[["encounter_id", "plan_id"]].drop_duplicates("encounter_id"), on="encounter_id", how="left") \
       .merge(pt[["patient_id", "first_seen_date"]], on="patient_id", how="left")
e["is_telehealth"] = e["place_of_service"].isin(["02", "10"])
e["is_office"] = e["encounter_id"].isin(office)
e["is_new_patient"] = e["service_date"].dt.date == pd.to_datetime(e["first_seen_date"]).dt.date
e = e.set_index("encounter_id").join([enc_status, em.rename("em_level_max"), rvu.rename("work_rvus")]).reset_index()
e["payment_status"] = e["payment_status"].fillna("Not billed")
e["work_rvus"] = e["work_rvus"].fillna(0.0)
e["em_level_max"] = e["em_level_max"].fillna("")
e["plan_id"] = e["plan_id"].fillna("")
e["service_date"] = e["service_date"].dt.date
fact_encounter = e[["encounter_id", "patient_id", "provider_id", "location_id", "plan_id", "service_date", "service_line",
                    "place_of_service", "is_telehealth", "is_office", "is_new_patient", "em_level_max",
                    "payment_status", "work_rvus"]]

# CELL ********************

# ---- appointments
ap = S["appointment"].copy()
# payer for scheduling views: the plan the patient is billed under most often
usual_plan = clm.merge(enc[["encounter_id", "patient_id"]], on="encounter_id").groupby("patient_id")["plan_id"] \
    .agg(lambda s: s.value_counts().index[0])
ap = ap.merge(usual_plan.rename("plan_id"), left_on="patient_id", right_index=True, how="left")
ap["plan_id"] = ap["plan_id"].fillna("")
ap["appointment_date"] = ap["scheduled_start"].dt.date
late = (ap["status"] == "cancelled_patient") & ((ap["scheduled_start"] - ap["cancelled_at"]) < pd.Timedelta(hours=24))
ap["is_late_cancel"] = late
ap["is_missed"] = ap["status"].isin(["no_show", "left_unseen"]) | late
ap["outcome"] = np.select([ap["is_missed"], ap["status"] == "kept", ap["status"] == "cancelled_patient",
                           ap["status"] == "cancelled_office"],
                          ["Missed", "Kept", "Cancelled by patient", "Cancelled by office"], "Other")
lead = (ap["scheduled_start"].dt.normalize() - ap["created_at"].dt.normalize()).dt.days
ap["lead_time_days"] = lead.astype("Int64")
ap["lead_time_bucket"] = np.select([lead <= 0, lead <= 7, lead <= 14, lead <= 30, lead <= 60],
                                   ["Same day", "1-7 days", "8-14 days", "15-30 days", "31-60 days"], "Over 60 days")
ap["lead_time_bucket_no"] = np.select([lead <= 0, lead <= 7, lead <= 14, lead <= 30, lead <= 60], [1, 2, 3, 4, 5], 6)
ap["is_digital_cancel"] = (ap["status"] == "cancelled_patient") & ap["cancel_channel"].isin(["portal", "reminder"])
fact_appointment = ap[["appointment_id", "patient_id", "provider_id", "location_id", "plan_id", "appointment_date",
                       "appointment_type", "status", "outcome", "is_missed", "is_late_cancel", "lead_time_days",
                       "lead_time_bucket", "lead_time_bucket_no", "cancel_channel", "is_digital_cancel", "encounter_id"]]

# ---- payments (cash view, by posting date)
fp = pay.merge(line[["line_id", "plan_id", "location_id", "rendering_provider_id"]], on="line_id", how="left")
fp["service_date"] = fp["service_date"].dt.date
fp["posted_date"] = fp["posted_date"].dt.date
fact_payment = fp[["payment_id", "line_id", "plan_id", "location_id", "rendering_provider_id", "service_date",
                   "posted_date", "source", "amount", "collected_at_visit", "counted"]]

# CELL ********************

# ---- financial (only with the books)
if S["expense_transaction"] is not None:
    x = S["expense_transaction"].merge(S["class_service_line_map"], on="class_name", how="left") \
        .merge(S["gl_account"], left_on="gl_account", right_on="account", how="left")
    x["service_line"] = np.where(x["shared"].fillna(False), "Shared", x["service_line"])
    fact_expense = x[["transaction_id", "gl_account", "account_name", "account_type", "vendor_id", "class_name",
                      "service_line", "location_id", "posted_date", "amount", "capital_flag"]]
else:
    fact_expense = None

# CELL ********************

for name, df in [("dim_date", dim_date), ("dim_provider", dim_provider), ("dim_location", dim_location),
                 ("dim_payer_plan", dim_payer_plan), ("dim_procedure", dim_procedure), ("dim_patient", dim_patient),
                 ("dim_denial_reason", dim_denial_reason), ("fact_claim_line", fact_claim_line),
                 ("fact_encounter", fact_encounter), ("fact_appointment", fact_appointment),
                 ("fact_payment", fact_payment), ("fact_expense", fact_expense)]:
    if df is not None:
        write_table(df, name)

"""Synthetic data for the open edition.

Riverbend Family Health is an invented two-site family practice. Nothing in
the output comes from a real practice. Patients, providers, payers, plans and
amounts are all generated from the lists in refdata.py.

    python generate.py                       # rebuilds ./sample (what is committed)
    python generate.py --out out --seed 7    # anything else goes to ./out (git-ignored)

Standard library only. Same seed and dates give the same files byte for byte.

The files are already in the conformed shape of docs/02-data-definitions.md.
A real deployment gets there with an entity map from its vendor's export
columns; here we skip that step so the tests and the model can run directly.
"""
import argparse
import csv
import datetime as dt
import math
import os
import random
from collections import defaultdict

from refdata import *  # noqa: F401,F403

D = dt.timedelta
iso = dt.date.fromisoformat


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample"))
    ap.add_argument("--start", default="2025-07-01")
    ap.add_argument("--end", default="2026-06-30")
    ap.add_argument("--as-of", default="2026-07-15", help="extract date; nothing is posted after it")
    ap.add_argument("--seed", type=int, default=20261018)
    ap.add_argument("--x12-month", default="2026-03", help="month written out as flattened 837P / 835")
    return ap.parse_args()


A = parse_args()
R = random.Random(A.seed)
START, END, ASOF = iso(A.start), iso(A.end), iso(A.as_of)
HOL = {iso(h) for h in HOLIDAYS}


def workday(d):
    return d.weekday() < 5 and d not in HOL


def next_workday(d):
    while not workday(d):
        d += D(1)
    return d


def wpick(pairs):
    items, weights = zip(*pairs)
    return R.choices(items, weights=weights, k=1)[0]


def lognorm_days(median, spread=0.45, lo=1):
    return max(lo, int(round(median * math.exp(R.gauss(0, spread)))))


def money(x):
    return round(x + 1e-9, 2)


def age_on(birth_year, d):
    return d.year - birth_year


PROC = {p[0]: p for p in PROCEDURES}
PLAN = {p[0]: p for p in PLANS}
PAYER = {p[0]: p for p in PAYERS}
PROV = {p[0]: p for p in PROVIDERS}
SEASON = {1: 1.12, 2: 1.10, 3: 1.02, 4: 0.96, 5: 0.95, 6: 0.90, 7: 0.86, 8: 0.92, 9: 1.00, 10: 1.05, 11: 1.03, 12: 0.90}

# ---------------------------------------------------------------- patients
patients = {}
panel = {"L01": [], "L02": []}
_pid = [310_000]


def new_patient(loc, d=None):
    _pid[0] += R.randint(1, 3)
    pid = str(_pid[0])
    band = wpick([((1, 17), 14), ((18, 44), 31), ((45, 64), 30), ((65, 74), 14), ((75, 94), 11)])
    ref = d or START
    by = ref.year - R.randint(*band)
    age = ref.year - by
    if age >= 65:
        plan = wpick([("MCB-VA", 56), ("MAA-PPO", 12), ("MAA-HMO", 9), ("MAB-HMO", 10), ("MAB-DSNP", 4),
                      ("COMA-PPO", 3), ("BLA-PPO", 3), ("FEPA-STD", 3)])
    elif age < 18:
        plan = wpick([("MCOA-01", 14), ("MCOA-02", 8), ("MCOB-01", 9), ("MCD-FFS", 3), ("COMA-PPO", 12),
                      ("COMA-HMO", 6), ("COMB-CHOICE", 9), ("COMC-OAP", 7), ("BLA-PPO", 12), ("BLB-PPO", 7),
                      ("FEPA-STD", 6), ("MIL-SEL", 4), ("SELF", 3)])
    else:
        plan = wpick([("MCOA-01", 7), ("MCOB-01", 5), ("MCD-FFS", 2), ("COMA-PPO", 10), ("COMA-HMO", 4),
                      ("COMA-POS", 3), ("COMA-HDHP", 6), ("COMB-CHOICE", 8), ("COMB-OPT", 4), ("COMC-OAP", 6),
                      ("COMC-LOC", 3), ("BLA-PPO", 11), ("BLA-HMO", 4), ("BLA-OOA", 2), ("BLB-PPO", 7),
                      ("BLB-HDHP", 4), ("FEPA-STD", 6), ("FEPA-BAS", 2), ("MIL-SEL", 3), ("SELF", 5)])
    sec = ""
    if plan == "MCB-VA" and R.random() < 0.62:
        sec = wpick([("SUPA-G", 70), ("SUPA-N", 30)])
    chronic = [c for c, prev, min_age in CHRONIC if age >= min_age and R.random() < prev * (1.6 if age >= 65 else 1.0)]
    recorded = R.random() < 0.7
    p = dict(patient_id=pid, birth_year=by, sex=wpick([("F", 53), ("M", 46), ("X", 0.4), ("", 0.6)]),
             race=wpick([("White", 46), ("Black or African American", 22), ("Asian", 15),
                         ("Some other race", 9), ("Two or more races", 8)]) if recorded else "",
             ethnicity=wpick([("Hispanic or Latino", 17), ("Not Hispanic or Latino", 83)]) if recorded else "",
             coverage_type=PLAN[plan][4], home_zip=wpick(ZIPS[loc]), deceased=False,
             _plan=plan, _sec=sec, _loc=loc, _chronic=chronic, _seen=None, _last_phys=None,
             _visit_w=(0.6 + 0.35 * len(chronic)) * (1.4 if age >= 65 else 1.0))
    # plans that only show up later go to new patients after the date
    if d and plan in ("COMA-PPO", "BLA-PPO"):
        for up, since in UNMAPPED_FROM.items():
            if d >= iso(since) and R.random() < 0.3 and UNMAPPED_PRICED_AS[up] == PLAN[plan][2]:
                p["_plan"] = up
    patients[pid] = p
    panel[loc].append(pid)
    return p


for loc, n in (("L01", 1550), ("L02", 1050)):
    for _ in range(n):
        p = new_patient(loc)
        p["_seen"] = START - D(R.randint(30, 900))   # established before the sample starts
# one bad birth year for D14
patients[panel["L02"][17]]["birth_year"] = 1899

# ---------------------------------------------------------------- appointments, encounters
appointments, encounters, referrals = [], [], []
_aid, _eid, _rid = [600_000], [800_000], [1000]
TYPE_W = [("Follow-Up Visit", 46), ("Sick Visit", 13), ("Annual Physical", 11), ("Telehealth Visit", 10),
          ("New Patient Visit", 0), ("Procedure Visit", 3)]
LEAD = {"Follow-Up Visit": 16, "Sick Visit": 1, "Annual Physical": 42, "Medicare Wellness": 38,
        "Telehealth Visit": 4, "New Patient Visit": 19, "Procedure Visit": 11, "Nurse Visit": 3}
SLINE = {"Follow-Up Visit": "Primary care", "Sick Visit": "Primary care", "Telehealth Visit": "Primary care",
         "New Patient Visit": "Primary care", "Annual Physical": "Preventive", "Medicare Wellness": "Preventive",
         "Procedure Visit": "Procedures", "Nurse Visit": "Nurse visit"}
NEW_PER_DAY = {"L01": 2.4, "L02": 2.0}


def pick_patient(loc, d, kind):
    pool = panel[loc]
    for _ in range(40):
        p = patients[R.choice(pool)]
        if p["_seen"] is None or p["_seen"] > d:
            continue
        if kind == "phys":
            if p["_last_phys"] and (d - p["_last_phys"]).days < 330:
                continue
        if R.random() < min(1.0, p["_visit_w"] / 2.2):
            return p
    return patients[R.choice([x for x in pool if patients[x]["_seen"] and patients[x]["_seen"] <= d] or pool)]


def visit_time(d, slot, n):
    mins = 8 * 60 + int(slot * (8.5 * 60) / max(n, 1))
    if mins >= 12 * 60:
        mins += 30   # lunch
    return dt.datetime.combine(d, dt.time(mins // 60, mins % 60 // 15 * 15))


d = START
while d <= END:
    if workday(d):
        for prov in PROVIDERS:
            pid_, name, role, spec, clin, loc, since, until, slots, _ = prov
            if d < iso(since) or (until and d > iso(until)):
                continue
            n = int(round(slots * SEASON[d.month] * R.uniform(0.85, 1.08)))
            if pid_ == "P04" and d < iso(since) + D(70):
                n = int(n * (0.45 + 0.55 * (d - iso(since)).days / 70))   # new provider ramping up
            if R.random() < 0.035:
                continue   # provider out that day
            new_today = 0
            for s in range(n):
                if role == "RN":
                    atype = "Nurse Visit"
                    p = pick_patient(loc, d, "any")
                else:
                    want_new = new_today < 1 and R.random() < NEW_PER_DAY[loc] / 3 / max(n, 1) * 3
                    if want_new:
                        atype = "New Patient Visit"
                        p = new_patient(loc, d)
                        new_today += 1
                    else:
                        atype = wpick(TYPE_W) if loc == "L01" else wpick(TYPE_W[:-1])
                        p = pick_patient(loc, d, "phys" if atype == "Annual Physical" else "any")
                        if atype == "Annual Physical" and age_on(p["birth_year"], d) >= 65 and PLAN[p["_plan"]][5] in ("mcr", "ma"):
                            atype = "Medicare Wellness"
                start_ts = visit_time(d, s, n)
                lead = 0 if (atype == "Sick Visit" and R.random() < 0.55) else lognorm_days(LEAD[atype], 0.6, 0)
                created = start_ts - D(days=lead, hours=R.randint(1, 9))
                if created.date() < START - D(120):
                    created = dt.datetime.combine(START - D(120), dt.time(10, 0))
                # outcome: longer waits go wrong more often
                risk = 1 + min(lead, 60) / 40
                if p["coverage_type"] in ("Medicaid", "Medicaid managed care"):
                    risk *= 1.45
                r = R.random()
                ns, cp, co, lu = 0.040 * risk, 0.075 * risk, 0.022, 0.004
                if atype == "Telehealth Visit":
                    ns *= 0.6
                status = ("no_show" if r < ns else "cancelled_patient" if r < ns + cp else
                          "cancelled_office" if r < ns + cp + co else "left_unseen" if r < ns + cp + co + lu else "kept")
                if start_ts.date() > ASOF:
                    status = "kept"
                _aid[0] += R.randint(1, 2)
                a = dict(appointment_id=str(_aid[0]), patient_id=p["patient_id"], provider_id=pid_, location_id=loc,
                         appointment_type=atype, created_at=created, scheduled_start=start_ts, status=status,
                         cancelled_at="", cancel_channel="", checked_in_at="", encounter_id="")
                if status.startswith("cancelled"):
                    hrs = R.choice([2, 5, 14, 20]) if R.random() < 0.27 else R.randint(26, 24 * 9)
                    ca = start_ts - D(hours=hrs)
                    a["cancelled_at"] = max(ca, created + D(hours=1))
                    a["cancel_channel"] = ("phone" if status == "cancelled_office" else
                                           wpick([("portal", 33), ("reminder", 27), ("phone", 34), ("in_person", 6)]))
                if status in ("kept", "left_unseen"):
                    a["checked_in_at"] = start_ts - D(minutes=R.randint(-12, 25))
                if status == "kept":
                    _eid[0] += R.randint(1, 2)
                    pos = "11"
                    if atype == "Telehealth Visit":
                        pos = "10" if R.random() < 0.85 else "02"
                    e = dict(encounter_id=str(_eid[0]), patient_id=p["patient_id"], provider_id=pid_, location_id=loc,
                             service_date=d, service_line=SLINE[atype], modality="", place_of_service=pos,
                             _atype=atype, _new=p["_seen"] is None, _p=p)
                    if p["_seen"] is None:
                        p["_seen"] = d
                        if R.random() < 0.34:
                            who, org = R.choice(REFERRERS)
                            _rid[0] += 1
                            referrals.append(dict(referral_id=f"R{_rid[0]}", patient_id=p["patient_id"],
                                                  referring_provider=who, referring_org=org,
                                                  referral_date=(created - D(days=R.randint(0, 8))).date(),
                                                  service_requested="New patient, primary care", outcome="seen"))
                            e["_ref"] = who
                    if atype in ("Annual Physical", "Medicare Wellness"):
                        p["_last_phys"] = d
                    if R.random() < 0.004:
                        e["place_of_service"] = ""   # unknown, for D11
                    encounters.append(e)
                    a["encounter_id"] = e["encounter_id"]
                appointments.append(a)
    d += D(1)

# referrals that never turned into a visit
for _ in range(int(len(referrals) * 0.18)):
    who, org = R.choice(REFERRERS)
    loc = wpick([("L01", 6), ("L02", 4)])
    p = new_patient(loc, START + D(R.randint(0, (END - START).days)))
    _rid[0] += 1
    rd = START + D(R.randint(0, (END - START).days))
    referrals.append(dict(referral_id=f"R{_rid[0]}", patient_id=p["patient_id"], referring_provider=who,
                          referring_org=org, referral_date=rd, service_requested="New patient, primary care",
                          outcome=wpick([("declined", 4), ("open", 5), ("scheduled", 2)]) if (ASOF - rd).days < 45 else "declined"))

# ---------------------------------------------------------------- coding
EM_EST = {"Follow-Up Visit": [("99212", 8), ("99213", 47), ("99214", 38), ("99215", 7)],
          "Sick Visit": [("99212", 18), ("99213", 60), ("99214", 20), ("99215", 2)],
          "Telehealth Visit": [("99212", 15), ("99213", 60), ("99214", 25)]}
EM_NEW = [("99202", 5), ("99203", 45), ("99204", 42), ("99205", 8)]


def bump(code_pairs, intensity):
    out = []
    for c, w in code_pairs:
        lvl = int(c[-1])
        out.append((c, w * (intensity ** (lvl - 3))))
    return out


def prev_code(age, new):
    if age < 5:
        return "99392"
    if age < 12:
        return "99383" if new else "99393"
    if age < 18:
        return "99384" if new else "99394"
    if age < 40:
        return "99385" if new else "99395"
    if age < 65:
        return "99386" if new else "99396"
    return "99387" if new else "99397"


def flu_season(d):
    return (d.month >= 10) or (d.month <= 2) or (d.month == 9 and d.day >= 15)


def code_encounter(e):
    p, t, d = e["_p"], e["_atype"], e["service_date"]
    age = age_on(p["birth_year"], d)
    kind = PLAN[p["_plan"]][5]
    inten = PROV[e["provider_id"]][9]
    lines, dx = [], []
    if t == "Nurse Visit":
        if flu_season(d) and R.random() < 0.5:
            lines += [("90686", ""), ("90471", "")]
            dx = ["Z23"]
        else:
            lines.append(("99211", ""))
            if R.random() < 0.25:
                lines.append(("36415", ""))
            dx = [p["_chronic"][0] if p["_chronic"] else "I10"]
        return lines, dx
    if t in ("Annual Physical", "Medicare Wellness"):
        if t == "Medicare Wellness":
            lines.append(("G0438" if R.random() < 0.12 else "G0439", ""))
            dx = ["Z00.00"]
        else:
            lines.append((prev_code(age, False), ""))
            dx = ["Z00.129" if age < 18 else wpick([("Z00.00", 70), ("Z00.01", 30)])]
            if R.random() < 0.5:
                lines.append(("96127", ""))
        if p["_chronic"] and R.random() < 0.12 and age >= 18:
            lines.append(("99213", "25"))
        dx += p["_chronic"][:2]
        if R.random() < 0.35 and age >= 18:
            lines.append(("36415", ""))
    elif t == "Procedure Visit":
        code = wpick([("20610", 35), ("11102", 25), ("17110", 25), ("94010", 15)])
        lines.append((code, ""))
        dx = [{"20610": "M25.561", "11102": "D48.5", "17110": "B07.9", "94010": "J45.909"}[code]]
        if R.random() < 0.3:
            lines.insert(0, ("99213", "25"))
    else:
        if t == "New Patient Visit":
            lines.append((wpick(bump(EM_NEW, inten)), ""))
        else:
            lines.append((wpick(bump(EM_EST[t], inten)), "95" if t == "Telehealth Visit" else ""))
        if t == "Sick Visit":
            acute = wpick(ACUTE)
            dx = [acute] + p["_chronic"][:1]
            if acute == "J02.9" and R.random() < 0.7:
                lines.append(("87880", ""))
            if acute == "N39.0":
                lines.append(("81002", ""))
        else:
            dx = (p["_chronic"][:3] if p["_chronic"] else [wpick(ACUTE)])
            if kind in ("mcr", "ma") and t != "Telehealth Visit" and R.random() < 0.45:
                lines.append(("G2211", ""))
            if t != "Telehealth Visit":
                if R.random() < 0.22:
                    lines.append(("36415", ""))
                if age >= 45 and R.random() < 0.06:
                    lines.append(("93000", ""))
                if R.random() < 0.08:
                    lines.append(("96127", ""))
            if "F17.210" in p["_chronic"] and R.random() < 0.4:
                lines.append(("99406", ""))
    if flu_season(d) and t != "Telehealth Visit" and R.random() < 0.2 and not any(c == "90686" for c, _ in lines):
        lines += [("90686", ""), ("90471", "")]
        dx.append("Z23")
    seen = []
    for x in dx:
        if x not in seen:
            seen.append(x)
    return lines, seen[:4]


# ---------------------------------------------------------------- rates
def rate_factor(payer, d):
    f = RATE_FACTOR[payer]
    if payer == RATE_CHANGE[0] and d >= iso(RATE_CHANGE[1]):
        f *= RATE_CHANGE[2]
    return f


def contract_rate(plan, code, d):
    payer = PLAN[plan][2] or UNMAPPED_PRICED_AS[plan]
    if payer in ("PY99", "PY14"):
        return None
    return money(PROC[code][3] * rate_factor(payer, d))


contracts = []
for plan in PLANS:
    pid_, _, payer, _, _, kind = plan
    if kind in ("self", "sup") or not payer:
        continue
    for code in PROC:
        if payer == RATE_CHANGE[0]:
            contracts.append(dict(plan_id=pid_, procedure_code=code, rate_per_unit=contract_rate(pid_, code, iso("2025-12-31")),
                                  effective_from="2025-01-01", effective_to="2025-12-31"))
            contracts.append(dict(plan_id=pid_, procedure_code=code, rate_per_unit=contract_rate(pid_, code, iso("2026-01-01")),
                                  effective_from="2026-01-01", effective_to=""))
        else:
            contracts.append(dict(plan_id=pid_, procedure_code=code, rate_per_unit=contract_rate(pid_, code, START),
                                  effective_from="2025-01-01", effective_to=""))

# ---------------------------------------------------------------- claims and adjudication
claims, lines_out, payments, adjustments = [], [], [], []
remits = []   # rows for the flattened 835
_cid, _lid, _payid, _adjid = [5_000_000], [9_000_000], [100_000], [400_000]
deductible_used = defaultdict(float)


def payday(payer, d):
    wd = PAYER_PAYDAY.get(payer, 2)
    while d.weekday() != wd or d in HOL:
        d += D(1)
    return d


def remit_ref(payer, d):
    return f"{int(payer[2:]):02d}{d:%y%m%d}{(int(payer[2:]) * 7919 + d.toordinal()) % 9000 + 1000}"


def post_payment(line, source, amount, when, ref=""):
    if when > ASOF:
        return False
    _payid[0] += 1
    payments.append(dict(payment_id=f"PM{_payid[0]}", line_id=line["line_id"], source=source, amount=money(amount),
                         posted_date=when, remit_ref=ref))
    return True


def post_adj(line, group, reason, amount, when, atype, remark=""):
    if when > ASOF:
        return False
    _adjid[0] += 1
    adjustments.append(dict(adjustment_id=f"AJ{_adjid[0]}", line_id=line["line_id"], group_code=group,
                            reason_code=reason, remark_codes=remark, amount=money(amount), posted_date=when,
                            adjustment_type=atype))
    return True


def patient_pays(line, amount, svc, at_visit_p=0.8):
    if amount < 0.005:
        return
    if R.random() < at_visit_p:
        post_payment(line, "patient", amount, svc + D(R.choice([0, 0, 0, 1, 2])))
    elif R.random() < 0.72:
        post_payment(line, "patient", amount, svc + D(lognorm_days(48, 0.5, 15)))
    elif (ASOF - svc).days > 150:
        post_adj(line, "", "WO-COLL", amount, svc + D(R.randint(140, 170)), "write_off")


def patient_share(plan, code, allowed, pt, year, mod):
    kind = PLAN[plan][5]
    if code in PREVENTIVE_ZERO_PR or allowed <= 0:
        return 0.0, ""
    if kind in ("mcd", "mil"):
        return 0.0, ""
    if kind == "mcr":
        key = (pt, year)
        left = max(0.0, 260 - deductible_used[key])     # illustrative Part B deductible
        ded = min(left, allowed)
        deductible_used[key] += ded
        return money(ded + 0.2 * (allowed - ded)), "PR-1" if ded else "PR-2"
    if kind == "ma":
        return (10.0 if code.startswith("992") else 0.0), "PR-3"
    if kind == "hdhp":
        key = (pt, year)
        left = max(0.0, 2400 - deductible_used[key])
        ded = min(left, allowed)
        deductible_used[key] += ded
        return money(ded + 0.2 * (allowed - ded)), "PR-1" if ded else "PR-2"
    # ppo / hmo / pos: copay on the visit line only
    if code.startswith("992") and mod != "25":
        return float({"PY07": 30, "PY08": 25, "PY09": 35, "PY10": 25, "PY11": 30, "PY12": 20}.get(PLAN[plan][2] or "PY07", 30)), "PR-3"
    return 0.0, ""


for e in encounters:
    p = e["_p"]
    plan = p["_plan"]
    svc = e["service_date"]
    codes, dx = code_encounter(e)
    payer = PLAN[plan][2] or UNMAPPED_PRICED_AS.get(plan, "")
    kind = PLAN[plan][5]
    _cid[0] += R.randint(1, 3)
    days_to_bill = lognorm_days(2.5, 0.75, 0)
    if R.random() < 0.04:
        days_to_bill += R.randint(10, 40)
    sub = next_workday(svc + D(days_to_bill))
    rendering = SUPERVISING if e["provider_id"] == "P05" else e["provider_id"]
    claim = dict(claim_id=str(_cid[0]), encounter_id=e["encounter_id"], plan_id=plan,
                 referring_provider=e.get("_ref", ""), diagnosis_codes="|".join(dx),
                 submitted_date=sub if sub <= ASOF else "", status="", total_charge=0.0,
                 _payer=payer, _kind=kind, _sec=p["_sec"], _lines=[])
    if R.random() < 0.0035:
        codes.append(("VOID", ""))   # junk line, excluded by D5
    for i, (code, mod) in enumerate(codes, 1):
        _lid[0] += 1
        ch = PROC[code][4] if code in PROC else 0.0
        units = 1
        ln = dict(line_id=f"{_lid[0]}", claim_id=claim["claim_id"], line_no=i, service_date=svc, procedure_code=code,
                  modifiers=mod, units=units, charge=money(ch), allowed_amount="", contracted_rate="",
                  rendering_provider_id=rendering, place_of_service=e["place_of_service"])
        if code in PROC and kind not in ("self",):
            cr = contract_rate(plan, code, svc)
            ln["contracted_rate"] = cr if cr is not None else ""
        if R.random() < 0.0012:
            ln["rendering_provider_id"] = "P99"   # not in the provider table, for D8
        claim["_lines"].append(ln)
        claim["total_charge"] += ln["charge"]
    claim["total_charge"] = money(claim["total_charge"])
    claims.append(claim)
    lines_out.extend(claim["_lines"])

    real_lines = [ln for ln in claim["_lines"] if ln["procedure_code"] in PROC]
    if not claim["submitted_date"]:
        claim["status"] = "not_billed"
        continue

    # ------------- self-pay
    if kind == "self":
        for ln in real_lines:
            disc = money(ln["charge"] * 0.45)
            post_adj(ln, "", "SP-DISC", disc, svc, "other")
            patient_pays(ln, ln["charge"] - disc, svc, 0.7)
        continue

    # ------------- insured
    lag = lognorm_days(PAYER_LAG[payer], 0.35, 6)
    if R.random() < 0.012:   # clearinghouse rejection, fixed and resent
        claim["_rejected"] = True
        if (ASOF - sub).days < 6:
            continue
        sub2 = next_workday(sub + D(R.randint(2, 6)))
    else:
        sub2 = sub
    remit_day = payday(payer, sub2 + D(lag))
    denied = R.random() < (0.085 if payer not in ("PY05", "PY06", "PY03") else 0.13)
    if denied:
        carc, _, recover, _ = R.choices(DENIALS, weights=[x[1] for x in DENIALS], k=1)[0]
        ref = remit_ref(payer, remit_day)
        for ln in real_lines:
            if post_adj(ln, "CO", carc, 0.0, remit_day, "denial", REMARK.get(carc, "")):
                remits.append((ref, payer, remit_day, claim, ln, 0.0, 0.0, [("CO", carc, ln["charge"])], REMARK.get(carc, "")))
        claim["_denied"] = carc
        if R.random() < recover:
            resub = next_workday(remit_day + D(lognorm_days(18, 0.6, 3)))
            remit_day = payday(payer, resub + D(lognorm_days(PAYER_LAG[payer], 0.3, 6)))
            if remit_day > ASOF:
                continue
        else:
            wo = remit_day + D(R.randint(35, 120))
            for ln in real_lines:
                post_adj(ln, "CO", carc, ln["charge"], wo, "write_off")
            continue
    if remit_day > ASOF:
        continue
    ref = remit_ref(payer, remit_day)
    for ln in real_lines:
        code = ln["procedure_code"]
        cr = ln["contracted_rate"] or 0.0
        allowed = cr * ln["units"]
        zero = (payer == "PY03" and code == "G2211" and R.random() < 0.3) or (payer == "PY09" and code == "36415" and R.random() < 0.5)
        if zero:
            ln["allowed_amount"] = 0.0
            post_adj(ln, "CO", "97", 0.0, remit_day, "denial", "M15")
            remits.append((ref, payer, remit_day, claim, ln, 0.0, 0.0, [("CO", "97", ln["charge"])], "M15"))
            if R.random() < 0.7:
                post_adj(ln, "CO", "97", ln["charge"], remit_day + D(R.randint(20, 75)), "write_off")
            continue
        if payer == UNDERPAY[0] and code in UNDERPAY[1]:
            allowed = allowed * UNDERPAY[2]
        if R.random() < 0.01:
            allowed *= R.choice([0.9, 0.95, 1.05])   # odd adjudication, should not move the current rate
        allowed = money(allowed)
        ln["allowed_amount"] = allowed
        pr, prtag = patient_share(plan, code, allowed, p["patient_id"], svc.year, ln["modifiers"])
        pr = min(pr, allowed)
        paid = money(allowed - pr)
        contractual = money(ln["charge"] - allowed)
        post_payment(ln, "primary", paid, remit_day, ref)
        post_adj(ln, "CO", "45", contractual, remit_day, "contractual")
        cas = [("CO", "45", contractual)]
        if pr > 0:
            cas.append(("PR", prtag.split("-")[1], pr))
        remits.append((ref, PAYER[payer][0], remit_day, claim, ln, allowed, paid, cas, ""))
        if pr > 0:
            if claim["_sec"] and prtag != "PR-1":
                when = payday("PY14", remit_day + D(lognorm_days(PAYER_LAG["PY14"], 0.3, 4)))
                post_payment(ln, "secondary", pr, when, remit_ref("PY14", when))
            elif claim["_sec"]:
                ded_part = min(pr, 260)
                patient_pays(ln, ded_part, remit_day, 0.0)
            else:
                patient_pays(ln, pr, svc, 0.82 if prtag == "PR-3" else 0.15)

# a couple of payments keyed with the wrong date (D12)
for pm in R.sample(payments, 3):
    pm["posted_date"] = pm["posted_date"] - D(400)

# ---------------------------------------------------------------- claim status at the extract date
paid_by_line, adj_by_line, den_by_line = defaultdict(float), defaultdict(float), defaultdict(list)
for pm in payments:
    paid_by_line[pm["line_id"]] += pm["amount"]
for aj in adjustments:
    adj_by_line[aj["line_id"]] += aj["amount"]
    if aj["adjustment_type"] == "denial":
        den_by_line[aj["line_id"]].append(aj)
for c in claims:
    if c["status"] == "not_billed":
        c["status"] = ""
        continue
    ls = [ln for ln in c["_lines"] if ln["procedure_code"] in PROC]
    bal = sum(ln["charge"] - paid_by_line[ln["line_id"]] - adj_by_line[ln["line_id"]] for ln in ls)
    ins_paid = any(paid_by_line[ln["line_id"]] > 0 for ln in ls)
    if c.get("_rejected") and not ins_paid and not any(den_by_line[ln["line_id"]] for ln in ls) and (ASOF - c["submitted_date"]).days < 6:
        c["status"] = "rejected"
    elif abs(bal) < 0.01:
        c["status"] = "closed"
    elif any(den_by_line[ln["line_id"]] for ln in ls) and not ins_paid:
        c["status"] = "denied"
    elif ins_paid and any(ln["allowed_amount"] == 0.0 for ln in ls):
        c["status"] = "paid_zero"
    elif ins_paid:
        c["status"] = "patient_balance" if c["_kind"] in ("ppo", "hdhp", "mcr", "ma") else "partially_paid"
    else:
        c["status"] = "submitted"

# ---------------------------------------------------------------- accounting
months = []
m = dt.date(START.year, START.month, 1)
while m <= END:
    months.append(m)
    m = dt.date(m.year + (m.month == 12), m.month % 12 + 1, 1)
enc_by_month_loc = defaultdict(int)
for e in encounters:
    enc_by_month_loc[(e["service_date"].replace(day=1), e["location_id"])] += 1
flu_by_month = defaultdict(int)
for ln in lines_out:
    if ln["procedure_code"] == "90686":
        flu_by_month[ln["service_date"].replace(day=1)] += 1

expenses = []
_xid = [70_000]


def exp(acct, vendor, cls, day, amount, capital=False, memo=""):
    _xid[0] += 1
    expenses.append(dict(transaction_id=f"X{_xid[0]}", gl_account=acct, vendor_id=vendor, class_name=cls,
                         posted_date=day, amount=money(amount), capital_flag=capital, memo=memo))


for m in months:
    last = (m.replace(day=28) + D(4)).replace(day=1) - D(1)
    for loc, pre in (("L01", "MAIN"), ("L02", "WEST")):
        vol = enc_by_month_loc[(m, loc)]
        clin = {"L01": 2, "L02": 1 + (m >= iso("2025-10-01"))}[loc]
        exp("6000", "V10", f"{pre}-PC", last, clin * 21500 * R.uniform(0.98, 1.02), memo="payroll")
        exp("6000", "V10", f"{pre}-PREV", last, clin * 2600 * R.uniform(0.95, 1.05), memo="payroll")
        exp("6020", "V10", f"{pre}-PC", last, clin * 4900 * R.uniform(0.97, 1.03), memo="benefits")
        exp("6100", "V04" if loc == "L01" else "V05", f"{pre}-PC", m, 9800 if loc == "L01" else 7400, memo="rent")
        exp("6200", "V01", f"{pre}-PC", m + D(R.randint(3, 20)), vol * R.uniform(5.5, 7.0))
        exp("6300", "V03", f"{pre}-PC", m + D(R.randint(10, 25)), vol * R.uniform(2.0, 3.2))
        exp("6600", "V09", f"{pre}-PC", m + D(R.randint(8, 14)), R.uniform(650, 1100))
        if loc == "L01":
            exp("6000", "V10", "MAIN-NURSE", last, 6900 * R.uniform(0.98, 1.02), memo="payroll")
            exp("6200", "V01", "MAIN-PROC", m + D(R.randint(3, 20)), R.uniform(400, 900))
    if flu_by_month[m] or m.month in (8, 9):
        doses = flu_by_month[m] or 0
        exp("6210", "V02", "MAIN-PREV", m + D(5), (doses + (220 if m.month == 8 else 0)) * 16.4)
    exp("6010", "V10", "SHARED", (m.replace(day=28) + D(4)).replace(day=1) - D(1), 23800 * R.uniform(0.98, 1.02), memo="payroll")
    exp("6400", "V06", "SHARED", m, 1850)
    exp("6410", "V07", "SHARED", m + D(2), 1250)
    exp("6500", "V08", "SHARED", m, 3100)
    if m.month in (3, 9):
        exp("6700", "V12", "SHARED", m + D(12), R.uniform(1500, 2800))
    if R.random() < 0.25:
        exp("6800", "V11", "MAIN-PROC", m + D(R.randint(5, 25)), R.uniform(180, 700))
exp("1500", "V11", "MAIN-PROC", iso("2025-09-22"), 3980.00, True, "spirometer")
exp("1500", "V11", "MAIN-PC", iso("2026-02-10"), 6450.00, True, "ECG unit")
exp("1500", "V11", "WEST-PC", iso("2026-04-06"), 6450.00, True, "ECG unit")

# ---------------------------------------------------------------- write
os.makedirs(A.out, exist_ok=True)


def fmt(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dt.datetime):
        return v.strftime("%Y-%m-%d %H:%M")
    if isinstance(v, dt.date):
        return v.isoformat()
    if isinstance(v, float):
        return f"{v:.2f}"
    return v


def write(folder, name, rows, cols):
    path = os.path.join(A.out, folder)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, name), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(cols)
        for r in rows:
            w.writerow([fmt(r.get(c, "")) for c in cols])
    return len(rows)


counts = {}
for p in patients.values():
    p["first_seen_date"] = p["_seen"] or ""
pm = "pm"
counts["patients"] = write(pm, "patients.csv", patients.values(),
                           ["patient_id", "birth_year", "sex", "race", "ethnicity", "coverage_type", "home_zip", "first_seen_date", "deceased"])
counts["providers"] = write(pm, "providers.csv",
                            [dict(provider_id=p[0], provider_name=p[1], role=p[2], specialty=p[3], is_clinician=p[4],
                                  home_location_id=p[5], active_from=p[6], active_to=p[7]) for p in PROVIDERS],
                            ["provider_id", "provider_name", "role", "specialty", "is_clinician", "home_location_id", "active_from", "active_to"])
counts["locations"] = write(pm, "locations.csv",
                            [dict(zip(["location_id", "location_name", "city", "state", "zip", "service_lines"], l)) for l in LOCATIONS],
                            ["location_id", "location_name", "city", "state", "zip", "service_lines"])
counts["appointments"] = write(pm, "appointments.csv", appointments,
                               ["appointment_id", "patient_id", "provider_id", "location_id", "appointment_type", "created_at",
                                "scheduled_start", "status", "cancelled_at", "cancel_channel", "checked_in_at", "encounter_id"])
counts["encounters"] = write(pm, "encounters.csv", encounters,
                             ["encounter_id", "patient_id", "provider_id", "location_id", "service_date", "service_line", "modality", "place_of_service"])
counts["claims"] = write(pm, "claims.csv", [c for c in claims if c["submitted_date"]],
                         ["claim_id", "encounter_id", "plan_id", "referring_provider", "diagnosis_codes", "submitted_date", "status", "total_charge"])
billed = {c["claim_id"] for c in claims if c["submitted_date"]}
counts["claim_lines"] = write(pm, "claim_lines.csv", [ln for ln in lines_out if ln["claim_id"] in billed],
                              ["line_id", "claim_id", "line_no", "service_date", "procedure_code", "modifiers", "units", "charge",
                               "allowed_amount", "contracted_rate", "rendering_provider_id", "place_of_service"])
counts["payments"] = write(pm, "payments.csv", payments, ["payment_id", "line_id", "source", "amount", "posted_date", "remit_ref"])
counts["adjustments"] = write(pm, "adjustments.csv", adjustments,
                              ["adjustment_id", "line_id", "group_code", "reason_code", "remark_codes", "amount", "posted_date", "adjustment_type"])
counts["payers"] = write(pm, "payers.csv", [dict(payer_id=p[0], payer_name=p[1], payer_class=p[2]) for p in PAYERS],
                         ["payer_id", "payer_name", "payer_class"])
counts["payer_plans"] = write(pm, "payer_plans.csv",
                              [dict(plan_id=p[0], plan_name=p[1], payer_id=p[2], product_type=p[3],
                                    contract_ref=("C-" + p[2]) if p[2] and p[5] not in ("self", "sup") else "") for p in PLANS],
                              ["plan_id", "plan_name", "payer_id", "product_type", "contract_ref"])
counts["referrals"] = write(pm, "referrals.csv", referrals,
                            ["referral_id", "patient_id", "referring_provider", "referring_org", "referral_date", "service_requested", "outcome"])

# PM/EHR month-end totals for D15 (what the vendor's own month-end report says)
tot = defaultdict(lambda: [0.0, 0.0, 0.0])
for ln in lines_out:
    if ln["claim_id"] in billed and ln["procedure_code"] in PROC:
        tot[ln["service_date"].replace(day=1)][0] += ln["charge"]
for p_ in payments:
    tot[p_["posted_date"].replace(day=1)][1] += p_["amount"]
for aj in adjustments:
    tot[aj["posted_date"].replace(day=1)][2] += aj["amount"]
pm_tot = []
for k in sorted(tot):
    if START <= k <= END:
        c_, p_, a_ = tot[k]
        if k == iso("2026-02-01"):
            p_ *= 1.0018   # vendor report includes a late posting we don't have
        pm_tot.append(dict(period=k.strftime("%Y-%m"), charges=money(c_), payments=money(p_), adjustments=money(a_)))
write(pm, "pm_period_totals.csv", pm_tot, ["period", "charges", "payments", "adjustments"])

ref = "reference"
write(ref, "payer_contracts.csv", contracts, ["plan_id", "procedure_code", "rate_per_unit", "effective_from", "effective_to"])
write(ref, "procedure_reference.csv",
      [dict(procedure_code=p[0], label=p[1], work_rvu=f"{p[2]:.2f}", category=p[5]) for p in PROCEDURES],
      ["procedure_code", "label", "work_rvu", "category"])
write(ref, "dx_reference.csv", [dict(dx_code=k, dx_group=v[0]) for k, v in DX.items()], ["dx_code", "dx_group"])

acc = "accounting"
write(acc, "gl_accounts.csv", [dict(account=g[0], account_name=g[1], account_type=g[2]) for g in GL],
      ["account", "account_name", "account_type"])
write(acc, "vendors.csv", [dict(vendor_id=v[0], vendor_name=v[1], category=v[2]) for v in VENDORS], ["vendor_id", "vendor_name", "category"])
write(acc, "class_service_line_map.csv",
      [dict(class_name=c[0], service_line=c[1], location_id=c[2], shared=c[1] == "Shared") for c in CLASSES],
      ["class_name", "service_line", "location_id", "shared"])
counts["expenses"] = write(acc, "expense_transactions.csv", expenses,
                           ["transaction_id", "gl_account", "vendor_id", "class_name", "posted_date", "amount", "capital_flag", "memo"])
led = defaultdict(float)
for x in expenses:
    led[(x["gl_account"], x["posted_date"].strftime("%Y-%m"))] += x["amount"]
write(acc, "ledger_period_totals.csv",
      [dict(account=a, period=p_, amount=money(v)) for (a, p_), v in sorted(led.items())], ["account", "period", "amount"])

# ---------------------------------------------------------------- flattened X12 for one month
ym = A.x12_month
lines_by_claim = defaultdict(list)
for ln in lines_out:
    lines_by_claim[ln["claim_id"]].append(ln)
c837 = []
for c in claims:
    if not c["submitted_date"] or c["submitted_date"].strftime("%Y-%m") != ym:
        continue
    e_dx = c["diagnosis_codes"].split("|")
    for ln in lines_by_claim[c["claim_id"]]:
        c837.append(dict(clm01_claim_id=c["claim_id"], clm02_total_charge=c["total_charge"], clm05_pos=ln["place_of_service"],
                         clm05_freq="1", billing_provider="RIVERBEND FAMILY HEALTH", payer_plan_id=c["plan_id"],
                         patient_id="",
                         hi_dx1=e_dx[0] if len(e_dx) > 0 else "", hi_dx2=e_dx[1] if len(e_dx) > 1 else "",
                         hi_dx3=e_dx[2] if len(e_dx) > 2 else "", hi_dx4=e_dx[3] if len(e_dx) > 3 else "",
                         lx_line_no=ln["line_no"], ref6r_line_id=ln["line_id"], sv101_procedure=ln["procedure_code"],
                         sv101_modifiers=ln["modifiers"], sv102_charge=ln["charge"], sv104_units=ln["units"],
                         sv107_dx_pointer="1", dtp472_service_date=ln["service_date"],
                         nm182_rendering=ln["rendering_provider_id"], nm1dn_referring=c["referring_provider"]))
enc_pt = {e["encounter_id"]: e["patient_id"] for e in encounters}
claim_enc = {c["claim_id"]: c["encounter_id"] for c in claims}
for r_ in c837:
    r_["patient_id"] = enc_pt[claim_enc[r_["clm01_claim_id"]]]
write("x12", f"claims_837p_{ym}.csv", c837, list(c837[0].keys()) if c837 else [])

r835 = []
for ref_, payer, day, c, ln, allowed, paid, cas, remark in remits:
    if day.strftime("%Y-%m") != ym:
        continue
    base = dict(trn02_trace=ref_, payer=payer if not payer.startswith("PY") else PAYER[payer][1], bpr16_date=day,
                clp01_claim_id=c["claim_id"], clp02_status="4" if paid == 0 and allowed == 0 else "1",
                clp03_claim_charge=c["total_charge"], ref6r_line_id=ln["line_id"], svc01_procedure=ln["procedure_code"],
                svc01_modifiers=ln["modifiers"], svc02_charge=ln["charge"], svc03_paid=paid, svc05_units=ln["units"],
                dtm472_service_date=ln["service_date"], amtb6_allowed=allowed, lq_remark=remark)
    for g, rc, amt in cas:
        r835.append(dict(base, cas01_group=g, cas02_reason=rc, cas03_amount=amt))
cols835 = ["trn02_trace", "payer", "bpr16_date", "clp01_claim_id", "clp02_status", "clp03_claim_charge", "ref6r_line_id",
           "svc01_procedure", "svc01_modifiers", "svc02_charge", "svc03_paid", "svc05_units", "dtm472_service_date",
           "amtb6_allowed", "cas01_group", "cas02_reason", "cas03_amount", "lq_remark"]
write("x12", f"remit_835_{ym}.csv", r835, cols835)

for k, v in counts.items():
    print(f"{k:>14}: {v:>7,}")

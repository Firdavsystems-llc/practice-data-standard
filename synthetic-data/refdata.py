"""Reference lists for the generator. All names here are invented.

Rates and RVUs are rounded, illustrative values in the neighbourhood of the
Medicare physician fee schedule. They are good enough to make the sample
behave like a real practice. Do not use them for anything real; load the
current CMS RVU file instead.
"""

LOCATIONS = [
    # id, name, city, state, zip, service lines
    ("L01", "Riverbend Family Health - Main", "Alexandria", "VA", "22305", "Primary care|Preventive|Procedures|Nurse visit"),
    ("L02", "Riverbend Family Health - West", "Annandale", "VA", "22003", "Primary care|Preventive|Nurse visit"),
]

PROVIDERS = [
    # id, name, role, specialty, clinician, home location, active_from, active_to, slots per day, coding intensity
    ("P01", "Haddad, Leila", "MD", "Family Medicine", True, "L01", "2019-01-07", "", 16, 1.00),
    ("P02", "Okonkwo, Daniel", "DO", "Family Medicine", True, "L01", "2021-03-01", "", 15, 1.15),
    ("P03", "Portillo, Maria", "NP", "Family Nurse Practitioner", True, "L02", "2022-08-15", "", 13, 0.90),
    ("P04", "Brennan, Thomas", "MD", "Internal Medicine", True, "L02", "2025-10-06", "", 14, 1.05),
    ("P05", "Mercer, Julia", "RN", "Nursing", False, "L01", "2020-01-06", "", 6, 1.00),
]
SUPERVISING = "P01"   # nurse visits are billed under this provider

PAYERS = [
    ("PY01", "Medicare Part B", "Medicare"),
    ("PY02", "Medicare Advantage Plan A", "Medicare"),
    ("PY03", "Medicare Advantage Plan B", "Medicare"),
    ("PY04", "State Medicaid", "Medicaid"),
    ("PY05", "Medicaid MCO A", "Medicaid"),
    ("PY06", "Medicaid MCO B", "Medicaid"),
    ("PY07", "Commercial Payer A", "Commercial"),
    ("PY08", "Commercial Payer B", "Commercial"),
    ("PY09", "Commercial Payer C", "Commercial"),
    ("PY10", "Blue Plan A", "Commercial"),
    ("PY11", "Blue Plan B", "Commercial"),
    ("PY12", "Federal Employee Plan A", "Commercial"),
    ("PY13", "Military Health Plan", "Other"),
    ("PY14", "Medicare Supplement Carrier A", "Commercial"),
    ("PY99", "Self-pay", "Self-pay"),
]

# plan id, plan name as billed, payer, product type, coverage type, kind
# kind: ppo (copay), hdhp (deductible), mcr (medicare ffs), ma, mcd, mil, sup (secondary only), self
PLANS = [
    ("MCB-VA", "MEDICARE PART B VA", "PY01", "Medicare FFS", "Medicare", "mcr"),
    ("MAA-PPO", "MA PLAN A PPO", "PY02", "Medicare Advantage PPO", "Medicare Advantage", "ma"),
    ("MAA-HMO", "MA PLAN A HMO", "PY02", "Medicare Advantage HMO", "Medicare Advantage", "ma"),
    ("MAB-HMO", "MA PLAN B HMO", "PY03", "Medicare Advantage HMO", "Medicare Advantage", "ma"),
    ("MAB-DSNP", "MA PLAN B DUAL SNP", "PY03", "Medicare Advantage D-SNP", "Medicare Advantage", "ma"),
    ("MCD-FFS", "STATE MEDICAID", "PY04", "Medicaid FFS", "Medicaid", "mcd"),
    ("MCOA-01", "MCO A MEDICAID", "PY05", "Medicaid managed care", "Medicaid managed care", "mcd"),
    ("MCOA-02", "MCO A FAMIS", "PY05", "Medicaid managed care", "Medicaid managed care", "mcd"),
    ("MCOB-01", "MCO B MEDICAID", "PY06", "Medicaid managed care", "Medicaid managed care", "mcd"),
    ("COMA-PPO", "COMMERCIAL A PPO", "PY07", "Commercial PPO", "Commercial", "ppo"),
    ("COMA-HMO", "COMMERCIAL A HMO", "PY07", "Commercial HMO", "Commercial", "ppo"),
    ("COMA-POS", "COMMERCIAL A POS", "PY07", "Commercial POS", "Commercial", "ppo"),
    ("COMA-HDHP", "COMMERCIAL A HDHP/HSA", "PY07", "Commercial HDHP", "Commercial", "hdhp"),
    ("COMB-CHOICE", "COMMERCIAL B CHOICE PLUS", "PY08", "Commercial PPO", "Commercial", "ppo"),
    ("COMB-OPT", "COMMERCIAL B OPTIONS", "PY08", "Commercial PPO", "Commercial", "ppo"),
    ("COMC-OAP", "COMMERCIAL C OPEN ACCESS", "PY09", "Commercial PPO", "Commercial", "ppo"),
    ("COMC-LOC", "COMMERCIAL C LOCALPLUS", "PY09", "Commercial HMO", "Commercial", "ppo"),
    ("BLA-PPO", "BLUE PLAN A PPO", "PY10", "Commercial PPO", "Commercial", "ppo"),
    ("BLA-HMO", "BLUE PLAN A HMO", "PY10", "Commercial HMO", "Commercial", "ppo"),
    ("BLA-OOA", "BLUE PLAN A OUT OF AREA", "PY10", "Commercial PPO", "Commercial", "ppo"),
    ("BLB-PPO", "BLUE PLAN B PPO", "PY11", "Commercial PPO", "Commercial", "ppo"),
    ("BLB-HDHP", "BLUE PLAN B HDHP", "PY11", "Commercial HDHP", "Commercial", "hdhp"),
    ("FEPA-STD", "FEP A STANDARD OPTION", "PY12", "Commercial PPO", "Commercial", "ppo"),
    ("FEPA-BAS", "FEP A BASIC OPTION", "PY12", "Commercial PPO", "Commercial", "ppo"),
    ("MIL-SEL", "MILITARY SELECT", "PY13", "Military", "Other", "mil"),
    ("SUPA-G", "MEDICARE SUPPLEMENT A PLAN G", "PY14", "Medicare Supplement", "Medicare", "sup"),
    ("SUPA-N", "MEDICARE SUPPLEMENT A PLAN N", "PY14", "Medicare Supplement", "Medicare", "sup"),
    ("SELF", "SELF PAY", "PY99", "Self-pay", "Self-pay", "self"),
    # new identifiers that nobody has mapped yet (test D9 lists them)
    ("COMX-26", "COMMERCIAL NEW PLAN 2026", "", "", "Commercial", "ppo"),
    ("BLA-PPO2", "BLUE A PPO (NEW ID)", "", "", "Commercial", "ppo"),
]
UNMAPPED_FROM = {"COMX-26": "2026-04-01", "BLA-PPO2": "2026-05-15"}
UNMAPPED_PRICED_AS = {"COMX-26": "PY07", "BLA-PPO2": "PY10"}

# contract level vs. the base rate, per payer
RATE_FACTOR = {"PY01": 1.00, "PY02": 0.99, "PY03": 0.97, "PY04": 0.70, "PY05": 0.76, "PY06": 0.74,
               "PY07": 1.32, "PY08": 1.25, "PY09": 1.38, "PY10": 1.30, "PY11": 1.28, "PY12": 1.35,
               "PY13": 0.96}
RATE_CHANGE = ("PY08", "2026-01-01", 1.035)     # payer B moves its rates up on Jan 1
UNDERPAY = ("PY09", {"99214", "99215"}, 0.94)  # payer C pays 6% under contract on these

# median days from submission to the payer's remittance
PAYER_LAG = {"PY01": 14, "PY02": 20, "PY03": 24, "PY04": 26, "PY05": 30, "PY06": 33, "PY07": 18,
             "PY08": 22, "PY09": 25, "PY10": 19, "PY11": 21, "PY12": 17, "PY13": 31, "PY14": 12}
PAYER_PAYDAY = {"PY01": 1, "PY02": 3, "PY03": 2, "PY04": 4, "PY05": 3, "PY06": 1, "PY07": 2,
                "PY08": 4, "PY09": 0, "PY10": 3, "PY11": 1, "PY12": 2, "PY13": 4, "PY14": 3}  # weekday

PROCEDURES = [
    # code, short label (ours, not the AMA descriptor), work RVU, base rate, charge, category
    ("99202", "Office visit, new, level 2", 0.93, 72, 160, "E/M office"),
    ("99203", "Office visit, new, level 3", 1.60, 113, 245, "E/M office"),
    ("99204", "Office visit, new, level 4", 2.60, 168, 365, "E/M office"),
    ("99205", "Office visit, new, level 5", 3.50, 222, 480, "E/M office"),
    ("99211", "Office visit, established, minimal", 0.18, 23, 55, "E/M office"),
    ("99212", "Office visit, established, level 2", 0.70, 57, 125, "E/M office"),
    ("99213", "Office visit, established, level 3", 1.30, 92, 200, "E/M office"),
    ("99214", "Office visit, established, level 4", 1.92, 130, 285, "E/M office"),
    ("99215", "Office visit, established, level 5", 2.80, 183, 400, "E/M office"),
    ("99383", "Preventive visit, new, 5-11", 1.50, 112, 245, "Preventive"),
    ("99384", "Preventive visit, new, 12-17", 1.70, 125, 270, "Preventive"),
    ("99385", "Preventive visit, new, 18-39", 1.92, 125, 270, "Preventive"),
    ("99386", "Preventive visit, new, 40-64", 2.33, 140, 305, "Preventive"),
    ("99387", "Preventive visit, new, 65+", 2.50, 150, 330, "Preventive"),
    ("99392", "Preventive visit, est., 1-4", 1.50, 105, 230, "Preventive"),
    ("99393", "Preventive visit, est., 5-11", 1.50, 104, 230, "Preventive"),
    ("99394", "Preventive visit, est., 12-17", 1.70, 113, 250, "Preventive"),
    ("99395", "Preventive visit, est., 18-39", 1.75, 115, 255, "Preventive"),
    ("99396", "Preventive visit, est., 40-64", 1.90, 125, 275, "Preventive"),
    ("99397", "Preventive visit, est., 65+", 2.00, 135, 295, "Preventive"),
    ("G0438", "Annual wellness visit, initial", 2.60, 170, 360, "Preventive"),
    ("G0439", "Annual wellness visit, subsequent", 1.92, 133, 290, "Preventive"),
    ("G2211", "Visit complexity add-on", 0.33, 16, 35, "E/M add-on"),
    ("36415", "Venipuncture", 0.00, 3, 15, "Lab"),
    ("81002", "Urinalysis, non-automated", 0.00, 3.5, 15, "Lab"),
    ("87880", "Strep test, rapid", 0.00, 16, 40, "Lab"),
    ("93000", "ECG with interpretation", 0.17, 16, 65, "Testing"),
    ("94010", "Spirometry", 0.17, 30, 90, "Testing"),
    ("96127", "Brief behavioral assessment", 0.00, 4.5, 20, "Screening"),
    ("99406", "Tobacco cessation counseling, 3-10 min", 0.24, 15, 40, "Counseling"),
    ("90471", "Immunization administration", 0.17, 18, 35, "Immunization"),
    ("90686", "Influenza vaccine, quadrivalent", 0.00, 21, 45, "Immunization"),
    ("20610", "Joint injection, major joint", 0.79, 60, 175, "Procedure"),
    ("11102", "Skin biopsy, tangential", 0.66, 95, 225, "Procedure"),
    ("17110", "Destruction of benign lesions", 0.70, 110, 240, "Procedure"),
]
PREVENTIVE_ZERO_PR = {"G0438", "G0439", "90471", "90686", "99383", "99384", "99385", "99386", "99387",
                      "99392", "99393", "99394", "99395", "99396", "99397", "96127"}

DX = {
    # code: (group, kind)
    "I10": ("Hypertension", "chronic"), "E11.9": ("Diabetes", "chronic"), "E78.5": ("Lipid disorders", "chronic"),
    "E03.9": ("Thyroid", "chronic"), "F41.1": ("Anxiety", "chronic"), "F32.A": ("Depression", "chronic"),
    "J45.909": ("Asthma", "chronic"), "K21.9": ("Digestive", "chronic"), "E66.9": ("Obesity", "chronic"),
    "I48.91": ("Heart rhythm", "chronic"), "G47.33": ("Sleep disorders", "chronic"), "F17.210": ("Tobacco use", "chronic"),
    "J06.9": ("Respiratory infection", "acute"), "R05.9": ("Respiratory symptoms", "acute"), "N39.0": ("Urinary infection", "acute"),
    "M54.50": ("Back pain", "acute"), "R10.9": ("Abdominal symptoms", "acute"), "J30.9": ("Allergy", "acute"),
    "M25.561": ("Joint pain", "acute"), "R53.83": ("General symptoms", "acute"), "J02.9": ("Respiratory infection", "acute"),
    "Z00.00": ("Preventive exam", "exam"), "Z00.01": ("Preventive exam", "exam"), "Z00.129": ("Preventive exam", "exam"),
    "Z23": ("Immunization", "exam"), "B07.9": ("Skin", "proc"), "D48.5": ("Skin", "proc"), "L57.0": ("Skin", "proc"),
}
CHRONIC = [("I10", 0.30, 40), ("E78.5", 0.25, 40), ("E11.9", 0.11, 35), ("E03.9", 0.06, 30), ("F41.1", 0.08, 18),
           ("F32.A", 0.07, 18), ("J45.909", 0.07, 5), ("K21.9", 0.08, 30), ("E66.9", 0.12, 18), ("I48.91", 0.03, 60),
           ("G47.33", 0.05, 35), ("F17.210", 0.09, 18)]   # code, prevalence among adults, min age
ACUTE = [("J06.9", 25), ("R05.9", 14), ("J02.9", 8), ("N39.0", 9), ("M54.50", 12), ("R10.9", 7), ("J30.9", 8),
         ("M25.561", 8), ("R53.83", 9)]

ZIPS = {  # home ZIP weights by the location a patient mostly uses
    "L01": [("22305", 22), ("22314", 16), ("22301", 10), ("22302", 10), ("22304", 15), ("22311", 9), ("22312", 8), ("22306", 10)],
    "L02": [("22003", 34), ("22041", 10), ("22151", 14), ("22150", 10), ("22042", 14), ("22312", 10), ("22044", 8)],
}

REFERRERS = [
    ("Dr. A. Molina", "Urgent Care Group A"), ("Dr. S. Grant", "Hospital A Emergency Dept"),
    ("Dr. P. Rao", "Cardiology Group A"), ("Dr. H. Lindqvist", "Women's Health Group A"),
    ("Dr. K. Mensah", "Orthopedic Group A"), ("Dr. J. Castillo", "Pediatrics Group A"),
    ("Dr. E. Novak", "Hospital A Discharge Planning"), ("Dr. R. Bauer", "Endocrinology Group A"),
]

HOLIDAYS = {"2025-07-04", "2025-09-01", "2025-11-27", "2025-11-28", "2025-12-25", "2026-01-01",
            "2026-01-19", "2026-02-16", "2026-05-25", "2026-06-19", "2025-12-24"}

DENIALS = [
    # CARC, share of denials, recoverable share, label
    ("197", 0.20, 0.75, "Prior authorization absent"),
    ("27", 0.13, 0.45, "Coverage terminated"),
    ("16", 0.17, 0.90, "Claim lacks information"),
    ("22", 0.12, 0.80, "Coordination of benefits"),
    ("50", 0.08, 0.40, "Not medically necessary"),
    ("204", 0.09, 0.20, "Not covered under benefit plan"),
    ("29", 0.05, 0.00, "Timely filing limit"),
    ("252", 0.07, 0.85, "Attachment required"),
    ("109", 0.09, 0.70, "Not covered by this payer"),
]
REMARK = {"197": "N54", "16": "M51", "252": "N706", "22": "MA04"}

GL = [
    # account, name, type, default class
    ("6000", "Salaries - clinical", "expense", ""),
    ("6010", "Salaries - administrative", "expense", "SHARED"),
    ("6020", "Payroll taxes and benefits", "expense", ""),
    ("6100", "Rent", "expense", ""),
    ("6200", "Medical supplies", "expense", ""),
    ("6210", "Vaccines", "expense", ""),
    ("6300", "Reference lab fees", "expense", ""),
    ("6400", "PM/EHR subscription", "expense", "SHARED"),
    ("6410", "IT and network services", "expense", "SHARED"),
    ("6500", "Professional liability insurance", "expense", "SHARED"),
    ("6600", "Utilities", "expense", ""),
    ("6700", "Marketing", "expense", "SHARED"),
    ("6800", "Equipment maintenance", "expense", ""),
    ("1500", "Medical equipment", "asset", ""),
]
CLASSES = [
    # class, service line, location
    ("MAIN-PC", "Primary care", "L01"), ("MAIN-PREV", "Preventive", "L01"), ("MAIN-PROC", "Procedures", "L01"),
    ("MAIN-NURSE", "Nurse visit", "L01"), ("WEST-PC", "Primary care", "L02"), ("WEST-PREV", "Preventive", "L02"),
    ("WEST-NURSE", "Nurse visit", "L02"), ("SHARED", "Shared", ""),
]
VENDORS = [
    ("V01", "Medical Supply Distributor A", "Supplies"), ("V02", "Vaccine Distributor A", "Vaccines"),
    ("V03", "Reference Laboratory A", "Lab"), ("V04", "Landlord - Main", "Facilities"),
    ("V05", "Landlord - West", "Facilities"), ("V06", "PM/EHR Vendor A", "Software"),
    ("V07", "IT Services Provider A", "IT"), ("V08", "Liability Carrier A", "Insurance"),
    ("V09", "Electric Utility A", "Facilities"), ("V10", "Payroll", "Payroll"),
    ("V11", "Diagnostic Equipment Vendor A", "Equipment"), ("V12", "Local Marketing Agency A", "Marketing"),
]

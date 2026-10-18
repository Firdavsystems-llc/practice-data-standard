# 2. Data definitions

This file defines the conformed entities in Silver: what one row means,
the key, and the fields. Gold tables and the semantic model are built only
from these. If a practice's export has something that doesn't fit, it gets
mapped here or left out. It doesn't get a new entity without a change to
this document.

## Layers, briefly

| Layer | Holds | Rule |
|---|---|---|
| Bronze | every extract exactly as received, one folder per source per extract date | never modified, full history kept |
| Silver | the entities below, with stable keys | tested before anything moves on (`04-data-quality-tests.md`) |
| Gold | subject-area tables the practice reads, plus analytic tables | built only from Silver |

Bronze history is what lets a practice change PM/EHR vendor without losing
the past, and it makes every number traceable to a file.

## Conventions

- Column names are `snake_case`. Keys end in `_id`.
- Dates are ISO 8601 (`2026-03-14`). Timestamps are local practice time, no offset.
- Amounts are decimal dollars, two places. Payments and adjustments are stored
  as **positive** numbers that reduce the balance (test D7).
- `_id` values are the source system's own identifiers, as text. They are
  never re-numbered, so a row can always be found again in the source.
- Empty means unknown. Don't write `N/A`, `0` or `-` for unknown.

## Entities

### patient

One row per patient. Key: `patient_id` (the practice account number).

| Field | Type | Notes |
|---|---|---|
| patient_id | text | practice account identifier |
| birth_year | int | year only; age is computed from it |
| sex | text | `F`, `M`, `X`, or empty |
| race | text | OMB categories, only where the practice records it |
| ethnicity | text | `Hispanic or Latino`, `Not Hispanic or Latino`, empty |
| coverage_type | text | current primary coverage; see code sets |
| home_zip | text | 5 digits |
| first_seen_date | date | first visit at the practice as the PM system records it. Needed because Bronze history rarely goes back far enough to tell new from established |
| deceased | bool | |

No name, no street address, no phone, no date of birth.

### provider

One row per provider per effective period. Key: `provider_id` + `active_from`.

| Field | Type | Notes |
|---|---|---|
| provider_id | text | |
| provider_name | text | display name |
| role | text | `MD`, `DO`, `NP`, `PA`, `RN`, `MA` |
| specialty | text | |
| is_clinician | bool | counts toward RVUs and productivity |
| home_location_id | text | |
| active_from | date | |
| active_to | date | empty if current |

### location

One row per service location. Key: `location_id`.

Fields: `location_id`, `location_name`, `city`, `state`, `zip`,
`service_lines` (pipe-separated list).

### appointment

One row per scheduled slot. Key: `appointment_id`.

| Field | Type | Notes |
|---|---|---|
| appointment_id | text | |
| patient_id | text | |
| provider_id | text | |
| location_id | text | |
| appointment_type | text | practice's own list, mapped to the types in code sets |
| created_at | timestamp | when it was booked |
| scheduled_start | timestamp | |
| status | text | `kept`, `no_show`, `cancelled_patient`, `cancelled_office`, `left_unseen` |
| cancelled_at | timestamp | |
| cancel_channel | text | `portal`, `reminder`, `phone`, `in_person` |
| checked_in_at | timestamp | |
| encounter_id | text | set when kept |

### encounter

One row per visit or study. Key: `encounter_id`.

Fields: `encounter_id`, `patient_id`, `provider_id`, `location_id`,
`service_date`, `service_line`, `modality` (for imaging / testing, else empty),
`place_of_service` (CMS two-digit code).

### claim

One row per claim. Key: `claim_id`.

| Field | Type | Notes |
|---|---|---|
| claim_id | text | the patient control number sent on the 837 |
| encounter_id | text | |
| plan_id | text | payer plan as billed |
| referring_provider | text | name or NPI of an outside referring provider, if on the claim |
| diagnosis_codes | text | ICD-10-CM, pipe-separated, primary first |
| submitted_date | date | first submission |
| status | text | see claim status in code sets |
| total_charge | decimal | |

### claim_line

One row per procedure line. Key: `line_id`.

| Field | Type | Notes |
|---|---|---|
| line_id | text | line item control number |
| claim_id | text | |
| line_no | int | |
| service_date | date | |
| procedure_code | text | CPT / HCPCS |
| modifiers | text | pipe-separated |
| units | decimal | |
| charge | decimal | |
| allowed_amount | decimal | from the remittance; empty until adjudicated |
| contracted_rate | decimal | from `payer_contract`, per unit |
| rendering_provider_id | text | |
| place_of_service | text | |

### payment

One row per posting. Key: `payment_id`.

Fields: `payment_id`, `line_id`, `source` (`primary`, `secondary`, `patient`),
`amount`, `posted_date`, `remit_ref` (the 835 check / EFT trace number;
empty for patient payments).

### adjustment

One row per adjustment. Key: `adjustment_id`.

Fields: `adjustment_id`, `line_id`, `group_code` (`CO`, `PR`, `OA`, `PI`),
`reason_code` (CARC), `remark_codes` (RARC, pipe-separated), `amount`,
`posted_date`, `adjustment_type` (`contractual`, `denial`, `write_off`, `other`).

Two things that trip people up:

- **PR amounts are not adjustments.** Patient responsibility on the 835
  (group `PR`) moves the balance to the patient. It doesn't reduce it, so it
  is not written to `adjustment`. The patient's payment, when it comes, is a
  `payment` with source `patient`.
- **Denials are posted at $0.00.** A denial is an `adjustment` row with
  type `denial`, the CARC, and amount 0. The balance stays open until the
  claim is paid on appeal or written off (a second row, type `write_off`).
  That's what lets the denial rate and "claims requiring action" be counted
  from one table.

Write-offs and discounts the practice books itself (self-pay discount,
sent to collections) have no CARC. They use the practice's own code in
`reason_code` and leave `group_code` empty. Keep that list short and in the
design note.

### payer_plan

One row per plan identifier as billed. Key: `plan_id`.

Fields: `plan_id`, `plan_name`, `payer_id`, `product_type`, `contract_ref`.

This is the table that does most of the work. A small practice can bill
more than a hundred plan identifiers that come down to fifteen or twenty
payers. Every one has to map (test D9).

### payer

One row per paying organization. Key: `payer_id`.

Fields: `payer_id`, `payer_name`, `payer_class` (`Medicare`, `Medicaid`,
`Commercial`, `Other`, `Self-pay`).

### referral

One row per referral event. Key: `referral_id`.

Fields: `referral_id`, `patient_id`, `referring_provider`, `referring_org`,
`referral_date`, `service_requested`, `outcome` (`seen`, `scheduled`,
`declined`, `open`).

### payer_contract

Practice-maintained reference table. Key: `plan_id` + `procedure_code` + `effective_from`.

Fields: `plan_id`, `procedure_code`, `rate_per_unit`, `effective_from`, `effective_to`.

### procedure_reference

Key: `procedure_code`. Fields: `procedure_code`, `label`, `work_rvu`,
`category`. Work RVUs come from the CMS physician fee schedule RVU file for
the year of service. `label` is the practice's own short wording.

## Accounting entities

Only where the practice's books are in scope. These come from the
accounting system (QuickBooks or similar), not the PM/EHR.

### gl_account

One row per general-ledger account. Key: `account`.
Fields: `account`, `account_name`, `account_type` (`expense`, `asset`, `revenue`).

### vendor

One row per vendor. Key: `vendor_id`. Fields: `vendor_id`, `vendor_name`, `category`.

### expense_transaction

One row per posted expense or purchase line. Key: `transaction_id`.

| Field | Type | Notes |
|---|---|---|
| transaction_id | text | |
| gl_account | text | |
| vendor_id | text | |
| class_name | text | the accounting class or department it was booked to |
| posted_date | date | |
| amount | decimal | positive |
| capital_flag | bool | true for capital purchases (equipment) |
| memo | text | free text from the books; check it for anything that shouldn't be there |

### class_service_line_map

One row per accounting class. Key: `class_name`.
Fields: `class_name`, `service_line`, `location_id`, `shared` (bool).

This is the join between the two record systems. Every class with spend
must map to a service line or be marked shared (test D17). Shared costs
stay shared; the standard doesn't allocate them.

## Code sets

Use public code sets wherever one exists.

| Field | Code set | Source |
|---|---|---|
| procedure_code | CPT, HCPCS Level II | AMA (CPT), CMS (HCPCS). CPT descriptors are AMA-licensed and are not reproduced here. |
| diagnosis_codes | ICD-10-CM | CDC / CMS |
| place_of_service | CMS Place of Service codes | CMS |
| reason_code / remark_codes | CARC / RARC | X12 code lists |
| group_code | Claim adjustment group codes | X12 |
| case mix grouping | CCSR for ICD-10-CM | AHRQ HCUP |
| work RVUs | Medicare Physician Fee Schedule RVU file | CMS |

`coverage_type`: `Medicare`, `Medicare Advantage`, `Medicaid`,
`Medicaid managed care`, `Commercial`, `Self-pay`, `Other`.

Claim `status`: `submitted`, `paid`, `partially_paid`, `denied`, `rejected`,
`paid_zero`, `patient_balance`, `closed`.

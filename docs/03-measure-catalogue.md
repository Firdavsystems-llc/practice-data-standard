# 3. Measure catalogue

These are the standard definitions. A deployment can add measures. It
can't redefine these without the change going through the design note
(`05-dataops-and-delivery.md`), because the whole point is that "no-show
rate" means the same thing at every practice that uses this.

Unless a measure says otherwise:

- **Grain:** available by month, provider, location and payer class.
- Amounts are dollars. Voided and empty lines are excluded everywhere (test D5).
- Field names refer to `02-data-definitions.md`.

## C.1 Volume and access

| Measure | Definition | Formula / source |
|---|---|---|
| Encounters | One patient seen on one date of service, counted once however many services were billed. | distinct (`patient_id`, `service_date`) in `encounter` |
| Office encounters | Encounters that include an office visit billed at an office place of service. | encounters with an E/M office code and `place_of_service` = `11` |
| Services | Billed procedure lines, in units. | sum `claim_line.units` |
| Services per encounter | | Services / Encounters |
| Unique patients | Distinct patients with at least one encounter in the period. | distinct `patient_id` |
| New and follow-up patients | New in the period that holds the patient's first recorded encounter at the practice; follow-up in every later period. | first `service_date` per `patient_id` |
| Referred new patients | New patients whose claim names an outside referring provider. | new patients where `claim.referring_provider` is not empty |
| Office encounters per working day | | Office encounters / working days (weekdays less practice holidays) |
| Monthly average | For any volume measure across several months. | total / months with activity |
| Active patients | Patients with an encounter in the trailing three years, not deceased. Three years is the new vs. established line used in billing. | |

## C.2 Scheduling

**Appointments by outcome.** Each scheduled appointment is one of: kept,
cancelled by the patient, cancelled by the office, or missed. *Missed*
means a no-show, a patient cancellation less than 24 hours before the
start, or a patient who left before being seen.

**No-show rate.** Missed / (kept + missed). Timely cancellations are in
neither number. Grain: by provider, location, appointment type, month.

**Digital cancellation share.** Patient cancellations through the portal or an
automated reminder / all patient cancellations. (`cancel_channel` in
`portal`, `reminder`.)

**Missed-visit revenue.** Missed office appointments x average payment per
office encounter in the same period. This is an estimate and is labelled as
one on every report that shows it.

## C.3 Revenue cycle

| Measure | Definition |
|---|---|
| Charges | Billed amount on service lines. `sum(claim_line.charge)` |
| Payments | Amounts received, positive, by `source` (primary, secondary, patient). Postings under $1 are not counted as payments. |
| Adjustments | Reductions to charges, by `adjustment_type`, from group and reason codes. |
| Payment status | Each line is one of: paid, awaiting payment, unpaid or paid at zero, patient balance, insurance balance, written off (by cause). |
| Gross collection rate | Payments / charges, on lines no longer awaiting payment. |
| Net collection rate | Payments / (charges - contractual adjustments), same lines. |
| Payment per encounter / patient / paid service | Payments / encounters, unique patients or paid services. Encounters in the last 60 days are left out because they aren't fully paid yet. |
| Allowed amount | What the payer allows for the line. Self-pay lines excluded. |
| Claims requiring action | Claims with an open balance that need someone at the practice to do something: denied, rejected, paid at zero, or unpaid past the payer's usual payment time (its 90th percentile payment velocity). By payer plan and reason category. |
| Denial rate | Lines denied on first submission / lines submitted. By count and by charge dollars. |
| Revenue at risk | For claims requiring action, the expected payment: average paid for the same procedure code and payer over the trailing 12 months. |
| Days to bill | `submitted_date - service_date`. Median and 90th percentile. |
| A/R age | Open balance by age from date of service: 0-30, 31-60, 61-90, 91-120, 120+. Plus the dollar-weighted average age. |
| Days in A/R | Open receivable / average daily charges over the trailing three months. |
| Net realizable receivable | Open charges x net collection rate of the same payer class. |
| Payment velocity | Days from service to first and to last payment, by payer: min, quartiles, median, mean, p90, max; and the share paid within 30, 60, 90, 180 days. Payments collected at the visit (D13) are not timed. |
| Days since last action | Open claims by days since the last posting or status change: <14, 14-29, 30-59, 60+. |

## C.4 Payer rates

- **Current rate.** The most frequent allowed amount per unit for a procedure
  code and payer in the month. (Mode, not mean. One odd adjudication shouldn't
  move it.)
- **Previous valid rate.** The current rate of the most recent earlier month,
  looking back no more than six months, same code and payer.
- **Rate change.** Current - previous valid, in dollars and percent. Over 2%
  gets flagged for review.
- **Variance against contract.** Allowed and paid, less `payer_contract.rate_per_unit`
  x units, by payer plan and procedure code.

## C.5 Productivity

TODO

## C.6 Financial

TODO - needs the accounting entities in 02 first.

## C.7 Population and case mix

| Measure | Definition |
|---|---|
| Patients by group | Unique patients by age band (0-17, 18-44, 45-64, 65-74, 75+), sex, coverage type and home ZIP. |
| Income band of home ZIP | Median household income of the patient's home ZIP, from the public Census ACS 5-year table B19013, in bands. |
| Race and ethnicity group | Only where the practice records it and a planning or regulatory submission asks for it. |
| Case mix | Encounters by diagnosis category, grouping ICD-10-CM with AHRQ's CCSR (primary diagnosis, default category). |

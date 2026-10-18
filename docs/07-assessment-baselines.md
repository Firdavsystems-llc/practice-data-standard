# 7. Assessment baselines

Every deployment is measured the same way, twice: once before the
application goes live (Phase 6) and once at the post-handover assessment
(Phase 8). The comparison goes to the practice in an assessment memo.

Because the definitions in `03-measure-catalogue.md` are fixed, a B2
figure at one practice means the same thing as a B2 figure at another.
That is the reason for having baselines at all.

## The four baselines

### B1. Reporting cycle

*What:* hours per month someone at the practice spends putting together
operational reports by hand, and days from month end until the month's
report is available.

*Before:* the practice administrator keeps a simple log for one full month
before the build (who, what report, how long). Ask for the last three
month-end packs and note when each was sent.

*After:* refresh timestamps from the pipeline run history give
availability. The administrator keeps the same log for one month after
handover.

Report: hours/month before and after; days-to-report before and after.

### B2. Payer-level visibility

*What:* number and dollar value of claims requiring practice action, broken
out by payer plan and reason code; payment-rate variance against
contracted rates by payer plan.

*Before:* what the practice can actually produce from its vendor's
standard reports, in the time it would normally spend. Often this is a
total with no payer split, or a denial list with no dollars. Write down what
was produced, not what might have been.

*After:* `Claims Requiring Action`, `Revenue at Risk` and `Variance against
contract` from the Gold revenue-cycle tables, by payer plan and reason
category.

### B3. Utilization and capacity

*What:* encounters and studies by provider, location and service line;
slot utilization; and the number of capacity, staffing or service-line
decisions made with platform data during the period.

*Before:* the practice's own records.

*After:* Gold utilization tables, plus a decision log kept with the
practice: date, decision, which numbers were looked at. One line per
decision is enough. The log is the only part of the assessment that isn't
computed, so keep it honest and short.

### B4. Cost and return by service line

Only where the accounting source is in scope.

*What:* can the practice state, for each service line, its expenses, its
collections and its investment for the period, from one governed source?

*Before:* usually no, or only with manual work across two systems. Record
how long it took to answer, if it could be answered.

*After:* the financial-performance tables (`fact_expense` joined to
payments by service line and location).

## The memo

One to two pages. For each baseline: the before figure, the after figure,
how each was obtained, and anything that makes them not comparable
(a payer change mid-period, a provider leaving, a new location). Record
the standard version the deployment was executed from.

Don't present B3 or B4 results as causal. "The practice made three
staffing decisions using the platform" is a fact. "The platform improved
staffing" is not something the memo can show.

## Across practices

Assessment memos are kept with the version they were measured against.
When the standard changes in a way that alters what a baseline measures,
the major version goes up (see `05-dataops-and-delivery.md`) and memos
from different major versions aren't compared directly.

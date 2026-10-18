# 5. DataOps and delivery

How a deployment is delivered, and how it is run once it's live. Written
for a practice with one administrator, no data team, and an outside
implementer who will leave at the end.

## Delivery phases

Each phase ends in something that can be checked. If the exit isn't met,
the next phase doesn't start.

| # | Phase | Work | Exit |
|---|---|---|---|
| 1 | Discover | List the decisions the practice actually makes (staffing, schedules, billing follow-up, a new service line) and what data each needs. List the sources. Risk assessment. BAA signed. Access provisioned. | decision list signed by the owner; BAA on file; access works |
| 2 | Design | Map the practice's export columns to the entities in `02`. Pick the measures from `03` that answer the decision list. Security design (`06`). Capacity plan. | design note signed by the practice |
| 3 | Build | Bronze, Silver, Gold in Dev. Semantic model. Report pages per audience. | runs end to end in Dev; tests in place |
| 4 | Load history | Schedule ingestion. Backfill to the earliest extract the vendor can give. | full history in Bronze; refresh runs unattended for a week |
| 5 | Reconcile | All stop tests pass. Walk the D15 (and D16) results with the administrator, month by month. | administrator signs the reconciliation |
| 6 | Baseline | Capture B1-B4 (`07`). First review of the numbers with the owner. | baseline memo |
| 7 | Go live | Publish the app to audiences in Prod. Train each role on its own pages. | app live; training record |
| 8 | Assess | Post-handover assessment against the baselines. Record the standard version used. | assessment memo; handover signed |

The **design note** is the one document that matters most after the
build. It records: the entity map, which measures are in, any threshold
tightened or loosened (with the reason), the practice's own adjustment
codes, the audiences, who owns each measure at the practice, and the
version of this standard the deployment follows. Anything that differs
from the standard is written there, or it isn't allowed.

## Environments

Three workspaces: **Dev**, **Test**, **Prod**, joined by a Fabric
deployment pipeline. Nothing is edited in Prod. Ever. If something is
wrong in Prod, it's fixed in Dev and promoted.

- Dev is connected to the practice's Git repository (Fabric Git
  integration). Notebooks, the semantic model and the report live there as
  files, the same layout as `fabric/` in this repo.
- Test points at a copy of the latest extract. Promotion to Test runs the
  full pipeline once before anyone looks at it.
- Prod is what the app reads.

Small practices sometimes ask to skip Test. Don't. It's one more
workspace on the same capacity, and it's the only place a change meets
real data before users see it.

## Versioning

The repository belongs to the practice. The implementer works on
branches; `main` is what Dev syncs from.

The standard itself uses semantic versioning:

- **patch** (1.0.x): wording, fixes that don't change any number
- **minor** (1.x.0): new or changed entities, tests or controls
- **major** (x.0.0): anything that changes what a deployment is assessed
  against (a baseline definition, a measure used by a baseline)

Every deployment records the version it was built from in its design note
and in its assessment memo. That's how results from two practices can be
compared, and how a fix can be carried back to older deployments.

## A normal refresh

```
landing files  ->  nb_01 bronze to silver  ->  nb_02 validate  ->  nb_03 build gold  ->  model (Direct Lake)
   (pipeline)         load_stats                 dq_results           star schema
                                                 stop = halt here
```

1. The vendor export lands in `lh_bronze/Files/landing/<extract date>/`.
   How it gets there depends on the vendor: SFTP pickup by a pipeline,
   a shared folder, or the vendor's API. Files are never edited after
   they land.
2. `nb_01` loads the extract into Silver and records what it saw.
3. `nb_02` runs D1-D19. Any stop failure raises, the pipeline fails, and
   Gold keeps the last good load. That is the intended behaviour, not an
   outage.
4. `nb_03` rebuilds Gold. Direct Lake picks up the new tables; there is no
   import refresh to schedule.

In 1.0 each extract is a full snapshot and Silver is overwritten. For
larger practices or daily extracts, switch Silver to an incremental merge
on the entity keys. The tests don't change.

## Monitoring

- `dq_results` gets one row per test per run. Keep it forever, it's small.
- Alerts go to the practice administrator (and, during the support
  window, the implementer) on any stop, warn or alert outcome. Alerts
  carry the test, counts and totals. Never patient-level rows.
- Look at the Capacity Metrics app monthly for the first quarter. If
  the refresh fits comfortably, leave the SKU alone.
- D9 will fire in the first weeks as new plan identifiers appear. Each
  one is a row added to the payer-plan map, done by the administrator.

## Handover

Handover is done when the administrator, without help, can:

1. run a refresh,
2. add a user to an audience,
3. change which pages an audience sees,
4. restore the previous version of the semantic model from the repository.

Handed over: the three workspaces, the repository, the run-book, the
design note, the measure catalogue as deployed, the security design, the
baseline and assessment memos, and the training record.

A 30-day support window follows go-live. After that, the practice's own IT
contact or vendor is first line. The implementer asks in writing for
their access to be removed and keeps the confirmation.

## Run-book (minimum contents)

- where the extracts come from, who to call when they don't arrive
- how to rerun a failed refresh, and how to read `dq_results`
- how to add a payer plan to the map
- how to add or remove a user, change an audience
- how to restore a prior version (Git history, then sync Dev, then promote)
- who owns which measure at the practice

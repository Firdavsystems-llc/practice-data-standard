# 1. Scope and principles

## What this standard is for

The standard describes one way to build a data platform for an independent
medical practice, and to do it the same way every time. The point of
writing it down is that two deployments at two practices end up measuring
the same things in the same way, and that a competent implementer can
follow it without the author in the room.

It is written for three kinds of reader:

- the practice owner or administrator, who will own the platform;
- the practice's IT contact or practice-management vendor, who provisions access;
- the implementer who builds it.

## In scope

Physician-owned practices with **fewer than 20 clinicians**, in any
specialty, that run a commercial practice-management or EHR system
("PM/EHR") able to produce scheduled exports or offer a data API.

The platform covers the practice's operational data: scheduling,
encounters, charges, claims, remittances, payer contracts, referrals and,
where available, ancillary volumes (imaging, lab). If the practice keeps its
books in an accounting system, the financial record is in scope too:
expenses, vendors and capital purchases by account and class.

Joining those two records is deliberate. Most practices hold them in two
systems that never meet, which is why "what does this service line cost
us, and what does it bring in" usually has no answer.

## Out of scope

- Clinical decision support and clinical documentation.
- Anything a certified EHR does. The platform sits underneath the practice's
  vendor tools as a data layer. It does not replace or change them.
- Hosting. There is no hosted service; see "practice-owned tenant" below.

## Principles

**Practice-owned tenant.** Storage, compute, identity and logs all live in
the practice's own Microsoft 365 / Azure tenant. The implementer runs no
platform of their own for practice data and moves none of it into storage
they control. Work that has to happen before the platform exists (a demo,
or building a report from export files) is the one exception, and it needs
the practice's written authorization, an encrypted workstation and a
deletion date agreed up front.

**Minimum necessary.** Bring in only the data an agreed measure needs.
Patient names and street addresses are not loaded. A patient is the
practice's own account identifier (see `02-data-definitions.md`).

**The practice owns it from day one.** Data, code, pipelines, models,
reports, workspaces and credentials belong to the practice. The implementer
keeps only work product with no practice data in it: code, transformation
logic, measure definitions, scripts, documentation.

**Standard before custom.** Every deployment uses the same layers, the same
conformed entities, the same measure catalogue and the same tests.
Specialty content goes in Gold and in reports. Never in ingestion or Silver.

**Vendor-neutral at the boundary.** Use what the PM/EHR and accounting
systems already produce. No vendor change, no add-on, no change to the
source systems. Where a public format exists (X12 835/837, FHIR R4) the
standard uses it.

**Measured.** Every deployment is assessed against the same baselines,
before the build and after handover (`07-assessment-baselines.md`).

**Handover is a deliverable.** If the practice can't run the platform
without the implementer, it hasn't been delivered.

**Security is designed in.** Every control concern gets a named platform
control before the build starts (`06-security-and-tenancy.md`).

## Target environment

Microsoft Fabric in the practice's tenant:

- OneLake storage, one lakehouse per layer (Bronze, Silver, Gold)
- data pipelines for orchestration, Dataflows Gen2 for file and accounting extracts
- notebooks (Python / PySpark) for conformance and analytic tables
- one Power BI semantic model in Direct Lake mode over Gold
- Microsoft Entra ID for identity

The practice holds the capacity subscription and pays for it. Size it
trial-first: build on a trial or the smallest SKU, watch the Capacity
Metrics app through a few refresh cycles, then buy.

Three workspaces (Dev, Test, Prod) joined by a deployment pipeline.

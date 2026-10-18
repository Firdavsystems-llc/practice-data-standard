# 6. Security and tenancy

The design keeps practice data inside the practice's own Microsoft
tenant from start to finish. Most of what follows is a consequence of that
one decision.

This section describes design controls. It does not make a deployment
compliant with anything; the practice's obligations under HIPAA and state
law are its own, and its security officer decides whether these controls
meet them.

## Principles

1. **The practice's tenant is the only place practice data lives.**
   Storage, compute, identity and logs are the practice's. The implementer
   operates no platform for practice data and copies none of it to storage
   they control.
2. **Minimum necessary.** Only what an agreed measure needs is loaded.
   No patient names, street addresses, phone numbers or dates of birth.
   Patients are the practice's own account number, which staff resolve in
   their own systems when they need to.
3. **Risk first.** A written risk assessment of the engagement (data
   flows, accounts, systems, any exception) is done in Phase 1, before any
   access is provisioned, and redone when scope changes.
4. **One control per concern, decided before the build.**

## Controls

| Concern | Control |
|---|---|
| Where does the data live? | OneLake, Fabric and the Power BI service in the practice's tenant. Nothing else. |
| What is loaded? | What the measures need (see `02`). Identifiers beyond the account number are not loaded. |
| Who can get in? | Accounts provisioned by the practice in its own Entra ID, least privilege, MFA enforced, no shared accounts. The implementer's account is removed at the end, in writing. |
| Where are secrets? | Fabric connection objects or Azure Key Vault. No credentials in notebooks, pipelines or the repository. Notebooks get storage tokens at run time. |
| Who sees what? | Workspace roles for builders; the app and its audiences for everyone else. Row-level security in the semantic model (a physician sees their own productivity, a site manager their site). Object-level security hides practice-level revenue and expense from roles that don't need them. |
| Who can export? | Tenant export and download settings; sensitivity labels on the model and report. |
| Can it be audited? | Entra sign-in logs, Purview audit log, Fabric/Power BI activity logs, all in the practice's tenant and kept on its schedule. The implementer keeps a separate engagement log with no patient data in it. |
| AI tools? | The implementer doesn't put practice data into any AI service. If the practice turns on Copilot in its own tenant, it runs over the semantic model under the same security. |
| Subcontractors? | Anyone else who would touch practice data signs the same terms and a business associate agreement first. |
| At the end? | Nothing to return, because nothing left the tenant. Access removed, confirmation kept. |
| BAA? | Signed before access is provisioned. |

## The one exception

Sometimes work has to happen before the platform exists: a demonstration
on the practice's own export files, or a first report built in Power BI
Desktop. Then, and only then, practice data sits on the implementer's
workstation. Three conditions, all in writing before any file moves:

- the practice authorizes it and names the data, the purpose and a
  deletion date;
- the files are the minimum the work needs, on a full-disk-encrypted
  workstation, in one folder for that practice, not synced to any cloud
  service, never on removable media;
- on or before the date, the files and any report containing the data are
  deleted, and the deletion is confirmed to the practice in writing.

Once the platform exists, the work moves into the tenant and the exception
no longer applies.

## What's not in the 1.0 model

The semantic model in `fabric/` has no RLS or OLS roles defined. Roles
depend on the practice's audiences, which are decided in the design note.
Add them before anything goes to Prod. See `08-implementer-guide.md`.

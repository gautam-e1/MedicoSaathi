# MedicoSaathi — Phase 6: Development Roadmap & Implementation Plan
### CTO / Principal Engineering Manager Review · Pre-Development Sign-Off

This document plans **execution**, not design. Every module, dependency, and sprint below maps to a screen in the Product Blueprint, a domain in the Database Architecture, a service/blueprint in the Backend Architecture, and an endpoint group in the API Architecture. Nothing here adds a feature, table, or endpoint that those four phases didn't already approve — this is the order, the test gates, and the readiness bar for building exactly what was already designed.

**Assumed team shape (stated explicitly because sprint math depends on it):** 4 backend engineers (Flask/SQLAlchemy), 2 frontend engineers (HTML/CSS/vanilla JS), 1 DevOps/SRE, 1 QA engineer, 1 EM/CTO. Two-week sprints. Adjust durations proportionally if the actual team differs — the **order and dependency logic do not change** with team size, only the calendar.

---

## 1. Development Phases

Twelve build phases plus a launch-readiness phase, sequenced by what each phase requires to exist first.

| Phase | Name | Core Modules (API Arch §1 refs) | Why this phase exists as its own unit |
|---|---|---|---|
| **0** | Foundation & Platform Scaffolding | Project skeleton, CI/CD, environment config, DB migrations baseline, Redis/Celery wiring | Nothing else can be built without a running app skeleton, a connected DB, and a working pipeline — this is infrastructure, not a feature, but it gates everything |
| **1** | Identity, Auth & RBAC | `/auth/*`, RBAC engine, tenant-context middleware | Every other module's endpoints are permission-gated and tenant-scoped — this must exist before a second real feature is written, not retrofitted later |
| **2** | Platform Admin Core & Shop Onboarding | `/platform/*` (shop verification), `/settings/statutory` | A shop must be able to register and get verified before any tenant feature has real data to operate on — this is the "front door" to the whole multi-tenant system |
| **3** | Catalog & Inventory | `/medicines/*`, `/medicines/{id}/batches/*` | Billing, procurement, and analytics all read from the catalog — it has zero upstream dependencies among feature modules and the most downstream consumers, so it goes first among "real" features |
| **4** | Billing / POS | `/billing/*` | The product's highest-frequency, highest-NFR-pressure module (sub-second target); needs Inventory (stock to sell) and a minimal Customer record (walk-in support) already in place |
| **5** | Customers & Customer Ledger | `/customers/*` | Could move earlier, but Billing's "walk-in" mode means full Customer Management isn't a hard blocker for Billing — sequencing it right after Billing lets POS ship sooner while the ledger work happens in parallel with POS hardening |
| **6** | Suppliers, Procurement (PO) & GRN | `/suppliers/*`, `/purchase-orders/*`, `/goods-receipts/*` | GRN completion is the **only** path that creates `medicine_batches` (besides manual adjustment) — this phase closes the loop Inventory opened in Phase 3 |
| **7** | Supplier Finance & Relationship Intelligence | `/suppliers/{id}/relationship`, `/suppliers/finance/*` | Needs real PO/GRN/invoice history (Phase 6) to compute aging, trust scores, and early-payment recommendations against — building it earlier would mean testing against fabricated data |
| **8** | Delivery / Dispatch | `/deliveries/*`, `/riders` | Depends on Billing producing real invoices to dispatch against; lower business-criticality than Billing/Inventory per Blueprint's own priority signals, so it's sequenced after the revenue-critical path is stable |
| **9** | Notifications & Command Center | `/notifications/*`, `/search` | Cross-cutting by design — needs Phases 3–8's domains to exist as *something to notify about and search across*; building it earlier produces an empty shell |
| **10** | Analytics, Audit & Dashboard | `/analytics/*`, `/audit/*`, `/dashboard/*` | These are aggregation layers over every other domain's data — by definition they cannot be meaningfully built, let alone tested, before the domains they aggregate exist with real data flowing |
| **11** | Subscription & Platform Admin Completion | `/subscription/*`, remainder of `/platform/*` | Monetization and full platform-ops tooling are required for launch but not for internal functional testing of the product itself — sequenced late so they don't block feature velocity, but well before Production Ready |
| **12** | Hardening: Performance, Security, Multi-Tenant Scale Validation | Cross-cutting | Dedicated phase, not folded into feature work — load testing, RLS/tenant-isolation penetration testing, and the full Section 6 testing strategy need every module to exist first |
| **13** | Launch Readiness | Cross-cutting | Deployment checklist (Section 8), release-gate sign-off (Section 9) — the bridge between "built" and "live" |

---

## 2. Module Development Order

The exact build order, restated as a single sequence with the dependency reasoning made explicit per step (expanded from Phase table above):

1. **Foundation/Infra** — must exist before any code runs anywhere.
2. **Auth + RBAC** — every single downstream endpoint in the API Architecture is permission-gated (API Arch §4); building any feature before this exists means building it twice (once without auth, once retrofitted).
3. **Platform Admin: Shop Verification + Tenant provisioning** — a `shops` row with `Verified` status is the precondition for *any* tenant data to legitimately exist (Blueprint §5.1 onboarding workflow; API Arch §11.5 `SHOP_NOT_VERIFIED`).
4. **Catalog & Inventory (Medicines, Batches, Stock Ledger)** — has no dependency on any other feature module; everything downstream (Billing, Procurement, Analytics) reads from it.
5. **Billing / POS** — depends on (4) for sellable stock; depends on (2)/(3) for a verified shop context; depends only minimally on Customers (walk-in mode covers the gap).
6. **Customers & Customer Ledger** — depends on (5) existing so the ledger has real invoice references to attach to; could theoretically run parallel to (5) with a second engineering pair, but is sequenced just after to avoid two teams racing on overlapping walk-in/customer-link logic.
7. **Suppliers, Purchase Orders, GRN** — depends on (4) because GRN completion writes `medicine_batches`; depends on (2) because supplier relationships are shop-scoped.
8. **Supplier Finance & Relationship Scoring** — depends on (7) for real procurement/invoice history to score against.
9. **Delivery** — depends on (5) (invoices to dispatch).
10. **Notifications & Command Center** — depends on (4)–(9) existing as event sources and search targets.
11. **Analytics, Audit, Dashboard** — depends on (4)–(9) for real data to aggregate; Audit specifically depends on every write-path module already emitting audit events (retrofitting audit logging onto modules built *after* the Audit module would be backwards).
12. **Subscription & remaining Platform Admin** — depends on (3) for the shop lifecycle hooks (plan limits gate billing, per API Arch §11.5 `PLAN_LIMIT_EXCEEDED`, so the *check* exists from Phase 5 onward as a stub, but full plan management UI/flows land here).
13. **Hardening** — by definition requires everything above to exist to test against.
14. **Launch Readiness** — final gate.

**The one deliberate parallelism:** frontend (HTML/CSS/vanilla JS) work for a given module starts as soon as that module's API contract (Phase 5, already frozen) is implemented and its OpenAPI/contract tests pass — frontend never waits for backend "polish," only for a stable contract. This is why Section 3's sprints show backend and frontend work overlapping within a module, not strictly sequential.

---

## 3. Sprint Planning

Two-week sprints, numbered continuously. Each sprint lists its goal, duration, hard dependencies (what must be **done**, not just started, before this sprint can begin), and concrete deliverables tied to API Architecture endpoint groups.

### Phase 0 — Foundation

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S0** | Project scaffolding: Flask app factory, config classes, folder structure (Backend Arch §1), CI pipeline, base Docker images, dev/staging Postgres+Redis provisioned | 2 wks | None | Running empty app in all three environments; green CI on an empty test suite; migration tooling (Alembic) initialized against the approved schema (no DDL authored yet — this just wires the tool) |

### Phase 1 — Identity, Auth & RBAC

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S1** | Core identity schema migration (Domain B tables) + `auth_service`/`identity` repositories | 2 wks | S0 | `users`, `roles`, `permissions`, `role_permissions`, `shop_users`, `auth_sessions` tables live; repository layer passing unit tests |
| **S2** | Auth endpoints: login, refresh, logout, shop-switch (API Arch §1.1, §3) | 2 wks | S1 | `/auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/shops/select` functional + integration-tested |
| **S3** | RBAC middleware (`tenant_context`, `rbac_guard`) + permission-cache (Backend Arch §8) + password reset flow | 2 wks | S2 | All four pipeline stages from API Arch §4.1 operational; `/auth/password/*` live; seed data for system roles loaded |

### Phase 2 — Platform Admin Core & Shop Onboarding

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S4** | Platform schema migration (Domain A) + separate platform auth realm | 2 wks | S3 | `shops`, `shop_settings`, `shop_verification_documents` live; `/platform/auth/login` with mandatory MFA functional |
| **S5** | Shop self-registration + verification queue + document upload (API Arch §7.2 verification docs) | 2 wks | S4 | `/auth/register-shop`, `/settings/statutory/documents`, `/platform/shops/verification-queue/*` end-to-end: a shop can register, submit docs, get approved, flip to Verified |

### Phase 3 — Catalog & Inventory

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S6** | Catalog schema migration (Domain C) + `medicine_master`/`shop_medicines` CRUD | 2 wks | S5 | `/medicines/*` (list, detail, create, edit) live; frontend medicine list/detail screens begin |
| **S7** | Batches, stock ledger, low-stock/expiry queries + partial indexes | 2 wks | S6 | `/medicines/{id}/batches/*`, `/inventory/expiring`, `/inventory/low-stock`, `/medicines/{id}/stock-ledger` live |
| **S8** | Inventory frontend completion (Item Detail Drawer, master-search, manual adjustment UI) + unit/integration test closure for the domain | 2 wks | S7 | Catalog & Inventory module feature-complete and test-gated |

### Phase 4 — Billing / POS

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S9** | Sales schema migration (Domain E, invoice-related tables) + cart pricing (`gst_calculator`) + invoice creation transaction | 2 wks | S8 | `/billing/cart/price`, `/billing/invoices` (POST) atomic transaction live, including stock decrement |
| **S10** | Held bills, void (with step-up confirmation), barcode/customer lookup, receipt rendering | 2 wks | S9 | `/billing/held-bills/*`, `/billing/invoices/{id}/void`, `/billing/lookup/*`, `/billing/invoices/{id}/receipt` live |
| **S11** | POS frontend: keyboard-shortcut-driven cart UI (F2/F3/Enter), performance pass against the < 300ms target (API Arch §12.1) | 2 wks | S10 | Desktop POS feature-complete; perf budget validated under synthetic load |

### Phase 5 — Customers & Ledger

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S12** | Customer directory/segmentation + ledger entries + "Record Payment" | 2 wks | S11 | `/customers/*`, `/customers/{id}/ledger/*` live; POS wired to real (non-walk-in) customer records |

### Phase 6 — Suppliers, Procurement & GRN

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S13** | Procurement schema migration (Domain D) + supplier directory + PO creation/send | 2 wks | S12 | `/suppliers` (read), `/purchase-orders/*` live |
| **S14** | GRN verification workflow + batch-creation-on-complete transaction (the one path besides manual adjustment that writes `medicine_batches`) | 2 wks | S13 | `/goods-receipts/*` end-to-end: PO → GRN → batch creation → PO closure |
| **S15** | Supplier invoices/payments + frontend for PO/GRN screens | 2 wks | S14 | `/suppliers/finance` payment recording wired; PO/GRN UI complete |

### Phase 7 — Supplier Finance & Relationship Intelligence

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S16** | Relationship scoring/tiering, credit aging buckets, Smart Payment Engine, optimization insights | 2 wks | S15 | `/suppliers/{id}/relationship`, `/suppliers/finance/aging`, `/suppliers/finance/smart-payments` live (recommendation logic computed against real procurement history accumulated since S13) |

### Phase 8 — Delivery

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S17** | Delivery schema (Domain F) + dispatch lifecycle, rider roster, live tracking | 2 wks | S16 (invoices to dispatch against) | `/deliveries/*`, `/riders/*` live, including the pipeline-funnel and tracking endpoints |

### Phase 9 — Notifications & Command Center

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S18** | Notification schema (Domain G) + feed/preferences + async dispatch jobs (WhatsApp/SMS) + Command Center search | 2 wks | S17 | `/notifications/*`, `/search` live; Celery notification-dispatch jobs (Backend Arch §9.2) wired to real event sources from every module built so far |

### Phase 10 — Analytics, Audit, Dashboard

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S19** | Audit schema (Domain H) + interceptor middleware retrofitted onto every existing write path + DB-trigger safety net (Backend Arch §9 high-compliance tables) | 2 wks | S18 | `/audit/*` live; every module from Phase 1–9 now emits structured audit events |
| **S20** | Analytics rollup jobs + endpoints + Dashboard aggregation endpoints | 2 wks | S19 | `/analytics/*`, `/dashboard/*` live, read-replica-routed per API Arch §12.3 |

### Phase 11 — Subscription & Platform Admin Completion

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S21** | Subscription plans, usage metering, plan-limit enforcement wired retroactively into Billing/Settings; payment gateway integration | 2 wks | S20 | `/subscription/*` live; `PLAN_LIMIT_EXCEEDED` enforcement active on real metered actions |
| **S22** | Platform admin completion: system health, plan management, cross-tenant shop search/support tooling | 2 wks | S21 | Full `/platform/*` surface live |

### Phase 12 — Hardening

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S23** | Load/performance testing against API Arch §12 targets; query/index validation against DB Arch §5–6 at simulated 10,000-tenant scale | 2 wks | S22 | Performance report; partition/index behavior validated under load; read-replica routing confirmed effective |
| **S24** | Security hardening: penetration testing, RLS/tenant-isolation adversarial testing, secrets audit, dependency CVE scan | 2 wks | S23 | Security sign-off report; all Section 6.5 security tests passing |

### Phase 13 — Launch Readiness

| Sprint | Goal | Duration | Dependencies | Deliverables |
|---|---|---|---|---|
| **S25** | Full QA checklist (Section 7) execution, UAT (Section 6.7) with pilot pharmacies, deployment checklist (Section 8) closure | 2 wks | S24 | Go/no-go decision for Closed Beta |

**Total: 26 sprints ≈ 52 weeks (~12 months) for the assumed team, end-to-end through launch readiness.** This is the planning baseline, not a contractual estimate — Section 10 names the risks most likely to extend it.

---

## 4. Development Dependencies

A single dependency chain, restated visually as the planning tool requested it (mirrors Section 2's reasoning, compressed):

```
Foundation/Infra
   ↓
Auth ──→ RBAC ──→ Tenant Context Middleware
   ↓
Platform Admin (Shop Verification)
   ↓
Catalog & Inventory  ─────────────────────────────┐
   ↓                                               │
Billing / POS                                      │
   ↓                                               │
Customers & Ledger                                 │
   ↓                                               │
Suppliers + Purchase Orders ──→ GRN ───────────────┘ (GRN writes back into Inventory's medicine_batches)
   ↓
Supplier Finance & Relationship Intelligence  (needs real PO/GRN/invoice history)
   ↓
Delivery  (needs real invoices to dispatch)
   ↓
Notifications & Command Center  (needs every module above as event source / search target)
   ↓
Audit  (must wrap every write path already built — retrofitted by design, not built first)
   ↓
Analytics & Dashboard  (aggregates everything above)
   ↓
Subscription & full Platform Admin  (plan-limit gates apply retroactively to Billing/Settings)
   ↓
Hardening (Performance + Security) — requires the full system to exist
   ↓
Launch Readiness
```

**Two non-obvious cross-dependencies worth calling out explicitly** (both already reflected in Section 3's sprint sequencing, restated here because they're easy to miss in a casual reading of the chain):
1. **GRN depends on Inventory *and* feeds back into it** — it's not purely downstream; GRN completion is the second of only two code paths that create `medicine_batches` rows (the other being manual adjustment), so Inventory's batch-write contract must be finalized before GRN work starts, not the other way around.
2. **Audit is built last among "core" modules but conceptually depends on everything before it being instrumented** — building Audit early would mean re-touching every prior module's service layer to add the interceptor call once Audit exists; building it after means a dedicated retrofit sprint (S19) instead of N small retrofits scattered across N earlier sprints. This is a deliberate efficiency trade, not an oversight.

---

## 5. Milestones

| Milestone | Definition | Modules Required | Exit Criteria |
|---|---|---|---|
| **MVP** | A single pharmacy can run its full daily operation: log in, manage inventory, bill a customer, reorder stock | Auth/RBAC, Platform Admin (basic verification), Catalog/Inventory, Billing/POS, Customers (basic) | A pilot shop can complete a full day's billing + one reorder cycle without engineering intervention; corresponds to completion of Sprint **S12** |
| **Beta** | Full supplier relationship lifecycle + delivery + notifications layered on top of MVP, running with multiple real pilot shops simultaneously | + Suppliers/PO/GRN, Supplier Finance, Delivery, Notifications/Command Center | Multiple pilot shops operating concurrently with no cross-tenant data leakage observed in testing; corresponds to completion of Sprint **S18** |
| **Production Ready** | Every Blueprint-evidenced module is live, audited, analyzed, monetized, and platform-administered; full QA checklist and security sign-off passed | + Audit, Analytics/Dashboard, Subscription, full Platform Admin, all of Hardening (Section 12) | All items in Section 7 (QA Checklist) and Section 8 (Deployment Readiness) checked; corresponds to completion of Sprint **S24** |
| **Enterprise Ready** | Demonstrated operation at a meaningful fraction of the 10,000-pharmacy design target, with the read-replica/partition/Citus-readiness story (DB Arch §6.4, Backend Arch §10.6) validated under real multi-tenant load, plus enterprise-tier support processes (priority support, custom SLAs per Blueprint §1.3) operational | All modules + proven scale validation | Load-tested at a representative multi-thousand-tenant simulated scale; enterprise subscription tier fully operational with its differentiated support process; SLA monitoring live |

---

## 6. Testing Strategy

Each layer below is **continuous from the sprint it becomes possible in**, not a phase that happens only at the end — Section 3's sprints each close with their own deliverable's tests passing; Section 12 (Hardening) is where the *cross-module* and *at-scale* versions of these same test types run.

### 6.1 Unit Testing
- **Scope:** Service-layer business logic and repository-layer query construction, in isolation, per Backend Architecture's `tests/unit/` structure — one suite per service/repository module.
- **Standard:** every service method that enforces a business rule (plan-limit check, credit-limit check, GST calculation, RBAC-adjacent logic) has an explicit test for both the pass and the documented failure code (API Arch §11.5).
- **Gate:** no PR merges with a service-layer change that drops unit coverage on the touched module.

### 6.2 Integration Testing
- **Scope:** API blueprint level — a real request through `auth_guard` → `tenant_context` → `rbac_guard` → service → repository → a real (test) database, per Backend Architecture's `tests/integration/`.
- **Multi-tenant fixture requirement (non-negotiable):** every integration suite runs against **at least two seeded shops** specifically to catch tenant-isolation bugs that a single-tenant fixture would never expose — this directly operationalizes Backend Architecture's own fixture guidance.
- **Gate:** any endpoint touching a tenant table must have an integration test asserting Shop A's request never returns Shop B's data.

### 6.3 API Testing
- **Scope:** Contract-level testing against the frozen API Architecture (Phase 5) — every endpoint in API Arch §1 has a corresponding contract test validating request/response envelope shape (§2), pagination mode correctness (§5), and error-code correctness (§11) independent of business-logic correctness (that's Section 6.2's job).
- **Tooling approach:** schema-driven (OpenAPI/JSON-schema validation against actual responses) so a contract drift is caught automatically, not by manual review.
- **Gate:** a contract test failure blocks merge regardless of whether the underlying feature "works" — a correct feature with a wrong response shape breaks every client integration silently.

### 6.4 UI Testing
- **Scope:** HTML/CSS/vanilla JS frontend, tested at two levels: (a) component/DOM-interaction tests for POS keyboard shortcuts, cart state, form validation rendering of the §2.3 validation-error shape; (b) end-to-end browser flows for each Blueprint workflow (§5.1–§5.8) — onboarding, daily billing, procurement cycle, credit collection, etc.
- **Cross-browser/device matrix:** desktop POS flow + mobile-condensed flow (Blueprint §1.6 mobile variants) tested separately, since they are genuinely different UI surfaces over the same API.
- **Gate:** every Blueprint user workflow (Blueprint §5) has at least one passing end-to-end test before that workflow's milestone is declared complete.

### 6.5 Security Testing
- **Tenant isolation (highest priority, given the architecture's own stated risk):** adversarial tests that attempt to access another shop's data via direct ID manipulation, token tampering, and RLS-bypass attempts — run both as automated regression tests and as a manual penetration-testing pass in Sprint S24.
- **AuthN/AuthZ:** token expiry/replay/rotation correctness, RBAC bypass attempts (calling an endpoint with a token lacking the required permission), platform/tenant realm-confusion attempts (API Arch §11.1 `REALM_MISMATCH`).
- **Injection & input handling:** SQL injection (mitigated structurally by ORM use, but tested anyway on any raw-query paths), file-upload validation (type/size spoofing against §7.2 policies).
- **Dependency/secrets hygiene:** automated CVE scanning on every dependency update; secrets-in-code scanning in CI (ties into Section 8).
- **Gate:** zero open critical/high findings before Production Ready milestone.

### 6.6 Performance Testing
- **Scope:** validates API Architecture §12's targets under realistic and stress load — POS p95 < 300ms, dashboard cache-hit/miss targets, audit cursor-pagination behavior at simulated 12,000+-row-per-shop scale (Blueprint §1.6's own stated enterprise expectation), and partition/index behavior at the volumes DB Architecture §6.1 projects (≈1M invoice rows/day at full scale).
- **Method:** synthetic load generation simulating concurrent multi-tenant traffic (not single-tenant load — the whole point is confirming the `shop_id`-leading-index design holds up when many shops write concurrently), run in Sprint S23 and re-run before every major release thereafter.
- **Gate:** any p95 target miss blocks Production Ready until resolved or the target is explicitly renegotiated with product sign-off — never silently shipped.

### 6.7 User Acceptance Testing (UAT)
- **Participants:** real pilot pharmacy owners/staff (Beta-stage tenants), not internal engineering staff role-playing the persona.
- **Method:** structured walkthroughs of each Blueprint workflow (§5) plus open unscripted usage over a defined pilot window; issues triaged by severity against the QA Checklist (Section 7).
- **Gate:** UAT sign-off from a minimum viable set of pilot shops (number set by product/business, not engineering) is a named precondition for the Production milestone, not a parallel nice-to-have.

---

## 7. QA Checklist (Pre-Production)

### 7.1 Functional
- [ ] Every endpoint in API Architecture §1 implemented and contract-tested
- [ ] Every Blueprint workflow (§5.1–§5.8) passes its end-to-end UI test
- [ ] Every Blueprint screen's evidenced action (Blueprint §1.6, per-module) has a working backend path — no orphaned UI button calling a missing endpoint
- [ ] Every documented gap (Blueprint §6, Backend Arch §11) confirmed **absent**, not half-built (no dangling wholesaler/rider/2FA/returns surface)

### 7.2 Data Integrity
- [ ] All financial calculations (CGST/SGST split, totals, aging buckets, credit utilization) verified against hand-calculated test cases
- [ ] Append-only tables (`invoices`, `stock_ledger`, `audit_logs`, `customer_ledger_entries`) confirmed to have no UPDATE/DELETE code path or DB grant, anywhere
- [ ] Soft-delete behavior confirmed correct on master/reference data (medicines, customers, suppliers) — `RESTRICT` enforced where invoice history exists
- [ ] GRN-completion → batch-creation transaction confirmed atomic (no partial-batch state possible on failure)

### 7.3 Multi-Tenancy
- [ ] Cross-tenant data leakage tests passing on every list/detail endpoint (Section 6.2 gate)
- [ ] RLS policies confirmed active on every `tenant` schema table (DB Arch §9) — not just app-layer filtering
- [ ] Connection-pooling mode (session vs. transaction-level with `SET LOCAL`) confirmed correctly configured end-to-end under concurrent multi-shop load (DB Arch §9 caution, Backend Arch §10.2)
- [ ] Platform-admin `BYPASSRLS` role confirmed inaccessible from any tenant-facing code path

### 7.4 Auth/RBAC
- [ ] All four pipeline stages (API Arch §4.1) confirmed enforced on every protected route, no exceptions found by automated route audit
- [ ] Permission matrix (Blueprint §2) matches seeded `role_permissions` data exactly, reviewed line-by-line
- [ ] Step-up confirmation (void PIN) confirmed required and bypass-tested
- [ ] Platform vs. tenant realm separation confirmed with no shared secrets/session store

### 7.5 Performance
- [ ] All Section 6.6 targets met at the tested scale
- [ ] Index usage confirmed via query plans on the highest-traffic endpoints (no accidental full table scans on `shop_id`-leading-index tables)
- [ ] Cache hit-rate measured and acceptable on dashboard/search/RBAC caches (Backend Arch §8)

### 7.6 Security
- [ ] Section 6.5 zero-open-critical/high gate met
- [ ] All secrets confirmed out of source control (Section 8.2)
- [ ] TLS termination and HSTS confirmed at the edge
- [ ] Rate limiting confirmed active and tuned on auth/POS endpoints

### 7.7 Compliance
- [ ] GST invoice format reviewed against statutory requirement (legal/compliance sign-off, not just engineering self-check)
- [ ] Drug License verification workflow confirmed gating shop operational access correctly
- [ ] Audit log retention/immutability behavior confirmed matches the (still-pending, per DB Arch §10.1) compliance retention window once that number is finalized

### 7.8 Operational
- [ ] Rollback plan tested for the most recent migration
- [ ] On-call runbook exists for every Celery job category (Backend Arch §9)
- [ ] Backup restore drill completed successfully (not just backup-job-succeeded — an actual restore)

---

## 8. Deployment Readiness Checklist

### 8.1 Environment Setup
- [ ] Dev, Staging, Production environments fully parity-configured (same Flask config classes, Backend Arch §1's `config.py` pattern)
- [ ] Postgres primary + at least one streaming read replica provisioned in Staging and Production (Backend Arch §10.2)
- [ ] Redis cluster provisioned, cache and Celery-broker namespaces logically separated (Backend Arch §10.3)
- [ ] `pg_partman` configured and verified pre-creating partitions 2–3 months ahead in Staging before Production cutover (DB Arch §6.2)
- [ ] Reverse proxy / API gateway configured for `/api/v1` path routing, TLS termination, rate limiting (Backend Arch §10.4)

### 8.2 Secrets
- [ ] All credentials (DB, Redis, JWT signing keys, payment gateway, WhatsApp/SMS provider, object storage) in a managed secrets store — none in source control, none in plain environment files committed anywhere
- [ ] Separate secret sets per environment, no Staging/Production credential reuse
- [ ] JWT signing key rotation procedure documented and tested at least once before launch
- [ ] Platform-admin DB role credential (`BYPASSRLS`) stored and access-logged separately from the tenant app's DB credential (Backend Arch §10.2)

### 8.3 Logging
- [ ] Structured, request-ID-correlated logging (API Arch §2.1 `meta.request_id` threaded through) confirmed end-to-end from edge → app → Celery → DB query log
- [ ] Log retention policy set, with financial/audit-adjacent logs distinguished from general application logs per their different compliance lifecycles (DB Arch §6.3)
- [ ] No PII/financial data logged in plaintext at INFO level or below

### 8.4 Monitoring
- [ ] APM/tracing wired across the full request path
- [ ] `pg_stat_statements` enabled and feeding the observability stack (DB Arch §0, Backend Arch §10.5)
- [ ] Platform Admin's System Health screen (`/platform/system-health`) confirmed backed by real live metrics, not mocked data
- [ ] Alerting configured for: replica lag exceeding threshold, Celery queue depth/backlog, partition pre-creation failure, error-rate spikes per endpoint group, plan-limit-exceeded rate (business-relevant signal)

### 8.5 Backup
- [ ] Automated daily Postgres backups confirmed running in Production-equivalent Staging
- [ ] Point-in-time recovery (PITR) capability confirmed available, not just full-snapshot backup
- [ ] Object storage (uploads, exports) backup/versioning policy confirmed

### 8.6 Recovery
- [ ] Documented, rehearsed disaster-recovery runbook with a stated RTO/RPO target
- [ ] Failover procedure to a read replica tested (even if full automatic failover isn't launch-day scope, manual failover must be rehearsed)
- [ ] Rollback procedure for a bad deploy tested in Staging (not just "we can revert the container image" — confirm migrations roll back cleanly too, or are forward-only with a documented mitigation)

### 8.7 Security (deployment-specific, distinct from Section 6.5's testing activity)
- [ ] Network segmentation between platform-admin and tenant-facing services confirmed live, not just designed (Backend Arch §2, §10.1)
- [ ] WAF/DDoS protection at the edge confirmed active
- [ ] Dependency CVE scan clean at deploy time, with a process for re-scanning on a schedule, not just at launch
- [ ] Principle-of-least-privilege confirmed on every service's DB/Redis/storage credentials (no service holding broader access than its repositories require)

---

## 9. Release Strategy

| Stage | Audience | Scope | Exit Criteria to Advance |
|---|---|---|---|
| **Alpha** | Internal team + a small number of friendly, low-risk test shops (possibly fictitious/sandbox data) | MVP milestone modules only | Core daily-operation workflow (Blueprint §5.2) runs without engineering hand-holding for a full week |
| **Closed Beta** | A defined, small set of real pilot pharmacies (Blueprint's actual target persona), under direct support contact with the engineering/product team | Beta milestone modules | UAT sign-off (Section 6.7) from the pilot cohort; no open critical/high security findings; tenant-isolation tests fully green |
| **Public Beta** | Open self-registration (Blueprint §1.6 "Register Shop"), broader but still pre-GA, clearly labeled as Beta to manage expectations | Production Ready milestone modules, with monitoring/alerting fully live (Section 8.4) | Sustained performance targets (Section 6.6) met under real (not just synthetic) multi-tenant load for a defined observation window; support process proven able to handle real-shop ticket volume |
| **Production (GA)** | General availability, all subscription tiers live | Full Production Ready milestone + Section 8 deployment checklist fully closed | Formal go/no-go sign-off across engineering, security, and business stakeholders |
| **Version 1.0** | First stable, fully-supported release | Every Blueprint-in-scope module (Blueprint §1.5 "In scope") live and stable | Defined as the release that closes out this entire roadmap document — Production milestone + at least one full stable operating cycle (e.g., one monthly billing cycle, Section 9.2's subscription module) observed without a sev-1 incident |
| **Version 2.0** | Planned future major release | Explicitly **out of scope for this roadmap** — would address Blueprint §6.2/§6.3 gaps (wholesaler portal, rider app, returns, multi-branch, 2FA UI, Rx management) *only if and when* those go through their own Phase 1–5 design sign-off first. This roadmap does not pre-commit scope to v2.0; naming it here is a placeholder acknowledging the gaps exist, not a planning decision to build them. |

---

## 10. Risk Analysis

### 10.1 Technical Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Tenant-isolation bug ships to production (app-layer filter forgotten somewhere) | Critical — cross-tenant data exposure, the single worst possible incident for this product | Defense-in-depth already designed (RLS + app-layer, per DB Arch §9); mitigated operationally by the mandatory two-tenant integration-test fixture (Section 6.2) and the dedicated adversarial security pass (Sprint S24) |
| Connection-pooling misconfiguration silently breaks RLS under load (the exact caution DB Arch §9 raises) | Critical — same class of risk as above, but load-dependent and therefore easy to miss in low-traffic testing | Explicit checklist item (Section 7.3); load-tested specifically for this in Sprint S23, not assumed safe from functional testing alone |
| Partition/index strategy doesn't hold up at real multi-tenant write concurrency (vs. single-tenant test load) | High — POS write-path degradation directly hits the highest-NFR-pressure module | Sprint S23's load test explicitly simulates concurrent multi-shop writes, not single-tenant throughput, per Section 6.6 |
| Celery job backlog under real load (notification dispatch, exports) delays time-sensitive actions (e.g., WhatsApp receipts) | Medium | Queue separation by priority (Backend Arch §10.1) already designed; monitored via the queue-depth alert in Section 8.4 |
| Vanilla JS frontend (no framework) accumulates unmaintainable complexity as POS UI grows in interaction complexity (keyboard shortcuts, live totals, hold/recall state) | Medium — slows future feature velocity, not a launch blocker | Enforce a lightweight internal component convention/style guide early (Sprint S11) rather than letting POS JS grow ad hoc; revisit framework adoption as an explicit, separate decision if complexity outgrows vanilla JS — not silently absorbed into sprint estimates |

### 10.2 Business Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Pilot pharmacies (Closed Beta) churn before reaching Public Beta due to incomplete feature parity with their existing tools/process | High — undermines the whole UAT signal this roadmap depends on | Sequence MVP to cover the actual daily-operation loop (Section 5) before asking for pilot commitment, not a partial slice |
| Subscription/billing module (Sprint S21) ships late relative to pilot shops' actual need to be charged, creating an awkward "free usage" period that's hard to walk back | Medium | Subscription is explicitly sequenced before Production milestone (Section 1, Phase 11) specifically to avoid this — flagged here as a risk if that sequencing slips |
| Regulatory/compliance items still marked open in prior phases (DB Arch §10.1's retention-window number, the Blueprint's Rx/pharmacist-verification gap) remain unresolved at launch | High for a healthcare-adjacent product in a regulated market | These are named, not silently assumed — Section 7.7's QA checklist explicitly gates on legal/compliance sign-off, not engineering's own judgment of "good enough" |
| Two unreconciled design systems / product names from the original UI archive (Blueprint §6.1) resurface if frontend work proceeds without a final decision | Medium — inconsistent brand/UX undermines trust signals (the product's own value prop is partly "trust") | Must be resolved before Sprint S2 frontend work begins — this is a product decision blocking engineering, called out so it isn't discovered mid-sprint |

### 10.3 Security Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Platform-admin credential compromise (cross-tenant blast radius) | Critical | Mandatory MFA (already in design, Backend Arch §5.2), separate realm with no shared secrets, access logged exhaustively (DB Arch §7) |
| JWT signing-key leakage | Critical | Rotation procedure tested before launch (Section 8.2); short access-token TTL (15 min) limits exposure window even on leak |
| Verification-document storage (Drug License, GSTIN) exposed via storage-level misconfiguration | High — sensitive regulated-business documents | `shop_id`-prefixed object keys plus storage-level access policy as a second isolation layer (API Arch §7.3), tested explicitly in Sprint S24 |
| Rate-limit gaps on auth endpoints allow brute-force/enumeration | Medium | Tiered rate limiting explicitly stricter on `/auth/login` and `/auth/password/forgot` (API Arch §11.4) |

### 10.4 Scalability Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Single Postgres primary becomes a write bottleneck before the 10,000-pharmacy target is reached | High at scale, not at launch | DB Arch §6.4's explicitly-deferred Citus migration path exists precisely because the schema is already `shop_id`-shaped for it — this roadmap doesn't build it now, but Sprint S23's load testing should surface the actual headroom remaining, informing *when* (not *whether*) that migration becomes necessary |
| Read-replica lag causes user-visible staleness on aggressively-cached or replica-routed reads (dashboard, analytics) under real load | Medium | API Arch §12.3 already commits to routing same-request-reflects-own-write cases to primary; monitored via the replica-lag alert (Section 8.4) |
| Audit log / stock ledger growth outpaces the tiered-storage archival automation (DB Arch §6.3) if pg_partman maintenance silently fails | High over time, low immediate visibility | Dedicated monitoring checklist item (Section 8.4: "partition pre-creation failure" alert) rather than relying on someone noticing slow queries months later |
| Notification/export Celery workload grows faster than worker fleet scaling keeps pace as tenant count grows | Medium | Independent scaling of priority vs. throughput queues (Backend Arch §10.1) gives an operational lever; queue-depth alerting (Section 8.4) gives the early-warning signal |

---

## 11. Success Metrics

### 11.1 Development KPIs
- **Sprint goal completion rate** — % of sprints in Section 3 closing all stated deliverables on schedule; tracked from S0 onward as the primary delivery-health signal.
- **Test coverage trend** — unit + integration coverage per module, tracked per Section 6.1/6.2 gates, not allowed to regress sprint-over-sprint.
- **Defect escape rate** — issues found in UAT/Beta that should have been caught by an earlier test layer (Section 6.2–6.6) — a proxy for whether the testing strategy is actually catching what it's designed to catch.
- **Mean time to resolve a Sev-1/Sev-2 defect** during Beta and post-GA.

### 11.2 Performance KPIs
- **p95 response time per endpoint class**, measured continuously against the Section 6.6 / API Arch §12.1 targets — not just at the Sprint S23 load-test snapshot, but as an ongoing production dashboard.
- **Cache hit rate** on dashboard/search/RBAC caches (target informed by Backend Arch §8's TTL design — a consistently low hit rate signals a TTL or invalidation-trigger problem worth revisiting).
- **Read-replica lag**, continuously monitored (Section 8.4).
- **Celery queue depth / job-completion latency** per queue (priority vs. throughput, Backend Arch §10.1).
- **Database partition health** — partitions pre-created on schedule, no partition exceeding its designed row-count/size envelope (DB Arch §6).

### 11.3 Business KPIs
- **Active verified shops** (mirrors the Platform Admin Panel's own "Total Active Shops" KPI, Blueprint §1.4) — tracked from Closed Beta onward.
- **Total Platform GMV** and **Active Subscriptions by tier** (same Blueprint §1.4 metrics) — the product's own stated success signals, now also engineering-tracked as a sanity check that the Subscription module (Sprint S21) is functioning correctly in production.
- **Plan-limit-exceeded event rate** — both a business signal (upsell opportunity, tracked by product) and a technical health signal (confirms the metering logic from API Arch §11.5 is actually firing in production, not silently broken).
- **Verified-wholesaler count** (Blueprint §1.4) — tracked even though no wholesaler portal exists, since the verification *workflow itself* (Phase 6/7 modules) is fully built and this is its output metric.

### 11.4 User Adoption KPIs
- **Daily Active Shops** (shops with at least one billing transaction that day) — the most direct behavioral signal that the MVP's core loop (Section 5) is actually being used, not just provisioned.
- **POS transactions per shop per day**, tracked against the subscription tier's transaction limits (Blueprint §1.3 table) — both an adoption signal and an early indicator of shops approaching their plan ceiling.
- **Feature-module adoption breadth** — % of active shops using Procurement (PO/GRN), Delivery, and Analytics beyond core Billing, since the Blueprint's value proposition depends on the *unified* tool, not just POS replacement.
- **UAT-to-Beta retention** — % of Closed Beta pilot shops still active at Public Beta launch, the most direct test of whether the roadmap's sequencing genuinely produced a usable product end to end, not just a feature checklist.
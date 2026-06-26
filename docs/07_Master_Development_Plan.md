# MedicoSaathi — Phase 8: Master Development Plan
### CTO / EM / TPM / Scrum Master Execution Document · Sprint 0 → Version 1.0

This is an execution document. It does not redesign Phases 1–7 — it sequences exactly what those seven frozen documents already approved into a sprint-by-sprint build order, with every sprint accountable against the Engineering Constitution (Phase 7) and every module placed in the order the Development Roadmap (Phase 6) already justified. Sprint numbering (`Sprint 0`…`Sprint 25`) matches Phase 6 §3 exactly, now expanded to full execution detail per sprint.

**Team assumption (restated from Phase 6, load-bearing for every duration estimate below):** 4 backend engineers, 2 frontend engineers, 1 DevOps/SRE, 1 QA engineer, 1 EM/CTO. Two-week sprints. 20+ engineer orgs should run multiple module tracks in parallel within a sprint (e.g., a second backend pair starting Phase 6's Customers work while the first finishes Billing) — Section "Critical Path Analysis" below identifies exactly which work is safe to parallelize and which is not.

---

## Sprint 0 — Foundation & Platform Scaffolding

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Stand up a running, empty, fully-pipelined application skeleton across all three environments |
| 2 | Business Goal | Zero — this sprint produces no user-visible value; it is the precondition for every dollar of value every later sprint produces |
| 3 | Engineering Goal | A new engineer can clone the repo, run the app locally, and see CI go green on day one |
| 4 | Modules Covered | None (infrastructure only) |
| 5 | Features to Build | App factory, config classes (Dev/Staging/Prod), Dockerized local dev environment, Alembic wiring |
| 6 | Backend Tasks | `app/__init__.py` factory, `app/config.py`, `app/extensions.py` (db, redis, celery, jwt, limiter stubs) per Backend Architecture §1 |
| 7 | Database Tasks | Provision Dev/Staging Postgres instances; connect Alembic to the approved schema baseline (DB Architecture, Phase 3) — no DDL authored, only tooling validated against the frozen schema |
| 8 | API Tasks | Register the empty `api/v1/__init__.py` blueprint shell with no live routes yet |
| 9 | Frontend Tasks | Static asset pipeline scaffolding, base HTML layout shell, shared CSS variables file |
| 10 | Security Tasks | Secrets-management tooling wired (Phase 7 §14.2) before any credential is ever created; CI secret-scanning enabled from commit one |
| 11 | Testing Tasks | CI pipeline running an empty test suite green; linter/formatter (Phase 7 §2.1) enforced from the first commit |
| 12 | Documentation Tasks | Root README (Phase 7 §18.5): how to run locally, how to run tests, links to all seven frozen Phase documents |
| 13 | Deployment Tasks | Dev/Staging/Production environment shells provisioned (App Architecture §10.1); reverse proxy stub configured |
| 14 | Dependencies | None — this is sprint zero |
| 15 | Expected Deliverables | Running empty Flask app in all three environments; green CI; Alembic connected |
| 16 | Acceptance Criteria | A fresh clone + documented setup steps produces a working local app and a passing test run with no manual undocumented steps |
| 17 | Definition of Done | Phase 7 §19 DoD checklist satisfied for infrastructure scope (no feature-specific items apply yet) |
| 18 | Risks | Environment-parity drift between Dev/Staging/Prod if config classes aren't disciplined from day one (Phase 7 §2.4) |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical (blocks everything) |

---

## Sprint 1 — Identity Schema & Core Repositories

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Stand up the Identity domain (DB Architecture Domain B) and its repository layer, fully unit-tested, with no endpoints exposed yet |
| 2 | Business Goal | None directly visible to users yet — this is the foundation every login, every permission check, and every audit trail depends on |
| 3 | Engineering Goal | `identity/` repository module passes its full unit-test suite against a real (test) Postgres instance |
| 4 | Modules Covered | Auth/RBAC (data layer only) |
| 5 | Features to Build | `users`, `roles`, `permissions`, `role_permissions`, `shop_users`, `auth_sessions` tables live; `identity/user_repository`, `identity/role_permission_repository`, `identity/session_repository` |
| 6 | Backend Tasks | `models/identity.py`; `repositories/identity/*`; `base_repository.py`'s tenant-binding contract (Backend Architecture §4) implemented and unit-tested in isolation |
| 7 | Database Tasks | First real migration: Domain B tables, indexes, RLS policy scaffolding (DB Architecture §9) applied even though no app code exercises it yet |
| 8 | API Tasks | None — no routes this sprint |
| 9 | Frontend Tasks | None |
| 10 | Security Tasks | Password hashing utility selected and implemented (never rolled in-house); RLS policies on `users`/`shop_users` verified present even pre-launch |
| 11 | Testing Tasks | Unit tests for every repository method, including the deliberate failure case (no tenant context bound → repository refuses to query, per Backend Architecture §4) |
| 12 | Documentation Tasks | Module docstrings (Phase 7 §18.2) for every new repository; ADR if any repository contract deviates from Backend Architecture §4's base contract |
| 13 | Deployment Tasks | Migration applied to Staging |
| 14 | Dependencies | Sprint 0 |
| 15 | Expected Deliverables | Identity schema live in Staging; repository layer 100% unit-test covered |
| 16 | Acceptance Criteria | A repository call without a bound tenant context raises the expected exception in every method, verified by test, not by inspection |
| 17 | Definition of Done | Phase 7 §19 satisfied; no endpoint exists yet so API/contract-test items are N/A this sprint |
| 18 | Risks | Getting the tenant-binding contract wrong here propagates into every later repository — this sprint gets disproportionate review attention for exactly that reason |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 2 — Authentication Endpoints

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | A user can log in, refresh, log out, and select an active shop, end to end |
| 2 | Business Goal | First real login screen functions — the literal front door of the product opens |
| 3 | Engineering Goal | `auth_service` + `auth_bp` fully implemented against API Architecture §1.1/§3 with zero contract drift |
| 4 | Modules Covered | Authentication |
| 5 | Features to Build | Login, refresh, logout, logout-all, shop-select |
| 6 | Backend Tasks | `services/auth_service.py`: credential verification, session issuance, token rotation logic (API Arch §3) |
| 7 | Database Tasks | None new — uses Sprint 1's schema |
| 8 | API Tasks | `POST /auth/login`, `/auth/refresh`, `/auth/logout`, `/auth/logout-all`, `/auth/shops/select`, `GET /auth/me` — contract-tested against API Architecture §2 envelope shapes |
| 9 | Frontend Tasks | Login screen, shop-picker screen (multi-shop case) |
| 10 | Security Tasks | JWT signing key provisioned via secrets store (Phase 7 §14.2); refresh-token rotation verified by an explicit replay-attack test (API Arch §3.3) |
| 11 | Testing Tasks | Integration tests for full login→refresh→logout lifecycle; security test for token replay and expired-token rejection |
| 12 | Documentation Tasks | API doc generation wired for these first live endpoints (Phase 7 §18.4) — establishes the pattern every later sprint reuses |
| 13 | Deployment Tasks | First real feature deployed to Staging |
| 14 | Dependencies | Sprint 1 |
| 15 | Expected Deliverables | Functional login flow in Staging, frontend and backend both |
| 16 | Acceptance Criteria | A multi-shop test user can log in, see a shop picker, select a shop, and receive a shop-scoped token verified to carry correct claims |
| 17 | Definition of Done | Phase 7 §19 fully applicable from this sprint forward |
| 18 | Risks | Shop-context token design (API Arch §3.2) is subtle — under-testing the multi-shop edge case here is the most likely place for a later production confusion bug |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 3 — RBAC Middleware, Permission Cache & Password Reset

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Every subsequent endpoint in the system can be permission-gated and tenant-scoped automatically |
| 2 | Business Goal | None directly visible — this sprint is what makes every later business feature *safe* to ship |
| 3 | Engineering Goal | The four-stage authorization pipeline (API Architecture §4.1) fully operational and proven on a test route |
| 4 | Modules Covered | Auth/RBAC |
| 5 | Features to Build | `tenant_context` middleware, `rbac_guard` middleware, permission cache (Backend Architecture §8), password reset flow |
| 6 | Backend Tasks | `middleware/tenant_context.py`, `middleware/rbac_guard.py`; seed `role_permissions` data matching Blueprint §2's permission matrix exactly |
| 7 | Database Tasks | Seed-data migration for system roles (`owner`/`manager`/`cashier`/`auditor`) and their permission sets |
| 8 | API Tasks | `POST /auth/password/forgot`, `/auth/password/reset` |
| 9 | Frontend Tasks | Password reset request/confirm screens |
| 10 | Security Tasks | Account-enumeration protection verified (forgot-password always returns generic success, API Arch §3.5); brute-force rate limiting tuned on `/auth/login` and `/auth/password/forgot` (API Arch §11.4) |
| 11 | Testing Tasks | A dummy protected test route built solely to prove the pipeline rejects unauthorized/unscoped/wrong-permission requests correctly, across every failure mode in API Architecture §11.1/§11.2 |
| 12 | Documentation Tasks | RBAC permission matrix documented as the literal seed-data source of truth (Phase 7 §6.6) |
| 13 | Deployment Tasks | Deployed to Staging; permission cache (Redis) provisioned |
| 14 | Dependencies | Sprint 2 |
| 15 | Expected Deliverables | Fully operational auth+RBAC pipeline; password reset live |
| 16 | Acceptance Criteria | All API Architecture §11.1/§11.2 error codes reproducible on demand via the test route; password reset revokes all sessions per API Arch §3.5 |
| 17 | Definition of Done | Phase 7 §19 + Phase 7 §14 security checklist fully walked, since this sprint is pure security-critical infrastructure |
| 18 | Risks | This is the highest-leverage sprint in the whole plan for a tenant-isolation defect to be born silently — extra reviewer attention mandated per Phase 7 §12.7 |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 4 — Platform Schema & Platform Admin Auth Realm

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Stand up the entirely separate platform-admin identity realm |
| 2 | Business Goal | Internal team can begin operating the verification workflow that every shop's onboarding depends on |
| 3 | Engineering Goal | Platform auth realm proven to share zero code paths/secrets with tenant auth |
| 4 | Modules Covered | Platform Admin (identity layer) |
| 5 | Features to Build | `shops`, `shop_settings`, `shop_verification_documents` schema; `platform_admins` auth with mandatory MFA |
| 6 | Backend Tasks | `services/platform_auth_service.py`; `repositories/platform/shop_repository.py` |
| 7 | Database Tasks | Domain A migration; `BYPASSRLS` platform DB role provisioned and credentialed separately (Backend Architecture §10.2) |
| 8 | API Tasks | `POST /platform/auth/login` with MFA step |
| 9 | Frontend Tasks | Platform admin login screen (separate app shell from tenant frontend, per Backend Architecture §2's network-segmentation intent) |
| 10 | Security Tasks | Mandatory MFA enforced and tested as a hard block, not a soft prompt (Backend Architecture §5.2); realm-mismatch rejection test (`REALM_MISMATCH`, API Arch §11.1) |
| 11 | Testing Tasks | Adversarial test: a tenant token presented to any `/platform/*` route must be rejected at `auth_guard`, before `rbac_guard` even runs |
| 12 | Documentation Tasks | ADR documenting the platform/tenant realm separation as implemented, cross-referenced to Backend Architecture §5 |
| 13 | Deployment Tasks | Platform-admin surface deployed on its separate routing/network segment in Staging (Backend Architecture §10.1) |
| 14 | Dependencies | Sprint 3 (reuses the RBAC mechanism conceptually, though against a distinct permission set) |
| 15 | Expected Deliverables | Platform admins can log in with MFA on an isolated surface |
| 16 | Acceptance Criteria | Network/route isolation verified by an actual cross-realm request attempt, not just code inspection |
| 17 | Definition of Done | Phase 7 §19 + explicit sign-off that no shared secret exists between realms |
| 18 | Risks | Platform-admin credential compromise has the largest blast radius in the system (Phase 6 §10.3) — this sprint's security bar is the highest in the early roadmap |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 5 — Shop Self-Registration & Verification Queue

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | A pharmacy can register, submit statutory documents, and be approved end to end |
| 2 | Business Goal | The actual top-of-funnel acquisition flow is live — MedicoSaathi can onboard its first real shop |
| 3 | Engineering Goal | Full document-upload-to-verification-approval pipeline proven, including the signed-URL upload pattern (API Architecture §7) |
| 4 | Modules Covered | Platform Admin, Settings (statutory) |
| 5 | Features to Build | Shop registration, document upload, verification queue review/approve/reject |
| 6 | Backend Tasks | `services/settings_service.py` (statutory submission), `services/platform_admin_service.py` (queue review) |
| 7 | Database Tasks | `shop_verification_queue` wired; verification-status transitions enforced at the service layer |
| 8 | API Tasks | `POST /auth/register-shop`, `/settings/statutory/documents`, `GET/POST /platform/shops/verification-queue/*` |
| 9 | Frontend Tasks | Shop registration form, statutory-document upload screen, platform-admin verification-queue review screen |
| 10 | Security Tasks | Object-storage `shop_id`-prefixed key isolation verified for verification documents (API Architecture §7.3); platform-scoped signed URL for document review confirmed never reusable as a tenant URL |
| 11 | Testing Tasks | End-to-end test: register → submit doc → approve → shop flips to `Verified` → `SHOP_NOT_VERIFIED` (API Arch §11.5) no longer blocks the shop |
| 12 | Documentation Tasks | Onboarding workflow documented against Blueprint §5.1, confirming implementation matches the approved flow exactly |
| 13 | Deployment Tasks | Object storage provisioned in Staging with the tenant-prefixed key policy live |
| 14 | Dependencies | Sprint 4 |
| 15 | Expected Deliverables | First end-to-end shop onboarding in Staging |
| 16 | Acceptance Criteria | A test shop can complete registration-to-verified-status without any manual database intervention |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | This is the first sprint exercising real file upload — type/size-spoofing tests (Phase 7 §14.9) are mandatory before sign-off, not optional |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 6 — Catalog Schema & Medicine CRUD

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | A verified shop can build out its medicine catalog |
| 2 | Business Goal | First piece of genuinely operational pharmacy data enters the system |
| 3 | Engineering Goal | Catalog repository/service layer live, with `pg_trgm` search infrastructure proven functional |
| 4 | Modules Covered | Catalog & Inventory |
| 5 | Features to Build | `medicine_categories`, `medicine_master`, `shop_medicines` CRUD; typeahead search |
| 6 | Backend Tasks | `services/inventory_service.py` (catalog portion), `repositories/catalog/medicine_repository.py` |
| 7 | Database Tasks | Domain C migration (catalog tables); `pg_trgm` extension enabled and indexed (DB Architecture §5) |
| 8 | API Tasks | `GET/POST/PATCH/DELETE /medicines`, `GET /medicines/master-search`, `GET /medicines/categories` |
| 9 | Frontend Tasks | Medicine list screen, add/edit medicine form, category browser |
| 10 | Security Tasks | RBAC permission `(inventory, view/create/edit/delete)` enforced and tested per role per Blueprint §2's matrix |
| 11 | Testing Tasks | Multi-tenant isolation test on every new endpoint (mandatory per Phase 7 §17.2); search-relevance smoke test |
| 12 | Documentation Tasks | Repository docstrings stating index reliance for the new `pg_trgm` search queries (Phase 7 §18.3) |
| 13 | Deployment Tasks | Migration applied to Staging |
| 14 | Dependencies | Sprint 5 (needs a verified shop to attach catalog data to) |
| 15 | Expected Deliverables | Functional medicine catalog management in Staging |
| 16 | Acceptance Criteria | Two seeded test shops' catalogs never cross-leak in any list/search/detail call |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | First module with meaningful per-shop data volume — early signal on whether `pg_trgm` index performance assumptions (DB Architecture §5) hold |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 7 — Batches, Stock Ledger & Alert Queries

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Real, batch-level inventory tracking with expiry/low-stock detection live |
| 2 | Business Goal | The product's core "never run out, never expire silently" value proposition becomes real |
| 3 | Engineering Goal | Partial-index-backed expiry/low-stock queries proven performant at representative data volume |
| 4 | Modules Covered | Catalog & Inventory |
| 5 | Features to Build | Batch CRUD, stock ledger, near-expiry queries, low-stock queries, manual adjustment |
| 6 | Backend Tasks | `repositories/catalog/batch_repository.py`, `repositories/catalog/stock_ledger_repository.py` |
| 7 | Database Tasks | `medicine_batches`, `stock_ledger` tables; partial indexes for near-expiry and below-threshold queries (DB Architecture §5); BRIN index on `stock_ledger` for range scans |
| 8 | API Tasks | `GET /medicines/{id}/batches/*`, `/inventory/expiring`, `/inventory/low-stock`, `POST /medicines/{id}/batches/adjustment`, `GET /medicines/{id}/stock-ledger` |
| 9 | Frontend Tasks | Batch breakdown view, manual adjustment form, low-stock/expiry alert widgets |
| 10 | Security Tasks | Adjustment endpoint restricted to `(inventory, edit)` only — verified no lower-privileged role can silently alter stock |
| 11 | Testing Tasks | EXPLAIN-plan verification (Phase 7 §5.7) on the expiry/low-stock queries at a seeded multi-thousand-batch test dataset, not a handful of rows |
| 12 | Documentation Tasks | Index-usage docstrings (Phase 7 §18.3) for every new repository method |
| 13 | Deployment Tasks | Migration applied to Staging |
| 14 | Dependencies | Sprint 6 |
| 15 | Expected Deliverables | Full batch/stock-ledger functionality, alert queries performant |
| 16 | Acceptance Criteria | Expiry/low-stock queries return correct results in under the dashboard-tier response target even at seeded high-batch-count test data |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | Stock ledger is append-only and will be the fastest-growing table in early testing — any accidental `UPDATE`/`DELETE` path here is treated as a Sev-1 finding (Phase 7 §20.4) |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 8 — Inventory Frontend Completion & Module Test Closure

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Catalog & Inventory module fully feature-complete and test-gated, ready to be relied upon by Billing |
| 2 | Business Goal | A pharmacy owner can fully manage their inventory end to end through the UI, no backend-only gaps |
| 3 | Engineering Goal | Close out any remaining unit/integration coverage gaps before Billing starts consuming this module |
| 4 | Modules Covered | Catalog & Inventory |
| 5 | Features to Build | Item Detail Drawer (margin, 6-month trend, movement activity), master-catalog linking UI |
| 6 | Backend Tasks | `GET /medicines/{id}/detail` aggregation logic |
| 7 | Database Tasks | None new — query-tuning only if Sprint 7's EXPLAIN review flagged anything |
| 8 | API Tasks | Final contract-test pass on the full `/medicines/*` and `/inventory/*` surface |
| 9 | Frontend Tasks | Item Detail Drawer UI, polish pass on list/search screens |
| 10 | Security Tasks | Full RBAC matrix re-verification across all Inventory endpoints before sign-off |
| 11 | Testing Tasks | Module-level regression suite finalized; this is the explicit "test closure" gate referenced in Phase 6 §3 |
| 12 | Documentation Tasks | Module README finalized (Phase 7 §18.5) |
| 13 | Deployment Tasks | Staging soak test |
| 14 | Dependencies | Sprint 7 |
| 15 | Expected Deliverables | Catalog & Inventory module signed off as feature-complete |
| 16 | Acceptance Criteria | Every Blueprint §1.6 Inventory screen has a working, tested backend path; zero open defects above Sev-3 |
| 17 | Definition of Done | Full Phase 7 §19 DoD, module-wide |
| 18 | Risks | If this closure is rushed, Billing (next sprint) inherits hidden inventory defects under its own higher time pressure — this sprint is the deliberate pressure-release valve before that happens |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 9 — Billing Core: Cart Pricing & Invoice Transaction

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | A bill can be generated end to end, atomically, with correct tax math and stock decrement |
| 2 | Business Goal | The product's revenue-critical core transaction goes live |
| 3 | Engineering Goal | The single most failure-sensitive transaction in the system (invoice + items + payment + stock decrement) proven atomic under failure-injection testing |
| 4 | Modules Covered | Billing/POS |
| 5 | Features to Build | Cart pricing preview, invoice creation transaction |
| 6 | Backend Tasks | `services/billing_service.py`; `utils/gst_calculator.py`; `repositories/sales/invoice_repository.py` |
| 7 | Database Tasks | Domain E sales schema (invoice-related tables) migrated; partition strategy (DB Architecture §6.2) applied from day one, not retrofitted |
| 8 | API Tasks | `POST /billing/cart/price`, `POST /billing/invoices` |
| 9 | Frontend Tasks | Cart UI skeleton (full keyboard-driven polish deferred to Sprint 11) |
| 10 | Security Tasks | Plan-limit pre-check (Backend Architecture §3, API Arch §11.5 `PLAN_LIMIT_EXCEEDED`) wired even though Subscription module itself ships later — the gate exists from day one, stubbed against a default plan if needed |
| 11 | Testing Tasks | Failure-injection test: forced failure mid-transaction must leave zero partial state (no invoice without stock decrement, no decrement without invoice) |
| 12 | Documentation Tasks | GST calculation logic documented with worked examples for compliance reviewability |
| 13 | Deployment Tasks | Migration applied to Staging |
| 14 | Dependencies | Sprint 8 (real stock to sell against) |
| 15 | Expected Deliverables | Atomic bill-generation transaction live in Staging |
| 16 | Acceptance Criteria | 100 concurrent simulated invoice creations against shared low-stock batches never oversell (race condition test, ties to API Arch §11.5 `BATCH_OUT_OF_STOCK`) |
| 17 | Definition of Done | Phase 7 §19 fully applied, with the atomicity test as an explicit named gate |
| 18 | Risks | Highest-stakes transaction in the codebase — any shortcut here is a direct revenue-integrity risk; extra senior review mandated |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 10 — Held Bills, Void, Lookups & Receipts

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | The full POS workflow beyond the happy-path sale is live |
| 2 | Business Goal | Real-world cashier workflows (interruptions, corrections, customer lookup) are supported, not just the ideal-case sale |
| 3 | Engineering Goal | Step-up confirmation pattern (void) proven as a reusable mechanism, not a one-off hack |
| 4 | Modules Covered | Billing/POS |
| 5 | Features to Build | Held bills, void with PIN confirmation, barcode/customer lookup, receipt rendering, WhatsApp receipt dispatch |
| 6 | Backend Tasks | `repositories/sales/held_bill_repository.py`; void step-up logic in `billing_service` |
| 7 | Database Tasks | `held_bills` table (JSONB cart snapshot) |
| 8 | API Tasks | `/billing/held-bills/*`, `/billing/invoices/{id}/void`, `/billing/lookup/*`, `/billing/invoices/{id}/receipt`, `/billing/invoices/{id}/send` |
| 9 | Frontend Tasks | Hold/recall UI, void confirmation modal, barcode scan integration, receipt preview |
| 10 | Security Tasks | Void step-up tested as a genuine blocker (a request without the confirmation field must fail, not silently succeed) — `STEP_UP_REQUIRED` (API Arch §11.2) |
| 11 | Testing Tasks | Integration tests for hold→recall round-trip data integrity (cart snapshot fidelity); async receipt-dispatch job tested for idempotency (Phase 7 §8.4) |
| 12 | Documentation Tasks | Runbook for the WhatsApp-dispatch Celery job (Phase 7 §18.6) |
| 13 | Deployment Tasks | First Celery job category deployed (`notification_jobs` subset for receipts) |
| 14 | Dependencies | Sprint 9 |
| 15 | Expected Deliverables | Full non-happy-path POS workflow live |
| 16 | Acceptance Criteria | Void cannot succeed without the confirmation field under any client manipulation attempt |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | First real third-party integration (WhatsApp) — external API instability risk; mitigated by Celery retry/idempotency design, but worth explicit monitoring from day one |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 11 — POS Frontend Performance Hardening

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | The desktop POS screen hits its sub-second, keyboard-first NFR target under real conditions |
| 2 | Business Goal | The single highest-frequency, highest-visibility screen in the product feels instant to a cashier |
| 3 | Engineering Goal | API Architecture §12.1's < 300ms p95 target for Billing/POS endpoints validated, not assumed |
| 4 | Modules Covered | Billing/POS |
| 5 | Features to Build | Keyboard-shortcut-driven cart interactions (F2/F3/Enter), live total updates, performance polish |
| 6 | Backend Tasks | Targeted query/caching optimization on any endpoint found short of its target |
| 7 | Database Tasks | Index tuning if profiling surfaces a gap |
| 8 | API Tasks | No new endpoints — performance-only pass on existing Billing endpoints |
| 9 | Frontend Tasks | Centralized keyboard-input-handling module (Phase 7 §2.2's explicit requirement), perceived-performance polish (optimistic UI where safe) |
| 10 | Security Tasks | None new this sprint — focus is performance, not new surface area |
| 11 | Testing Tasks | Synthetic load test against the < 300ms target (Phase 7 §15.1); UI interaction timing test for the keyboard-shortcut flow |
| 12 | Documentation Tasks | Performance baseline recorded for future regression comparison (Phase 7 §17.6) |
| 13 | Deployment Tasks | Performance-tuned build promoted to Staging |
| 14 | Dependencies | Sprint 10 |
| 15 | Expected Deliverables | POS module fully feature-complete and performance-validated |
| 16 | Acceptance Criteria | Measured p95 under synthetic load meets the documented target; this becomes the baseline all future Billing changes are regression-tested against |
| 17 | Definition of Done | Phase 7 §19 + Phase 7 §15.7 explicit performance sign-off |
| 18 | Risks | If the target is missed, this sprint extends rather than shipping a known-slow core workflow — flagged explicitly so schedule pressure doesn't quietly waive the gate |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 12 — Customers & Customer Ledger

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Full customer relationship and credit-ledger management live, replacing POS's walk-in-only mode |
| 2 | Business Goal | **MVP milestone reached** (Phase 6 §5) — a single pharmacy can now run its complete daily operation |
| 3 | Engineering Goal | Append-only ledger semantics proven correct under concurrent payment-recording load |
| 4 | Modules Covered | Customers |
| 5 | Features to Build | Customer directory/segmentation, ledger entries, "Record Payment" |
| 6 | Backend Tasks | `services/customer_service.py`; `repositories/sales/customer_repository.py` |
| 7 | Database Tasks | `customers`, `customer_ledger_entries` tables; segmentation query indexes |
| 8 | API Tasks | `/customers/*`, `/customers/{id}/ledger/*` |
| 9 | Frontend Tasks | Customer directory (segmented tabs), customer profile drawer, ledger view, payment-recording form |
| 10 | Security Tasks | Ledger repository confirmed to have no update/delete method at the interface level (Phase 7 §5.6/§20.4) |
| 11 | Testing Tasks | Concurrency test on simultaneous payment recordings against the same customer, confirming `balance_after` always computes correctly with no lost update |
| 12 | Documentation Tasks | Ledger correction procedure documented (offsetting entries only, never edits) per Phase 7 §5.6 |
| 13 | Deployment Tasks | Migration applied to Staging |
| 14 | Dependencies | Sprint 11 (POS needs to link real customers to invoices) |
| 15 | Expected Deliverables | **MVP-complete** Staging environment |
| 16 | Acceptance Criteria | A pilot-representative full day's billing + customer credit cycle completes without engineering intervention (Phase 6 §5 MVP exit criteria) |
| 17 | Definition of Done | Phase 7 §19 fully applied; this sprint's closure is the formal MVP milestone gate |
| 18 | Risks | First module where a lost-update concurrency bug would directly misstate a customer's owed balance — financial-correctness review weighted accordingly |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical — **MVP Milestone** |

---

## Sprint 13 — Supplier Directory & Purchase Orders

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Shops can browse suppliers and create/send purchase orders |
| 2 | Business Goal | The procurement side of the business — half the product's "relationship network" promise — begins coming online |
| 3 | Engineering Goal | PO lifecycle state machine (draft→sent→partially_received→completed→cancelled) implemented cleanly against lookup-table-backed statuses |
| 4 | Modules Covered | Suppliers, Purchase Orders |
| 5 | Features to Build | Supplier directory read, PO creation/edit/send/cancel |
| 6 | Backend Tasks | `services/supplier_service.py` (directory portion), `services/procurement_service.py` (PO portion) |
| 7 | Database Tasks | Domain D migration (suppliers, `shop_supplier_relationships`, `purchase_orders`, `purchase_order_items`) |
| 8 | API Tasks | `GET /suppliers`, `GET/POST/PATCH /purchase-orders`, `/purchase-orders/{id}/send`, `/cancel` |
| 9 | Frontend Tasks | Supplier directory screen, PO creation form (with below-min-threshold pre-fill from Inventory), PO list/detail |
| 10 | Security Tasks | RBAC matrix for `procurement:*` permissions verified per role |
| 11 | Testing Tasks | Integration test confirming "Reorder Now" (Sprint 7's endpoint) correctly pre-fills a draft PO end to end |
| 12 | Documentation Tasks | PO state-machine documented explicitly (valid transitions, what blocks each) |
| 13 | Deployment Tasks | Migration applied to Staging |
| 14 | Dependencies | Sprint 12 |
| 15 | Expected Deliverables | Functional PO creation-to-send flow |
| 16 | Acceptance Criteria | An invalid state transition (e.g., sending an already-cancelled PO) is rejected with the correct business-rule error code |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | First module exercising the lookup-table-backed status design under real workflow logic — worth confirming the pattern holds up before GRN (next sprint) builds on it |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 14 — Goods Receiving (GRN) & Batch Creation

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Incoming stock can be verified and converted into real, sellable batches |
| 2 | Business Goal | The procurement loop closes — stock ordered becomes stock available to sell, fully traceable |
| 3 | Engineering Goal | The GRN-completion transaction (the second of only two paths that write `medicine_batches`) proven atomic and consistent with Sprint 7's batch contract |
| 4 | Modules Covered | Goods Receiving |
| 5 | Features to Build | GRN start, per-item verification with discrepancy flagging, GRN completion |
| 6 | Backend Tasks | `repositories/procurement/goods_receipt_repository.py`; GRN-completion orchestration in `procurement_service` |
| 7 | Database Tasks | `goods_receipts`, `goods_receipt_items` tables |
| 8 | API Tasks | `/goods-receipts/*` full surface |
| 9 | Frontend Tasks | GRN verification screen (per-line-item check-off), discrepancy flag UI |
| 10 | Security Tasks | `(procurement, edit)` permission required for verification steps; completion step requires no lower-privileged bypass |
| 11 | Testing Tasks | Atomicity test: a forced failure mid-GRN-completion must leave the PO open and create zero partial batches — direct extension of Sprint 9's failure-injection pattern, applied here because this is the other high-stakes atomic transaction in the system |
| 12 | Documentation Tasks | Cross-reference doc explicitly tying GRN completion back to Sprint 7's batch contract, confirming no divergence crept in |
| 13 | Deployment Tasks | Migration applied to Staging |
| 14 | Dependencies | Sprint 13 |
| 15 | Expected Deliverables | Full PO → GRN → batch-creation → PO-closure loop functional |
| 16 | Acceptance Criteria | A GRN against a multi-item PO with one deliberately-flagged discrepancy completes correctly, creating batches only for the verified items |
| 17 | Definition of Done | Phase 7 §19 fully applied, atomicity test as an explicit named gate (mirrors Sprint 9) |
| 18 | Risks | This is the dependency Phase 6 §4 calls out as "non-obvious" — GRN both depends on and writes back into Inventory; regression risk to Sprint 7's batch logic is reviewed explicitly, not assumed safe |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 15 — Supplier Invoices, Payments & PO/GRN Frontend Polish

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Supplier-side financial tracking goes live and the PO/GRN UI reaches completion |
| 2 | Business Goal | Shops can track what they owe suppliers, not just what they've ordered |
| 3 | Engineering Goal | Procurement module reaches the same test-closure bar Sprint 8 set for Inventory |
| 4 | Modules Covered | Suppliers (finance), Purchase Orders, GRN (frontend) |
| 5 | Features to Build | Supplier invoice tracking, payment recording, full PO/GRN UI |
| 6 | Backend Tasks | `repositories/procurement/goods_receipt_repository.py` extension for `supplier_invoices`/`supplier_payments` |
| 7 | Database Tasks | `supplier_invoices`, `supplier_payments` tables |
| 8 | API Tasks | `POST /suppliers/invoices/{id}/payments` |
| 9 | Frontend Tasks | PO list/detail polish, GRN AI-insight panel (shelf-routing/cold-chain alert display), payment-recording form |
| 10 | Security Tasks | `(suppliers, edit)` permission scoped correctly to payment-recording action |
| 11 | Testing Tasks | Module-level regression closure for Procurement (mirrors Sprint 8's role for Inventory) |
| 12 | Documentation Tasks | Procurement module README finalized |
| 13 | Deployment Tasks | Staging soak test |
| 14 | Dependencies | Sprint 14 |
| 15 | Expected Deliverables | Procurement module (Suppliers directory + PO + GRN + payments) signed off as feature-complete |
| 16 | Acceptance Criteria | Every Blueprint §1.6 Procurement screen has a working, tested backend path |
| 17 | Definition of Done | Full Phase 7 §19 DoD, module-wide |
| 18 | Risks | None beyond standard closure risk — flagged as a deliberate "calm" sprint after two consecutive high-stakes atomic-transaction sprints |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 16 — Supplier Finance & Relationship Intelligence

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Relationship scoring, credit aging, and the Smart Payment Engine go live against real procurement history |
| 2 | Business Goal | The "Relationship Network" half of the product's tagline becomes a tangible, data-driven feature, not just a directory |
| 3 | Engineering Goal | Scoring/aging computation jobs validated against real (Sprint 13–15-generated) data rather than synthetic fixtures |
| 4 | Modules Covered | Supplier Relationships, Supplier Finance |
| 5 | Features to Build | Relationship tiering/trust score, credit aging buckets, Smart Payment Engine, optimization insights, due-date calendar |
| 6 | Backend Tasks | `services/supplier_service.py` (relationship/finance portion); scheduled `finance_jobs.py` (credit aging recompute) |
| 7 | Database Tasks | Query/index validation on aggregate-heavy relationship/aging queries |
| 8 | API Tasks | `/suppliers/{id}/relationship`, `/suppliers/{id}/performance`, `/suppliers/{id}/activity`, `/suppliers/optimization-insights`, `/suppliers/finance/*` |
| 9 | Frontend Tasks | Relationship Dashboard, Finance Center screens (aging chart, smart-payment recommendations, due-date calendar) |
| 10 | Security Tasks | Manual tier/credit-limit override (`PATCH /suppliers/{id}/relationship`) restricted to owner-level role, tested explicitly |
| 11 | Testing Tasks | Aging-bucket correctness test against a seeded dataset with known invoice ages, verifying bucket boundaries exactly (0–15/16–30/31–45/46–60/60+) |
| 12 | Documentation Tasks | Scoring/recommendation algorithm documented at a level sufficient for a future engineer to audit its logic without reverse-engineering it |
| 13 | Deployment Tasks | First scheduled Celery beat job (`finance_jobs`) deployed |
| 14 | Dependencies | Sprint 15 |
| 15 | Expected Deliverables | Full Supplier Relationship & Finance Center functionality live |
| 16 | Acceptance Criteria | Aging buckets and credit-utilization figures independently hand-verified against the seeded test dataset, not just "the chart renders" |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | First "intelligence"/recommendation feature — risk of an unverified algorithm producing plausible-looking but wrong financial guidance; mitigated by the explicit hand-verification acceptance criterion |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 17 — Delivery / Dispatch

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Full delivery dispatch lifecycle live against real invoices |
| 2 | Business Goal | **Beta milestone progress** — last-mile fulfillment, a key differentiator for delivery-offering pharmacies, comes online |
| 3 | Engineering Goal | Status-transition state machine and live-tracking data flow proven end to end |
| 4 | Modules Covered | Delivery |
| 5 | Features to Build | Dispatch creation, status pipeline (Pending→Assigned→Packed→Dispatched→Delivered), rider roster, live ETA tracking |
| 6 | Backend Tasks | `services/delivery_service.py`; `repositories/delivery/delivery_repository.py` |
| 7 | Database Tasks | Domain F migration (`riders`, `delivery_orders`, `delivery_status_history`) |
| 8 | API Tasks | `/deliveries/*`, `/riders/*` |
| 9 | Frontend Tasks | Dispatch table, pipeline-funnel widget, live-tracking map view, rider roster screen |
| 10 | Security Tasks | Confirmed no rider-authenticated surface exists anywhere (Blueprint §6.2 gap respected, per Phase 7 §1.1's "don't redesign" discipline) |
| 11 | Testing Tasks | Status-transition test suite covering every valid/invalid transition in the pipeline |
| 12 | Documentation Tasks | Explicit doc note (mirrors API Architecture §1.12) that all writes are staff-performed on the rider's behalf, never rider-initiated |
| 13 | Deployment Tasks | Maps/geocoding third-party integration (`integrations/maps_client.py`) provisioned in Staging |
| 14 | Dependencies | Sprint 16 (needs real invoices from Billing to dispatch against) |
| 15 | Expected Deliverables | Full delivery dispatch module live |
| 16 | Acceptance Criteria | A dispatch created against a real invoice progresses through every pipeline stage correctly, with status history fully recorded |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | Third-party maps/geocoding dependency introduces external-service risk; mitigated by this being a read-enrichment feature, not a blocking dependency for core dispatch functionality |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Medium-High |

---

## Sprint 18 — Notifications & Command Center

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Cross-cutting notification feed and global search go live across every module built so far |
| 2 | Business Goal | **Beta milestone reached** (Phase 6 §5) — the product now functions as a unified workspace, not a set of disconnected modules |
| 3 | Engineering Goal | Prove the notification dispatch pipeline and federated search both correctly aggregate across every prior module without introducing a write path of their own |
| 4 | Modules Covered | Notifications, Command Center |
| 5 | Features to Build | Categorized notification feed, mark-read/bulk-read, preferences, global ⌘K search |
| 6 | Backend Tasks | `services/notification_service.py`, `services/command_center_service.py`; `jobs/notification_jobs.py` (async dispatch) |
| 7 | Database Tasks | Domain G migration (`notifications`, `notification_preferences`); partial index for unread-state queries |
| 8 | API Tasks | `/notifications/*`, `/search`, `/search/quick-actions`, `/search/recent` |
| 9 | Frontend Tasks | Notification bell/feed UI, preferences settings screen, Command Center palette (⌘K) |
| 10 | Security Tasks | Confirmed `command_center_service` issues zero writes (API Architecture §1.18) — explicit test that every quick-action is a deep link, never a direct mutation |
| 11 | Testing Tasks | Cross-module integration test: an action in Billing/Procurement/Delivery correctly produces a notification event; search correctly respects each result's underlying RBAC visibility |
| 12 | Documentation Tasks | Runbook for notification-dispatch job queue (Phase 7 §18.6) |
| 13 | Deployment Tasks | Notification dispatch queue separated from other Celery workloads per priority (Backend Architecture §10.1) |
| 14 | Dependencies | Sprint 17 (needs every prior module as an event source / search target) |
| 15 | Expected Deliverables | **Beta-complete** Staging environment |
| 16 | Acceptance Criteria | Multiple concurrently-active pilot-representative test shops show zero cross-tenant notification or search leakage (Phase 6 §5 Beta exit criteria) |
| 17 | Definition of Done | Phase 7 §19 fully applied; this sprint's closure is the formal Beta milestone gate |
| 18 | Risks | Cross-module aggregation is exactly the kind of feature where a forgotten `shop_id` filter hides easily — extra isolation-testing attention mandated |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High — **Beta Milestone** |

---

## Sprint 19 — Audit Logging Retrofit

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Every write path built in Sprints 1–18 now emits a structured, immutable audit event |
| 2 | Business Goal | Enterprise-grade compliance/traceability — a core trust signal for a regulated-adjacent industry — becomes real |
| 3 | Engineering Goal | The deliberate "retrofit" sprint (Phase 6 §4) executed as one disciplined pass rather than scattered across every prior sprint |
| 4 | Modules Covered | Audit (cross-cutting) |
| 5 | Features to Build | `audit_interceptor` middleware wired onto every existing write path; DB-trigger safety net for high-compliance tables |
| 6 | Backend Tasks | `middleware/audit_interceptor.py`; retrofit call-sites across every service touched in Sprints 1–18 |
| 7 | Database Tasks | Domain H migration (`audit_logs`, `system_events`); composite indexes (DB Architecture §6); RLS policy ensuring tenant audit reads exclude `shop_id IS NULL` platform events (DB Architecture §7.4) |
| 8 | API Tasks | `GET /audit`, `GET /audit/{id}`, `GET /audit/filters` (export endpoints land in Sprint 20 alongside Analytics export infra) |
| 9 | Frontend Tasks | Audit log list/filter screen, inspect-drill-in detail view |
| 10 | Security Tasks | Audit repository confirmed insert-only at the DB grant level (Phase 7 §5.6) — no update/delete method exists, verified by interface inspection, not just convention |
| 11 | Testing Tasks | Regression pass across **every** module from Sprints 1–18 confirming the expected audit event now fires for each write action — this sprint has the widest regression-test surface of any sprint in the plan |
| 12 | Documentation Tasks | Audit-event catalog documented (which action produces which event, with what payload) |
| 13 | Deployment Tasks | DB trigger safety net deployed alongside the application-layer interceptor (belt-and-suspenders per Backend Architecture §9) |
| 14 | Dependencies | Sprint 18 (must exist after the modules it instruments, by design) |
| 15 | Expected Deliverables | Full audit trail live across the entire product surface built so far |
| 16 | Acceptance Criteria | A scripted walkthrough of one representative action per module (billing, procurement, delivery, settings, etc.) produces exactly the expected audit row, every time |
| 17 | Definition of Done | Phase 7 §19 fully applied; this sprint additionally requires a signed-off audit-event catalog as a deliverable, not just passing tests |
| 18 | Risks | Widest blast radius of any single sprint — a regression introduced while retrofitting one module's service layer could silently break that module's actual business logic, not just its audit logging; mandates full regression suite re-run, not incremental testing alone |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 20 — Analytics & Dashboard

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Cross-module aggregation, rollups, and the home dashboard go live, replica-routed |
| 2 | Business Goal | Pharmacy owners get the headline insight screens (revenue trend, fast/dead movers, supplier performance index) that justify the product as more than a POS replacement |
| 3 | Engineering Goal | Prove primary/replica query routing (Backend Architecture §4, API Architecture §12.3) works correctly under real replication lag, not just in theory |
| 4 | Modules Covered | Analytics, Dashboard, Audit (export completion) |
| 5 | Features to Build | Dashboard KPI/aggregation endpoints, Analytics headline metrics, nightly rollup jobs, audit/analytics export jobs |
| 6 | Backend Tasks | `services/dashboard_service.py`, `services/analytics_service.py`; `jobs/analytics_jobs.py` (nightly rollups), `jobs/audit_export_jobs.py` |
| 7 | Database Tasks | Read-replica provisioned in Staging if not already (Backend Architecture §10.2); rollup-table or materialized-aggregate design validated against DB Architecture's stated read-heavy-workload intent (§6.4) |
| 8 | API Tasks | `/dashboard/*`, `/analytics/*`, `/audit/exports/*` |
| 9 | Frontend Tasks | Dashboard home screen (KPI cards, revenue trend chart, Smart Alerts feed, activity log), Analytics screens (top movers, dead stock, exports) |
| 10 | Security Tasks | Export-download signed-URL pattern (API Architecture §7.2/§9.1) verified tenant-scoped — a Shop A export link must never resolve to Shop B's data even if guessed |
| 11 | Testing Tasks | Explicit replica-lag test: confirm "same-request-reflects-own-write" cases (API Arch §12.3) correctly route to primary, while general analytics reads correctly route to replica |
| 12 | Documentation Tasks | Rollup-job schedule and dependency documented in the runbook (Phase 7 §18.6) |
| 13 | Deployment Tasks | Celery beat schedule for nightly rollups deployed; replica-routing config verified in Staging |
| 14 | Dependencies | Sprint 19 (aggregates depend on every prior domain having real, audited data) |
| 15 | Expected Deliverables | Full Dashboard + Analytics + export functionality live |
| 16 | Acceptance Criteria | Dashboard cache-hit/miss response times meet API Architecture §12.1 targets; a manually-triggered rollup produces figures matching a hand-calculated check against seeded data |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | First module where a replica-routing misconfiguration would be subtle (stale-but-plausible data) rather than loud (an error) — explicit lag-test gate exists specifically because this class of bug doesn't announce itself |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Medium-High |

---

## Sprint 21 — Subscription & Plan-Limit Enforcement

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Monetization goes live — plans, usage metering, and payment processing |
| 2 | Business Goal | MedicoSaathi can actually charge its customers |
| 3 | Engineering Goal | Retroactively wire real plan-limit enforcement into Billing/Settings (the stub from Sprint 9 becomes load-bearing) |
| 4 | Modules Covered | Subscription |
| 5 | Features to Build | Plan catalog, usage meters, upgrade/downgrade, payment methods, invoice history, payment-gateway integration |
| 6 | Backend Tasks | `services/subscription_service.py`; `integrations/payment_gateway_client.py` |
| 7 | Database Tasks | Domain A subscription tables (`subscription_plans`, `shop_subscriptions`, `subscription_invoices`, `shop_payment_methods`) |
| 8 | API Tasks | `/subscription/*` full surface |
| 9 | Frontend Tasks | Plan comparison screen, usage-meter widgets, payment-method management, invoice history with PDF download |
| 10 | Security Tasks | Payment-gateway credentials and PCI-relevant handling reviewed explicitly (no card data ever touches MedicoSaathi's own storage — gateway tokenization only) |
| 11 | Testing Tasks | Plan-limit enforcement regression test against Billing: a shop at its transaction limit must receive `PLAN_LIMIT_EXCEEDED` on the next invoice attempt, verified against the real Billing module, not a mock |
| 12 | Documentation Tasks | Billing-cycle and dunning/retry policy documented |
| 13 | Deployment Tasks | `jobs/billing_jobs.py` (usage-meter rollup) deployed; payment gateway sandbox wired in Staging |
| 14 | Dependencies | Sprint 20 |
| 15 | Expected Deliverables | Full monetization stack live in Staging (sandbox payments) |
| 16 | Acceptance Criteria | End-to-end: a shop signs up, hits its plan's transaction limit, sees the correct warning state, and successfully upgrades — verified as one continuous test scenario |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | Retroactively wiring a real gate into an already-built, already-tested module (Billing) carries regression risk — the explicit cross-module regression test in row 11 exists specifically to catch that |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | High |

---

## Sprint 22 — Platform Admin Completion

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Full platform operations tooling live: system health, plan management, cross-tenant support tools |
| 2 | Business Goal | Internal operations team can run the platform at scale without engineering hand-holding |
| 3 | Engineering Goal | `BYPASSRLS` cross-tenant query paths fully proven safe and exclusively reachable from the platform realm |
| 4 | Modules Covered | Platform Admin (completion) |
| 5 | Features to Build | System health dashboard, plan management, cross-tenant shop search/support view, wholesaler verification queue |
| 6 | Backend Tasks | `services/platform_admin_service.py` completion |
| 7 | Database Tasks | `wholesaler_verification_queue` wired |
| 8 | API Tasks | `/platform/kpis`, `/platform/system-health`, `/platform/plans/*`, `/platform/shops/*`, `/platform/wholesalers/*`, `/platform/audit` |
| 9 | Frontend Tasks | Platform Admin dashboard (KPIs, system health, plan management screens, support search tool) |
| 10 | Security Tasks | Platform-role granularity tested (Support vs. Verification Officer vs. Super Admin per Backend Architecture §6.3) — a Support-role token must be rejected on Super-Admin-only actions |
| 11 | Testing Tasks | Cross-tenant query test confirming `GET /platform/shops/{shop_id}` correctly bypasses RLS via the dedicated role, while every other route in the system still cannot |
| 12 | Documentation Tasks | Platform operations runbook for support staff |
| 13 | Deployment Tasks | System-health telemetry pipeline wired to real `pg_stat_statements`/infra metrics (Backend Architecture §10.5), not mocked data |
| 14 | Dependencies | Sprint 21 |
| 15 | Expected Deliverables | Full Platform Admin surface live |
| 16 | Acceptance Criteria | System Health screen reflects a deliberately-induced test condition (e.g., simulated replica lag) accurately, proving it's wired to real telemetry |
| 17 | Definition of Done | Phase 7 §19 fully applied |
| 18 | Risks | `BYPASSRLS` is the single most powerful credential in the system — this sprint's security review is held to the same bar as Sprint 4's platform-auth-realm sprint |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Medium-High |

---

## Sprint 23 — Performance Hardening at Scale

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Validate the entire system against API Architecture §12 and DB Architecture's stated 10,000-pharmacy targets under simulated concurrent multi-tenant load |
| 2 | Business Goal | Confidence that the platform will not fall over as real adoption grows — protects every business KPI defined in Phase 6 §11.3 |
| 3 | Engineering Goal | Every response-time target in API Architecture §12.1 measured and met under realistic concurrent load, not single-tenant synthetic load |
| 4 | Modules Covered | Cross-cutting (all) |
| 5 | Features to Build | None — this is a validation sprint, not a feature sprint; fixes are scoped reactively to findings |
| 6 | Backend Tasks | Query/cache optimization on any endpoint found short of target |
| 7 | Database Tasks | Partition/index behavior validated at simulated full scale (DB Architecture §6.1's ≈1M invoice rows/day projection); connection-pooling mode (Backend Architecture §10.2) load-tested specifically for the RLS-under-load failure mode it warns about |
| 8 | API Tasks | None new |
| 9 | Frontend Tasks | None new — any UI-perceived latency issues found get logged as findings, not fixed mid-sprint unless trivial |
| 10 | Security Tasks | None new this sprint (Sprint 24 owns security specifically) |
| 11 | Testing Tasks | Full synthetic concurrent multi-shop load test suite (Phase 6 §6.6); EXPLAIN-plan audit across every high-traffic query |
| 12 | Documentation Tasks | Performance report published with every target's measured result, pass/fail, and any deferred-fix tickets |
| 13 | Deployment Tasks | Load-testing infrastructure provisioned against a Staging environment scaled to approximate Production |
| 14 | Dependencies | Sprint 22 (requires the full system to exist) |
| 15 | Expected Deliverables | Signed-off performance report |
| 16 | Acceptance Criteria | Every Section 12.1 target met, or explicitly renegotiated with documented product sign-off (Phase 7 §15.1's "never silently shipped" rule) |
| 17 | Definition of Done | No target left silently unmet; every miss has either a merged fix or a documented, approved exception |
| 18 | Risks | This is the sprint most likely to reveal that a target needs to extend — flagged explicitly as acceptable schedule risk, not a sprint to compress under pressure |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 24 — Security Hardening & Penetration Testing

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Full adversarial security validation across the entire built system |
| 2 | Business Goal | Protects the single most existential risk named anywhere in this program — a tenant-isolation breach |
| 3 | Engineering Goal | Zero open critical/high security findings at sprint close |
| 4 | Modules Covered | Cross-cutting (all) |
| 5 | Features to Build | None — fixes scoped reactively to findings |
| 6 | Backend Tasks | Remediation of any finding |
| 7 | Database Tasks | RLS policy audit across every tenant table, confirmed active and correctly scoped |
| 8 | API Tasks | None new |
| 9 | Frontend Tasks | None new |
| 10 | Security Tasks | Full Phase 7 §14 checklist executed as a formal audit; manual penetration test (tenant-isolation bypass attempts, token tampering, realm-confusion attempts, file-upload spoofing, dependency CVE scan, secrets audit) |
| 11 | Testing Tasks | Every Phase 6 §6.5 security test category re-run as a dedicated suite, plus manual adversarial testing beyond what automation covers |
| 12 | Documentation Tasks | Security sign-off report, findings log with remediation status for each item |
| 13 | Deployment Tasks | Any infrastructure-level hardening (WAF rules, network segmentation verification) applied to Staging and confirmed before Production |
| 14 | Dependencies | Sprint 23 (and can run partially in parallel with it given separate focus areas, per the Critical Path Analysis below) |
| 15 | Expected Deliverables | Security sign-off report, zero open critical/high findings |
| 16 | Acceptance Criteria | Independent (ideally external) penetration test confirms no tenant-isolation bypass achievable by any tested method |
| 17 | Definition of Done | Phase 7 §19 + explicit named security sign-off from the CTO |
| 18 | Risks | A critical finding here could meaningfully delay launch — this is treated as success, not failure, since the alternative (finding it in Production) is categorically worse |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

## Sprint 25 — Launch Readiness

| # | Field | Detail |
|---|---|---|
| 1 | Sprint Objective | Close out every remaining QA, UAT, and deployment-readiness item; produce a formal go/no-go decision |
| 2 | Business Goal | The product is genuinely ready for real pharmacies to depend on daily |
| 3 | Engineering Goal | Every checklist in Sections 5–10 below fully closed, no exceptions carried forward silently |
| 4 | Modules Covered | Cross-cutting (all) |
| 5 | Features to Build | None — closure sprint |
| 6 | Backend Tasks | Final defect burn-down from UAT findings |
| 7 | Database Tasks | Final backup/restore drill (Phase 6 §8.5/§8.6) executed and confirmed |
| 8 | API Tasks | Final full-surface contract-test pass |
| 9 | Frontend Tasks | Final UAT-driven UI defect burn-down |
| 10 | Security Tasks | Final confirmation that Sprint 24's findings are fully remediated, not just "ticketed" |
| 11 | Testing Tasks | Full regression suite run clean; UAT (Phase 6 §6.7) executed with real pilot pharmacies |
| 12 | Documentation Tasks | All runbooks, READMEs, and ADRs reviewed for currency before launch |
| 13 | Deployment Tasks | Full Phase 6 §8 Deployment Readiness Checklist executed and closed |
| 14 | Dependencies | Sprint 24 |
| 15 | Expected Deliverables | Formal go/no-go decision for Closed Beta → Production progression |
| 16 | Acceptance Criteria | Every checklist item in Sections 5–10 below is checked, with named sign-off per category (engineering, security, product, business) |
| 17 | Definition of Done | Phase 7 §19, applied as a final whole-system gate, not a per-feature one |
| 18 | Risks | Pressure to declare "ready enough" under launch-date pressure is the named risk here, explicitly — this Constitution-bound plan treats an incomplete checklist as a blocker, not a judgment call to override |
| 19 | Estimated Duration | 2 weeks |
| 20 | Priority | Critical |

---

# Post-Sprint Program-Level Sections

## A. Complete Sprint Timeline

| Sprint | Weeks | Calendar (from kickoff) | Phase |
|---|---|---|---|
| 0 | 1–2 | Month 1 | Foundation |
| 1–3 | 3–8 | Months 1.5–2 | Identity, Auth & RBAC |
| 4–5 | 9–12 | Month 3 | Platform Admin & Onboarding |
| 6–8 | 13–18 | Months 3.5–4.5 | Catalog & Inventory |
| 9–11 | 19–24 | Months 5–6 | Billing/POS |
| 12 | 25–26 | Month 6.5 | Customers & Ledger — **MVP Milestone** |
| 13–15 | 27–32 | Months 7–8 | Suppliers, PO, GRN |
| 16 | 33–34 | Month 8.5 | Supplier Finance & Relationships |
| 17 | 35–36 | Month 9 | Delivery |
| 18 | 37–38 | Month 9.5 | Notifications & Command Center — **Beta Milestone** |
| 19 | 39–40 | Month 10 | Audit Retrofit |
| 20 | 41–42 | Month 10.5 | Analytics & Dashboard |
| 21–22 | 43–46 | Month 11–11.5 | Subscription & Platform Admin Completion |
| 23–24 | 47–50 | Month 12 | Hardening (Performance + Security) — **Production Ready Milestone** |
| 25 | 51–52 | Month 12.5 | Launch Readiness → **Version 1.0** |

**Total: 26 sprints, ~52 weeks, ~12 months from Sprint 0 to Version 1.0**, matching Phase 6's baseline exactly.

## B. Engineering Milestones

| Milestone | Sprint Closure | Defined By |
|---|---|---|
| Foundation Complete | Sprint 0 | Running, pipelined, empty app across all environments |
| Auth/RBAC Complete | Sprint 3 | Four-stage authorization pipeline operational and security-reviewed |
| First Real Tenant Onboarded | Sprint 5 | A real shop can register, verify, and operate |
| **MVP** | Sprint 12 | Phase 6 §5 MVP definition met |
| **Beta** | Sprint 18 | Phase 6 §5 Beta definition met |
| Audit-Complete System | Sprint 19 | Every write path instrumented |
| **Production Ready** | Sprint 24 | Phase 6 §5 Production Ready definition met (full QA + security sign-off) |
| **Version 1.0** | Sprint 25 | Launch readiness fully closed, go/no-go approved |

## C. Module Dependency Graph

```
Foundation
   ↓
Auth ─→ RBAC ─→ Tenant Context
   ↓
Platform Admin (Shop Verification)
   ↓
Catalog & Inventory ───────────────────────────┐
   ↓                                            │
Billing/POS                                     │
   ↓                                            │
Customers & Ledger  ── [MVP] ──                 │
   ↓                                            │
Suppliers ─→ Purchase Orders ─→ GRN ────────────┘ (writes back into Inventory's batches)
   ↓
Supplier Finance & Relationship Intelligence
   ↓
Delivery
   ↓
Notifications & Command Center  ── [BETA] ──
   ↓
Audit (retrofit across everything above)
   ↓
Analytics & Dashboard (aggregates everything above)
   ↓
Subscription ─→ Platform Admin Completion
   ↓
Hardening (Performance + Security)  ── [PRODUCTION READY] ──
   ↓
Launch Readiness  ── [VERSION 1.0] ──
```

## D. Critical Path Analysis

The **critical path** — the sequence that cannot be compressed by adding engineers, because each step's start genuinely depends on the prior step's completion — runs:

**Foundation → Auth/RBAC → Platform Admin (Verification) → Catalog/Inventory → Billing → Customers (MVP) → Procurement (PO/GRN) → Notifications (Beta) → Audit → Analytics → Hardening → Launch.**

This is 21 of the 26 sprints. The remaining 5 sprints are where additional engineering capacity (the "20+ engineer org" the prompt specifies) genuinely shortens the calendar:

| Sprint(s) | Can run in parallel with | Why it's safe |
|---|---|---|
| Sprint 16 (Supplier Finance) | Tail end of Sprint 17 prep work | Finance/relationship scoring reads from Procurement data already complete by Sprint 15; a second backend track can begin Delivery's schema/repository groundwork once Sprint 15 (not 16) closes, since Delivery only needs Billing (Sprint 11), not Supplier Finance |
| Sprint 21 (Subscription) | Sprint 22 prep | Plan-catalog/payment-gateway integration work has no dependency on Platform Admin completion; a second track can start this as soon as Sprint 20 closes |
| Sprint 23 / Sprint 24 | Each other | Performance hardening and security hardening test largely disjoint concerns (throughput vs. adversarial access) against the same frozen feature set — a 20+ engineer org runs these as two simultaneous tracks rather than sequential sprints, the single biggest compression opportunity in the whole plan |
| Frontend tracks generally | One sprint behind their corresponding backend sprint | Per Phase 6 §2's stated rule: frontend starts as soon as a module's API contract passes contract tests, not after full backend "polish" — this is already baked into the 2-week-per-sprint estimate as parallel work, not sequential |

**Net effect for a 20+ engineer organization:** Sprints 23/24 collapsing into one calendar block, and Sprint 16/21's parallel-track opportunities, can realistically compress the 26-sprint/~12-month baseline by 2–4 sprints (roughly 4–8 weeks) without touching the critical path's actual dependency logic — the order in Section A above does not change, only the calendar does.

## E. Development Checklist (Standing, Every Sprint)

- [ ] Sprint deliverables match this document's sprint table exactly — no silent scope addition or reduction
- [ ] Every new endpoint matches the frozen API Architecture (Phase 5) exactly
- [ ] Every new query is tenant-scoped and isolation-tested (Phase 7 §17.2)
- [ ] Every new business rule has a corresponding API Architecture §11 error code mapped, not invented ad hoc
- [ ] CI green, linter/formatter clean, on every merged PR
- [ ] Module docstrings and READMEs updated in the same PR as the code (Phase 7 §18.7)
- [ ] Phase 7 §19 Definition of Done satisfied per feature before sprint close

## F. QA Checklist (Pre-Production)
*(Restated and bound to this execution plan — full detail in Phase 6 §7; closure tracked against Sprints 23–25 specifically)*
- [ ] All Phase 6 §7.1–§7.8 categories (Functional, Data Integrity, Multi-Tenancy, Auth/RBAC, Performance, Security, Compliance, Operational) signed off
- [ ] Every sprint's individual Acceptance Criteria (column 16 above) verified closed, not just "implemented"
- [ ] Zero open Sev-1/Sev-2 defects at the close of Sprint 25

## G. Production Readiness Checklist
- [ ] Sprint 23 performance report shows every API Architecture §12.1 target met or formally exception-approved
- [ ] Sprint 24 security sign-off report shows zero open critical/high findings
- [ ] Phase 6 §8 Deployment Readiness Checklist (Environment, Secrets, Logging, Monitoring, Backup, Recovery, Security) fully closed
- [ ] Subscription/payment-gateway integration validated against a real (non-sandbox) gateway account before go-live
- [ ] On-call rotation staffed and runbooks (Phase 7 §18.6) reviewed by every on-call engineer, not just authored

## H. Release Checklist
- [ ] Phase 6 §9 Release Strategy stages (Alpha → Closed Beta → Public Beta → Production) each individually exited per their own stated criteria — no stage skipped under schedule pressure
- [ ] Version tag cut on `main` corresponding to the exact commit promoted to Production
- [ ] Release notes published, cross-referenced to the modules delivered per this plan's sprint table
- [ ] Rollback plan for this specific release rehearsed in Staging (Phase 7 §9.1/§10's environment-parity discipline applied at release time, not assumed)

## I. Go-Live Checklist
- [ ] Final go/no-go sign-off obtained from engineering, security, product, and business stakeholders (Sprint 25's stated deliverable)
- [ ] Monitoring/alerting dashboards (Phase 6 §8.4) confirmed live and being actively watched during the go-live window, not just configured
- [ ] Support team briefed and staffed for the go-live window, with escalation path to engineering confirmed
- [ ] Database backup taken immediately pre-cutover, independent of the standing daily backup schedule
- [ ] Feature flags (if any features shipped dark) confirmed in their correct go-live state

## J. Post-Launch Checklist
- [ ] First-24-hours error-rate and performance dashboards reviewed against Sprint 23's established baselines, not assumed fine by absence of complaints
- [ ] First-week defect triage cadence established, feeding Phase 6 §11.1's defect-escape-rate KPI from day one of real usage
- [ ] First-billing-cycle (Subscription module) reconciliation performed manually once, even though it's automated, to confirm real-world correctness before trusting it unattended
- [ ] Postmortem scheduled for any Sev-1/Sev-2 incident in the first 30 days, per Phase 7's hotfix-branch discipline (Section 10 of Phase 7: a hotfix branch existing is itself a signal worth a postmortem)
- [ ] Version 1.0 retrospective conducted across the full 26-sprint program, feeding lessons into the (separately-scoped, not pre-committed) Version 2.0 planning process

---

# Official MedicoSaathi Development Order

This is the permanent, binding implementation sequence. It supersedes informal scheduling discussions and may only be revised through the same ADR-and-CTO-sign-off process the Engineering Constitution (Phase 7 §18.1) requires for any deviation from frozen planning.

```
Sprint 0   — Foundation & Platform Scaffolding
Sprint 1   — Identity Schema & Core Repositories
Sprint 2   — Authentication Endpoints
Sprint 3   — RBAC Middleware, Permission Cache & Password Reset
Sprint 4   — Platform Schema & Platform Admin Auth Realm
Sprint 5   — Shop Self-Registration & Verification Queue
Sprint 6   — Catalog Schema & Medicine CRUD
Sprint 7   — Batches, Stock Ledger & Alert Queries
Sprint 8   — Inventory Frontend Completion & Module Test Closure
Sprint 9   — Billing Core: Cart Pricing & Invoice Transaction
Sprint 10  — Held Bills, Void, Lookups & Receipts
Sprint 11  — POS Frontend Performance Hardening
Sprint 12  — Customers & Customer Ledger                         ← MVP MILESTONE
Sprint 13  — Supplier Directory & Purchase Orders
Sprint 14  — Goods Receiving (GRN) & Batch Creation
Sprint 15  — Supplier Invoices, Payments & PO/GRN Frontend Polish
Sprint 16  — Supplier Finance & Relationship Intelligence
Sprint 17  — Delivery / Dispatch
Sprint 18  — Notifications & Command Center                      ← BETA MILESTONE
Sprint 19  — Audit Logging Retrofit
Sprint 20  — Analytics & Dashboard
Sprint 21  — Subscription & Plan-Limit Enforcement
Sprint 22  — Platform Admin Completion
Sprint 23  — Performance Hardening at Scale
Sprint 24  — Security Hardening & Penetration Testing             ← PRODUCTION READY MILESTONE
Sprint 25  — Launch Readiness                                     ← VERSION 1.0
```

**This order is permanent.** Future modules, features, or a future Version 2.0 scope are appended after Sprint 25 through a new, separately-numbered planning cycle — they are never inserted retroactively into Sprints 0–25, and Sprints 0–25 are never reordered, skipped, or compressed below the dependency logic in Section D above. Any engineer, team lead, or future CTO proposing a deviation follows the Engineering Constitution's ADR process; this document, once approved, is the implementation law of the project until Version 1.0 ships.
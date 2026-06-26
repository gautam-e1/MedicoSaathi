# MedicoSaathi — Backend Architecture
### Principal Backend Architect Review · Flask · Derived strictly from the approved Product Blueprint and Database Architecture

No code is included below by design. Every structure is specified at the architectural/conceptual level — folder responsibility, module boundary, contract, and rationale — so this can be reviewed and signed off before implementation begins.

**Source-of-truth discipline:** every module named below maps 1:1 to a section of the Product Blueprint's Module Hierarchy (Section 4) and every data access point maps 1:1 to a table/domain in the Database Architecture (Section 1). No new product capability or schema element is introduced. Where the Blueprint flags a gap (Section 6) — wholesaler portal, rider app, 2FA UI, returns — the corresponding backend surface is **deliberately absent**, not stubbed, to avoid silently inheriting an undecided product question.

---

## 0. Architectural Premises (carried over, not re-decided)

| Premise | Source | Backend Consequence |
|---|---|---|
| Multi-tenant, shared schema, `shop_id` discriminator + Postgres RLS | DB Arch §0, §9 | Every request must establish a **tenant context** before touching the data layer; this is the single most load-bearing decision in this document. |
| Two identity realms: `users` (shop staff) vs `platform_admins` (platform team) | DB Arch §0, Domain A/B | Two **separate authentication architectures**, not one auth system with a "platform" role flag. |
| Multi-shop membership: one `user` can belong to many `shops` via `shop_users` | DB Arch Domain B | Auth must support an explicit **active-shop context switch**, not a single fixed tenant per user. |
| Suppliers and riders are managed *entities*, not logged-in actors (Blueprint §6.2) | Blueprint, DB Arch §10.4 | **No auth, no API surface, no service layer for supplier/rider self-service.** They are read/write targets of shop-side services only. |
| RLS is defense-in-depth; the app layer must filter by `shop_id` explicitly in every query | DB Arch §9 | Repository layer is the **single enforcement point** for this — no repository method may run without a bound tenant. |
| Lookup-table-backed statuses, not native ENUM | DB Arch §0 | Service layer treats status values as data (cacheable, validated against the lookup table), not hardcoded constants. |
| Read-heavy workloads (dashboards, analytics, audit export) belong on read replicas | DB Arch §6.4, §7.3 | Repository layer must support **routing a query to primary or replica**, decided by the service layer per use case. |

---

## 1. Folder Structure

```
medicosaathi-backend/
│
├── app/
│   ├── __init__.py                  # application factory, extension init, blueprint registration
│   ├── config.py                    # environment-driven config classes (Dev/Staging/Prod)
│   ├── extensions.py                # db, redis, celery, jwt, limiter — instantiated, not configured here
│   │
│   ├── api/
│   │   └── v1/                      # API versioning boundary — see Section 7
│   │       ├── __init__.py          # registers all v1 blueprints under /api/v1
│   │       ├── auth/                # Domain B — Identity & Access
│   │       ├── platform_auth/       # platform_admins realm — separate from auth/
│   │       ├── dashboard/           # 1.1
│   │       ├── billing/             # 1.2 Fast Billing / POS
│   │       ├── inventory/           # 1.3
│   │       ├── procurement/         # 1.4 — Purchase Orders + GRN
│   │       ├── suppliers/           # 1.5 — Directory, Relationship, Credit & Finance
│   │       ├── customers/           # 1.6
│   │       ├── delivery/            # 1.7
│   │       ├── analytics/           # 1.8
│   │       ├── notifications/       # 1.9
│   │       ├── audit/               # 1.10 Enterprise Audit Log Center (tenant-scoped view)
│   │       ├── settings/            # 1.11
│   │       ├── subscription/        # 1.12
│   │       ├── command_center/      # 2 — Global ⌘K search (cross-cutting, read-only aggregator)
│   │       └── platform_admin/      # 3 — Platform Admin Workspace (separate auth realm)
│   │
│   ├── services/                    # business logic — one module per domain, mirrors api/v1/
│   │   ├── auth_service.py
│   │   ├── platform_auth_service.py
│   │   ├── dashboard_service.py
│   │   ├── billing_service.py
│   │   ├── inventory_service.py
│   │   ├── procurement_service.py
│   │   ├── supplier_service.py
│   │   ├── customer_service.py
│   │   ├── delivery_service.py
│   │   ├── analytics_service.py
│   │   ├── notification_service.py
│   │   ├── audit_service.py
│   │   ├── settings_service.py
│   │   ├── subscription_service.py
│   │   ├── command_center_service.py
│   │   └── platform_admin_service.py
│   │
│   ├── repositories/                # data access — one module per DB Architecture domain
│   │   ├── base_repository.py       # tenant-context binding, primary/replica routing, common query helpers
│   │   ├── platform/                # Domain A
│   │   │   ├── shop_repository.py
│   │   │   ├── subscription_repository.py
│   │   │   └── verification_queue_repository.py
│   │   ├── identity/                # Domain B
│   │   │   ├── user_repository.py
│   │   │   ├── role_permission_repository.py
│   │   │   └── session_repository.py
│   │   ├── catalog/                  # Domain C
│   │   │   ├── medicine_repository.py
│   │   │   ├── batch_repository.py
│   │   │   └── stock_ledger_repository.py
│   │   ├── procurement/              # Domain D
│   │   │   ├── supplier_repository.py
│   │   │   ├── purchase_order_repository.py
│   │   │   └── goods_receipt_repository.py
│   │   ├── sales/                    # Domain E
│   │   │   ├── invoice_repository.py
│   │   │   ├── customer_repository.py
│   │   │   └── held_bill_repository.py
│   │   ├── delivery/                 # Domain F
│   │   │   └── delivery_repository.py
│   │   ├── notifications/            # Domain G
│   │   │   └── notification_repository.py
│   │   └── audit/                    # Domain H
│   │       └── audit_repository.py
│   │
│   ├── models/                       # ORM models — one module per domain, no business logic
│   │   ├── platform.py
│   │   ├── identity.py
│   │   ├── catalog.py
│   │   ├── procurement.py
│   │   ├── sales.py
│   │   ├── delivery.py
│   │   ├── notifications.py
│   │   └── audit.py
│   │
│   ├── schemas/                      # request/response validation & serialization (marshmallow/pydantic-style)
│   │   └── (mirrors api/v1/ module-for-module)
│   │
│   ├── middleware/
│   │   ├── tenant_context.py         # resolves & binds shop_id per request — see Section 6
│   │   ├── auth_guard.py             # JWT verification, session validity
│   │   ├── rbac_guard.py             # permission-check decorator — see Section 6
│   │   ├── audit_interceptor.py      # writes audit_logs entries for state-changing requests
│   │   └── rate_limiter.py           # per-shop and per-IP throttling
│   │
│   ├── jobs/                         # Celery task definitions — see Section 9
│   │   ├── alerting_jobs.py          # low-stock, expiry, dead-stock scans
│   │   ├── billing_jobs.py           # subscription usage metering, plan-limit warnings
│   │   ├── notification_jobs.py      # WhatsApp/SMS/email dispatch
│   │   ├── finance_jobs.py           # early-payment engine, credit aging recompute
│   │   ├── audit_export_jobs.py      # CSV/PDF export generation
│   │   ├── partition_jobs.py         # pg_partman maintenance trigger/verification
│   │   └── analytics_jobs.py         # nightly rollups for Analytics & Insights
│   │
│   ├── integrations/                 # outbound third-party adapters (no business logic)
│   │   ├── whatsapp_client.py
│   │   ├── sms_client.py
│   │   ├── payment_gateway_client.py # cards/UPI for subscription billing
│   │   ├── print_receipt_client.py   # thermal printer protocol adapter
│   │   └── maps_client.py            # delivery ETA/geocoding
│   │
│   └── utils/
│       ├── pagination.py
│       ├── gst_calculator.py         # CGST/SGST split — pure function, used by billing & procurement services
│       ├── caching.py                # cache-key builders, TTL constants — see Section 8
│       └── exceptions.py             # domain exception hierarchy (NotFound, Forbidden, TenantMismatch, PlanLimitExceeded…)
│
├── migrations/                       # schema migrations (Alembic) — structure only, no DDL authored here
├── tests/
│   ├── unit/                         # service + repository layer, per domain
│   ├── integration/                  # API blueprint level, per domain
│   └── fixtures/                     # multi-tenant test fixtures (≥2 shops, to catch isolation bugs)
├── scripts/                          # one-off ops scripts (backfills, manual partition checks)
└── wsgi.py / celery_worker.py        # entrypoints
```

**Rationale for the `api → service → repository → model` four-layer split:** it mirrors the DB Architecture's own domain boundaries exactly (Domains A–I), so any future schema change is traceable to exactly one repository module, and any future product change (Blueprint revision) is traceable to exactly one service + API module. No layer is allowed to skip another — API never calls a repository directly, and a repository never contains business rules.

---

## 2. Flask Blueprint Structure

One Flask blueprint per Module Hierarchy branch (Blueprint §4), each independently registerable so platform-admin and tenant blueprints can be deployed as separate WSGI apps later if load profiles diverge (see Section 10).

| Blueprint | URL Prefix | Maps to Blueprint §4 | Auth Realm |
|---|---|---|---|
| `auth_bp` | `/api/v1/auth` | 0. Public / Pre-Auth | Public → `users` |
| `dashboard_bp` | `/api/v1/dashboard` | 1.1 | `users` (tenant) |
| `billing_bp` | `/api/v1/billing` | 1.2 Fast Billing / POS | `users` (tenant) |
| `inventory_bp` | `/api/v1/inventory` | 1.3 | `users` (tenant) |
| `procurement_bp` | `/api/v1/procurement` | 1.4 (PO + GRN) | `users` (tenant) |
| `suppliers_bp` | `/api/v1/suppliers` | 1.5 (Directory, Relationship, Credit & Finance) | `users` (tenant) |
| `customers_bp` | `/api/v1/customers` | 1.6 | `users` (tenant) |
| `delivery_bp` | `/api/v1/delivery` | 1.7 | `users` (tenant) |
| `analytics_bp` | `/api/v1/analytics` | 1.8 | `users` (tenant) |
| `notifications_bp` | `/api/v1/notifications` | 1.9 | `users` (tenant) |
| `audit_bp` | `/api/v1/audit` | 1.10 (tenant-scoped view) | `users` (tenant, elevated role) |
| `settings_bp` | `/api/v1/settings` | 1.11 | `users` (tenant, owner-only for statutory/security tabs) |
| `subscription_bp` | `/api/v1/subscription` | 1.12 | `users` (tenant, owner-only) |
| `command_center_bp` | `/api/v1/search` | 2. Global Command Center | `users` (tenant) — read-only fan-out, no writes |
| `platform_admin_bp` | `/api/v1/platform` | 3. Platform Admin Workspace | `platform_admins` only — **never** mounted under tenant auth |

**Blueprint isolation rule:** `platform_admin_bp` is registered on a distinct internal routing path and, in production, can be served from a separate listener/network segment so a misconfiguration can never expose platform routes to a tenant-authenticated request — this mirrors DB Arch §0's "identity separation" decision at the API layer.

Each blueprint exposes only the endpoints implied by its screens in Blueprint §1.6 (Functional Requirements). No blueprint exposes a generic CRUD surface beyond what a screen evidences — e.g., `suppliers_bp` has no endpoint for supplier self-registration, because Blueprint §6.2 confirms no such actor/portal exists.

---

## 3. Service Layer

The service layer is where all business rules live. Each service is the **only** caller of its corresponding repositories, and is the only place where rules spanning multiple tables are enforced.

| Service | Core Responsibilities | Cross-Domain Reads (read-only, never writes outside its own domain) |
|---|---|---|
| `auth_service` | Login, session issuance/revocation, shop-context switch for multi-shop users, password reset | identity |
| `platform_auth_service` | Platform admin login, MFA verification, session issuance (fully separate session store from tenant auth) | platform |
| `dashboard_service` | Assembles KPI cards, revenue trend, Smart Alerts feed, Recent Transactions, Activity Log — an **aggregator**, not an owner, of data | sales, catalog, notifications, audit |
| `billing_service` | Cart pricing (delegates GST math to `gst_calculator`), payment recording, hold/recall/void rules, invoice numbering, stock decrement orchestration | catalog (batch availability), customers (ledger update on credit sale) |
| `inventory_service` | Batch CRUD rules, reorder-threshold evaluation, expiry-window queries, stock-ledger write orchestration | procurement (triggers PO suggestion) |
| `procurement_service` | PO creation/approval rules, below-min flagging, GRN verification workflow, discrepancy handling, batch creation on GRN completion | catalog (writes new batches), suppliers (credit exposure check) |
| `supplier_service` | Directory queries, relationship scoring/tiering rules, credit-limit utilization, early-payment recommendation logic ("Smart Payment Engine") | procurement (outstanding POs/invoices) |
| `customer_service` | Directory segmentation (Dues Pending/High Value/Inactive), ledger entry creation, loyalty-segment recompute | sales (invoice history) |
| `delivery_service` | Dispatch lifecycle transitions (Pending→Assigned→Packed→Dispatched→Delivered), rider assignment, ETA tracking | sales (invoice→delivery link) |
| `analytics_service` | Revenue/fast-mover/dead-stock computation — reads from **replica only** (see Section 8 & DB Arch §6.4) | catalog, sales, procurement |
| `notification_service` | Categorized feed assembly, mark-as-read, preference-aware dispatch trigger (delegates actual send to background jobs) | — |
| `audit_service` | Tenant-scoped audit query/filter/export; **never writes** — writes happen via `audit_interceptor` middleware and DB triggers (DB Arch §7.1) | — |
| `settings_service` | Shop profile, statutory re-verification submission, hardware/preference toggles | platform (re-verification routes into `shop_verification_queue`) |
| `subscription_service` | Usage-meter computation against `subscription_plans.transaction_limit`/`staff_account_limit`, upgrade/downgrade orchestration, payment-method management | platform |
| `command_center_service` | Federated read-only search across medicines/customers (delegates to `pg_trgm`-backed repository queries); **issues no writes, ever** | catalog, customers |
| `platform_admin_service` | Cross-tenant shop verification, wholesaler trust-badge verification, system health aggregation, plan management | bypasses tenant RLS via the dedicated platform DB role (DB Arch §9) |

**Service-layer rule on plan limits:** any service whose action increments a metered resource (`billing_service` creating an invoice, `settings_service` inviting a staff member) must call `subscription_service`'s limit-check **before** committing the write, and raise `PlanLimitExceeded` rather than allow a silent over-quota transaction — this operationalizes the Blueprint's "Nearing plan limit" warning (§1.3) as a hard architectural gate, not just a UI banner.

---

## 4. Repository Layer

Repositories are the **only** code permitted to issue SQL/ORM queries. Every repository method requires a bound tenant context (Section 6) except the explicitly platform-scoped repositories.

**`base_repository.py` contract (conceptual, no code):**
- Accepts a `TenantContext` (or `PlatformContext`) on construction; refuses to execute any query without one, except for the small set of methods marked `@platform_bypass` (used only by `platform_admin_service`).
- Every query method automatically applies `WHERE shop_id = :tenant_shop_id` as the **first** predicate — this is the app-layer enforcement that DB Arch §9 requires to sit alongside RLS, never instead of it.
- Exposes `.on_primary()` / `.on_replica()` query routing, defaulting to primary; services performing dashboard/analytics/audit-export reads explicitly request the replica.
- Translates DB-level constraint violations (unique, FK) into the domain exception hierarchy (`utils/exceptions.py`) so services never branch on raw DB error codes.

**Repository-to-domain mapping** (mirrors DB Architecture Section 1 exactly):

| Repository module | Tables owned | Notable query responsibilities |
|---|---|---|
| `platform/shop_repository` | `shops`, `shop_verification_documents`, `shop_settings` | shop lookup by slug, statutory status reads |
| `platform/subscription_repository` | `subscription_plans`, `shop_subscriptions`, `subscription_invoices`, `shop_payment_methods` | plan-limit lookups, invoice history |
| `platform/verification_queue_repository` | `shop_verification_queue`, `wholesaler_verification_queue` | platform-only, bypasses tenant RLS |
| `identity/user_repository` | `users`, `shop_users` | multi-shop membership resolution |
| `identity/role_permission_repository` | `roles`, `permissions`, `role_permissions` | RBAC lookups — heavily cached (Section 8) |
| `identity/session_repository` | `auth_sessions` | session issuance/revocation, active-shop context |
| `catalog/medicine_repository` | `medicine_categories`, `medicine_master`, `shop_medicines` | typeahead search (pg_trgm), barcode lookup |
| `catalog/batch_repository` | `medicine_batches` | near-expiry partial-index queries, reorder thresholds |
| `catalog/stock_ledger_repository` | `stock_ledger` | append-only writes, movement history (BRIN-indexed range scans) |
| `procurement/supplier_repository` | `suppliers`, `shop_supplier_relationships` | directory + relationship scoring reads |
| `procurement/purchase_order_repository` | `purchase_orders`, `purchase_order_items` | status-filtered "active POs" queries |
| `procurement/goods_receipt_repository` | `goods_receipts`, `goods_receipt_items`, `supplier_invoices`, `supplier_payments` | discrepancy flagging writes, aging-bucket reads |
| `sales/invoice_repository` | `invoices`, `invoice_items`, `invoice_payments` | partitioned-table-aware date-range queries |
| `sales/customer_repository` | `customers`, `customer_ledger_entries` | segmentation queries (Dues Pending/High Value/Inactive) |
| `sales/held_bill_repository` | `held_bills` | cart-snapshot JSONB read/write |
| `delivery/delivery_repository` | `riders`, `delivery_orders`, `delivery_status_history` | pipeline-funnel counts, live-ETA reads |
| `notifications/notification_repository` | `notifications`, `notification_preferences` | partial-index "unread" queries |
| `audit/audit_repository` | `audit_logs`, `system_events` | composite-index filtered reads; **insert-only access** at the DB grant level (DB Arch §7.2) — repository never exposes an update/delete method, full stop |

---

## 5. Authentication Architecture

Two fully separate authentication stacks, matching DB Arch §0's identity-separation decision.

### 5.1 Tenant Auth (`users` realm)
- **Credential:** email/phone + password (Blueprint §1.6 "Authentication & Onboarding"), verified against `users.password_hash`.
- **Session issuance:** on successful login, a row is created in `auth_sessions` (per DB Arch Domain B) and a short-lived **access token** (JWT, ~15 min) plus a longer-lived **refresh token** (rotated, tied to the `auth_sessions` row) are issued. The JWT carries `user_id` only — **not** `shop_id** — because a user may hold memberships in multiple shops.
- **Shop-context selection:** immediately after login, if the user has exactly one `shop_users` membership, the active shop is auto-selected; if more than one, the client must call a `select-shop` endpoint, which mints a **shop-scoped token** (short-lived, embeds `shop_id` + `role_id`) layered on top of the base session. This is the token the `tenant_context` middleware reads on every subsequent request (Section 6).
- **"Remember me":** extends refresh-token lifetime only, never the access token's.
- **Password reset:** time-boxed, single-use token, delivered via the existing notification channels (SMS/email) — reuses `notification_service`, not a separate mechanism.
- **2FA:** Blueprint §6.3 explicitly flags 2FA as referenced-but-undesigned (no settings UI exists). The architecture reserves the `users.mfa_enabled` column and the `auth_sessions` flow for a second factor, but **no 2FA enrollment/verification endpoint is built** until the product team closes this gap — building it now would be inventing UI-less product scope.

### 5.2 Platform Auth (`platform_admins` realm)
- Entirely separate login endpoint (`platform_auth_service`), separate token issuer, separate session store — **no shared secret, no shared session table** with tenant auth, per DB Arch §0's stated rationale (prevent privilege escalation from a compromised shop account).
- `platform_admins.mfa_enabled` is enforced as **mandatory**, not optional, for this realm given the cross-tenant blast radius of a compromised platform credential — this is a stricter posture than tenant auth, justified by the asymmetric risk, not a product requirement invented beyond the documents.
- Platform tokens carry `admin_id` + `platform_role` and are only ever validated by `platform_admin_bp`; the tenant `auth_guard` middleware explicitly rejects a platform token presented to any tenant route, and vice versa.

### 5.3 Connection-pooling / RLS interaction (carried over from DB Arch §9)
- Because the data layer's tenant isolation depends on a session-scoped Postgres setting, the auth/middleware layer's job ends at producing a **validated `shop_id`** — the repository layer (Section 4) and the DB connection pooling strategy (Section 10) are jointly responsible for getting that value into `SET LOCAL` inside the same transaction as the query, per the explicit caution in DB Arch §9. This is called out here so auth design and connection-pool design aren't decided independently and accidentally contradict each other.

---

## 6. RBAC Design

RBAC is **data-driven**, sourced entirely from the `roles` / `permissions` / `role_permissions` tables (DB Arch Domain B) — no role or permission is hardcoded in application logic.

### 6.1 Model
- `roles.role_code` (owner/manager/cashier/auditor) are the **system roles** confirmed by DB Arch §0; the architecture does not invent additional roles beyond what Blueprint §2's permission matrix and the DB schema both evidence.
- `permissions` are keyed by `(module, action)` — module values align exactly with the Blueprint §4 hierarchy (billing/inventory/suppliers/customers/delivery/analytics/admin/settings/subscription), action values are view/create/edit/delete/approve.
- A user's effective permission set for a request = the permissions attached to the `role_id` on their **current shop's** `shop_users` row — never a global role, since the same user can hold different roles in different shops (multi-shop membership).

### 6.2 Enforcement point
- `rbac_guard.py` middleware (or a per-endpoint decorator) resolves `(module, action)` from the route + HTTP verb, checks it against the cached effective-permission set (Section 8) for the request's bound `(user_id, shop_id)`, and rejects with 403 before the request reaches the service layer. **The service layer never re-checks permissions** — this keeps authorization in exactly one place.
- The Blueprint's "Suggested Permission Matrix" (§2) is implemented as the **seed data** for `role_permissions`, not as code — e.g., "Staff/Cashier: Inventory (view only)" becomes a `cashier` → `(inventory, view)` row, with no corresponding `(inventory, edit)` row. Where the Blueprint flags an item as needing stakeholder validation (e.g., "void may need Admin PIN"), that nuance is implemented as an **additional confirmation step in `billing_service`**, not as a new permission, since it's a step-up-auth pattern rather than a binary allow/deny.

### 6.3 Platform-side RBAC
- `platform_admins.platform_role` (Super Admin / Verification Officer / Support, per DB Arch Domain A) drives a **separate, smaller** permission check inside `platform_admin_bp` only — e.g., a Support role can view but not approve a wholesaler verification. This reuses the same `rbac_guard` mechanism conceptually but against a distinct, platform-only permission set, never the tenant `role_permissions` table.

### 6.4 Auditor role
- Blueprint §2 notes the Auditor/Compliance Viewer role "could be a restricted view... or just Admin" — pending confirmation. The architecture supports it cleanly either way because RBAC is data-driven: if confirmed as distinct, it is added as one more `role_code` + a read-only `role_permissions` set on the `admin` module, with zero application-code change.

---

## 7. API Versioning

- **URL-path versioning**: `/api/v1/...` for all routes, enforced at the blueprint-registration layer (Section 1's `api/v1/__init__.py`) rather than via headers — chosen for cache-ability (CDN/reverse-proxy can route on path) and for unambiguous debugging in a system with 10,000+ tenants generating support tickets.
- **One version directory per major version** (`api/v1/`, future `api/v2/`); a new version is a new sibling directory, never a set of conditionals inside existing handlers — this keeps a deprecated version's code frozen and removable as a unit.
- **Versioning boundary is the contract (schemas), not the service/repository layers** — `api/v1/billing` and a hypothetical `api/v2/billing` can both call the same `billing_service` if the underlying business logic hasn't changed, only the request/response shape did. This avoids duplicating business logic across versions.
- **Mobile vs. desktop are not separate API versions** — Blueprint §1.6 shows mobile screens as the same functional modules with condensed UI (dashboard, POS), so they are served by the same `v1` endpoints with response payloads shaped by query parameters/fields-selection, not a parallel API surface.
- **Deprecation policy:** a version is marked deprecated via response headers once a successor is GA, with a minimum support window communicated to the (currently single) client team before removal — this is a placeholder governance note since no multi-client deprecation scenario exists yet at single-version launch.

---

## 8. Caching Strategy

Redis-backed, layered by data volatility — chosen to take direct pressure off the primary Postgres instance for the exact hot paths the Database Architecture itself calls out as high-read or high-frequency.

| Cache | Key Shape | TTL | Invalidation Trigger | Rationale |
|---|---|---|---|---|
| **RBAC effective permissions** | `perm:{shop_id}:{user_id}` | 15 min, or session lifetime | On any `role_permissions`/`shop_users.role_id` change for that pair | Permission check happens on **every** request; DB §5's index strategy is unnecessary if this is cache-resident instead. |
| **Active-shop context resolution** | `shopctx:{session_id}` | session lifetime | On logout / shop-switch / session revoke | Avoids a join on every request just to confirm which shop a token is currently scoped to. |
| **Dashboard KPI tiles** | `dash:{shop_id}:{date_bucket}` | 60–120 sec | Time-based expiry only (acceptable staleness for KPI cards per Blueprint's "Today's Sales" framing) | Dashboard is the highest-traffic screen (Blueprint §1.6); short TTL balances freshness against the read-replica load DB Arch §6.4 already plans to offload here. |
| **Medicine/customer typeahead (⌘K, POS search)** | `search:{shop_id}:{query_hash}` | 30–60 sec | Time-based; explicit bust on medicine/customer create | `pg_trgm` queries (DB Arch §5) are still real DB hits; caching the hottest repeated prefixes cuts load without inventing a separate search index. |
| **Subscription plan + usage meters** | `subscription:{shop_id}` | 5 min | On invoice creation crossing a threshold, or explicit plan change | Plan-limit checks happen on the billing hot path (Section 3); cannot afford a DB round-trip per invoice. |
| **Supplier directory / relationship scores** | `suppliers:{shop_id}` | 5–10 min | On any write to `shop_supplier_relationships` | Directory is read far more often than relationship scores change (scores recompute on a schedule, not per-request — see Section 9). |
| **Notification unread badge count** | `unread:{user_id}` | event-driven (updated on read/write, not polled) | On notification create/read | Matches DB Arch §5's partial-index design intent — this is the cache-layer equivalent of that index, for the highest-frequency poll in the UI (the bell badge). |
| **Lookup tables** (status types, role/permission definitions, subscription plan catalog) | `lookup:{table_name}` | Long TTL (hours) with manual bust on admin edit | Explicit invalidation on the rare write | These are the tables DB Arch §0 chose specifically so they could be inserted into without migrations — caching them long is the read-side complement of that design choice. |

**What is explicitly NOT cached:** invoices, stock ledger, audit logs, and any financial/append-only data — these are read from Postgres (primary for writes-adjacent reads, replica for historical/report reads per Section 4) every time, because staleness in financial records is a compliance risk, not a UX nuisance.

**Cache-aside pattern throughout**, never write-through — services populate cache lazily on read-miss and explicitly invalidate on the relevant write, keeping Redis a pure performance layer with Postgres as the unconditional source of truth.

---

## 9. Background Jobs

Celery (with Redis or RabbitMQ as broker), organized by trigger type. Every job here corresponds to a Blueprint-evidenced feature that is inherently asynchronous or scheduled — no job is invented beyond what a screen or NFR implies.

### 9.1 Scheduled (Celery beat)

| Job | Schedule | Blueprint Source | Touches |
|---|---|---|---|
| Low-stock / reorder threshold scan | Every 15–30 min | Dashboard "Low Stock Alert," Inventory "Reorder Now" | `catalog/batch_repository`, writes to `notifications` |
| Expiry alert scan (30-day window) | Daily | Dashboard "Expiry Alert," Inventory near-expiry partial index | `catalog/batch_repository` |
| Dead-stock detection (60+ days unsold) | Daily | Analytics "Dead Stock Alert" | `sales` + `catalog` repositories (read-replica) |
| Supplier invoice due-date / early-payment scan | Daily | Finance Center "Smart Payment Engine," due-date calendar | `procurement/goods_receipt_repository` (supplier_invoices) |
| Credit aging bucket recompute | Daily | Finance Center aging analysis (0–15/16–30/.../60+) | `procurement` repositories |
| Subscription usage-meter rollup & plan-limit warning | Daily, plus real-time check on metered writes (Section 3) | Subscription "Nearing plan limit" | `platform/subscription_repository` |
| Customer loyalty-segment recompute (High Value/Inactive 60d+) | Daily | Customer Management segmentation tabs | `sales/customer_repository` (read-replica) |
| Analytics nightly rollups (revenue trend, top movers, supplier performance index) | Nightly | Analytics & Insights | read-replica only, per DB Arch §6.4 |
| Partition lifecycle verification | Daily | DB Arch §6.2 (pg_partman automation) | Not a data job — a **monitoring/alerting** job confirming pg_partman pre-created the next 2–3 months of partitions; pages on-call if it hasn't. |
| Audit log archival trigger past retention window | Monthly | DB Arch §6.3 (tiered storage) | Triggers detach/export of aged `audit_logs`/financial partitions to cold storage |

### 9.2 Event-triggered (fired by services, not on a schedule)

| Job | Fired By | Purpose |
|---|---|---|
| WhatsApp/SMS notification dispatch | `notification_service`, `billing_service` (digital receipt), `customer_service` (dues reminder) | Decouples third-party API latency from the request/response cycle |
| Print-receipt job | `billing_service` on "Generate Bill" | Hardware I/O must never block the POS response (NFR: sub-second POS, Blueprint §1.7) |
| Audit export generation (CSV/PDF) | `audit_service` on export request | Large export queries are routed to a worker reading the replica (DB Arch §7.3), result delivered via signed download link, not held open on an HTTP request |
| GST report / internal audit export generation | `analytics_service` | Same large-export pattern as above |
| Subscription invoice PDF generation | `subscription_service` on billing-cycle close | Matches "Invoice History with PDF export" (Blueprint §1.6) |
| Shop/wholesaler verification notification | `platform_admin_service` on approve/reject | Notifies the shop the moment statutory status flips (Blueprint workflow §5.1, §5.7) |
| Stock-ledger-derived reorder suggestion | `inventory_service` after a sale pushes stock below threshold | Real-time complement to the scheduled scan above, for the "immediate" alert case |

**Idempotency rule:** every job is designed to be safely re-runnable (keyed by a natural idempotency key — e.g., `shop_id + date_bucket` for rollups, `invoice_id` for receipt jobs) since Celery's at-least-once delivery semantics mean retries are expected, not exceptional.

---

## 10. Deployment Architecture

### 10.1 Compute topology
- **Containerized Flask app** (Gunicorn/uvicorn workers behind a reverse proxy), horizontally scaled, stateless — no server-local session state, consistent with the JWT + Redis session design in Section 5.
- **Platform-admin surface deployable as a separately scaled, separately network-segmented service** (or at minimum a separate listener) from the tenant-facing app — operationalizes the identity-separation principle (DB Arch §0, Section 5.2) at the infrastructure level, not just the code level. Low traffic volume (internal team only) means it can run on a much smaller fleet.
- **Celery workers** scaled independently by queue: a high-priority queue for receipt-printing/notification dispatch (latency-sensitive, small payloads) separated from a low-priority queue for exports/rollups (throughput-sensitive, large payloads) — prevents a slow GST export from delaying a customer's WhatsApp receipt.
- **Celery beat** runs as a single scheduled instance (leader-elected if the platform requires HA for scheduling) — schedule definitions live in `app/jobs/`, not in infra config, so they're reviewed the same way as application code.

### 10.2 Database topology (operationalizes DB Arch §6.4 and §9)
- **One Postgres primary**, sized for the OLTP write path (POS billing, stock ledger) — the single most write-heavy surface per DB Arch §6.1's volume estimates.
- **One or more streaming read replicas**, explicitly the target for: dashboard reads, analytics rollups, audit-log exports, and platform-admin cross-tenant queries — the repository layer's primary/replica routing (Section 4) is what makes this split possible without scattering the decision across services.
- **Connection pooling:** given RLS's dependency on a per-transaction session setting (DB Arch §9), the deployment must choose explicitly between (a) **session-level pooling**, simpler but less connection-efficient, or (b) **transaction-level pooling (PgBouncer)** with the application setting the tenant context via `SET LOCAL` inside every transaction. This is called out as a **required deployment decision**, not a default, exactly because DB Arch §9 warns that getting this wrong silently breaks tenant isolation under load — it is not safe to leave to a default pooler configuration.
- **Platform-admin DB role** is a distinct connection credential with `BYPASSRLS`, used exclusively by the platform-admin service tier, never by the tenant-facing app tier — enforced by deploying it as a separate database credential/secret, not a runtime flag.

### 10.3 Caching & messaging infrastructure
- **Redis** (or equivalent) deployed as a managed cluster, used for: caching (Section 8), Celery broker/result backend (or a separate broker if message volume warrants it), and rate-limiter state.
- Redis cache and Redis-as-broker are logically separated (different databases/namespaces or separate clusters at scale) so a cache eviction storm cannot stall job processing.

### 10.4 Edge / network layer
- Reverse proxy / API gateway terminates TLS (operationalizes the "256-bit SSL" trust signal at login, Blueprint §1.6) and is the layer where `/api/v1` path-based routing (Section 7) and per-shop/per-IP rate limiting (Section 6's middleware) are enforced before requests reach app containers.
- Static/exported assets (audit CSV/PDF exports, subscription invoice PDFs, receipts) are written to object storage and served via signed URLs, never streamed through the Flask app process — keeps app workers free for request handling.

### 10.5 Observability (operationalizes DB Arch's `pg_stat_statements` extension and the Blueprint's "System Health" screen)
- Application logs, Celery job outcomes, and DB query performance (via `pg_stat_statements`) feed a central observability stack; the **Platform Admin Panel's "System Health" widget (API status, transaction success rate, DB latency)** is backed by this same telemetry pipeline via `system_events` (DB Arch Domain H) and live infra metrics — not a separate hand-rolled health-check system.

### 10.6 Growth path (explicitly deferred, not designed now)
- DB Arch §6.4 notes the schema is already shaped (`shop_id`-keyed) for a future move to a distributed Postgres layer (e.g., Citus) if a single primary is outgrown. This backend architecture makes no infrastructure commitment to that path today — the repository layer's strict `shop_id`-scoped query discipline (Section 4) is what keeps that option open later without an application rewrite, exactly mirroring the database document's own stated rationale.

---

## 11. Explicit Non-Scope (carried forward from Blueprint §6, not redesigned here)

To avoid this architecture silently answering product questions the Blueprint deliberately left open, the following have **no backend surface** in this design:

- No wholesaler/supplier-facing API or auth realm (no portal exists in the product spec).
- No rider-facing API or auth realm (no rider app exists in the product spec).
- No returns/refunds endpoints (no such workflow evidenced).
- No multi-branch/inter-warehouse transfer endpoints.
- No 2FA enrollment/verification endpoints (referenced in audit logs, but no settings UI — see Section 5.1).
- No drug-interaction/dosage-safety checking logic.
- No in-app chat/messaging endpoints (buttons exist in the UI per Blueprint §6.3, but no thread/inbox screen to back).
- No tax-filing/GST-return submission integration beyond the existing export job (Section 9.2).

Any of these becoming in-scope requires a Blueprint/Database Architecture revision first — this document does not get ahead of that sign-off.
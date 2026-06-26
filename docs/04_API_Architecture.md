# MedicoSaathi — API Architecture
### Principal API Architect Review · REST/JSON over Flask · Phase 5

No implementation code is included below by design. Every endpoint, contract, and standard is specified at the architectural level — path, method, purpose, request/response shape, and rationale — so this can be reviewed and signed off before a single route is implemented.

**Source-of-truth discipline:** every endpoint below maps to a screen/workflow in the Product Blueprint, a table/domain in the Database Architecture, and a blueprint/service/repository in the Backend Architecture. No new product capability, table, or service is introduced here. Where a prior document flagged a gap (no wholesaler portal, no rider app, no 2FA UI, no returns flow), the corresponding API surface is **deliberately absent**, not stubbed.

All endpoints are mounted under `/api/v1` (Backend Architecture §7) unless explicitly marked as the platform-admin surface, which is described in Section 1.19.

---

## 1. Complete REST API Structure

### Conventions used throughout this section
- `{shop_id}` is **never** part of the URL path for tenant endpoints — it is derived server-side from the authenticated shop-context token (Backend Architecture §5.1, §6.2). Putting it in the path would invite path-based tenant-confusion bugs; the only acceptable place for tenant identity is the token.
- Path parameters use the table's natural entity ID (e.g., `{medicine_id}` → `shop_medicines.shop_medicine_id`).
- Every `GET` list endpoint supports the pagination (§5) and filtering (§6) standards by default; only deviations are called out per-endpoint.
- `Permission` column states the `(module, action)` pair from `permissions` (DB Arch Domain B) that `rbac_guard` checks (Backend Architecture §6.2).

### 1.1 Authentication — `/api/v1/auth`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| POST | `/auth/login` | Email/phone + password login (Blueprint §1.6) | Public |
| POST | `/auth/refresh` | Exchange refresh token for new access token | Authenticated (refresh token) |
| POST | `/auth/logout` | Revoke current session | Authenticated |
| POST | `/auth/logout-all` | Revoke all sessions for the user (e.g., "log out everywhere") | Authenticated |
| POST | `/auth/password/forgot` | Request password reset (sends reset token via existing notification channel) | Public |
| POST | `/auth/password/reset` | Complete reset using token | Public (token-bound) |
| GET | `/auth/me` | Current user profile + shop memberships | Authenticated |
| POST | `/auth/shops/select` | Select active shop context (multi-shop users) — mints shop-scoped token | Authenticated |
| POST | `/auth/register-shop` | Self-serve shop registration entry point (Blueprint §1.6 "Register Shop" link) — creates `shops` row in Pending status, **not** a fully operational tenant until platform verification | Public |

Full flow detail in Section 3.

### 1.2 Dashboard — `/api/v1/dashboard`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/dashboard/summary` | KPI cards: revenue (weekly/Δ%), today's sales, low-stock count, expiry-alert count (Blueprint §1.6) | `dashboard:view` |
| GET | `/dashboard/revenue-trend?range=weekly\|monthly` | Revenue trend chart data | `dashboard:view` |
| GET | `/dashboard/smart-alerts` | Smart Alerts feed (stock/expiry/supplier-due, each with an action hint) | `dashboard:view` |
| GET | `/dashboard/recent-transactions` | Recent orders-in / supplier-bills-out ledger | `dashboard:view` |
| GET | `/dashboard/activity-log` | System activity feed (order created, inventory updated, alert triggered, backup completed) | `dashboard:view` |

Dashboard is read-only — it aggregates other domains' data (Backend Architecture §3) and has no write endpoints of its own.

### 1.3 Medicines (Catalog) — `/api/v1/medicines`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/medicines` | List shop's medicine catalog (`shop_medicines`), filterable/searchable | `inventory:view` |
| GET | `/medicines/{medicine_id}` | Single SKU detail (excludes batch breakdown — see §1.4) | `inventory:view` |
| POST | `/medicines` | Add a medicine to the shop catalog (link to `medicine_master` or `is_custom`) | `inventory:create` |
| PATCH | `/medicines/{medicine_id}` | Edit pricing, thresholds, GST rate, active flag | `inventory:edit` |
| DELETE | `/medicines/{medicine_id}` | Soft-delete (`deleted_at`) — blocked if referenced by invoice history (DB Arch §4 `ON DELETE RESTRICT`) | `inventory:delete` |
| GET | `/medicines/{medicine_id}/detail` | Item Detail Drawer: profit margin, 6-month sales trend, stock-movement activity (Blueprint §1.6) | `inventory:view` |
| GET | `/medicines/master-search?q=` | Search the platform-curated `medicine_master` reference catalog when linking a new SKU | `inventory:create` |
| GET | `/medicines/categories` | `medicine_categories` tree (self-referencing hierarchy) | `inventory:view` |

### 1.4 Batches — `/api/v1/medicines/{medicine_id}/batches`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/medicines/{medicine_id}/batches` | Full batch breakdown for a SKU (multiple batches, independent expiry/cost/qty) | `inventory:view` |
| GET | `/medicines/{medicine_id}/batches/{batch_id}` | Single batch detail | `inventory:view` |
| POST | `/medicines/{medicine_id}/batches/adjustment` | Manual stock adjustment (writes a `stock_ledger` row, `movement_type=adjustment`) | `inventory:edit` |
| GET | `/inventory/expiring?window_days=30` | Cross-SKU near-expiry list (Dashboard "Expiry Alert," partial-index backed per DB Arch §5) | `inventory:view` |
| GET | `/inventory/low-stock` | Cross-SKU below-min-threshold list | `inventory:view` |
| GET | `/medicines/{medicine_id}/stock-ledger` | Movement history for a SKU (restock in / sale out) | `inventory:view` |
| POST | `/medicines/{medicine_id}/reorder` | "Reorder Now" — pre-fills and creates a draft Purchase Order (delegates to `procurement_service`) | `inventory:edit`, `procurement:create` |

`batch_id` is never created directly via this resource for goods receipt — batches are created exclusively through GRN completion (§1.10), matching the DB Architecture's 1:1 `goods_receipt_items → medicine_batches` rule.

### 1.5 Billing / POS — `/api/v1/billing`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| POST | `/billing/cart/price` | Stateless cart pricing preview (CGST/SGST split, discount, totals) — no persistence | `billing:create` |
| POST | `/billing/invoices` | Generate a bill ("Generate Bill" / Enter shortcut) — atomic: invoice + items + payment + stock decrement | `billing:create` |
| GET | `/billing/invoices` | List invoices (date/status/customer filters — see §6) | `billing:view` |
| GET | `/billing/invoices/{invoice_id}` | Invoice detail | `billing:view` |
| POST | `/billing/invoices/{invoice_id}/void` | Void a bill — step-up confirmation per Backend Architecture §6.2 ("void may need Admin PIN") | `billing:delete` |
| GET | `/billing/invoices/{invoice_id}/receipt` | Render/fetch printable receipt payload | `billing:view` |
| POST | `/billing/invoices/{invoice_id}/send` | Dispatch receipt via WhatsApp (async — Backend Architecture §9.2) | `billing:view` |
| POST | `/billing/held-bills` | Hold the current cart | `billing:create` |
| GET | `/billing/held-bills` | List held bills | `billing:view` |
| GET | `/billing/held-bills/{held_bill_id}` | Recall a held bill (returns cart snapshot) | `billing:view` |
| DELETE | `/billing/held-bills/{held_bill_id}` | Void a held bill | `billing:delete` |
| GET | `/billing/lookup/barcode/{code}` | F2 barcode/product scan lookup | `billing:create` |
| GET | `/billing/lookup/customer?q=` | F3 customer lookup (or walk-in) | `billing:create` |

### 1.6 Customers — `/api/v1/customers`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/customers` | Directory, segmented (`segment=all\|dues_pending\|high_value\|inactive`) | `customers:view` |
| POST | `/customers` | Create customer | `customers:create` |
| GET | `/customers/{customer_id}` | Full profile: contact, YTD spend, current due, AOV, top medicines, recent invoices (Blueprint §1.6) | `customers:view` |
| PATCH | `/customers/{customer_id}` | Edit contact/profile fields | `customers:edit` |
| DELETE | `/customers/{customer_id}` | Soft-delete | `customers:delete` |
| GET | `/customers/{customer_id}/quick-view` | Condensed drawer payload (current due, LTV, recent purchases) | `customers:view` |
| POST | `/customers/{customer_id}/reminder` | Send WhatsApp/call dues reminder (async) | `customers:view` |

### 1.7 Customer Ledger — `/api/v1/customers/{customer_id}/ledger`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/customers/{customer_id}/ledger` | Full debit/credit running ledger | `customers:view` |
| POST | `/customers/{customer_id}/ledger/payments` | "Record Payment" against the ledger — writes a `customer_ledger_entries` credit row, recalculates `balance_after` | `customers:edit` |

`customer_ledger_entries` is append-only (DB Arch §0) — there is no `PATCH`/`DELETE` on a ledger entry; corrections are recorded as a new offsetting entry, never an edit.

### 1.8 Suppliers (Directory) — `/api/v1/suppliers`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/suppliers` | Directory (verified badge, category, relationship score, filters) | `suppliers:view` |
| GET | `/suppliers/{supplier_id}` | Supplier detail | `suppliers:view` |
| POST | `/suppliers/{supplier_id}/chat` | "Chat" action entry point — **note:** Blueprint §6.3 confirms no thread/inbox screen exists; this endpoint is **not built** until that gap closes (listed here only to document the deliberate omission) | — *(not implemented)* |

### 1.9 Supplier Relationships — `/api/v1/suppliers/{supplier_id}/relationship`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/suppliers/{supplier_id}/relationship` | Tiering, trust score, tenure, cumulative procurement value, credit-limit utilization | `suppliers:view` |
| PATCH | `/suppliers/{supplier_id}/relationship` | Manual tier/credit-limit override (owner-level action) | `suppliers:edit` |
| GET | `/suppliers/{supplier_id}/performance` | Delivery speed, fulfillment rate, price-competitiveness tier | `suppliers:view` |
| GET | `/suppliers/{supplier_id}/activity` | Activity feed (tier upgrades, payments cleared, orders placed, delays) | `suppliers:view` |
| GET | `/suppliers/optimization-insights` | AI sourcing-switch recommendations (Relationship Dashboard) | `suppliers:view` |
| GET | `/suppliers/finance/summary` | Aggregate Finance Center KPIs: total outstanding, credit line + utilization, due-in-7-days, early-payment savings | `suppliers:view` |
| GET | `/suppliers/finance/aging` | Credit aging buckets (0–15/16–30/31–45/46–60/60+), segmented by wholesaler/manufacturer | `suppliers:view` |
| GET | `/suppliers/finance/smart-payments` | Smart Payment Engine recommendations (invoice, pay-by date, computed savings) | `suppliers:view` |
| POST | `/suppliers/invoices/{supplier_invoice_id}/payments` | "Make Payment" / "Review & Pay" — records a `supplier_payments` row | `suppliers:edit` |
| GET | `/suppliers/finance/due-dates` | Upcoming due-dates calendar list | `suppliers:view` |

### 1.10 Purchase Orders — `/api/v1/purchase-orders`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/purchase-orders` | List, filterable by status (draft/sent/partially_received/completed/cancelled) | `procurement:view` |
| POST | `/purchase-orders` | Create PO (supplier pre-filled by trust score, below-min items flagged) | `procurement:create` |
| GET | `/purchase-orders/{po_id}` | PO detail with line items | `procurement:view` |
| PATCH | `/purchase-orders/{po_id}` | Edit a draft PO | `procurement:edit` |
| POST | `/purchase-orders/{po_id}/send` | Dispatch via email/WhatsApp (sets `sent_at`) | `procurement:edit` |
| POST | `/purchase-orders/{po_id}/cancel` | Cancel | `procurement:delete` |

### 1.11 Goods Receiving (GRN) — `/api/v1/goods-receipts`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/goods-receipts` | Pending shipments queue (status: arrived/in_transit/delayed → maps to `in_progress`/`completed`) | `procurement:view` |
| POST | `/goods-receipts` | Start a GRN against a PO (`po_id`) | `procurement:create` |
| GET | `/goods-receipts/{grn_id}` | GRN detail with per-SKU verification progress | `procurement:view` |
| POST | `/goods-receipts/{grn_id}/items` | Verify one line item: batch number, expiry, quantity, optional discrepancy flag | `procurement:edit` |
| PATCH | `/goods-receipts/{grn_id}/items/{grn_item_id}` | Correct a verified item before completion | `procurement:edit` |
| POST | `/goods-receipts/{grn_id}/complete` | "Complete GRN" — atomically creates `medicine_batches` rows, closes the PO, updates inventory | `procurement:edit` |
| GET | `/goods-receipts/{grn_id}/ai-insights` | Fast-mover shelf-routing + cold-chain temperature alerts | `procurement:view` |
| GET | `/goods-receipts/stats/daily` | Items-verified vs. % of expected daily volume KPI | `procurement:view` |

### 1.12 Deliveries — `/api/v1/deliveries`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/deliveries/summary` | Active deliveries, avg delivery time, successful-today, rider availability | `delivery:view` |
| GET | `/deliveries/pipeline` | Funnel counts: Pending → Assigned → Packed → Dispatched → Delivered | `delivery:view` |
| GET | `/deliveries` | Active dispatch table (filterable by date, status) | `delivery:view` |
| POST | `/deliveries` | "New Dispatch" creation against an invoice | `delivery:create` |
| GET | `/deliveries/{delivery_id}` | Detail incl. live ETA/distance | `delivery:view` |
| PATCH | `/deliveries/{delivery_id}/status` | Transition status (writes `delivery_status_history`) | `delivery:edit` |
| PATCH | `/deliveries/{delivery_id}/assign` | Assign/reassign a rider | `delivery:edit` |
| GET | `/deliveries/{delivery_id}/tracking` | Live lat/lng + ETA for the map view | `delivery:view` |
| GET | `/riders` | Fleet roster (rider, zone, current load) | `delivery:view` |
| PATCH | `/riders/{rider_id}/status` | Update rider availability | `delivery:edit` |

No rider-authenticated endpoints exist (Blueprint §6.2 gap) — every write above is performed by shop staff on the rider's behalf, never by the rider.

### 1.13 Notifications — `/api/v1/notifications`

Full design in Section 8.

### 1.14 Analytics — `/api/v1/analytics`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/analytics/headline` | Fast-Moving Flow %, Customer Retention %, Supplier Performance Index | `analytics:view` |
| GET | `/analytics/revenue-growth?range=30d\|6m\|12m` | Revenue growth chart | `analytics:view` |
| GET | `/analytics/top-movers` | Leaderboard: product, category, units sold | `analytics:view` |
| GET | `/analytics/dead-stock` | 60+ day unsold list (batch, expiry, days-aged, ₹ value at risk) | `analytics:view` |
| GET | `/analytics/exports/gst-report?format=csv\|pdf` | GST report export (async job, §9 and Backend Arch §9.2) | `analytics:view` |
| GET | `/analytics/exports/internal-audit?format=csv\|pdf` | Internal audit summary export | `analytics:view` |
| GET | `/analytics/exports/{export_id}` | Poll export job status / fetch signed download URL | `analytics:view` |

All `analytics/*` reads are served from the **read replica** (Backend Architecture §8 caching table, §4 routing) — never the primary.

### 1.15 Audit Logs — `/api/v1/audit`

Full design in Section 9.

### 1.16 Subscription — `/api/v1/subscription`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/subscription` | Current plan, usage meters (transactions, staff seats), renewal date/amount | `subscription:view` (owner-only per Backend Arch §1) |
| GET | `/subscription/plans` | Full plan comparison matrix | `subscription:view` |
| POST | `/subscription/upgrade` | Upgrade to a higher tier | `subscription:edit` |
| POST | `/subscription/downgrade` | Downgrade, requires explicit confirmation flag in payload | `subscription:edit` |
| POST | `/subscription/contact-sales` | Enterprise tier inquiry | `subscription:view` |
| GET | `/subscription/payment-methods` | Saved cards/UPI | `subscription:view` |
| POST | `/subscription/payment-methods` | Add a payment method | `subscription:edit` |
| PATCH | `/subscription/payment-methods/{method_id}/default` | Set default method | `subscription:edit` |
| DELETE | `/subscription/payment-methods/{method_id}` | Remove a method | `subscription:edit` |
| GET | `/subscription/invoices` | Invoice history | `subscription:view` |
| GET | `/subscription/invoices/{invoice_id}/pdf` | Per-invoice PDF download | `subscription:view` |

### 1.17 Settings — `/api/v1/settings`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/settings/shop` | Shop identity (logo, name, tagline) | `settings:view` |
| PATCH | `/settings/shop` | Edit identity fields | `settings:edit` |
| GET | `/settings/statutory` | GSTIN/Drug License status (verified/unverified, expiry) | `settings:view` |
| POST | `/settings/statutory/documents` | Submit/re-submit a statutory document → lands in platform's `shop_verification_queue` (Blueprint §5.1) | `settings:edit` |
| GET | `/settings/business` | Business details tab | `settings:view` |
| PATCH | `/settings/business` | Edit | `settings:edit` |
| GET | `/settings/operations` | Billing mode (tax_invoice/estimate), hardware toggles | `settings:view` |
| PATCH | `/settings/operations` | Edit billing mode, thermal printer, barcode auto-focus, WhatsApp receipts (Beta) | `settings:edit` |
| GET | `/settings/security` | Security tab (session list, **not** 2FA enrollment — gap, Backend Arch §5.1) | `settings:view` |
| POST | `/settings/security/sessions/{session_id}/revoke` | Revoke a specific session | `settings:edit` |

### 1.18 Global Command Center — `/api/v1/search`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/search?q=` | Federated read-only search: medicines (with stock-level), customers (with balance) | `dashboard:view` (broadest common read permission — command center never exposes data a user couldn't otherwise see in its owning module) |
| GET | `/search/quick-actions` | Static/contextual quick-action list (Create PO ⌘P, New Customer ⌘N) for client-side palette rendering | Authenticated |
| GET | `/search/recent` | Recently used actions/entities for the current user | Authenticated |

`command_center_service` issues **no writes** (Backend Architecture §3) — every action surfaced here is a deep link to the owning module's existing endpoint, not a new write path.

### 1.19 Platform Admin — `/api/v1/platform`

Mounted on a distinct routing/network segment per Backend Architecture §2, validated only against `platform_admins` tokens (§5.2). A tenant-scoped token is rejected outright by `auth_guard` before reaching `rbac_guard`.

| Method | Path | Purpose | Permission (platform_role) |
|---|---|---|---|
| POST | `/platform/auth/login` | Platform admin login (mandatory MFA) | Public (platform realm) |
| GET | `/platform/kpis` | Total active shops, verified wholesalers, total GMV, active subscriptions (MoM delta) | Super Admin, Verification Officer, Support (view) |
| GET | `/platform/shops/verification-queue` | Pending shop document review (Drug License, GST) | Verification Officer+ |
| GET | `/platform/shops/verification-queue/{queue_id}` | Document detail | Verification Officer+ |
| POST | `/platform/shops/verification-queue/{queue_id}/review` | Approve/reject | Verification Officer+ (approve restricted to Super Admin per Backend Arch §6.3 nuance) |
| GET | `/platform/wholesalers/verification-queue` | Pending wholesaler trust-badge IDs | Verification Officer+ |
| POST | `/platform/wholesalers/verification-queue/{queue_id}/review` | "Verify Details" approve/reject | Verification Officer+ |
| GET | `/platform/system-health` | API status, transaction success rate, DB latency | All platform roles |
| GET | `/platform/plans` | Active plan breakdown, user counts per tier | Super Admin |
| PATCH | `/platform/plans/{plan_id}` | Manage a subscription plan definition | Super Admin only |
| GET | `/platform/shops` | Cross-tenant shop search (support tooling) | Support+ |
| GET | `/platform/shops/{shop_id}` | Single shop detail, cross-tenant (uses `BYPASSRLS` role, Backend Arch §10.2) | Support+ |
| GET | `/platform/audit` | Platform-level audit events (`audit_logs` where `shop_id IS NULL`) | Super Admin |

---

## 2. Request / Response Standards

A single envelope shape is used across **every** endpoint, success or failure, so client code can branch on one consistent field rather than per-endpoint shapes.

### 2.1 Success response

```
{
  "success": true,
  "data": { ... } | [ ... ],
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO-8601"
  },
  "pagination": { ... }   // present only on list endpoints, see Section 5
}
```

- `data` holds the resource(s) — a single object for detail endpoints, an array for list endpoints.
- `meta.request_id` is generated at the edge (reverse proxy or first middleware) and threaded through logs/audit entries/job traces for correlatable debugging — particularly valuable at 10,000-tenant scale where a single support ticket needs to trace one request across the app tier, Celery, and Postgres logs.

### 2.2 Error response

```
{
  "success": false,
  "error": {
    "code": "MACHINE_READABLE_CODE",
    "message": "Human-readable, safe-to-display message",
    "details": { ... }      // optional, structured context — never a stack trace
  },
  "meta": {
    "request_id": "uuid",
    "timestamp": "ISO-8601"
  }
}
```

- `error.code` is a stable, documented enum (Section 11) — clients branch on `code`, never on `message` text, since `message` may be localized later (Blueprint §6.3 flags missing localization as a future gap).
- No internal exception class names, SQL fragments, or file paths ever appear in `error.message` or `details` — this is enforced at the global error handler, which translates the domain exception hierarchy (Backend Architecture, `utils/exceptions.py`) into this shape exclusively.

### 2.3 Validation error response

A specialization of the error envelope for `422 Unprocessable Entity`, carrying per-field detail:

```
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "One or more fields are invalid.",
    "details": {
      "fields": [
        { "field": "gst_rate", "code": "OUT_OF_RANGE", "message": "Must be between 0 and 28." },
        { "field": "phone", "code": "REQUIRED", "message": "Phone is required." }
      ]
    }
  },
  "meta": { "request_id": "...", "timestamp": "..." }
}
```

- `field` uses the exact request-body field name, dot-notation for nested objects (`items[2].quantity`) — so client-side form libraries can map an error straight onto the failing input without string parsing.
- Validation happens at the schema layer (Backend Architecture's `schemas/`), before the request ever reaches a service — business-rule failures (e.g., "PO total exceeds credit limit") are **not** validation errors; they use the Business Rule Error category (Section 11.5) with `422` or `409` as appropriate, keeping "malformed input" and "well-formed but disallowed" distinct.

---

## 3. Authentication Flow

### 3.1 Login
1. `POST /auth/login` with email-or-phone + password.
2. On success: a row is written to `auth_sessions`; an access token (JWT, ~15 min TTL, claims = `user_id`, `session_id` only) and a refresh token (opaque, rotated, stored hashed, tied to the `auth_sessions` row) are returned.
3. Response also returns the user's `shop_users` memberships list so the client can immediately render a shop-picker if there's more than one, or auto-select if there's exactly one.

### 3.2 Shop switching
1. `POST /auth/shops/select` with `{ shop_id }`, bearing the base access token.
2. Server validates an **active** `shop_users` row exists for `(user_id, shop_id)`.
3. Returns a **shop-scoped token** (JWT, same ~15 min TTL, claims = `user_id`, `session_id`, `shop_id`, `role_id`) — this is the token every tenant endpoint in Section 1 actually requires; the base login token alone is insufficient for any tenant route.
4. Switching shops mid-session does not invalidate the previous shop-scoped token's remaining TTL by default — clients should discard it locally, but server-side, each shop-scoped token is independently valid until expiry or explicit logout, since a user may legitimately keep two browser tabs open against two shops.

### 3.3 Refresh
1. `POST /auth/refresh` with the refresh token (sent as an httpOnly cookie or in the body, per client platform).
2. Server validates the token against `auth_sessions` (not revoked, not expired), rotates it (issues a new refresh token, invalidates the old one — refresh-token rotation prevents replay of a stolen, already-used token), and issues a new access token.
3. **Refresh does not re-issue shop context automatically** — if the access token was shop-scoped, the new one carries the same `shop_id`/`role_id` claims, re-validated against current `shop_users` state (so a mid-session role downgrade or membership revocation takes effect on next refresh, not just next login).

### 3.4 Logout
- `POST /auth/logout`: revokes only the current session (`auth_sessions.revoked_at`).
- `POST /auth/logout-all`: revokes every session for the user — used for "this looks like unauthorized access" recovery.

### 3.5 Password reset
1. `POST /auth/password/forgot` with email/phone — always returns a generic success response regardless of whether the identifier exists (prevents account enumeration).
2. A single-use, time-boxed token is generated and delivered via the existing notification channel (SMS/email), reusing `notification_service` rather than a bespoke mailer.
3. `POST /auth/password/reset` with the token + new password — on success, **all existing sessions for that user are revoked**, forcing re-login everywhere, since a password reset is itself a signal the old credential may have been compromised.

### 3.6 Platform admin auth
- Entirely separate endpoint (`/platform/auth/login`), separate token issuer and claim namespace (`admin_id`, `platform_role` — never `user_id`/`shop_id`), mandatory MFA step before token issuance (Backend Architecture §5.2). No shared code path with Section 3.1–3.5 beyond the password-hashing utility.

---

## 4. Authorization Flow

### 4.1 Request-level pipeline
Every tenant-scoped request passes through, in order:

1. **`auth_guard`** — verifies JWT signature/expiry, confirms the token's realm (tenant vs. platform) matches the route's expected realm, rejects immediately on mismatch (no fallthrough, no "try both").
2. **`tenant_context` middleware** — extracts `shop_id`/`role_id` from a shop-scoped token; if the route requires tenant context and the presented token is realm-correct but **not yet shop-scoped** (i.e., still the base login token from step 3.1), returns `403 SHOP_CONTEXT_REQUIRED` rather than guessing a shop.
3. **`rbac_guard`** — resolves the `(module, action)` pair the route declares, fetches the effective permission set for `(user_id, shop_id)` from cache (Backend Architecture §8; cache-miss falls through to `role_permissions` via the repository layer), and checks membership. Failure → `403 PERMISSION_DENIED`.
4. **Repository-layer tenant binding** — every repository call made downstream is constructed with the same `shop_id` resolved in step 2; this is the second, independent enforcement of tenant scope (Backend Architecture §4), and it is what backs the database's RLS policy with an explicit `WHERE shop_id = :shop_id` on every query regardless of what step 2/3 already checked.

### 4.2 RBAC evaluation detail
- Permission checks are **never** role-name string comparisons in application code (e.g., `if role == 'owner'`) — they are always `(module, action)` lookups against the cached `role_permissions` set, so a future change to what "manager" can do is a data change, not a deploy.
- A route declares exactly one `(module, action)` requirement (occasionally two, where a single endpoint spans domains — e.g., "Reorder Now" in §1.4 needs both `inventory:edit` and `procurement:create`). Multi-permission routes require **all** listed permissions, never any-of, to avoid an endpoint becoming reachable through an unintended role combination.
- Step-up actions (PIN-confirmed void, owner-only downgrade) are **not** modeled as a different permission — they're an additional explicit confirmation field/challenge the service layer checks after RBAC passes, per Backend Architecture §6.2's stated rationale (it's an authentication step-up, not an authorization tier).

### 4.3 Tenant isolation guarantees
- **Defense in depth, two independent layers, never one alone:** app-layer `WHERE shop_id =` (enforced by the repository base class) plus Postgres RLS (DB Arch §9) — a bug that skips one is still caught by the other.
- **No endpoint accepts a client-supplied `shop_id`.** Even the platform-admin "cross-tenant shop detail" endpoint (`GET /platform/shops/{shop_id}`) takes `shop_id` as a path parameter precisely *because* that surface is intentionally cross-tenant and uses the `BYPASSRLS` platform role — the absence of `shop_id` in every tenant-realm path is the tell that distinguishes "this route trusts the token's tenant" from "this route is platform-only and explicitly cross-tenant."
- **Audit interceptor runs after authorization, before the service commits**, attaching the resolved `shop_id`/`user_id`/`role_id` to the eventual `audit_logs` row (Backend Architecture middleware list) — so authorization context and audit context are guaranteed to agree, never independently derived and possibly inconsistent.

---

## 5. Pagination Standards

Two pagination modes are supported, chosen per-endpoint based on the data's access pattern — not interchangeably available everywhere, to avoid clients depending on whichever one happens to "work."

### 5.1 Offset pagination — default for bounded, UI-table-style lists
Used for: medicines, customers, suppliers, purchase orders, GRNs, deliveries — lists a user pages through via numbered/prev-next controls.

**Request:** `?page=1&page_size=25`
**Response `pagination` block:**
```
{
  "mode": "offset",
  "page": 1,
  "page_size": 25,
  "total_items": 482,
  "total_pages": 20
}
```

### 5.2 Cursor pagination — required for high-volume, append-only, infinite-scroll-style feeds
Used for: invoices, stock ledger, audit logs, notifications — exactly the tables the Database Architecture partitions by `created_at` and indexes with `(shop_id, created_at DESC)` (DB Arch §5, §6). Offset pagination on a partitioned, fast-growing table degrades (`OFFSET` still scans skipped rows) and produces duplicate/skipped results under concurrent inserts; cursor pagination avoids both.

**Request:** `?cursor=<opaque_token>&limit=25`
**Response `pagination` block:**
```
{
  "mode": "cursor",
  "next_cursor": "opaque_token_or_null",
  "has_more": true,
  "limit": 25
}
```
- The cursor encodes `(created_at, id)` of the last item seen — never just a timestamp alone, since multiple rows can share a timestamp at high write volume, and `id` as a tiebreaker guarantees stable ordering.
- Cursor endpoints **never** accept a `page` parameter — the two modes are not mixed on a single endpoint.

### 5.3 Default and maximum limits

| Setting | Value | Rationale |
|---|---|---|
| Default `page_size` / `limit` | 25 | Matches a typical UI table page without over-fetching |
| Maximum `page_size` / `limit` | 100 | Hard server-side cap — requests above this are clamped, not rejected, to keep client integration forgiving while protecting the DB/replica from a runaway export-style query through a list endpoint |
| Audit/analytics export endpoints | Not paginated at the API layer at all | These are handled as async export jobs (Section 9, Backend Architecture §9.2) returning a downloadable file, specifically because "give me all 12,000+ rows" is not a pagination problem, it's a batch-export problem |

---

## 6. Filtering Standards

A consistent query-parameter vocabulary across all list endpoints, so client code can build one generic list-fetching utility rather than per-endpoint parsing.

### 6.1 Search
- `?q=` — free-text search, routed to the `pg_trgm`-backed repository methods (DB Arch §5) for medicines, customers, suppliers, audit actor names. Minimum 2 characters; shorter values are ignored server-side rather than erroring, to keep typeahead UX smooth.

### 6.2 Sort
- `?sort=field` ascending, `?sort=-field` descending (leading `-` for descending) — e.g., `?sort=-created_at`.
- Only fields with a backing index are sortable (enumerated per-endpoint in the schema layer); requesting a non-sortable field returns `400 INVALID_SORT_FIELD` rather than a silent full-table-scan sort.
- Default sort is always the most recent first (`-created_at` or domain-equivalent) unless the screen's evidenced UX implies otherwise (e.g., Supplier Directory defaults to `-relationship_score`).

### 6.3 Date filters
- `?date_from=YYYY-MM-DD&date_to=YYYY-MM-DD` — inclusive range, applied to the endpoint's natural date column (`created_at`, `expiry_date`, `due_date` as appropriate, documented per-endpoint).
- Convenience presets accepted as an alternative to explicit range, matching Blueprint-evidenced UI filters exactly: `?range=24h|7d|30d|custom` (Audit Log Center, Blueprint §1.6) — `custom` requires `date_from`/`date_to` to also be present.

### 6.4 Status filters
- `?status=` — accepts one or more comma-separated values from that resource's lookup-table-backed status set (DB Arch §0's "status types are lookup tables, not native ENUM" decision means this filter's valid-value set is **data**, fetched once via a small reference endpoint per resource, e.g., `GET /purchase-orders/statuses`, and cached client-side — not hardcoded in client code).
- Examples: `?status=draft,sent` on Purchase Orders; `?status=overdue` on Supplier Invoices; `?status=pending,assigned` on Deliveries.

### 6.5 Batch filters (medicines/batches domain specifically)
- `?expiry_before=YYYY-MM-DD` — batches expiring before a date (powers the Expiry Alert widget).
- `?stock_state=low|critical|ok` — server-computed bucket against `min_stock_threshold`/`max_stock_threshold`, not a raw quantity comparison the client would otherwise have to replicate.
- `?supplier_id=` — batches sourced from a specific supplier.
- `?has_discrepancy=true` — GRN items flagged during verification.

---

## 7. File Upload Architecture

All uploads follow a **two-step, signed-URL pattern** — the Flask app never proxies raw file bytes through a request/response cycle, keeping app workers free and avoiding large multipart bodies hitting the same process tier that serves POS billing.

### 7.1 General pattern (applies to all four upload types)
1. `POST /{resource}/upload-intent` with `{ filename, content_type, size_bytes }` → server validates type/size against the per-type policy below, returns a **pre-signed object-storage upload URL** plus a `file_id` reference.
2. Client uploads the file bytes directly to object storage using that URL.
3. `POST /{resource}/upload-complete` with `{ file_id }` → server verifies the object exists in storage, runs any required post-processing (image resize, virus scan), and attaches the final URL to the owning record.

### 7.2 Per-type policy

| Upload type | Endpoint family | Accepted types | Max size | Notes |
|---|---|---|---|---|
| Shop logo | `/settings/shop/logo/upload-intent` → `.../upload-complete` | png, jpg, svg | 2 MB | Resized server-side to standard nav/header dimensions on complete |
| Medicine images | `/medicines/{medicine_id}/images/upload-intent` → `.../upload-complete` | png, jpg | 5 MB | Not evidenced as a current screen feature in Blueprint §1.6 — included here as a forward-compatible pattern only if the product team confirms it's in scope; **not wired to any UI surface today** |
| Verification documents (Drug License, GSTIN) | `/settings/statutory/documents/upload-intent` → `.../upload-complete` | pdf, png, jpg | 10 MB | On complete, creates a `shop_verification_documents` row in `Pending` status and a corresponding `shop_verification_queue` entry (Blueprint §5.1 flow) |
| Invoice / report exports | Not a client-initiated upload — these are **system-generated** files from async jobs (Section 9, Backend Architecture §9.2), delivered via `GET /.../{export_id}` returning a signed **download** URL | csv, pdf | N/A | Listed here for completeness since the prompt groups it under "File Upload Architecture," but the correct mental model is *download*, not upload — documented explicitly to avoid the implementation team building an unneeded upload endpoint |

### 7.3 Cross-cutting upload rules
- Every uploaded file is stored under a `shop_id`-prefixed object key (e.g., `shop-{shop_id}/logos/{file_id}.png`) so storage-level access policy can enforce tenant isolation independently of the application layer — the same defense-in-depth principle as RLS, applied to object storage.
- Verification-document uploads are the one category visible to a **second tenant context** (platform admin review) — those objects are read via a platform-scoped signed URL generated by `platform_admin_service`, never by handing the platform admin a tenant-scoped URL.

---

## 8. Notification APIs — `/api/v1/notifications`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/notifications` | Categorized feed (orders/inventory/payments/supplier_updates), cursor-paginated | `dashboard:view` |
| GET | `/notifications/unread-count` | Badge count — backed by the cached counter (Backend Architecture §8), not a live query, on this high-poll-frequency endpoint | `dashboard:view` |
| PATCH | `/notifications/{notification_id}/read` | Mark one as read | `dashboard:view` |
| POST | `/notifications/bulk-read` | "Mark all as read" — accepts an optional `category` filter to scope the bulk action, or omits it for true "all" | `dashboard:view` |
| GET | `/notifications/preferences` | Per-category channel preferences (app/sms/whatsapp/email) | `settings:view` |
| PUT | `/notifications/preferences` | Replace the full preference set in one call (simpler client logic than per-category PATCHes for a settings-page toggle grid) | `settings:edit` |

- The feed endpoint supports `?category=inventory,payments` filtering (Section 6.4 status-filter pattern, applied to category instead of status) and the filter chips evidenced in Blueprint §1.6.
- Bulk-read is **idempotent** — re-calling it on an already-all-read feed returns `200` with `{ updated_count: 0 }`, not an error.

---

## 9. Audit APIs — `/api/v1/audit`

| Method | Path | Purpose | Permission |
|---|---|---|---|
| GET | `/audit` | Full event ledger, cursor-paginated (Section 5.2 — this is the canonical high-volume case the cursor mode exists for) | `audit:view` |
| GET | `/audit/{event_id}` | "Inspect" drill-in — full before/after state | `audit:view` |
| GET | `/audit/filters` | Returns valid filter facets (action types, modules present) for the current shop, to populate filter-chip UI without hardcoding | `audit:view` |
| POST | `/audit/exports` | Request a CSV/PDF export job (async, Backend Architecture §9.2) | `audit:view` |
| GET | `/audit/exports/{export_id}` | Poll job status / fetch the signed download URL once ready | `audit:view` |

### 9.1 Filtering (applies the Section 6 vocabulary to this resource specifically)
- `?range=24h|7d|30d|custom` + `date_from`/`date_to`
- `?action_type=created,modified,deleted,auth`
- `?module=billing,inventory,...`
- `?q=` — free-text against the denormalized `actor_display_name` trigram index (DB Arch §7.3) — never a join-based name search on every page

### 9.2 Tenant boundary for this resource specifically
- A tenant `GET /audit` request **only** ever returns rows where `audit_logs.shop_id` equals the caller's own shop — rows with `shop_id IS NULL` (platform-level events) are excluded by the same RLS policy described in DB Architecture §7.4, not by an application-layer `if` statement, since this is exactly the kind of rule that must not depend on every code path remembering to apply it.
- Exports are always routed to a **read replica** (DB Arch §7.3, Backend Architecture §10.2) — a large CSV/PDF export query must never compete with POS write throughput on the primary.

---

## 10. API Naming Conventions

### 10.1 Resource naming
- **Plural nouns** for collections: `/medicines`, `/customers`, `/purchase-orders` — never verbs in the path (`/getMedicines` is not used anywhere in this design).
- **kebab-case** for multi-word path segments (`/purchase-orders`, `/goods-receipts`), **snake_case** for query parameters and JSON field names (`page_size`, `created_at`) — one casing convention per "zone" (URL vs. payload), not mixed within either.
- **Nesting reflects true ownership, capped at two levels deep:** `/medicines/{medicine_id}/batches` (batches belong to a medicine) is nested; `/medicines/{medicine_id}/batches/{batch_id}/ledger` would not be — instead `/medicines/{medicine_id}/stock-ledger` flattens back out, because the Database Architecture's own FK design already denormalizes `shop_id`/`shop_medicine_id` onto `stock_ledger` specifically to avoid deep join chains (DB Arch §4), and the API should mirror that same "don't force a deep walk" philosophy.
- **Sub-resource actions that aren't pure CRUD** (send, void, complete, review, select) are modeled as a `POST` to a noun-phrase sub-path — `/purchase-orders/{po_id}/send`, `/goods-receipts/{grn_id}/complete` — never as a custom HTTP verb and never bolted onto the parent resource's `PATCH` as a hidden flag, so the action is discoverable from the URL alone.

### 10.2 Versioning
- Path-based, `/api/v1/...`, per Backend Architecture §7 — restated here as the binding convention for every endpoint in Section 1.
- A version boundary is **per major version, whole-API**, not per-endpoint — there is no `/api/v1/medicines` coexisting with `/api/v2/billing` under casual use; if `v2` exists, it's a deliberate, documented platform-wide cutover with its own deprecation timeline for `v1`.

### 10.3 URL standards
- No trailing slashes.
- No file extensions in the path (`.json` is never appended — content type is negotiated via `Accept`/`Content-Type` headers, though JSON is the only format this platform serves at launch).
- Query parameters are always optional with sane defaults — no endpoint requires a query parameter to return a sensible default page of results.

### 10.4 HTTP method usage

| Method | Usage | Idempotent? |
|---|---|---|
| `GET` | Read a resource or collection. Never has side effects. | Yes |
| `POST` | Create a resource, **or** trigger a non-CRUD action (send, void, complete) per §10.1 | No (except where explicitly idempotent, e.g., bulk-read) |
| `PATCH` | Partial update of an existing resource | Yes |
| `PUT` | Full replace of a resource — used sparingly, only where a "replace the whole set" semantic is genuinely cleaner than PATCH (e.g., notification preferences, §8) | Yes |
| `DELETE` | Soft-delete (master/reference data) — **never** issued against append-only ledger/log resources, which have no `DELETE` route at all (invoices, stock ledger, audit logs, customer ledger) | Yes |

---

## 11. Error Handling Standards

All errors use the envelope from Section 2.2/2.3. `error.code` values are grouped by category; HTTP status code is determined by category, not chosen ad hoc per endpoint.

### 11.1 Authentication errors — `401`

| Code | Meaning |
|---|---|
| `INVALID_CREDENTIALS` | Login email/phone+password mismatch |
| `TOKEN_EXPIRED` | Access token past TTL — client should attempt refresh |
| `TOKEN_INVALID` | Malformed/unverifiable signature |
| `SESSION_REVOKED` | Token's underlying `auth_sessions` row was revoked (logout, password reset, admin action) |
| `REALM_MISMATCH` | A platform token was presented to a tenant route, or vice versa |
| `MFA_REQUIRED` | Platform login attempted without completing the mandatory second factor (Backend Architecture §5.2) |

### 11.2 Authorization errors — `403`

| Code | Meaning |
|---|---|
| `PERMISSION_DENIED` | `rbac_guard` check failed for the resolved `(module, action)` |
| `SHOP_CONTEXT_REQUIRED` | Valid tenant token, but no shop selected yet (Section 4.1, step 2) |
| `SHOP_ACCESS_REVOKED` | `shop_users.status` is no longer `Active` for the token's `shop_id` |
| `STEP_UP_REQUIRED` | Action needs an additional confirmation (e.g., void PIN) not present in the request |
| `PLATFORM_ROLE_INSUFFICIENT` | Platform admin's `platform_role` doesn't cover this action (e.g., Support attempting an approval) |

### 11.3 Validation errors — `422`
- Single code at the top level: `VALIDATION_ERROR`, with the per-field `details.fields` array from Section 2.3. No category subdivision needed beyond this — field-level codes (`REQUIRED`, `OUT_OF_RANGE`, `INVALID_FORMAT`, `UNIQUE_CONSTRAINT`, etc.) live inside `details.fields[].code`, not as top-level error codes, since the top level must stay stable while field rules evolve.

### 11.4 Rate limit errors — `429`

| Code | Meaning |
|---|---|
| `RATE_LIMITED` | Per-shop or per-IP request budget exceeded (Backend Architecture `middleware/rate_limiter.py`) |
- Response includes a `Retry-After` header (seconds) and `details.limit`/`details.reset_at` in the body — clients should back off, not retry immediately.
- Rate limits are tiered: a stricter limit on `auth/login` and `auth/password/forgot` (brute-force/enumeration protection) than on general authenticated traffic; billing/POS endpoints get a **higher** budget than other modules given the sub-second, high-frequency NFR (Blueprint §1.7) — this is documented here as a policy, with exact numeric limits left to ops tuning rather than fixed in this architecture.

### 11.5 Business rule errors — `409` (conflict with current state) or `422` (well-formed but disallowed)

| Code | HTTP | Meaning |
|---|---|---|
| `PLAN_LIMIT_EXCEEDED` | 422 | Metered action would exceed `subscription_plans.transaction_limit`/`staff_account_limit` (Backend Architecture §3) |
| `CREDIT_LIMIT_EXCEEDED` | 422 | Supplier relationship `credit_used` would exceed `credit_limit` on a PO/payment action |
| `BATCH_OUT_OF_STOCK` | 409 | Cart/PO line item exceeds `quantity_available` at commit time (race between price-preview and commit) |
| `INVOICE_ALREADY_VOIDED` | 409 | Void requested on a non-active invoice |
| `GRN_ALREADY_COMPLETED` | 409 | Edit attempted on a closed GRN |
| `DUPLICATE_BARCODE` | 409 | `(shop_id, barcode)` uniqueness violation surfaced as a domain error, not a raw DB constraint message |
| `STATUTORY_DOCUMENT_PENDING_REVIEW` | 409 | Re-submission attempted while a prior submission is still `Pending` |
| `SHOP_NOT_VERIFIED` | 403 | Action requires `shops.verification_status = Verified` and the shop hasn't cleared onboarding yet (Blueprint §5.1) — modeled as `403` rather than `409` since it's a standing eligibility gate, not a one-time state conflict |

This category is where the domain exception hierarchy (Backend Architecture `utils/exceptions.py`) surfaces — each named exception there maps to exactly one code here, translated by the global error handler, never serialized ad hoc per service.

---

## 12. Performance Standards

### 12.1 Response time targets

| Endpoint class | Target (p95) | Rationale |
|---|---|---|
| Billing/POS (`/billing/*`, lookups) | < 300 ms | Blueprint NFR: sub-second, keyboard-first POS flow (§1.7) — the API budget must leave headroom for client-side rendering within that "sub-second" feel |
| Dashboard summary/KPIs | < 500 ms (cache hit), < 1.5 s (cache miss, Section 8 of Backend Architecture) | Highest-traffic screen; cache-hit path should dominate in steady state |
| Standard list/detail reads (medicines, customers, suppliers, deliveries) | < 500 ms | General CRUD-read expectation for a responsive enterprise UI |
| Search / Command Center (`/search`) | < 400 ms | Typeahead UX requires near-instant feedback; backed by `pg_trgm` + cache (Backend Architecture §8) |
| Analytics / reporting reads | < 2 s | Acceptable to be slower — read-replica-served, often pre-aggregated by nightly rollup jobs (Backend Architecture §9.1) |
| Audit list (cursor page) | < 1 s | Large table, but composite-index-backed and cursor-paginated specifically to keep this bounded regardless of total row count |
| Async export job (audit/analytics/GST/subscription PDF) | Job accepted < 200 ms; completion notified via poll/webhook, no fixed SLA on the export itself | These are explicitly decoupled from request/response performance — see Section 7's "download, not upload" note and Backend Architecture §9.2 |

### 12.2 Caching strategy (API-layer application of Backend Architecture §8)
- Every cacheable endpoint in Section 1 (dashboard, search, RBAC-adjacent reads, subscription/plan reads, supplier directory, lookup tables) returns an `ETag` / `Cache-Control: private, max-age=...` header consistent with the Redis TTLs already defined in Backend Architecture §8 — so a CDN/reverse-proxy layer and client-side HTTP caching reinforce the server-side Redis cache rather than duplicating its policy independently.
- Cache-sensitive endpoints (financial: invoices, ledgers, audit) explicitly set `Cache-Control: no-store` — restated here as an API-contract guarantee, not just an internal Redis decision, so no intermediate proxy is tempted to cache a stale balance.

### 12.3 Read replica usage (API-layer application of Backend Architecture §4, §10.2)
- The API layer's contract with clients is identical whether a `GET` is served from primary or replica — **replica lag is an internal routing decision, never exposed in the response shape** — but the architecture commits to routing the following endpoint families to replica by default: all of Section 1.14 (Analytics), Section 1.15 (Audit) list/export reads, Dashboard's heavier aggregates, and Platform Admin's cross-tenant KPI/health reads.
- Endpoints that must reflect a write the same request just made (e.g., fetching an invoice immediately after creating it, fetching a PO right after sending it) are **always** routed to primary, regardless of general routing policy, to avoid replica-lag-induced "where did my data go" confusion immediately after a user action.

### 12.4 Pagination/filtering as a performance control (ties Sections 5–6 back to this section)
- The hard maximum `page_size`/`limit` of 100 (Section 5.3) and the requirement that `?sort=` only accept indexed fields (Section 6.2) are not just usability choices — they are the API layer's enforcement of the query-shape guarantees the Database Architecture's indexing strategy (DB Arch §5) was built around. An API that allowed arbitrary sort fields or unbounded page sizes would silently invalidate the index design this entire platform depends on at 10,000-tenant scale.
# MedicoSaathi — PostgreSQL Database Architecture
### Principal Database Architect Review · Multi-Tenant SaaS, 10,000+ Pharmacy Scale

No DDL/SQL is included below by design. Every table is specified at the logical/conceptual level — column name, data type, constraint intent, and rationale — so this can be reviewed and signed off before a single line of schema code is written.

---

## 0. Architectural Decisions (made once, applied everywhere)

| Decision | Choice | Rationale |
|---|---|---|
| Tenancy model | **Shared database, shared schema, `shop_id` discriminator column on every tenant table** + PostgreSQL Row-Level Security (RLS) | Cheapest to operate and migrate at 10,000-tenant scale; avoids 10,000 schemas/databases (connection and vacuum overhead). RLS gives DB-enforced isolation as a second line of defense behind app-layer filtering. |
| Tenant key placement | `shop_id` is the **first column in every composite index** on tenant tables and the **partition/sub-partition key** on high-volume tables | Matches the access pattern: 99% of queries are scoped to one shop. Leading-column indexes and partition pruning both key off this. |
| Primary key strategy | **UUID (v7/time-ordered)** for entity tables that may need to be referenced across services, merged, or exposed externally (shops, suppliers, customers, invoices, medicines). **BIGINT `GENERATED ALWAYS AS IDENTITY`** for pure append-only, high-volume, internally-referenced tables (stock_ledger, audit_logs, notifications, customer_ledger_entries, invoice/PO/GRN line items) | UUIDv7 keeps index locality reasonable (unlike UUIDv4) while staying globally unique and non-guessable. BIGINT identity is cheaper to index and faster to insert for tables doing millions of rows/day where global uniqueness across systems isn't required. |
| Platform vs. tenant separation | Two schemas: **`tenant`** (all shop-scoped operational tables) and **`platform`** (platform admin, subscription plans, wholesaler master registry, system health) | Keeps blast radius and permission grants clean — platform-admin credentials never need default access to tenant data, and vice versa. |
| Identity separation | `platform_admins` is a **completely separate table/auth realm** from `users` (shop staff) | Prevents privilege escalation between a compromised shop account and platform-level control — this is a security boundary, not just a data boundary. |
| Money/quantity types | `NUMERIC(14,2)` for currency, `NUMERIC(12,3)` for quantities (supports fractional units like ml/kg) | Never use floating point for money or stock counts. |
| Status fields | Backed by small **lookup tables** (e.g., `invoice_status_types`) rather than free-text or native `ENUM` | Native Postgres `ENUM` requires a schema migration (`ALTER TYPE`) to add a value — painful at 10,000-tenant scale with zero-downtime deploys. Lookup tables let you add a new status with a plain `INSERT`. |
| Soft delete | `deleted_at TIMESTAMPTZ NULL` on master/reference data (medicines, customers, suppliers); **hard append-only, no deletes at all** on ledgers/logs (stock_ledger, audit_logs, customer_ledger_entries, invoices) | Financial and audit trails must be immutable for compliance; master data needs reversible delete for UX ("undo," recovery). |
| Extensions required | `pgcrypto` (UUID generation, field-level encryption), `pg_trgm` (fuzzy/typeahead search — powers the ⌘K command center), `btree_gin` (composite GIN on mixed types), `pg_partman` (partition automation), `pg_stat_statements` (query performance monitoring) | Each maps directly to a blueprint feature (search, partitioning, security). |

---

## 1. Database Tables (by domain)

### Domain A — Platform & Tenant Management (`platform` schema)

**`platform_admins`**
`admin_id` UUID PK · `email` TEXT UNIQUE NOT NULL · `password_hash` TEXT · `mfa_enabled` BOOLEAN · `platform_role` TEXT (Super Admin / Verification Officer / Support) · `status` TEXT · `created_at`, `last_login_at` TIMESTAMPTZ

**`subscription_plans`**
`plan_id` UUID PK · `plan_code` TEXT UNIQUE (starter/growth/professional/enterprise) · `display_name` TEXT · `monthly_price` NUMERIC(10,2) · `transaction_limit` INTEGER NULL (NULL = unlimited) · `staff_account_limit` INTEGER NULL · `feature_flags` JSONB (advanced_analytics, priority_support, etc.) · `is_active` BOOLEAN

**`shops`** *(the tenant root entity)*
`shop_id` UUID PK · `legal_name` TEXT NOT NULL · `display_name` TEXT · `slug` TEXT UNIQUE · `gstin` TEXT · `gstin_verification_status` TEXT · `drug_license_number` TEXT · `drug_license_expiry` DATE · `drug_license_verification_status` TEXT · `verification_status` TEXT (Pending/Verified/Rejected/Suspended) · `current_plan_id` UUID FK→`subscription_plans` · `timezone` TEXT DEFAULT 'Asia/Kolkata' · `created_at`, `updated_at`, `deleted_at` TIMESTAMPTZ

**`shop_verification_documents`**
`document_id` UUID PK · `shop_id` UUID FK→`shops` · `document_type` TEXT (drug_license/gst_certificate/other) · `file_url` TEXT · `status` TEXT (Pending/Approved/Rejected) · `reviewed_by` UUID FK→`platform_admins` NULL · `reviewed_at` TIMESTAMPTZ NULL · `submitted_at` TIMESTAMPTZ

**`shop_settings`** *(1:1 with shops)*
`shop_id` UUID PK/FK→`shops` · `billing_mode` TEXT (tax_invoice/estimate) · `thermal_printer_enabled` BOOLEAN · `barcode_autofocus_enabled` BOOLEAN · `whatsapp_receipts_enabled` BOOLEAN · `preferences` JSONB · `updated_at` TIMESTAMPTZ

**`shop_subscriptions`**
`subscription_id` UUID PK · `shop_id` UUID FK→`shops` · `plan_id` UUID FK→`subscription_plans` · `status` TEXT (Active/PastDue/Cancelled) · `billing_cycle_start` DATE · `billing_cycle_end` DATE · `created_at`

**`subscription_invoices`**
`invoice_id` UUID PK · `shop_id` UUID FK→`shops` · `subscription_id` UUID FK→`shop_subscriptions` · `amount` NUMERIC(10,2) · `status` TEXT (Paid/Due/Failed) · `period_start`, `period_end` DATE · `paid_at` TIMESTAMPTZ NULL

**`shop_payment_methods`**
`payment_method_id` UUID PK · `shop_id` UUID FK→`shops` · `method_type` TEXT (card/upi) · `masked_details` JSONB (last4, network, upi_handle) · `is_default` BOOLEAN

---

### Domain B — Identity & Access (`tenant` schema, cross-cutting)

**`users`** *(a real person — may belong to more than one shop, e.g. a multi-outlet owner)*
`user_id` UUID PK · `email` TEXT UNIQUE NULL · `phone` TEXT UNIQUE NOT NULL · `password_hash` TEXT · `full_name` TEXT · `mfa_enabled` BOOLEAN DEFAULT false · `status` TEXT (Active/Disabled) · `created_at`, `last_login_at`

**`roles`**
`role_id` UUID PK · `role_code` TEXT UNIQUE (owner/manager/cashier/auditor) · `display_name` TEXT · `is_system_role` BOOLEAN

**`permissions`**
`permission_id` UUID PK · `module` TEXT (billing/inventory/suppliers/customers/delivery/analytics/admin/settings/subscription) · `action` TEXT (view/create/edit/delete/approve) · UNIQUE(`module`,`action`)

**`role_permissions`** *(junction)*
`role_id` UUID FK→`roles` · `permission_id` UUID FK→`permissions` · PRIMARY KEY(`role_id`,`permission_id`)

**`shop_users`** *(membership junction — this is where a user is granted access to a specific shop)*
`shop_user_id` UUID PK · `shop_id` UUID FK→`shops` · `user_id` UUID FK→`users` · `role_id` UUID FK→`roles` · `status` TEXT (Active/Invited/Revoked) · `invited_by` UUID FK→`users` NULL · `joined_at` TIMESTAMPTZ · UNIQUE(`shop_id`,`user_id`)

**`auth_sessions`**
`session_id` UUID PK · `user_id` UUID FK→`users` · `shop_id` UUID FK→`shops` NULL (active-context shop) · `device_info` JSONB · `ip_address` INET · `issued_at`, `expires_at` TIMESTAMPTZ · `revoked_at` TIMESTAMPTZ NULL

---

### Domain C — Catalog & Inventory (`tenant` schema)

**`medicine_categories`**
`category_id` UUID PK · `name` TEXT · `parent_category_id` UUID FK→`medicine_categories` NULL *(self-referencing, for hierarchy)*

**`medicine_master`** *(platform-curated shared catalog — generic/brand reference data, NOT shop-scoped)*
`medicine_id` UUID PK · `generic_name` TEXT · `brand_name` TEXT · `composition` TEXT · `category_id` UUID FK→`medicine_categories` · `schedule_type` TEXT (OTC/Rx/Schedule-H/Narcotic) · `hsn_code` TEXT · `default_gst_rate` NUMERIC(4,2)

**`shop_medicines`** *(shop's own catalog entry — pricing, thresholds; links to master OR is fully custom)*
`shop_medicine_id` UUID PK · `shop_id` UUID FK→`shops` · `medicine_id` UUID FK→`medicine_master` NULL · `is_custom` BOOLEAN DEFAULT false · `custom_name` TEXT NULL · `sku` TEXT · `barcode` TEXT · `unit_of_measure` TEXT (strip/bottle/box) · `min_stock_threshold` NUMERIC(12,3) · `max_stock_threshold` NUMERIC(12,3) · `default_sale_price` NUMERIC(14,2) · `gst_rate` NUMERIC(4,2) · `is_active` BOOLEAN · UNIQUE(`shop_id`,`medicine_id`) WHERE `is_custom`=false; UNIQUE(`shop_id`,`barcode`)

**`medicine_batches`**
`batch_id` UUID PK · `shop_id` UUID FK→`shops` · `shop_medicine_id` UUID FK→`shop_medicines` · `batch_number` TEXT · `manufacture_date` DATE NULL · `expiry_date` DATE NOT NULL · `cost_price` NUMERIC(14,2) · `mrp` NUMERIC(14,2) · `quantity_received` NUMERIC(12,3) · `quantity_available` NUMERIC(12,3) · `supplier_id` UUID FK→`suppliers` NULL · `received_via_grn_id` UUID FK→`goods_receipts` NULL · `created_at`

**`stock_ledger`** *(append-only movement log — every stock change of any kind)*
`ledger_id` BIGINT PK (identity) · `shop_id` UUID FK→`shops` · `shop_medicine_id` UUID FK→`shop_medicines` · `batch_id` UUID FK→`medicine_batches` NULL · `movement_type` TEXT (sale/purchase_receipt/adjustment/return/expiry_writeoff/transfer) · `quantity_delta` NUMERIC(12,3) *(signed: + in, − out)* · `reference_type` TEXT (invoice/grn/manual) · `reference_id` UUID NULL · `created_by` UUID FK→`users` NULL · `created_at` TIMESTAMPTZ

---

### Domain D — Procurement & Suppliers (`tenant` schema, suppliers shared at platform level)

**`suppliers`** *(platform-level master entity — one supplier can serve many shops)*
`supplier_id` UUID PK · `legal_name` TEXT · `gstin` TEXT · `category` TEXT (branded/generic/surgicals/fmcg) · `platform_trust_score` NUMERIC(5,2) · `verification_status` TEXT · `created_at`

**`shop_supplier_relationships`** *(the shop's view of a supplier — tiering, credit, scoring)*
`relationship_id` UUID PK · `shop_id` UUID FK→`shops` · `supplier_id` UUID FK→`suppliers` · `relationship_tier` TEXT (tier_1/tier_2/under_review) · `relationship_score` NUMERIC(5,2) · `credit_limit` NUMERIC(14,2) · `credit_used` NUMERIC(14,2) · `payment_terms_days` INTEGER · `status` TEXT (Active/Inactive) · `partnered_since` DATE · UNIQUE(`shop_id`,`supplier_id`)

**`purchase_orders`**
`po_id` UUID PK · `shop_id` UUID FK→`shops` · `supplier_id` UUID FK→`suppliers` · `po_number` TEXT · `status` TEXT (draft/sent/partially_received/completed/cancelled) · `expected_delivery_date` DATE · `subtotal`, `discount_amount`, `gst_amount`, `grand_total` NUMERIC(14,2) · `created_by` UUID FK→`users` · `created_at`, `sent_at` TIMESTAMPTZ

**`purchase_order_items`**
`po_item_id` BIGINT PK (identity) · `po_id` UUID FK→`purchase_orders` · `shop_medicine_id` UUID FK→`shop_medicines` · `ordered_qty` NUMERIC(12,3) · `unit_cost` NUMERIC(14,2) · `gst_rate` NUMERIC(4,2) · `line_total` NUMERIC(14,2)

**`goods_receipts`** *(GRN header)*
`grn_id` UUID PK · `shop_id` UUID FK→`shops` · `po_id` UUID FK→`purchase_orders` · `received_by` UUID FK→`users` · `status` TEXT (in_progress/completed) · `started_at`, `completed_at` TIMESTAMPTZ

**`goods_receipt_items`**
`grn_item_id` BIGINT PK (identity) · `grn_id` UUID FK→`goods_receipts` · `po_item_id` BIGINT FK→`purchase_order_items` · `batch_number` TEXT · `expiry_date` DATE · `received_qty` NUMERIC(12,3) · `discrepancy_flag` BOOLEAN DEFAULT false · `discrepancy_notes` TEXT NULL

**`supplier_invoices`**
`supplier_invoice_id` UUID PK · `shop_id` UUID FK→`shops` · `supplier_id` UUID FK→`suppliers` · `grn_id` UUID FK→`goods_receipts` NULL · `invoice_number` TEXT · `amount` NUMERIC(14,2) · `due_date` DATE · `status` TEXT (current/due/overdue/paid) · `early_payment_discount_pct` NUMERIC(4,2) NULL · `early_payment_deadline` DATE NULL · `created_at`

**`supplier_payments`**
`payment_id` UUID PK · `shop_id` UUID FK→`shops` · `supplier_invoice_id` UUID FK→`supplier_invoices` · `amount` NUMERIC(14,2) · `payment_method` TEXT · `payment_date` DATE · `reference_number` TEXT · `created_by` UUID FK→`users`

---

### Domain E — Sales, Billing & Customers (`tenant` schema)

**`customers`**
`customer_id` UUID PK · `shop_id` UUID FK→`shops` · `full_name` TEXT · `phone` TEXT · `address` TEXT NULL · `loyalty_segment` TEXT (high_value/regular/inactive) · `created_at`, `deleted_at` · UNIQUE(`shop_id`,`phone`)

**`invoices`** *(bills generated from POS)*
`invoice_id` UUID PK · `shop_id` UUID FK→`shops` · `customer_id` UUID FK→`customers` NULL *(NULL = walk-in)* · `invoice_number` TEXT · `billing_mode` TEXT (tax_invoice/estimate) · `subtotal`, `discount_amount`, `cgst_amount`, `sgst_amount`, `total_amount` NUMERIC(14,2) · `payment_status` TEXT (paid/due/partially_paid) · `created_by` UUID FK→`users` · `created_at` TIMESTAMPTZ · UNIQUE(`shop_id`,`invoice_number`)

**`invoice_items`**
`invoice_item_id` BIGINT PK (identity) · `invoice_id` UUID FK→`invoices` · `shop_medicine_id` UUID FK→`shop_medicines` · `batch_id` UUID FK→`medicine_batches` NULL · `quantity` NUMERIC(12,3) · `unit_price` NUMERIC(14,2) · `gst_rate` NUMERIC(4,2) · `line_total` NUMERIC(14,2)

**`invoice_payments`**
`invoice_payment_id` BIGINT PK (identity) · `invoice_id` UUID FK→`invoices` · `payment_mode` TEXT (cash/upi/card/credit) · `amount` NUMERIC(14,2) · `tendered_amount` NUMERIC(14,2) NULL · `change_amount` NUMERIC(14,2) NULL · `transaction_reference` TEXT NULL

**`held_bills`** *(in-progress carts parked mid-transaction)*
`held_bill_id` UUID PK · `shop_id` UUID FK→`shops` · `cart_snapshot` JSONB · `held_by` UUID FK→`users` · `held_at` TIMESTAMPTZ · `status` TEXT (held/recalled/voided)

**`customer_ledger_entries`** *(running debit/credit ledger backing the customer profile screen)*
`ledger_entry_id` BIGINT PK (identity) · `shop_id` UUID FK→`shops` · `customer_id` UUID FK→`customers` · `entry_type` TEXT (debit/credit) · `amount` NUMERIC(14,2) · `balance_after` NUMERIC(14,2) · `reference_type` TEXT (invoice/payment/adjustment) · `reference_id` UUID NULL · `created_at`

---

### Domain F — Delivery (`tenant` schema)

**`riders`**
`rider_id` UUID PK · `shop_id` UUID FK→`shops` · `full_name` TEXT · `phone` TEXT · `zone` TEXT · `status` TEXT (available/on_load/offline)

**`delivery_orders`**
`delivery_id` UUID PK · `shop_id` UUID FK→`shops` · `invoice_id` UUID FK→`invoices` NULL · `rider_id` UUID FK→`riders` NULL · `destination_address` TEXT · `status` TEXT (pending/assigned/packed/dispatched/delivered/delayed) · `current_lat`, `current_lng` NUMERIC(9,6) NULL · `eta_minutes` INTEGER NULL · `dispatched_at`, `delivered_at` TIMESTAMPTZ NULL · `created_at`

**`delivery_status_history`**
`history_id` BIGINT PK (identity) · `delivery_id` UUID FK→`delivery_orders` · `status` TEXT · `changed_by` UUID FK→`users` NULL · `changed_at` TIMESTAMPTZ · `notes` TEXT NULL

---

### Domain G — Notifications (`tenant` schema)

**`notifications`**
`notification_id` BIGINT PK (identity) · `shop_id` UUID FK→`shops` · `recipient_user_id` UUID FK→`users` NULL · `category` TEXT (inventory/orders/payments/supplier_updates) · `title` TEXT · `body` TEXT · `action_url` TEXT NULL · `is_read` BOOLEAN DEFAULT false · `created_at`

**`notification_preferences`**
`preference_id` UUID PK · `user_id` UUID FK→`users` · `category` TEXT · `channel` TEXT (app/sms/whatsapp/email) · `enabled` BOOLEAN

---

### Domain H — Audit & Compliance (cross-cutting, split across both schemas)

**`audit_logs`** *(system/security audit trail — see Section 6 for full design)*
`event_id` BIGINT PK (identity) · `shop_id` UUID FK→`shops` NULL *(NULL = platform-level event)* · `actor_user_id` UUID FK→`users` NULL · `actor_admin_id` UUID FK→`platform_admins` NULL · `module` TEXT · `action_type` TEXT (created/modified/deleted/auth) · `entity_type` TEXT · `entity_id` UUID NULL · `before_state` JSONB NULL · `after_state` JSONB NULL · `ip_address` INET NULL · `created_at` TIMESTAMPTZ

**`system_events`** *(platform health: backups, API status, deploys — not tenant data)*
`event_id` BIGINT PK (identity) · `event_type` TEXT · `payload` JSONB · `created_at`

---

### Domain I — Platform Verification Workflows (`platform` schema)

**`shop_verification_queue`**
`queue_id` UUID PK · `shop_id` UUID FK→`shops` · `status` TEXT (pending/approved/rejected) · `assigned_to` UUID FK→`platform_admins` NULL · `reviewed_at` TIMESTAMPTZ NULL · `submitted_at` TIMESTAMPTZ

**`wholesaler_verification_queue`**
`queue_id` UUID PK · `supplier_id` UUID FK→`suppliers` · `status` TEXT (pending/approved/rejected) · `reviewed_by` UUID FK→`platform_admins` NULL · `reviewed_at` TIMESTAMPTZ NULL · `submitted_at` TIMESTAMPTZ

---

## 2. Relationships (cardinality summary)

| Relationship | Cardinality | Notes |
|---|---|---|
| shops → shop_users | 1 : N | one shop has many staff memberships |
| users → shop_users | 1 : N | one person can belong to multiple shops (chain owner) |
| shops → subscription_plans | N : 1 (via current_plan_id / shop_subscriptions) | a plan serves many shops |
| shops → shop_medicines | 1 : N | shop's own catalog |
| medicine_master → shop_medicines | 1 : N (optional) | shop_medicines may instead be `is_custom` with no master link |
| shop_medicines → medicine_batches | 1 : N | one SKU, many batches over time |
| medicine_batches → stock_ledger | 1 : N | every movement against a batch is logged |
| shops ↔ suppliers | M : N (via shop_supplier_relationships) | a supplier serves many shops; a shop uses many suppliers |
| purchase_orders → purchase_order_items | 1 : N | |
| purchase_orders → goods_receipts | 1 : N | a PO can be received in multiple partial shipments |
| goods_receipts → goods_receipt_items | 1 : N | |
| goods_receipt_items → medicine_batches | 1 : 1 (a confirmed GRN item creates exactly one batch) | |
| suppliers → supplier_invoices → supplier_payments | 1 : N : N | an invoice can receive multiple partial payments |
| customers → invoices | 1 : N | NULL customer_id = walk-in |
| invoices → invoice_items / invoice_payments | 1 : N / 1 : N | a bill can be split across multiple payment modes |
| customers → customer_ledger_entries | 1 : N | running balance, append-only |
| invoices → delivery_orders | 1 : 0..1 | not every invoice is delivered (counter sale vs. delivery) |
| riders → delivery_orders | 1 : N | |
| delivery_orders → delivery_status_history | 1 : N | |
| shops/users → audit_logs | 1 : N (loosely coupled, nullable FKs) | audit_logs intentionally tolerates orphaned/nullable actor references so logging never blocks on a deleted user |

---

## 3 & 4. Primary Keys and Foreign Keys

Already specified per-table above. Cross-cutting rules applied platform-wide:

- **Every foreign key column is explicitly indexed** (Postgres does not auto-index FKs — this is the single most common scalability mistake in multi-tenant schemas, manifesting as slow cascading deletes and slow joins once tables pass a few million rows).
- **All FKs from a tenant table to another tenant table also carry the redundant `shop_id`** alongside the entity FK where the child table is high-volume (e.g., `invoice_items.shop_id` is denormalized even though it's derivable via `invoice_id`). This lets queries and partition pruning filter by `shop_id` directly without a join, which matters enormously once `invoices` is partitioned (Section 6).
- **`ON DELETE` policy:** `RESTRICT` on master/reference data referenced by financial records (you cannot delete a `shop_medicine` that has invoice history) · `CASCADE` only on pure child/detail rows that have no independent meaning (`invoice_items` cascades from `invoices`, `purchase_order_items` cascades from `purchase_orders`) · `SET NULL` on optional linking FKs where the parent's deletion shouldn't void the record (`delivery_orders.rider_id`, `audit_logs.actor_user_id`).
- **Platform-admin tables never hold a foreign key into tenant tables and vice versa across the schema boundary** except through the explicit `shop_id`/`supplier_id` reference — this keeps the platform schema able to be backed up, scaled, or migrated independently of tenant data.

---

## 5. Index Strategy

| Pattern | Applied To | Why |
|---|---|---|
| **Leading-column composite index `(shop_id, created_at DESC)`** | invoices, stock_ledger, audit_logs, notifications, customer_ledger_entries, delivery_status_history | The single most common query shape in the product: "show me this shop's recent X." |
| **Composite `(shop_id, status)`** partial/filtered where applicable | purchase_orders (status != 'completed'), delivery_orders (status NOT IN ('delivered')), supplier_invoices (status != 'paid') | Powers the "active/pending" dashboard widgets (Order Pipeline, Smart Alerts, Due-soon lists) without scanning settled history. |
| **Unique composite indexes** | (shop_id, phone) on customers · (shop_id, invoice_number) on invoices · (shop_id, barcode) on shop_medicines · (shop_id, supplier_id) on shop_supplier_relationships | Enforces tenant-scoped uniqueness — the same phone number or invoice number is legitimately reused across different shops. |
| **`pg_trgm` GIN trigram indexes** | shop_medicines.custom_name / medicine_master.brand_name+generic_name, customers.full_name, customers.phone | Powers fuzzy/typeahead search behind the Global Command Center (⌘K) and POS barcode/name search — exact-match B-tree indexes can't serve "search as you type." |
| **Partial index on near-expiry stock** | `medicine_batches (shop_id, expiry_date) WHERE quantity_available > 0` | Directly serves the Expiry Alerts widget and Dead Stock Alert report without a full table scan. |
| **Partial index on unread notifications** | `notifications (recipient_user_id) WHERE is_read = false` | Small, hot, frequently-polled index for the notification bell badge. |
| **BRIN indexes** | created_at column on stock_ledger and audit_logs (in addition to the B-tree composite above) | These tables are append-only and naturally time-ordered; BRIN is dramatically smaller than B-tree and ideal for range scans on insert-ordered data at hundreds-of-millions-of-rows scale. |
| **GIN indexes on JSONB** | audit_logs.before_state/after_state, shop_settings.preferences, shop_medicines feature flags | Enables querying inside the JSON payload (e.g., "find all audit events that changed `price`") without a schema migration for every new field. |
| **Covering/INCLUDE indexes** | invoices (shop_id, created_at DESC) INCLUDE (total_amount, payment_status) | Lets the Dashboard revenue-trend query satisfy itself entirely from the index without touching the heap, at high read volume. |
| **No index on low-selectivity boolean flags alone** | e.g., `is_custom`, `is_active` | Always pair with shop_id; a bare boolean index on a 10,000-tenant table is nearly useless on its own. |

---

## 6. Partition Strategy

### 6.1 Which tables get partitioned, and how

| Table | Partition Key | Scheme | Reasoning |
|---|---|---|---|
| `invoices`, `invoice_items` | `created_at` | RANGE, **monthly** partitions | POS billing is the highest-volume write path. At 10,000 shops × ~100 bills/day average, that's ~1M rows/day, ~30M/month, ~365M/year. Monthly partitions keep each partition's index small enough for fast vacuum/insert and let old months be archived/compressed independently. |
| `stock_ledger` | `created_at` | RANGE, **monthly**, with `shop_id` as a secondary **HASH sub-partition (16–32 buckets)** | Every sale, restock, and adjustment writes here — write volume rivals invoices. The hash sub-partition spreads write I/O across more physical relations to reduce hot-partition contention as concurrent shops write simultaneously. |
| `audit_logs` | `created_at` | RANGE, **monthly** | Append-only, time-ordered, queried almost exclusively by date range + shop + module (matches the Audit Log Center filters exactly). At enterprise scale (12,000+ rows visible per shop in the UI mock — multiply by 10,000 shops), this table will be the platform's largest. |
| `customer_ledger_entries`, `notifications`, `delivery_status_history` | `created_at` | RANGE, **monthly or quarterly** | Same append-only, time-windowed access pattern, but at lower individual volume than the three above — monthly is sufficient; quarterly is acceptable if write volume stays modest. |
| `shop_verification_documents`, `subscription_invoices` | none | Not partitioned | Low volume (bounded by number of shops × a handful of documents/invoices each), no benefit to partitioning. |
| `shops`, `suppliers`, `medicine_master`, `roles`, `permissions`, `subscription_plans` | none | Not partitioned | Reference/master data — row counts stay in the thousands to low millions even at full platform scale. |

### 6.2 Partitioning mechanics
- Use **native PostgreSQL declarative partitioning** (`PARTITION BY RANGE`/`HASH`), not table inheritance — gets partition pruning, parallel query, and `INSERT` routing for free in modern PostgreSQL.
- **Automate partition lifecycle with `pg_partman`**: pre-create the next 2–3 months of partitions ahead of time, auto-attach indexes/constraints to each new partition, and auto-detach/archive partitions past the retention window. Manual partition management does not scale to a 10,000-tenant, multi-year-retention system.
- **Two-level partitioning** (RANGE by month → HASH by shop_id) is reserved for `stock_ledger` and, if volume requires it later, `invoices`. Two-level partitioning adds operational complexity, so it's introduced only where a single dimension isn't enough to keep partitions a manageable size.

### 6.3 Retention & archival
- **Compliance distinction is critical:** GST/financial records (`invoices`, `supplier_invoices`, `customer_ledger_entries`, `supplier_payments`) fall under Indian tax record-keeping rules and must be retrievable for **~6–8 years**, even though they're rarely queried after the first 90 days. **System/security audit logs** (`audit_logs`) are an operational/security artifact with a shorter useful life — a 1–2 year hot retention with optional cold export is reasonable, but this should be confirmed against the company's actual compliance policy before implementation.
- **Tiered storage by partition age:** 0–3 months on the primary (fast SSD) tablespace · 3 months–2 years moved to a cheaper "warm" tablespace or a read-replica-only access tier · beyond the compliance window, partitions are detached, exported to columnar cold storage (e.g., Parquet in object storage), and dropped from the live database — keeping the operational database's working set bounded regardless of how many years the platform has been running.
- This tiering is what makes 10,000+ pharmacies sustainable: without it, every table above grows unbounded and every query (even tenant-scoped ones) eventually degrades as index depth grows.

### 6.4 Growth path beyond a single primary
- A single well-tuned PostgreSQL primary can plausibly carry 10,000 pharmacies' OLTP load with the partitioning above, **provided read-heavy workloads (dashboards, analytics, audit search) are offloaded to streaming read replicas** rather than competing with POS writes on the primary.
- If/when growth requires horizontal write scaling beyond one primary, the schema is **already shaped for it**: `shop_id` as a near-universal leading column and partition key means a future migration to a distributed PostgreSQL layer (e.g., Citus, which distributes tables by a chosen key — `shop_id` is the natural choice here) would not require a data-model redesign, only an infrastructure migration. This is noted as a future option, not a current requirement.

---

## 7. Audit Architecture

### 7.1 What gets audited, and how it's captured
Two complementary capture mechanisms, used together:

1. **Application-level structured logging (primary mechanism).** Every state-changing action in the app (bill created, medicine price edited, PO modified, login, permission change) writes an explicit row to `audit_logs` as part of the same transaction as the business write. This is the mechanism for the *majority* of audit coverage because it captures **business context** a database trigger cannot see — which screen the action came from, why a discrepancy was flagged, etc.
2. **Database-trigger-based audit (safety net, on a short list of high-compliance tables only).** A small set of financially/regulatorily sensitive tables — `invoices`, `medicine_batches` (quantity adjustments), `supplier_payments`, `shop_users` (role/permission changes), `shop_verification_documents` — get a generic AFTER trigger that captures the full before/after row as JSONB into `audit_logs` regardless of which code path performed the write. This guarantees these specific tables are audited even if a future code change forgets to log explicitly, a deliberate defense-in-depth choice for the tables where missing an audit entry is a compliance failure, not just an inconvenience.

### 7.2 Audit log immutability
- `audit_logs` is **append-only by design**: the application database role is granted `INSERT` and `SELECT` only — **no `UPDATE` or `DELETE` privilege**, enforced at the GRANT level, not just by convention. This is what makes the audit trail trustworthy as evidence, not just as a debugging aid.
- Each row carries `actor_user_id` **or** `actor_admin_id` (nullable, mutually exclusive) so platform-level actions and tenant-level actions share one table and one query surface (the Enterprise Audit Log Center screen filters across both).
- `before_state`/`after_state` JSONB columns store only the changed entity's relevant fields (not a full table dump) to keep row size manageable at the volumes described in Section 6.

### 7.3 Querying the audit trail at scale
- The Audit Log Center's filters (date range, action type, module, free-text user search) map directly onto the composite index `(shop_id, module, action_type, created_at DESC)` plus the trigram index on a denormalized `actor_display_name` column (avoiding a join to `users`/`platform_admins` on every page of results).
- Export (CSV/PDF) reads are routed to a **read replica**, never the primary, since audit exports are large, slow, and must never compete with POS write throughput.

### 7.4 Tenant isolation inside the audit trail itself
- `audit_logs.shop_id` is nullable specifically so platform-level events (a platform admin reviewing a shop's verification documents) are captured without forcing a fake tenant association — but **Row-Level Security on `audit_logs` still applies**: a shop's RLS policy is `shop_id = current_shop() OR shop_id IS NULL AND actor_admin_id IS NOT NULL` is deliberately **not** granted to tenant roles — tenants only ever see rows where `shop_id` matches their own; only the platform role can see `shop_id IS NULL` platform-level events. This prevents one shop from ever seeing another shop's audit trail, or platform-internal events, through the same table.

---

## 8. ER Diagram Structure

A textual entity-relationship structure, organized by domain, showing every connection (`──` for the relationship, `1`/`N`/`M` for cardinality at each end). This is the structure a diagramming tool (dbdiagram.io, Lucidchart, pgModeler) would be fed to render the visual ERD — intentionally not rendered as code here.

```
PLATFORM SCHEMA
================
subscription_plans (1) ──── (N) shops
shops (1) ──── (N) shop_verification_documents
shops (1) ──── (1) shop_settings
shops (1) ──── (N) shop_subscriptions ──── (N) subscription_invoices
shops (1) ──── (N) shop_payment_methods
shops (1) ──── (N) shop_verification_queue ──── (1) platform_admins [reviewer]
suppliers (1) ──── (N) wholesaler_verification_queue ──── (1) platform_admins [reviewer]

TENANT SCHEMA — Identity
========================
shops (1) ──── (N) shop_users (N) ──── (1) users
shop_users (N) ──── (1) roles (N) ──── (N) permissions   [via role_permissions]
users (1) ──── (N) auth_sessions
users (1) ──── (N) shop_users [invited_by, self-referencing through users]

TENANT SCHEMA — Catalog & Inventory
====================================
medicine_categories (1) ──── (N) medicine_categories [parent_category_id, self-referencing]
medicine_categories (1) ──── (N) medicine_master
shops (1) ──── (N) shop_medicines (N) ──── (0..1) medicine_master
shop_medicines (1) ──── (N) medicine_batches
medicine_batches (1) ──── (N) stock_ledger
suppliers (1) ──── (N) medicine_batches [batch source]

TENANT SCHEMA — Procurement
============================
shops (M) ──── (N) suppliers   [via shop_supplier_relationships]
shops (1) ──── (N) purchase_orders ──── (1) suppliers
purchase_orders (1) ──── (N) purchase_order_items ──── (1) shop_medicines
purchase_orders (1) ──── (N) goods_receipts
goods_receipts (1) ──── (N) goods_receipt_items ──── (1) purchase_order_items
goods_receipt_items (1) ──── (1) medicine_batches  [confirmed receipt creates a batch]
suppliers (1) ──── (N) supplier_invoices ──── (N) supplier_payments
goods_receipts (0..1) ──── (1) supplier_invoices

TENANT SCHEMA — Sales & Customers
===================================
shops (1) ──── (N) customers
customers (0..1) ──── (N) invoices   [NULL = walk-in]
invoices (1) ──── (N) invoice_items ──── (1) shop_medicines ──── (0..1) medicine_batches
invoices (1) ──── (N) invoice_payments
shops (1) ──── (N) held_bills ──── (1) users [held_by]
customers (1) ──── (N) customer_ledger_entries

TENANT SCHEMA — Delivery
==========================
shops (1) ──── (N) riders
invoices (0..1) ──── (1) delivery_orders ──── (0..1) riders
delivery_orders (1) ──── (N) delivery_status_history

TENANT SCHEMA — Notifications
================================
shops (1) ──── (N) notifications ──── (0..1) users [recipient]
users (1) ──── (N) notification_preferences

CROSS-CUTTING — Audit
========================
shops (0..1) ──── (N) audit_logs ──── (0..1) users [actor_user_id]
audit_logs ──── (0..1) platform_admins [actor_admin_id]
(any entity_type/entity_id pair) ──── (N) audit_logs   [polymorphic reference, not a true FK —
                                                          enforced at the application layer only,
                                                          since entity_type varies]
```

**Note on the one deliberately polymorphic relationship:** `audit_logs.entity_id` does not carry a database-level foreign key, because it can point to a row in any of two dozen different tables depending on `entity_type`. This is a standard, accepted trade-off for audit tables — referential integrity here is enforced by application logic and by the fact that audit rows are never deleted when their source row is, by design (an audit trail must survive the deletion of the thing it's auditing).

---

## 9. Row-Level Security & Isolation Enforcement (ties Sections 0, 5, 7 together)

- **RLS enabled on every table in the `tenant` schema.** Policy shape (conceptually): a row is visible only if its `shop_id` equals the value of a session-scoped setting representing "the shop this connection is currently acting on behalf of."
- That session-scoped value is set once per request/transaction by the application's data-access layer immediately after authenticating which shop the current user/session is operating in (a user with memberships in multiple shops sets it explicitly per request based on which shop context they've selected in the UI).
- **The application layer still filters by `shop_id` explicitly in every query, never relying on RLS alone.** RLS is the second line of defense (protects against a forgotten `WHERE` clause or a bug in a new code path); it is not a substitute for tenant-aware query design.
- **The platform-admin connection role bypasses tenant RLS entirely** (via a dedicated role with `BYPASSRLS`, used only by platform-side services), since platform admins legitimately need cross-tenant visibility for verification and system health — this access path is logged exhaustively per Section 7.
- **Connection pooling caution:** because RLS depends on a per-request session setting, the connection pooler must either use **session-level pooling** (so the setting persists for the connection's lifetime) or set the value via `SET LOCAL` **inside the same transaction** as the query when using **transaction-level pooling** (e.g., PgBouncer in transaction mode) — this needs to be an explicit decision in the data-access layer implementation, not an afterthought, or isolation guarantees silently break under load.

---

## 10. Open Items Requiring Sign-Off Before Implementation

1. **Compliance retention window** for financial vs. audit data (Section 6.3) — needs a real number from legal/compliance, not the placeholder "6–8 years" used here.
2. **Multi-shop user model** — confirmed as designed (`shop_users` junction supports it), but the blueprint's UI never showed a shop-switcher; product needs to confirm whether multi-outlet ownership is in scope for this release.
3. **Geospatial precision for delivery tracking** — `delivery_orders.current_lat/lng` is modeled as plain `NUMERIC`; if live map tracking needs proximity queries ("riders within 2km"), this should be revisited as a PostGIS `geography` column instead, which is a schema decision worth making once rather than retrofitting.
4. **Wholesaler/rider self-service portals** (flagged as a gap in the Blueprint) — if built later, they will need their own `users`-equivalent identity tables scoped to `suppliers`/`riders` rather than reusing the shop-staff `users` table, to keep authentication realms separate. Worth deciding now so `suppliers`/`riders` aren't designed as if they'll never need their own login.
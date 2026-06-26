# MedicoSaathi — Product Blueprint
### Reverse-Engineered from UI Archive · Senior Product Architect Review

---

## 0. Methodology & Source Note

This blueprint was built by treating every screen in `stitch_medicosaathi_pharma_relationship_network.zip` as ground truth. The archive contains **23 functional screens** (HTML + screenshot), **2 ambient background effects** (`shader_1`, `shader_2` — decorative, not screens), **2 broken/empty stubs** (`inventory_management`, `fast_billing_pos_enterprise_v2` — screenshots failed to render and have no markup; treated as *not yet designed*), and **4 design-token files** (`clinical_precision_1–4/DESIGN.md`) defining two competing visual systems ("MedicoSaathi Pro" and "Clinical Precision"). A component manifest (`enterprise_component_definitions.json`) confirms a shared `EnterpriseShell` layout.

**Important upfront finding:** this archive is a *design exploration set* (note the `_v2`, `_v3`, `_v3_final` suffixes and two different product names — "MedicoSaathi" and "PharmaCore ERP / Enterprise OS" — used interchangeably across dashboard variants). It is not a single locked spec. Section 6 documents every inconsistency found so the dev team doesn't silently inherit them.

---

## 1. Product Requirements Document (PRD)

### 1.1 Product Vision
MedicoSaathi is a **multi-tenant, enterprise SaaS platform for retail pharmacies in India**, unifying four things that are normally separate tools: point-of-sale billing, inventory/batch management, wholesaler relationship & credit management, and customer relationship management — wrapped in GST-compliant invoicing and presented through a single command-driven workspace (global ⌘K / Ctrl+K search on almost every screen).

### 1.2 Target Users
- **Primary:** Independent and small-chain retail pharmacy owners in India (the "Shop").
- **Secondary:** Pharmacy staff/cashiers running day-to-day billing.
- **Tertiary:** Wholesalers/distributors/manufacturers who supply the pharmacy (read about, not yet a logged-in actor — see Section 6).
- **Platform-side:** MedicoSaathi's own internal team operating the multi-tenant platform (verification, subscriptions, system health).

### 1.3 Business Model
Evidence from `subscription_billing_screen`: a **4-tier SaaS subscription** —

| Plan | Price | Monthly Transactions | Staff Accounts | Advanced Analytics | Priority Support |
|---|---|---|---|---|---|
| Starter | ₹999/mo | 500 | 2 | ✗ | ✗ |
| Growth | ₹2,499/mo | 2,000 | 5 | ✓ | ✗ |
| Professional | ₹4,999/mo | 5,000 | 10 | ✓ | ✓ |
| Enterprise | Custom | Unlimited | Unlimited | ✓ | ✓ |

Billing supports saved cards and UPI, monthly invoice history with PDF export, and usage meters that warn when nearing plan limits ("Staff Accounts 8/10 — Nearing plan limit").

### 1.4 Inferred Goals & Success Metrics
- Reduce per-transaction billing time (POS optimized for keyboard shortcuts: F2 scan, F3 customer lookup, Enter to generate bill).
- Reduce dead stock / expiry write-offs (`Dead Stock Alert`, `Critical Expiry Alerts`, AI cold-chain/storage routing suggestions).
- Improve supplier-side working capital (early-payment discount engine, credit aging analysis).
- Improve customer retention (loyalty/repeat-purchase tracking, WhatsApp re-engagement).
- Platform-level GMV and active-shop growth (visible KPIs in `platform_admin_panel`: Total Active Shops, Verified Wholesalers, Total Platform GMV, Active Subscriptions).

### 1.5 Scope

**In scope (evidenced by screens):**
Authentication & shop onboarding · POS billing (desktop + mobile) · Inventory & batch/expiry tracking · Purchase order creation · Goods receiving (GRN) with discrepancy flagging · Supplier/wholesaler directory & relationship scoring · Supplier credit & finance management · Customer directory, ledger & loyalty profile · Delivery dispatch & rider tracking · Analytics & GST/audit reporting · Notification center · Enterprise audit log · Platform-level multi-tenant administration · Shop profile/statutory/hardware settings · Subscription & billing management · Global command palette search.

**Out of scope / not evidenced (do not assume):**
e-prescriptions, patient medical records, drug-interaction checking, a wholesaler-facing portal, a rider-facing mobile app, multi-branch/warehouse transfer, HR/staff role management, returns/refunds, or any regulatory filing automation beyond invoice generation. See Section 6 for the full list.

### 1.6 Functional Requirements by Module

**Authentication & Onboarding** (`login_authentication`)
- Email/mobile + password sign-in, "Remember me," "Forgot password," self-serve "Register Shop" link.
- Marketing panel communicates 3 core value props: Trusted Wholesaler Network, Automated GST Billing, Predictive Analytics.
- 256-bit SSL trust badge displayed at login (compliance/trust signal, not a technical requirement on its own).

**Dashboard / Home** (`shop_owner_dashboard`, `*_enterprise_v2`, `*_v3_final`, `mobile_dashboard_medicosaathi_v3`)
- KPI cards: Total Revenue (weekly, % delta), Today's Sales (amount + transaction count), Low Stock Alert count, Expiry Alert count (30-day window).
- Revenue trend chart toggle: Weekly / Monthly.
- "Smart Alerts" feed: stock-expiry warnings, reorder recommendations, supplier invoice due reminders — each with a direct action button (Review Inventory / Create Purchase Order / Pay Now).
- Recent Transactions ledger (orders in, supplier bills out) with status (Completed/Pending) and directional arrows.
- System Activity Log (order created, inventory updated, alert triggered, backup completed).
- Quick actions: New Purchase Order, Add Patient, Fast Billing.
- Mobile variant condenses to 3 KPI tiles + critical-stock banner + recent transactions + bottom tab bar (Dashboard / Inventory / Billing / More).

**Fast Billing / POS** (`fast_billing_pos_system`, `mobile_fast_billing_medicosaathi_v3`)
- Barcode scan or product search (F2), customer lookup or walk-in (F3), line-item table (batch, expiry, qty, unit price, GST%, line total).
- Auto-computed CGST/SGST split, manual discount field, live total.
- Payment modes: Cash, UPI, Card, Credit (on-account) with tendered-amount/change calculator for cash.
- Hold Bill / Recall Held Bill / Void Bill.
- GST Bill toggle (tax invoice vs non-tax estimate).
- Output: Print Receipt and/or send via WhatsApp; "Generate Bill" (Enter key shortcut).
- Mobile version adds prescription-required tagging on line items and an explicit empty-cart state.

**Global Command Center** (`global_command_center_ctrl_k`)
- App-wide ⌘K/Ctrl+K palette: recent actions, quick actions (Create PO ⌘P, New Customer ⌘N), live search across Medicines (with stock-level state), Customers (with balance), with arrow-key navigate / Enter-to-select pattern.

**Inventory Management** (`inventory_health_detail_drawer`)
- Master list: medicine name, barcode/SKU, active batch, expiry date, stock level (unit-aware: strips/bottles).
- Item detail drawer: profit margin, sales trend (6-month), full batch breakdown (multiple batches per SKU with independent expiry/cost/qty), recent stock-movement activity (restock in / POS sale out), one-click "Reorder Now."

**Procurement: Purchase Orders** (`purchase_order_creation`)
- Supplier selector showing trust score and payment terms (e.g., Net 30).
- Line items pull current stock and flag "Below Min" with a suggested reorder quantity.
- Auto subtotal/discount/GST/grand total.
- Expected delivery date picker.
- Dispatch via Email or WhatsApp, or Save Draft.

**Procurement: Goods Receiving (GRN)** (`goods_receiving_inventory_verification`)
- Pending shipments queue with status (Arrived / In Transit / Delayed) and per-PO action (Receive).
- Verification modal: per-SKU progress counter, batch number + expiry capture, quantity stepper, barcode re-scan, "Flag Discrepancy," confirm-per-item, save-as-draft or "Complete GRN."
- AI-assisted insights panel: fast-mover shelf-routing suggestions, cold-chain/temperature alerts for cold-chain SKUs (e.g., insulin).
- Daily receiving KPI: items verified vs. % of expected daily volume.

**Supplier / Wholesaler Network** (`supplier_management`, `relationship_dashboard`)
- Directory with verified badge, category (Branded/Generic/Surgicals/FMCG), relationship score /100, direct Create PO and Chat actions.
- Relationship Dashboard: tiering (Tier 1/Tier 2/Under Review), trust score, relationship tenure, cumulative procurement value, per-supplier credit-limit utilization bar.
- Supplier Performance Matrix: delivery speed, fulfillment rate, price competitiveness ($ tier).
- AI "Optimization Insight": recommends switching a SKU's sourcing supplier for better margin.
- Activity feed: tier upgrades, payments cleared, orders placed, delivery delays.

**Supplier Credit & Finance** (`wholesaler_credit_finance_center`)
- Aggregate KPIs: Total Outstanding, Total Credit Line (+ % utilized), Due in next 7 days, potential early-payment savings.
- Credit Aging Analysis bucketed 0–15 / 16–30 / 31–45 / 46–60 / 60+ days, segmented by Wholesalers vs. Manufacturers.
- Top suppliers by outstanding balance with status (Current / Due in Nd / Overdue) and "View Details."
- "Smart Payment Engine": surfaces specific invoices eligible for early-payment discount with a Pay-by date and computed savings.
- Upcoming Due Dates calendar list.
- Global "Make Payment" and "Export Report" actions.

**Customer Management** (`customer_management`, `customer_full_profile`)
- Directory KPIs: Total Active Customers, Dues Pending (₹), High-Value (30d) count.
- Segmented tabs: All / Dues Pending / High Value / Inactive (60d+).
- Table: total bills, total spent, current due, last visit, quick actions (send reminder, view).
- Quick-view side panel: current due, LTV, recent purchases with paid/due status, "Message" and "Full Profile" actions.
- Full profile: contact (call/WhatsApp), YTD spend, current due, avg order value, visit-frequency insight, top medicines purchased, recent invoices, full **debit/credit running ledger** with "Record Payment."

**Delivery Management** (`delivery_management_dashboard`)
- Live KPIs: Active Deliveries, Avg Delivery Time, Successful-Today count, Rider Availability (x/y).
- Order pipeline funnel: Pending → Assigned → Packed → Dispatched → Delivered, each with a count.
- Active dispatch table: order ID, rider (name+phone), destination, live ETA/distance, status (On Route/Picked Up/Delayed).
- Live tracking map view and a fleet roster (rider, zone, current load count).
- "New Dispatch" creation action and date filter.

**Analytics & Insights** (`analytics_insights`)
- Headline KPIs: Fast-Moving Flow %, Customer Retention %, Supplier Performance Index (/10).
- Revenue Growth chart with 12M/6M/30D range toggle.
- Top Movers leaderboard (product, category, units sold).
- Dead Stock Alert list (60+ days unsold) with batch, expiry, days-aged, ₹ value at risk, and "Review Liquidation Options."
- Export to GST Report and Internal Audit summary exports.

**Notifications** (`notification_center_alerts`)
- Categorized feed: Orders / Inventory / Payments / Supplier Updates, each item time-stamped with an inline action (Reorder Now, Track Delivery, Dismiss).
- "Mark all as read," filter chips, "Open Full Notification Center."

**Enterprise Audit Log** (`enterprise_audit_log_center`)
- Full event ledger: Event ID, timestamp, actor, module, action type (Created/Modified/Deleted/Auth), free-text detail, "Inspect" drill-in.
- Filters: date range (24h/7d/30d/custom), action type, module.
- Export CSV / Export PDF. Pagination over 12,000+ entries (enterprise-scale expectation).

**Platform Administration** (`platform_admin_panel`)
- Platform KPIs: Total Active Shops, Verified Wholesalers, Total Platform GMV, Active Subscriptions (all with month-over-month delta).
- Shop Verification Queue: pending document review (Drug License, GST) with per-shop "Review" action.
- Wholesaler Trust-Badge Verification queue: "Verify Details" for pending wholesaler IDs.
- System Health: API status, transaction success rate, DB latency.
- Active Plans breakdown by tier with user counts, "Manage."

**Shop Profile & Settings** (`shop_profile_settings_enterprise_v3`)
- Tabbed settings: Shop Identity (logo, name, tagline), Statutory Info (GSTIN — verified/unverified state, Drug License Number + expiry, "Update Documents" re-verification flow), Business Details, Operations (Billing Mode: Tax Invoice vs Estimate; Hardware: thermal printer toggle, barcode-scanner auto-focus), Preferences, Security.
- WhatsApp digital receipts toggle (marked Beta).

**Subscription & Billing** (`subscription_billing_screen`)
- Current plan card with usage meters (transactions, staff seats) and renewal date/amount.
- Saved payment methods (card, UPI) with default-method selection.
- Full plan-comparison matrix and Upgrade/Downgrade/Contact-Sales actions.
- Invoice history with per-invoice PDF download.

### 1.7 Non-Functional Requirements (inferred)
- **Regulatory:** GST-compliant invoicing (CGST/SGST split) is a hard requirement, not optional. Drug License number + expiry tracking with a re-verification workflow is a compliance gate, not just metadata.
- **Performance:** POS flow is designed for sub-second, keyboard-first operation (F2/F3/Enter) — implies optimistic UI and local-first cart state.
- **Scale:** Audit log pagination over 12,000+ rows and a 5,000-transactions/month "Professional" plan ceiling imply the data layer must handle enterprise-scale, multi-tenant query loads.
- **Security:** SSL/encryption messaging at login, 2FA referenced in an audit log entry ("Successful authentication via 2FA") — 2FA is implied as available but has no visible settings UI (gap, see Section 6).
- **Multi-tenancy:** Platform admin operates across all shops/wholesalers from one console — strict tenant data isolation required at the data layer despite a single shared application shell.
- **Localization:** Primary currency is INR (₹); GST terminology is India-specific. (Several screens leak USD — flagged as a defect in Section 6, not a requirement.)

### 1.8 Design System Notes
Two named design systems coexist in the source files: **"MedicoSaathi Pro"** (primary `#004c6e`/`#006591`, Inter typeface, 8px radius, 260px sidebar) and **"Clinical Precision"** (primary `#006591`, sharper 4px radius, monospace data fields via Inter Mono, Stripe/Linear-inspired density). Both share: fixed 260px collapsible sidebar, 1440px max content width, 8pt spacing grid, soft tonal elevation (no heavy shadows), semantic status colors (green/amber/red) for stock and payment states. **This duplication must be resolved into one canonical system before build** (see Section 6).

---

## 2. User Roles & Permissions

The archive never shows a role picker, so roles are **inferred from which screens a given actor would plausibly need and from the platform/shop split visible in the nav.** This is the area requiring the most product-team confirmation before development.

| Role | Inferred From | Primary Screens |
|---|---|---|
| **Shop Owner / Tenant Admin** | Full sidebar access incl. Admin, Settings, Subscription | All shop-side screens: Dashboard, Inventory, Billing, Customers, Suppliers, Orders, Analytics, Admin, Settings, Subscription |
| **Pharmacist / Cashier (Staff)** | Staff-account seat limits on subscription plans; POS is keyboard-optimized for high-frequency single-purpose use | Fast Billing (POS), Customer lookup, basic Inventory view |
| **Delivery Rider** | Named riders with phone numbers and live ETA appear as *data*, not as a logged-in actor anywhere | No rider-facing screen exists in this archive (gap — see Section 6) |
| **Wholesaler / Supplier** | Appears only as a managed *entity* (directory, scorecards, credit lines) from the shop's point of view | No wholesaler-facing login or portal exists in this archive (gap) |
| **Platform Super Admin** | `platform_admin_panel` — manages shops, wholesaler verification, subscription plans, system health across the entire platform | Platform Administration only |
| **Auditor / Compliance Viewer** | `enterprise_audit_log_center` is read-heavy, export-oriented, with no destructive actions visible | Audit Log Center (could be a restricted view for this role, or just Admin) |

### Suggested Permission Matrix (to be validated with stakeholders, not yet confirmed by the UI)

| Module | Shop Owner/Admin | Staff/Cashier | Platform Super Admin |
|---|---|---|---|
| Fast Billing (create/void/hold bills) | Full | Full (void may need Admin PIN) | No tenant access |
| Inventory (view) | Full | View only | No tenant access |
| Inventory (edit/add medicine, reorder) | Full | Restricted/None | No tenant access |
| Purchase Orders | Full | None (or "create draft" only) | None |
| GRN / Goods Receiving | Full | Possible (warehouse staff) | None |
| Supplier Management & Credit/Finance | Full | None | View-only (trust-badge verification) |
| Customer Management | Full | View + record payment | None |
| Delivery Management | Full | Dispatch-level only | None |
| Analytics & Reports | Full | None or summary-only | Platform-wide aggregate only |
| Audit Log | Full (own tenant) | None | Full (cross-tenant) |
| Shop Profile/Settings | Full | None | Read access for verification |
| Subscription & Billing | Full (owner-only ideally) | None | Manage plans globally |
| Platform Administration | No access | No access | Full |

**Action item:** confirm whether a distinct "Manager" tier (between Owner and Cashier) is needed — several screens (Audit Log, GRN discrepancy flagging) imply oversight actions that a cashier shouldn't have but a sole owner may not always perform personally.

---

## 3. Feature Inventory

| # | Screen / Module | Core Features | Status |
|---|---|---|---|
| 1 | Login & Authentication | Email/mobile + password login, remember me, forgot password, shop self-registration | Complete |
| 2 | Shop Owner Dashboard (v1) | Revenue/sales KPIs, low-stock & expiry alert counts | Complete |
| 3 | Shop Owner Dashboard (Enterprise v2) | + Smart Alerts feed, activity log, recent transactions ledger, quick actions | Complete |
| 4 | Shop Owner Dashboard (Enterprise v3 Final) | Same as v2, refined; branding drift to "MedicoSaathi Enterprise OS" | Complete (superset of v2 — **duplicate**, needs reconciliation) |
| 5 | Mobile Dashboard | Condensed KPIs, critical stock banner, bottom tab nav | Complete |
| 6 | Fast Billing / POS (desktop) | Barcode scan, line items, GST split, multi-mode payment, hold/recall/void | Complete |
| 7 | Fast Billing / POS (mobile) | Same flow, touch-optimized, Rx-required tagging | Complete |
| 8 | Global Command Center (⌘K) | Universal search, quick actions, keyboard nav | Complete |
| 9 | Inventory Master + Health Drawer | Batch tracking, expiry, profit margin, sales trend, reorder | Complete |
| 10 | Purchase Order Creation | Supplier select, below-min flagging, GST totals, email/WhatsApp send | Complete |
| 11 | Goods Receiving (GRN) | Shipment queue, per-SKU verification, discrepancy flagging, AI storage insight | Complete |
| 12 | Supplier Management | Directory, trust scores, direct PO/chat | Complete |
| 13 | Relationship Dashboard | Tiering, credit utilization, performance matrix, AI sourcing insight | Complete |
| 14 | Supplier Credit & Finance Center | Aging analysis, smart early-payment engine, due-date calendar | Complete |
| 15 | Customer Management (directory) | Segmentation tabs, dues tracking, quick-view drawer | Complete |
| 16 | Customer Full Profile | Ledger, loyalty insights, top medicines, invoice history | Complete |
| 17 | Delivery Management Dashboard | Pipeline funnel, live tracking, fleet roster | Complete |
| 18 | Analytics & Insights | Revenue trend, top movers, dead-stock/liquidation | Complete |
| 19 | Notification Center | Categorized real-time alerts with inline actions | Complete |
| 20 | Enterprise Audit Log Center | Full event ledger, filters, CSV/PDF export | Complete |
| 21 | Platform Admin Panel | Shop verification queue, wholesaler trust-badge review, system health, plan mgmt | Complete |
| 22 | Shop Profile & Settings | Statutory compliance, hardware config, integrations | Complete |
| 23 | Subscription & Billing | Plan usage, payment methods, plan comparison, invoices | Complete |
| 24 | "Inventory Management" (standalone) | — | **Broken stub — no markup, image failed to render. Not usable as spec.** |
| 25 | "Fast Billing POS Enterprise v2" (standalone) | — | **Broken stub — no markup, image failed to render. Not usable as spec.** |
| 26 | shader_1 / shader_2 | Decorative animated background effects (likely login/marketing backdrop) | Asset, not a screen |
| 27 | Design tokens (clinical_precision_1–4) | Two parallel design systems (color, type, spacing, elevation) | Reference only — needs consolidation |
| 28 | enterprise_component_definitions.json | Shared shell + data-table component contract | Reference only |

---

## 4. Module Hierarchy

```
MedicoSaathi Platform
│
├── 0. Public / Pre-Auth
│   └── Login & Authentication
│       └── Shop Self-Registration (linked, screen not in archive)
│
├── 1. Shop Workspace  (tenant-scoped, role-gated)
│   ├── 1.1 Dashboard
│   │   ├── KPI Overview
│   │   ├── Revenue Trend Chart
│   │   ├── Smart Alerts Feed
│   │   ├── Recent Transactions
│   │   └── Activity Log
│   │
│   ├── 1.2 Fast Billing (POS)
│   │   ├── Product/Barcode Search
│   │   ├── Customer Lookup / Walk-in
│   │   ├── Cart & Line Items
│   │   ├── Payment & Tender
│   │   └── Hold / Recall / Void
│   │
│   ├── 1.3 Inventory
│   │   ├── Medicine Master List
│   │   ├── Item Detail Drawer (batches, trend, activity)
│   │   └── Reorder Trigger → Purchase Order
│   │
│   ├── 1.4 Billing & Procurement
│   │   ├── Purchase Order Creation
│   │   └── Goods Receiving / GRN Verification
│   │
│   ├── 1.5 Suppliers
│   │   ├── Supplier Directory
│   │   ├── Relationship Dashboard (scoring, tiering)
│   │   └── Credit & Finance Center
│   │       ├── Aging Analysis
│   │       └── Smart Payment Engine
│   │
│   ├── 1.6 Customers
│   │   ├── Customer Directory (segmented)
│   │   └── Customer Full Profile
│   │       ├── Ledger & Dues
│   │       └── Loyalty Insights
│   │
│   ├── 1.7 Orders / Delivery
│   │   ├── Order Pipeline (Pending → Delivered)
│   │   ├── Live Dispatch Tracking
│   │   └── Fleet Roster
│   │
│   ├── 1.8 Analytics
│   │   ├── Revenue & Fast-Mover Reports
│   │   ├── Dead Stock / Liquidation
│   │   └── GST / Internal Audit Export
│   │
│   ├── 1.9 Notifications (global, cross-module)
│   │
│   ├── 1.10 Admin (elevated, tenant-scoped)
│   │   └── Enterprise Audit Log Center
│   │
│   ├── 1.11 Settings
│   │   ├── Shop Identity
│   │   ├── Statutory Compliance (GST, Drug License)
│   │   ├── Operations & Hardware
│   │   └── Security
│   │
│   └── 1.12 Subscription & Billing (account-level, owner-only)
│
├── 2. Cross-Cutting
│   └── Global Command Center (⌘K / Ctrl+K — search + quick actions, available everywhere)
│
└── 3. Platform Admin Workspace  (MedicoSaathi internal, cross-tenant)
    ├── 3.1 Platform KPIs (GMV, shops, wholesalers, subscriptions)
    ├── 3.2 Shop Verification Queue
    ├── 3.3 Wholesaler Trust-Badge Verification
    ├── 3.4 System Health Monitoring
    └── 3.5 Subscription Plan Management
```

---

## 5. User Workflows

### 5.1 Shop Onboarding
1. Prospective owner clicks "Register Shop" from Login.
2. Shop completes registration (screen not in archive — gap).
3. Shop submits statutory documents (Drug License, GSTIN) via Shop Profile & Settings.
4. Document lands in Platform Admin's **Shop Verification Queue**.
5. Platform Admin reviews and approves/rejects.
6. On approval, GSTIN/Drug License status flips to "Verified" in the shop's own Settings page; shop gains full operational access.

### 5.2 Daily Billing (Fast Billing / POS)
1. Cashier opens Fast Billing, scans/searches a product (F2).
2. Adds customer via mobile lookup or "New Walk-in" (F3).
3. Adjusts qty/discount inline; system computes CGST+SGST and total live.
4. Selects payment mode (Cash/UPI/Card/Credit); for Cash, enters tendered amount and sees change.
5. Optionally toggles GST Bill vs. estimate.
6. Presses Enter/"Generate Bill" → invoice created, optionally printed and/or sent via WhatsApp.
7. Transaction appears immediately in Dashboard's Recent Transactions and feeds Analytics/Customer ledger.

### 5.3 Procurement Cycle (Reorder → Receive)
1. Dashboard or Inventory flags a SKU as low-stock/critical.
2. Owner clicks "Create Purchase Order" → Purchase Order Creation screen pre-fills supplier (by trust score) and suggested quantity.
3. PO is sent via Email/WhatsApp or saved as draft.
4. When goods arrive, staff opens **GRN**, matches the PO, scans each item, confirms batch/expiry/qty, flags any discrepancy.
5. Completed GRN updates Inventory batch records and closes the PO.
6. The resulting payable appears in Supplier Credit & Finance Center's aging buckets.

### 5.4 Supplier Credit & Early-Payment Optimization
1. Finance Center surfaces invoices nearing due date and any eligible early-payment discount.
2. Owner reviews "Smart Payment Engine" recommendation ("Pay ₹450,000 before Oct 15 to save ₹9,000").
3. Owner clicks "Review & Pay" or the global "Make Payment" action.
4. Aging buckets and Total Outstanding update; activity logs in Relationship Dashboard.

### 5.5 Customer Credit Collection
1. Customer Management directory surfaces "Dues Pending" segment.
2. Owner/staff opens quick-view drawer or Full Profile.
3. Reviews ledger (debit/credit/running balance), sends a WhatsApp/call reminder, or records a payment directly against the ledger.
4. Balance recalculates; customer's "Current Due" KPI updates platform-wide (Dashboard, Directory, Profile).

### 5.6 Delivery Dispatch
1. Completed/paid order triggers "New Dispatch" creation (manual today — no auto-trigger evidenced).
2. Order enters the pipeline at "Pending," gets Assigned to a rider, then Packed, Dispatched, and finally Delivered.
3. Dispatch table and live map track ETA in real time; delays surface a "Delayed" status badge.
4. Fleet roster shows rider zone/load to help the next assignment decision.

### 5.7 Platform-Side Wholesaler Trust Verification
1. A wholesaler submits/updates verification data (submission flow not in archive).
2. Entry appears in Platform Admin's "Wholesaler Trust-Badge Verification" queue.
3. Admin clicks "Verify Details," reviews, and approves.
4. Approved wholesaler's tier/badge updates and becomes visible to all shops in their Supplier Directory (evidenced by the notification: "Apex Pharma upgraded your Trust Badge to Tier 1... Net-45 payment terms").

### 5.8 Subscription Upgrade
1. Owner opens Subscription & Billing, sees usage nearing a plan limit (e.g., staff seats 8/10).
2. Reviews Plan Comparison table.
3. Selects a higher tier or contacts Sales (Enterprise); for downgrade, explicit "Downgrade Current Plan" confirmation.
4. Payment method on file is charged; new invoice appears in Invoice History.

---

## 6. Missing Features / Gap Analysis

### 6.1 Structural / Source-File Issues (fix before design handoff)
- **Two design systems, unreconciled** ("MedicoSaathi Pro" vs. "Clinical Precision" tokens) — different radius scale (8px vs 4px), different mono-font choice, different container colors. Pick one before any component library work starts.
- **Inconsistent product branding** — most screens say "MedicoSaathi Enterprise Pharmacy," but `shop_owner_dashboard_enterprise_v2/v3_final`, `purchase_order_creation`, `goods_receiving_inventory_verification`, and `wholesaler_credit_finance_center` rebrand the shell as **"PharmaCore ERP / Enterprise OS."** Needs a single decision on product name before frontend build.
- **Inconsistent currency** — most screens correctly use ₹ (INR/GST context), but `shop_owner_dashboard_enterprise_v2`, `_v3_final`, `purchase_order_creation`, `customer_full_profile`, and `mobile_fast_billing` show **$ (USD)**. Given the GST/Drug-License/India-specific framing, this is almost certainly template leakage, not an intentional multi-currency requirement — confirm before build.
- **Duplicate dashboard variants** (`shop_owner_dashboard`, `_enterprise_v2`, `_enterprise_v3_final`) — three iterations of the same screen exist with no marked "final." Product owner must designate the canonical version (this blueprint treats `v3_final` as most complete, but confirm).
- **Two broken/empty screens** (`inventory_management`, `fast_billing_pos_enterprise_v2`) contain no usable design — they are not specs and should not be treated as a second "Inventory" or "Billing" module; the working versions are `inventory_health_detail_drawer` and `fast_billing_pos_system`.
- **Sidebar item set is not consistent** across screens — most show 8 items (Dashboard, Inventory, Billing, Customers, Suppliers, Orders, Analytics, Settings); some add Admin/Audit Logs/Delivery (`shop_profile_settings_enterprise_v3`, `mobile_fast_billing_v3`, `notification_center_alerts`). A single canonical nav (Section 4) needs sign-off.

### 6.2 Missing Actors / Portals
- **No wholesaler/supplier-facing login or portal.** Suppliers exist only as records managed *by* the shop. If wholesalers are meant to confirm POs, update their own catalog/pricing, or see their own trust score, that entire portal is undesigned.
- **No rider-facing app/screen.** Riders are named entities with phone numbers in the Delivery dashboard, but there's no interface for a rider to accept a dispatch, update status, or navigate — this is a likely separate mobile app that doesn't exist in this archive.
- **No distinct "Manager" or "Pharmacist-in-charge" role surfaced**, despite pharmacy regulation in India typically requiring a Registered Pharmacist sign-off — relevant for Rx-required items (mobile POS shows "Prescription Required" tags but no pharmacist-verification step before sale).

### 6.3 Missing Functional Areas
- **No prescription (Rx) capture/management** — the mobile POS tags an item "Prescription Required" but there's no Rx upload, scan, or pharmacist-verification screen anywhere in the archive.
- **No returns/refunds/exchange workflow** for either customer sales or supplier goods (GRN handles incoming discrepancies, but not post-sale returns).
- **No multi-branch/multi-location support** — every screen assumes a single shop; chains with multiple outlets have no location switcher, no inter-branch stock transfer.
- **No staff/HR management screen** — subscription plans meter "Staff Accounts," but there is no add/edit/remove-staff or role-assignment UI anywhere.
- **No 2FA setup/management UI** — referenced in an audit log entry ("Successful authentication via 2FA") but no corresponding settings screen exists.
- **No data export/backup self-service** beyond Audit Log CSV/PDF — no full data export, no GDPR/data-portability equivalent, despite "Daily Backup Completed" being logged automatically.
- **No drug-interaction or dosage-safety checking** at the point of sale, despite handling prescription medicines.
- **No in-app messaging/chat history** — "chat" and "Message" buttons appear on Supplier and Customer screens, but no chat thread/inbox screen exists to view that conversation.
- **No tax-filing/GST-return submission integration** — Analytics offers a GST Report *export*, but no in-app filing or accountant hand-off flow.
- **No terms of service, privacy policy, or legal/consent screens** — required for a regulated healthcare-adjacent SaaS product in India (and for Drug License compliance generally).
- **No offline-mode handling** for POS, despite pharmacies often having unreliable connectivity — no indication of local caching/sync behavior.
- **No multi-language/localization toggle**, despite targeting Indian pharmacies where regional language support is commonly expected.
- **No accessibility (WCAG) considerations** are visible or specified in the design tokens.

### 6.4 Recommendation
Before development starts, the product team should: (1) pick one design system and one product name, (2) confirm currency is INR-only, (3) designate canonical screens among the duplicates, (4) make an explicit decision on whether a wholesaler portal and/or rider app are in scope for this release or a future one, and (5) decide how prescription verification and staff/role management — both regulatory-adjacent gaps — will be handled, since they affect core data models (Sales, Inventory, User) that are expensive to retrofit later.

---

*This blueprint is derived entirely from the supplied UI archive. No code has been generated. Recommended next step: validate Sections 2 and 6 with the product owner before any schema or component work begins.*
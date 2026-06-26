# MedicoSaathi — Engineering Constitution
### Phase 7 · The Permanent Engineering Handbook

**Status: Binding.** This document governs how MedicoSaathi is built, by everyone, forever — current team and every future hire. It does not redesign Phases 1–6; it exists to make sure what those phases approved gets built correctly, consistently, and durably. Where this Constitution and a prior phase document appear to conflict, the prior phase document wins on **what** to build; this Constitution wins on **how**.

Every engineer joining MedicoSaathi reads this document before writing a first line of code. Every PR is reviewable against it. Every exception to it requires a named, written, time-boxed waiver from the CTO — "we were in a hurry" is never a standing exception.

---

## 1. Engineering Principles

1. **The five frozen documents are the source of truth, not the codebase.** If code and the Blueprint/DB Architecture/Backend Architecture/API Architecture/Roadmap disagree, the code is wrong until a formal phase-revision process (not a PR) changes the document first. Architecture drifts when engineers "improve" things ad hoc; this rule exists to prevent that.
2. **Tenant isolation is the one mistake MedicoSaathi cannot survive.** Every engineering decision — from index design to caching to a one-line bug fix — is evaluated first against "could this leak Shop A's data to Shop B," before any other quality concern. This is not paranoia; it is proportionate to the architecture's own stated risk (DB Arch §9).
3. **Boring and explicit beats clever and implicit.** A junior engineer six months from now, who has never met the original author, must be able to read a service method and understand what it does without reverse-engineering intent. Cleverness is a cost paid by every future reader.
4. **Four layers, no shortcuts.** API → Service → Repository → Model, exactly as Backend Architecture §1 defines. An API handler that queries the database directly, or a service that returns an ORM model straight to a client, is a bug regardless of whether it "works."
5. **Every write path assumes it will be audited, retried, and read by someone debugging a production incident at 2 a.m.** Idempotency, structured logging, and traceability are not nice-to-haves bolted on later — they are written in on the first pass.
6. **Performance and security are requirements, not optimizations.** The API Architecture's response-time targets (§12) and the security posture (§11, §6.5) are part of "done," not a follow-up ticket.
7. **Scale to 10,000 pharmacies is assumed from day one of every feature**, even the first one. A query that works fine against ten test shops and falls over against ten thousand is not a future problem — it's a design defect found late.
8. **Consistency across the codebase outranks individual preference.** One way to name a route, one way to structure a service, one way to write a commit message — argued and settled once in this document, not re-litigated per PR.
9. **No module ships without its tests, no exceptions, including hotfixes.** A hotfix without a regression test is just a guarantee that the same bug returns.
10. **Documentation is part of the deliverable, not an artifact written after the fact if there's time.** A merged PR that changes behavior without updating the relevant doc is incomplete, full stop.

---

## 2. Coding Standards

### 2.1 Python (Flask / SQLAlchemy backend)
- **Style:** PEP 8, enforced by an automated formatter and linter in CI (not by review comments) — a PR is never blocked on a formatting nit a tool should have caught, and is never merged if the tool fails.
- **Type hints are mandatory** on every function signature in `services/`, `repositories/`, and `schemas/` — this is the layer where contracts matter most and where a wrong type causes the most expensive class of bug (silent data corruption, not a crash).
- **No bare `except:`** — every caught exception is either a named domain exception (Backend Architecture's `utils/exceptions.py` hierarchy) or re-raised. Swallowing an unexpected exception silently is forbidden.
- **No business logic in route handlers.** A handler's job is: parse/validate request → call exactly one service method → serialize response. If a handler has an `if`/`for` doing anything domain-meaningful, that logic belongs in the service layer.
- **No business logic in models.** Models (`models/`) are schema-shape only — columns, relationships, simple computed properties at most. Anything resembling a business rule belongs in `services/`.
- **Functions are small and named for what they do, not how.** `calculate_cgst_sgst_split()`, not `process_tax_stuff()`.
- **No magic numbers/strings for status values, roles, or permissions** — these are always looked up from the lookup tables (DB Arch §0) or imported from a single constants module that mirrors them, never hardcoded inline.

### 2.2 JavaScript (vanilla JS frontend)
- **No inline `<script>` business logic in HTML templates** — all JS lives in module files, one per screen/component, matching the Backend Architecture's API module boundaries.
- **`const`/`let`, never `var`.** Strict equality (`===`) always.
- **No silent failures on `fetch()` calls** — every API call has explicit success and error handling that maps the API Architecture's error envelope (API Arch §2.2) to a user-visible state, never a console-only failure.
- **DOM manipulation is isolated from data-fetching logic** — a module's "get data from the API" function and "render data into the DOM" function are separate, testable units, never interleaved in one callback.
- **Keyboard-shortcut handling (POS F2/F3/Enter) is centralized in one input-handling module per screen**, not scattered `addEventListener` calls across multiple files — this is the single highest-risk-of-regression interaction pattern in the product (Blueprint §1.7's sub-second NFR) and deserves one obvious place to look.

### 2.3 SQL / SQLAlchemy
- **No raw SQL string concatenation, ever** — parameterized queries or the ORM only. This is non-negotiable even for "just a quick admin script."
- **No N+1 query patterns** — eager-loading (`joinedload`/`selectinload`) is the default mindset for any list endpoint that includes related data; a PR introducing a list endpoint must show the query count is bounded, not proportional to result-set size.
- **Every query in a repository method states, in a comment or docstring, which index it expects to use** for any query against a table with more than one composite index option — this is cheap insurance against a future schema change silently degrading a hot path.

### 2.4 General
- **No commented-out code merged to main.** Delete it; Git history is the archive, not the source file.
- **No `TODO` without an attached ticket number.** An untracked TODO is a promise nobody owns.
- **Configuration, not hardcoding** — environment-specific values (URLs, limits, feature flags) live in config, never inline, per Backend Architecture's `config.py` pattern.

---

## 3. Project Folder Structure Rules

The folder structure is **Backend Architecture §1, frozen.** This section states the *rules of discipline* around it, not a new structure.

1. **No new top-level folder under `app/` without an Architecture Decision Record (ADR, see Section 18) and CTO sign-off.** The structure was designed to mirror the Database Architecture's domains exactly — an undisciplined new folder breaks that traceability.
2. **A new feature module gets a folder in `api/v1/`, `services/`, `repositories/`, and `models/` — in that same name, every time.** If a feature doesn't cleanly map to all four, that's a signal the feature needs an architecture review before code, not a workaround.
3. **`utils/` is for true cross-cutting helpers only** (pagination, GST math, caching key-builders, exceptions). A function used by exactly one service does not belong in `utils/` — it belongs in that service module.
4. **`integrations/` contains zero business logic** — adapters only (send this payload, get that response). Any retry/business-rule logic around a third-party call lives in the calling service, not the adapter.
5. **Tests mirror the source tree 1:1** — `tests/unit/services/billing_service_test.py` for `app/services/billing_service.py`, no exceptions, so coverage gaps are visually obvious from the tree alone.
6. **Nothing is written directly into `/mnt`-equivalent read-only or generated directories** (migrations output, build artifacts) by hand — these are tool-generated and reviewed as generated output, never hand-edited post-generation.

---

## 4. Naming Conventions

Restating and binding **API Architecture §10's** conventions as the company-wide standard, extended to the parts of the codebase the API document didn't cover:

| Context | Convention | Example |
|---|---|---|
| URL paths | kebab-case, plural nouns | `/purchase-orders` |
| Query params, JSON fields | snake_case | `page_size`, `created_at` |
| Python modules, functions, variables | snake_case | `calculate_cgst_sgst_split` |
| Python classes | PascalCase | `BillingService`, `PlanLimitExceeded` |
| SQLAlchemy model classes | PascalCase, singular | `Invoice`, `ShopMedicine` |
| Database tables | snake_case, plural — **already fixed by DB Architecture, never renamed** | `invoices`, `shop_medicines` |
| Celery task names | snake_case, verb-first, module-prefixed | `alerting_jobs.scan_low_stock` |
| JS modules/files | kebab-case filenames, camelCase identifiers inside | `pos-cart.js` exporting `calculateLineTotal()` |
| Branch names | see Section 10 | |
| Environment variables | SCREAMING_SNAKE_CASE | `DATABASE_URL`, `JWT_SIGNING_KEY` |
| Redis cache keys | colon-delimited, matching Backend Architecture §8's shapes exactly | `dash:{shop_id}:{date_bucket}` |
| Domain exceptions | PascalCase, name states the failure, not the layer | `CreditLimitExceeded`, not `SupplierError` |

**Rule of thumb:** if a name needs a comment to explain what it means, the name is wrong. Rename it instead of commenting it.

---

## 5. Database Development Standards

The schema itself is frozen (Database Architecture, Phase 3). This section governs how engineers **work with** that frozen schema.

1. **No engineer adds, renames, or removes a column/table outside the formal migration-and-architecture-revision process.** A "small" schema tweak still requires updating the Database Architecture document first — the document is not allowed to drift out of sync with reality, in either direction.
2. **Every migration is reviewed for its `RLS` and index implications**, not just its column correctness — does the new column need an index per the access pattern it serves? Does it touch a table with RLS policies that need updating? This is a mandatory review checklist item (Section 13), not assumed.
3. **No migration runs directly against Production by hand.** Migrations run through the deployment pipeline only, in the same order they were authored, with a tested rollback path (or an explicit, documented forward-only justification — e.g., a partition-related change that cannot safely reverse).
4. **`shop_id`-leading composite indexes are the default assumption for any new tenant-table query pattern** — a new repository method querying a tenant table without `shop_id` as the leading filter requires explicit justification in the PR description, not silent omission.
5. **No engineer queries a partitioned table (`invoices`, `stock_ledger`, `audit_logs`, etc.) without a `created_at` bound in the query**, except through the explicitly designed cursor-pagination/export paths — an unbounded query against a partitioned table defeats the entire point of partitioning.
6. **Append-only tables stay append-only in code, not just in DB grants.** A repository method for `audit_logs`, `stock_ledger`, `customer_ledger_entries`, or `invoices` literally does not have an `update()`/`delete()` method defined — this is enforced by the repository's own interface, not left to developer discipline alone.
7. **All new queries are EXPLAIN-checked against a representative-scale dataset before merge** for any endpoint expected to be high-traffic (POS, dashboard, search) — "it's fast on my laptop with 50 rows" is not evidence.
8. **Read-replica routing (Backend Architecture §4, API Architecture §12.3) is an explicit per-repository-method decision, documented in the method's docstring**, never left ambiguous for the next engineer to guess at.

---

## 6. API Development Standards

The contract is frozen (API Architecture, Phase 5). This section governs implementation discipline against that frozen contract.

1. **No endpoint ships that isn't already specified in API Architecture §1.** A developer who finds they "need" a new endpoint mid-implementation stops and raises it as an architecture question, not a quiet addition.
2. **Every endpoint's response is validated in CI against its documented contract shape** (API Arch §2) before merge — schema drift is caught by a tool, never discovered by a client integration breaking in production.
3. **Error codes are never invented ad hoc.** A new failure mode maps to an existing code in API Architecture §11, or the engineer raises a documented proposal to add a new one to that document first — `error.code` is a versioned public contract, not a free-text field.
4. **Pagination mode (offset vs. cursor) is fixed per endpoint by API Architecture §5 and never changed without a version bump.** An engineer does not "simplify" a cursor-paginated endpoint to offset because it's easier to implement against — that defeats the exact problem cursor pagination was chosen to solve.
5. **Every list endpoint enforces the maximum page size (100) at the schema-validation layer, not the service layer** — a malformed request asking for 10,000 rows is rejected before it costs a database round trip.
6. **RBAC permission requirements declared on a route are never modified without updating the corresponding row in the Blueprint's permission matrix understanding** — a route quietly becoming more permissive than its documented permission is a security regression, not a feature.
7. **No endpoint bypasses the four-stage authorization pipeline** (API Arch §4.1) for convenience, including internal/admin tooling endpoints — if an endpoint genuinely needs different rules, it is built under the explicitly separate platform-admin surface, never as an exception bolted onto the tenant pipeline.

---

## 7. Frontend Development Standards

1. **One module per screen, matching the Blueprint's screen inventory** (Blueprint §3) — the frontend file structure should be readable as a checklist against that inventory.
2. **All API calls go through a single shared request wrapper** that automatically attaches the auth token, handles the standard error envelope (API Arch §2.2), and triggers token refresh (API Arch §3.3) transparently on a `401 TOKEN_EXPIRED` — no screen module hand-rolls its own fetch/error logic.
3. **No screen renders data it fetched without first checking `success: false`** — every render path has a corresponding error-state render path, because the API contract guarantees an error envelope, and the frontend must honor that guarantee everywhere, not just on the "happy path" screens.
4. **Forms surface validation errors field-by-field**, mapped directly from the `details.fields` array (API Arch §2.3) onto the corresponding input — never a single generic "something went wrong" banner when the API already told you exactly which field failed.
5. **Mobile and desktop variants are separate templates/modules sharing the same API calls**, never one bloated responsive template trying to be both — the Blueprint itself documents them as genuinely different UI surfaces (condensed KPIs, bottom tab bar vs. full sidebar), and the code should reflect that honestly.
6. **No client-side business logic duplicates a server-side rule.** GST calculation preview, plan-limit warnings, etc. are always confirmed server-side before commit — any client-side version exists purely for instant UI feedback and is explicitly documented as "preview only, not authoritative."
7. **Accessibility is a checklist item, not an afterthought**, even though it's flagged as a current gap (Blueprint §6.3) — new screens built from this point forward should not deepen that gap; this Constitution does not wait for a separate accessibility initiative to start doing the basics right (semantic HTML, label associations, keyboard navigability) on every new screen.

---

## 8. Backend Development Standards

1. **A service method does exactly one business transaction's worth of work**, and if it touches more than one repository, it owns the transaction boundary (commit/rollback) — partial-failure states (e.g., a GRN that creates a batch but fails to close the PO) are treated as bugs, not edge cases to "handle later."
2. **No service calls another module's repository directly.** `billing_service` needing to check inventory calls `inventory_service`, not `catalog/batch_repository` — this is what keeps the service layer as the single place business rules live, per Backend Architecture §3's explicit cross-domain-read table.
3. **Every metered action (Section 3 of Backend Architecture) checks plan limits before committing the write**, never after, and never optimistically with a "we'll reconcile later" approach — `PlanLimitExceeded` is a hard gate, not a soft warning.
4. **Background jobs are idempotent by construction** (Backend Architecture §9's stated rule) — every job's first action, conceptually, is "have I already done this for this key," not "do the work and hope it doesn't double-fire."
5. **No synchronous external call (WhatsApp, SMS, payment gateway, print) in the request/response path of a user-facing endpoint** — these are dispatched to Celery, full stop, matching Backend Architecture §9.2 exactly. A "just this once, it's quick" synchronous integration call is the most common way a fast endpoint quietly becomes a slow one.
6. **Caching is cache-aside only** (Backend Architecture §8) — no write-through caching is introduced without an explicit architecture review, since it changes the failure-mode story (a failed cache write must never be allowed to fail the underlying business write).

---

## 9. Git Workflow

1. **`main` is always production-deployable.** No broken or half-finished feature ever sits on `main` behind anything less than a tested feature flag if it must merge before fully ready.
2. **All work happens on a branch, off the latest `main` (or `develop`, per Section 10), never directly committed to `main`.**
3. **Every branch maps to exactly one ticket** (feature, bug, chore) — no branch silently bundles two unrelated changes, even small ones; reviewers cannot meaningfully review a bundle.
4. **Rebase, don't merge, when bringing a feature branch up to date with the base branch** — keeps history linear and bisectable, which matters enormously when chasing down a regression at 10,000-tenant scale where "which exact commit introduced this" needs to be answerable fast.
5. **Squash-merge into the base branch on PR approval** — one feature, one commit in `main`'s history, full detail preserved in the PR itself.
6. **No force-push to any shared branch** (`main`, `develop`, `release/*`) — ever, by anyone, including the CTO.

---

## 10. Branching Strategy

A trunk-based-with-release-branches model, matched to the phased roadmap (Phase 6) rather than a generic Gitflow:

| Branch type | Naming | Lifetime | Purpose |
|---|---|---|---|
| `main` | — | permanent | Always production-deployable; tagged at every Production release |
| `develop` | — | permanent | Integration branch where sprint work lands before a release cut |
| `feature/{ticket-id}-{short-description}` | e.g. `feature/MS-214-grn-discrepancy-flagging` | one sprint or less | One feature/module slice, off `develop` |
| `fix/{ticket-id}-{short-description}` | e.g. `fix/MS-301-invoice-void-race` | days | Non-urgent bug fix, off `develop` |
| `hotfix/{ticket-id}-{short-description}` | e.g. `hotfix/MS-310-tenant-leak-patch` | hours | Urgent production fix, branched from `main`, merged to **both** `main` and `develop` immediately, never left to drift |
| `release/{version}` | e.g. `release/1.0.0` | duration of a release-stabilization window (Section 9's Alpha/Beta/GA cadence) | Cut from `develop` when a milestone (Phase 6 §5/§9) is feature-complete; only fixes land here, no new feature work |

**Rule:** a `hotfix` branch existing at all is itself a signal worth a postmortem — it means something reached `main` that shouldn't have, and the question "which test layer should have caught this" (Phase 6 §11.1's defect-escape-rate KPI) gets asked every time, not just shrugged off because the fix landed fast.

---

## 11. Commit Message Standards

Format (Conventional-Commits-style, binding):

```
<type>(<scope>): <short summary, imperative mood, no trailing period>

<optional body: what changed and why, not how — the diff already shows how>

<optional footer: ticket reference, breaking-change note>
```

**Types:** `feat`, `fix`, `refactor`, `perf`, `test`, `docs`, `chore`, `security`.
**Scope:** the module name, matching the folder structure (Section 3) — e.g., `billing`, `procurement`, `audit`, `auth`.

**Examples (style, not literal required content):**
- `feat(procurement): add discrepancy flagging to GRN item verification`
- `fix(billing): prevent double stock decrement on concurrent void`
- `security(auth): rotate refresh token on every use to prevent replay`

**Rules:**
- Imperative mood ("add", not "added" or "adds") — a commit message describes what applying it does.
- Every commit touching a financial, audit, or auth code path includes a ticket reference in the footer, no exceptions, since these are exactly the paths that need fast forensic traceability later.
- No commit message is ever just `"fix"`, `"wip"`, or `"updates"` — if squash-merging per Section 9, intermediate messy commits on a feature branch are acceptable, but the **final squashed message** must meet this standard.

---

## 12. Pull Request Rules

1. **No PR without a linked ticket.** The ticket states the *what and why*; the PR states the *how*.
2. **No PR larger than a reviewer can meaningfully hold in their head in one sitting.** If a feature is large, it ships as a sequence of smaller, individually reviewable PRs behind a feature flag, not one 2,000-line review.
3. **Every PR description states:** what changed, why, which tests were added/updated, and — for anything touching a tenant table, an auth/RBAC path, or a financial calculation — an explicit one-line statement of how tenant isolation and/or the relevant business rule was verified.
4. **CI must be fully green before review begins**, not just before merge — a reviewer's time is not spent waiting on or excusing a known-red pipeline.
5. **No PR merges with unresolved review comments**, even "minor" ones — either addressed in code or explicitly resolved with a stated reason in the thread.
6. **At least one approval from someone who did not write the code**, always — even for a one-line hotfix, even from the CTO. Self-approval is disabled at the tooling level, not just by policy.
7. **A PR touching the database (migration), the API contract, or the auth/RBAC pipeline requires a second, senior-engineer-or-CTO approval** beyond the standard one — these are the three blast-radius categories called out repeatedly across Phases 3–5, and review rigor should match that.

---

## 13. Code Review Checklist

Every reviewer checks, in order:

1. **Does this match the frozen architecture** (Blueprint/DB/Backend/API docs)? Anything that deviates gets flagged before anything else, since style nits are pointless on code that shouldn't exist in this shape at all.
2. **Tenant isolation** — does every new query filter by `shop_id` (or correctly belong to the explicitly cross-tenant platform-admin path)? Is there a multi-tenant test covering it?
3. **Layer discipline** — is business logic only in the service layer? Are repositories the only thing touching the DB? Are models free of business logic?
4. **RBAC** — does the new/changed route declare the correct `(module, action)` permission? Does it match Blueprint §2's permission matrix intent?
5. **Error handling** — does every failure path map to a documented API Architecture §11 error code? Is nothing swallowed silently?
6. **Tests** — unit tests for new service logic, integration tests for new/changed endpoints, and (per Section 5.6) a multi-tenant isolation test if a tenant table is touched. Does coverage hold or improve?
7. **Performance** — any new query checked for index usage? Any new endpoint estimated against its API Architecture §12.1 response-time target? Any N+1 risk?
8. **Security** — any new input validated? Any new file upload checked against its type/size policy (API Arch §7.2)? Any new external call appropriately async (Section 8.5)?
9. **Naming and structure** — does this follow Sections 3 and 4 without exception?
10. **Documentation** — does this change require updating an API doc, a README, or an inline docstring, and was that update included in the same PR?

A reviewer who approves a PR without having actually walked this list is, in effect, vouching for it unread — this checklist is the minimum bar for an honest approval, not a suggestion.

---

## 14. Security Standards

1. **Tenant isolation is verified, never assumed**, on every PR per Section 13.2 — this is restated here because it is the single standard this Constitution treats as load-bearing above all others.
2. **No secret, credential, or API key is ever committed to source control**, in any branch, at any time, including "temporarily for testing" — a leaked secret is rotated immediately, not just removed from the latest commit (Git history retains it).
3. **All input is validated at the schema layer before it reaches a service** — no service trusts its caller, even internal callers, to have already validated.
4. **All output to a client is the documented API envelope, never a raw exception message, stack trace, or internal identifier leak** (API Arch §2.2).
5. **Authentication tokens are short-lived, refresh tokens are rotated on use, and password resets revoke all existing sessions** — exactly as designed in API Architecture §3, restated here as a non-negotiable, not an implementation detail open to "simplification."
6. **Platform-admin and tenant auth realms never share code paths, secrets, or session storage**, enforced at the architecture level (Backend Architecture §5) and re-verified at every security review (Phase 6 §6.5).
7. **Every dependency addition is checked against known CVEs before merge**, and the dependency list is re-scanned on a recurring schedule, not just at major releases.
8. **Rate limiting is never disabled "for testing" in a shared environment** — testing happens against environment-appropriate limits, not by turning protection off.
9. **All file uploads are validated server-side against type and size policy** (API Arch §7.2), regardless of what the client claims about the file — client-side validation is a UX nicety, never the actual security boundary.
10. **Any security finding, however minor, gets a ticket and a fix timeline** — there is no informal "we'll get to it" for security issues; severity determines urgency, not convenience.

---

## 15. Performance Standards

1. **Every new endpoint is built against its API Architecture §12.1 response-time target from the start**, not optimized after the fact — performance is a design input, not a bug-fix category.
2. **No list endpoint ships without pagination** (Section 6.5/Section 4), and no endpoint accepts an unbounded result-set request.
3. **Caching decisions follow Backend Architecture §8's table exactly** — no engineer adds a new cache without documenting its key shape, TTL, and invalidation trigger in that same pattern, and no engineer caches financial/audit data, full stop.
4. **Every query against a high-volume table is checked for index usage before merge** (Section 5.7) — "it'll be fine at our current data volume" is rejected; the standard is 10,000-pharmacy scale, always.
5. **Read-replica routing is applied per Backend Architecture §4/§10.2 and API Architecture §12.3's rules**, and any deviation (e.g., a report endpoint that must read primary for freshness) is explicitly justified in code comments and the PR description.
6. **No synchronous third-party call sits in a user-facing request path** (Section 8.5) — this is a performance standard as much as an architecture one, since one slow external API is the most common cause of a fast endpoint becoming a slow one.
7. **Load testing is part of the Definition of Done (Section 19) for any module flagged as high-traffic** in the Backend/API Architecture documents (Billing/POS, Dashboard, Search), not deferred entirely to the Phase 6 Hardening sprints.

---

## 16. Logging Standards

1. **Every log line is structured (key-value/JSON), never a free-text string interpolation**, so logs are queryable, not just greppable.
2. **Every request-scoped log line carries the `request_id`** from API Architecture §2.1's `meta.request_id`, threaded through the entire call chain — app, service, repository, Celery job — so one ID traces one user action end to end across every system component.
3. **Log levels are meaningful and consistent:** `ERROR` for something that needs human attention, `WARNING` for a degraded-but-handled condition (e.g., a plan-limit near miss), `INFO` for significant business events (invoice created, GRN completed), `DEBUG` for anything else — and `DEBUG` is never enabled in Production by default.
4. **No PII or financial detail is logged in plaintext below the level needed for legitimate audit/debugging** — a customer's phone number or an exact invoice amount in a `DEBUG` log line is a standing risk; log identifiers (IDs), not raw sensitive values, wherever an ID is sufficient to look the rest up.
5. **Every caught-and-handled domain exception logs at `WARNING` with enough context to reproduce it** (which tenant, which entity, which rule failed) — silently catching and continuing without a log line is forbidden, since it turns a real signal into invisible noise.
6. **Audit logging (`audit_logs` writes) is never conflated with application logging** — they serve different purposes (compliance evidence vs. operational debugging) and live in different systems with different retention/immutability guarantees, per Database Architecture §7. An engineer does not "just write it to the app log too, for convenience."

---

## 17. Testing Standards

Builds directly on Phase 6 §6 — this section states the **standing, permanent rule**, not the one-time roadmap activity.

1. **No PR merges without tests for the behavior it adds or changes** — this is enforced by CI coverage gates per module, not by reviewer goodwill.
2. **Every endpoint touching a tenant table has a multi-tenant isolation test as a hard requirement**, not an optional "nice to have" — CI fails the build if a new tenant-table endpoint lacks one (Section 6.2 of Phase 6, made permanent here).
3. **Every business rule (plan limits, credit limits, GST math, RBAC permission checks) has an explicit pass/fail test pair** — one test proving the rule allows the valid case, one proving it correctly rejects the invalid case with the documented error code.
4. **Contract tests run on every PR touching an endpoint**, validating against the frozen API Architecture shapes — this is what keeps Section 6 of this document (API standards) actually enforced over time, not just at initial build.
5. **Flaky tests are a P1 bug, not background noise.** A test that intermittently fails is fixed or quarantined-with-a-ticket immediately — a culture that "just reruns CI" on flake erodes the entire safety net this section depends on.
6. **Performance regression tests exist for every endpoint named in API Architecture §12.1's table**, run on a recurring schedule (not just once at launch) so a slow regression is caught by CI, not by a user complaint.
7. **UAT findings (Phase 6 §6.7) are fed back into the permanent automated test suite** before being marked resolved — a bug a pilot pharmacy found and engineering fixed, without a regression test added, is a bug that can recur.

---

## 18. Documentation Standards

1. **Architecture Decision Records (ADRs)** are written for any decision that changes or extends something the frozen Phase 1–6 documents established — a short, dated, named-author record of what was decided and why, stored alongside the code, never just discussed verbally and lost.
2. **Every service module has a module-level docstring** stating its responsibility in one paragraph, matching its entry in Backend Architecture §3's table — if the docstring and that table diverge, one of them is wrong and must be reconciled.
3. **Every repository method's docstring states which index it relies on and whether it targets primary or replica** (Sections 5.8, 5.7) — this is the living, code-adjacent counterpart to the Database Architecture document, not a duplicate of it.
4. **API documentation is generated from the same schema definitions used for contract testing** (Section 6.2) — hand-maintained API docs that can silently drift from the real contract are not acceptable at this scale.
5. **Every README at the project root and per top-level module** states: what this module does, how to run its tests, and which Phase document governs its design — a new engineer should be productive within a day using only these, not a verbal handoff.
6. **Runbooks exist for every Celery job category and every on-call alert** (Phase 6 §8.4) — "what does this alert mean and what do I do" is documented before the alert is allowed to fire in Production, not written reactively during the first incident.
7. **Documentation updates are part of the same PR as the code change they describe** — a separate "update the docs" ticket filed for later is, in practice, a docs update that never happens.

---

## 19. Definition of Done (DoD)

A feature, endpoint, or module is **Done** only when **all** of the following are true — not most, not "the important ones":

- [ ] Implementation matches the frozen architecture exactly (Blueprint/DB/Backend/API) — no undocumented deviation.
- [ ] Unit tests written and passing (Section 17.1).
- [ ] Integration tests written and passing, including the mandatory multi-tenant isolation test if applicable (Section 17.2).
- [ ] Contract tests passing against the frozen API shape (Section 17.4).
- [ ] Code reviewed and approved per Section 12/13's full checklist, including the second senior approval if the PR touches DB/API contract/auth.
- [ ] Performance validated against the relevant API Architecture §12.1 target, for anything in a high-traffic module.
- [ ] Security checklist (Section 14) walked and clean for anything touching auth, RBAC, file upload, or external input.
- [ ] Logging in place per Section 16, with `request_id` correlation confirmed.
- [ ] Documentation (module docstring, README, API doc generation, runbook if applicable) updated in the same PR.
- [ ] No open `TODO` without a linked ticket (Section 2.4).
- [ ] CI fully green, including the formatter/linter, on the final commit before merge.
- [ ] Deployed and smoke-tested in Staging before being considered eligible for a Production release train.

A feature that is "done except for tests" or "done except for docs" is **not done** — it is in progress, and is described that way in standups and tickets, not marked complete.

---

## 20. Non-Negotiable Engineering Rules

These are the rules that override convenience, deadline pressure, and individual judgment calls, without exception, for every engineer including the CTO:

1. **No code merges to `main` without passing CI and at least one independent review.** No "I'll just push this small fix directly" — ever.
2. **No query against a tenant table ships without `shop_id` scoping**, verified by a test, no matter how internal, low-risk, or "obviously fine" the change seems.
3. **No secret is ever committed to source control.** A leaked secret is rotated immediately upon discovery, full stop, regardless of how it happened.
4. **No append-only table (`invoices`, `stock_ledger`, `audit_logs`, `customer_ledger_entries`) is ever given an UPDATE or DELETE code path**, at any layer, for any reason — corrections are new, offsetting entries, always.
5. **No platform-admin code path is ever reachable from a tenant-authenticated token, and no tenant code path is ever reachable from a platform-admin token.** This boundary is tested, not assumed.
6. **No business rule (plan limits, credit limits, RBAC permissions) is enforced only on the client.** The server is always the authority; client-side checks are UX convenience only, restated from Section 7.6 because it is genuinely this important.
7. **No synchronous external (third-party) call blocks a user-facing request.** It goes through Celery, no exceptions, including "just this once, it's a quick call."
8. **No schema change ships without updating the Database Architecture document first**, and no API contract change ships without updating the API Architecture document first. The documents and the system are never allowed to silently diverge.
9. **No engineer disables a test to make CI pass.** A failing test is fixed, or the underlying code/requirement is formally revised — a disabled test is a blind spot wearing a green checkmark.
10. **No deviation from this Constitution without a written, time-boxed, CTO-approved waiver.** "We'll clean it up later" without that waiver is not permission — it is technical debt incurred without authorization, and it is treated that way when discovered.
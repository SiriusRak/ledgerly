# Ledgerly — Product Requirements

> Invoice ingestion assistant for a French accounting-firm bookkeeper.
> UI chrome in English (Devpost judging); business data in French (invoices, accounts, €, dates, Sage columns).
> Target: web app deployed to Render, publicly accessible, running on free tiers (€0 cost).

---

## Problem Statement

A bookkeeper (*comptable en cabinet*) handling supplier invoices across multiple client files currently opens every incoming PDF, reads it, checks it, and **manually types each line into an Excel file** before importing that Excel into Sage. The app replaces **only** the manual-typing step — the Excel file remains the pivot, Sage and existing habits do not change. Expected volume: dozens to hundreds of invoices per week across client files. The adoption friction is minimal because the surrounding workflow is untouched; the ROI is immediate because manual data entry is eliminated for recurring suppliers.

---

## User Stories

### Epic 1 — Batch Upload

- **As a bookkeeper, I want to drag-and-drop up to 5 PDF invoices at once so I can ingest a morning's mail batch in one action.**
  - [ ] Landing screen shows a large drop zone with a fallback "Browse" button
  - [ ] First-visit empty state: "Drop your first invoices here" (no historical context)
  - [ ] Returning-visit state (≥1 prior invoice): compact recap above drop zone ("Last batch: 3 auto-classified, 2 to review — [Open queue]")
  - [ ] Max 5 PDFs per drop; if the user drops 7, **frontend rejects before upload** with an inline error ("Max 5 files per batch — remove 2 and retry"); no backend call is made
  - [ ] Accepted file type: `application/pdf` only; other types rejected client-side with a clear error
  - [ ] Per-file row appears immediately on drop with status `Extracting…` and a Lucide `loader` icon
  - [ ] HTMX polls each `pending`/`processing` row every 2 seconds and stops polling when the row reaches a terminal state
  - [ ] After the batch completes: toast `"5 invoices added to factures_2026-04.xlsx — PDFs stored in /EDF/, /Orange/…"` showing the storage path
  - [ ] If ≥1 invoice ends in `To review` status, the toast offers a direct link "Open validation queue (N)"
  - [ ] A batch banner `"3 invoices processing…"` stays visible **only on the Upload screen** while any row is non-terminal
  - [ ] Navigating away (to History / Validation) does **not** cancel the batch — extraction continues as a FastAPI `BackgroundTask`; each invoice has a DB state field (`pending / processing / done / error`)
  - [ ] On server crash / cold restart, orphaned `processing` rows older than 5 minutes are marked `error` with a retry action; **no automatic resume**

- **As a bookkeeper, I want each row to show a precise status with a real icon so I can see at a glance what needs my attention.**
  - [ ] Statuses with Lucide icons: `Extracting…` (`loader`), `Auto-classified` (`check-circle`), `To review` (`alert-triangle`), `Duplicate` (`copy`), `Error` (`x-circle`)
  - [ ] **No emoji anywhere in the UI** — icons are SVG (Lucide) only
  - [ ] `Auto-classified` rows show an additional learning badge: `"Recognized — EDF (3rd time)"` inline, visible for ~5 seconds then collapsed behind an info icon
  - [ ] `Duplicate` rows are informative only: PDF is not stored, not added to the .xlsx; row shows a link "See original invoice" jumping to the History entry
  - [ ] `Error` rows show a short cause (e.g. `"Not an invoice — looks like a bank statement"`, `"PDF unreadable"`) plus a "Retry" button that re-submits the same file

### Epic 2 — Validation Queue

- **As a bookkeeper, I want to see the PDF next to the extracted fields so I can verify and correct in one glance.**
  - [ ] Two-pane layout: PDF preview on the left (full page, scrollable for multi-page invoices), form on the right
  - [ ] All Sage-required fields are shown and editable: `Date`, `Journal`, `Compte`, `Libellé`, `Débit`, `Crédit`, `Code TVA`, `N° pièce`, `Dossier client` (all labels in French — these are business data, not UI chrome)
  - [ ] Supplier name is shown above the form with the detected SIRET if any
  - [ ] **Reason for review is displayed explicitly** at the top of the form — one of: `"New supplier"`, `"VAT mismatch: detected 19.6% but invoice states 20%"`, `"Possible duplicate of invoice #142 dated 2026-03-14"`
  - [ ] Amount fields accept both `1 234,56` and `1234.56`; displayed back as `1 234,56 €` (non-breaking space, comma decimal)
  - [ ] Date fields displayed and accepted in `JJ/MM/AAAA`
  - [ ] `Compte` field is a searchable dropdown seeded with the common French chart of accounts (606, 613, 625, 626, 627…) with free-text fallback
  - [ ] `Dossier client` field is a searchable dropdown of known client files + "New client" option that adds a row to the clients table
  - [ ] Single "Validate" button — **no separate "Reject"** in v1 (edit values to correct; errored extractions use "Retry" from the batch row)

- **As a bookkeeper, I want keyboard shortcuts so I can fly through the queue without touching the mouse.**
  - [ ] `Enter` = Validate and move to next invoice in queue
  - [ ] `Tab` / `Shift+Tab` = move between form fields
  - [ ] `Esc` = return to queue list
  - [ ] Shortcuts are discoverable via a small hint bar at the bottom of the form

- **As a bookkeeper, when I validate, I expect the system to remember for next time.**
  - [ ] Validation atomically: (1) updates/creates the supplier-memory row, (2) appends a line to the month's `.xlsx`, (3) moves the PDF to `/{SupplierName}/YYYY-MM_{supplier}_{amount}.pdf`, (4) auto-advances to the next invoice in the queue
  - [ ] Supplier memory key is **global per supplier** (not per `(supplier, client file)`); documented limitation — if the bookkeeper later needs different accounts per client file, she edits manually. v2 = composite key.
  - [ ] If queue becomes empty after validation, show a calm empty state: `"Queue clear. Nothing to review."`

### Epic 3 — History (read-only v1)

- **As a bookkeeper, I want a list of everything processed so I can audit and download the monthly Excel for Sage import.**
  - [ ] List columns: `Invoice date | Supplier | Amount TTC | Compte | Dossier client | Status (auto / manual) | PDF link`
  - [ ] Default order: most recent invoice first
  - [ ] **Read-only in v1** (no inline edit, no delete, no filters, no column sort — all deferred)
  - [ ] A prominent download button at the top: `"Download factures_2026-04.xlsx"` with a month selector to fetch prior months
  - [ ] Monthly `.xlsx` files are generated on demand from DB rows (not stored as static files) to ensure they reflect current data
  - [ ] Clicking a PDF link opens the stored PDF in a new tab (served from Supabase Storage)
  - [ ] Clicking a supplier name filters the list to that supplier (light interactivity, no formal filter UI)

### Epic 4 — Known Suppliers (read-only v1)

- **As a bookkeeper, I want to see which suppliers the app has learned so I can trust the auto-classification.**
  - [ ] List columns: `Supplier | SIRET | Default compte | Default dossier client | Invoices processed | Last seen`
  - [ ] Read-only in v1; inline edit deferred
  - [ ] Accessible from the main nav

### Epic 5 — Weekly Email Recap

- **As a bookkeeper, I want a Monday morning summary in my inbox so I know what to expect for the week.**
  - [ ] Cron runs every **Monday at 8:00 Europe/Paris** on Render
  - [ ] Recipient email is set via environment variable `RECAP_EMAIL` (no Settings UI in v1; Settings page deferred)
  - [ ] Email sent via Resend free tier (3000 mails/month budget — comfortable)
  - [ ] Subject: `Ledgerly — week 15 recap (Apr 6 → Apr 12)`
  - [ ] Body sections (Lucide SVG icons, no emoji):
    - Count of invoices processed this week
    - Split: N auto-classified · M manually validated
    - Total TTC for the week
    - Top 3 suppliers by amount
    - Direct link to download the current month's `.xlsx`
    - Count of duplicates detected and extraction errors
  - [ ] **If 0 invoices were processed this week → skip the send entirely**
  - [ ] If Resend API fails, log to a `recap_failures` table; do not block the app

### Epic 6 — Invisible Plumbing

- **Extraction pipeline**
  - [ ] Primary: pdfplumber extracts raw text from all pages; concatenated into one string
  - [ ] Primary LLM: Groq (Llama 3.3 70B or Qwen) receives the text + a prompt to extract Sage fields as JSON
  - [ ] Fallback LLM: Gemini Flash is used when pdfplumber yields <50 chars of usable text (likely image-heavy PDF) — but OCR of image scans remains out of scope
  - [ ] Prompt explicitly instructs the LLM: "Ignore partial/running totals; return the final invoice total only"

- **Supplier matching**
  - [ ] If SIRET is extracted → SIRET is the primary key for supplier lookup
  - [ ] Else → name normalization: lowercase + strip accents + remove legal suffixes (`SA`, `SARL`, `SAS`, `EURL`, `SA ENTREPRISES`) + collapse whitespace
  - [ ] Fallback: Levenshtein distance < 3 on normalized name → treat as same supplier
  - [ ] No LLM call for matching — deterministic and cheap

- **Confidence rules (γ — explicit, no ML)**
  - [ ] Confident (→ auto-classified) if **all three hold**: supplier already known **AND** TVA arithmetic coherent (HT + TVA ≈ TTC within ±0.02€) **AND** no duplicate detected (same supplier + same N° pièce, or same supplier + same amount within ±7 days)
  - [ ] Otherwise → validation queue, with the reason shown

- **Keep-alive**
  - [ ] A cron job (on Render or external like cron-job.org) pings `GET /health` every 10 minutes to prevent Render free-tier cold starts during working hours
  - [ ] Cold start impact noted in demo rehearsal (first request after inactivity ~30s)

### Epic 7 — Devpost Submission Assets

- **As the builder, I want demo artifacts captured automatically so the Devpost submission is polished and reproducible.**
  - [ ] A script `scripts/capture_demo_artifacts.py` that: (1) wipes + seeds a demo DB, (2) ingests 8 scripted PDFs via the real pipeline, (3) triggers the weekly recap email to a demo inbox, (4) dumps screenshots of the 3 main screens to `/demo-assets/`
  - [ ] Demo PDF set (8 files in `/demo-pdfs/`): 3× EDF (first triggers validation, second and third auto-classify showing the learning effect), 2× new suppliers (1 clean, 1 with TVA mismatch → validation queue), 1× intentional duplicate of the first EDF, 1× non-invoice (a RIB PDF → error), 1× multi-page invoice (Orange, 4 pages)
  - [ ] Demo video ≤ 2 minutes, hosted on YouTube, embedded on Devpost
  - [ ] The final `.xlsx` from the demo batch is included as a downloadable asset on the Devpost page

---

## Submission Copy (draft — refine in /iterate)

- **Title**: Ledgerly
- **Tagline**: *Your bookkeeper's invoice inbox, now on autopilot — minus the mistakes.*
- **Inspiration**: A real bookkeeper friend typing hundreds of invoices per week into Excel. Pennylane and Dext do this for a SaaS fee; we wanted to prove an open, frugal version is possible in a weekend.
- **What it does**: Drop supplier PDFs → the app extracts, classifies, and learns. Confident cases go straight to the Sage-ready Excel; uncertain cases land in a 1-click validation queue. A Monday recap email closes the loop.
- **How we built it**: pdfplumber + Groq (Llama 3.3 70B) for extraction, FastAPI + HTMX + Tailwind for a single-deploy web app, Supabase Postgres + Storage, Resend for email, Render for hosting. Zero paid services.
- **Challenges**: Making the confidence logic legible and debuggable (explicit rules, no ML), getting the supplier-learning effect viscerally visible in a 30-second demo, wrestling PDF parsing variability without going down the OCR rabbit hole.
- **Accomplishments**: A real bookkeeper could use this Monday morning. The .xlsx is a real Sage import. The cost is €0/month.
- **What we learned**: Mapping the gaps between a PM-heavy spec process (BMAD) and a leaner interview-driven spec process (Devpost `/scope → /prd → /spec`). Notes in `process-notes.md`.
- **What's next**: Composite `(supplier, client)` memory key, inbox forwarding, Sage API direct push, multi-user with RBAC.

---

## What We're Building (v1 locked scope)

1. Upload screen — drag&drop ≤5 PDFs, per-row status with Lucide icons, toast recap with storage paths
2. Validation queue — PDF preview + Sage fields form, reason displayed, `Enter/Tab/Esc` shortcuts, one-click validate + auto-advance
3. History — read-only list, monthly `.xlsx` download, supplier click-filter
4. Known Suppliers — read-only list
5. Weekly email recap — Monday 8h cron only, email via env var, skip on zero-activity week
6. Supplier memory — global key, SIRET-primary matching with Levenshtein fallback
7. Confidence rules — explicit γ (known supplier + TVA coherent + no duplicate)
8. Keep-alive ping every 10 minutes
9. Sage `.xlsx` export — columns `Date | Journal | Compte | Libellé | Débit | Crédit | Code TVA | N° pièce | Dossier client` (standard assumed format — **to validate on a real Sage file before /build if possible**)
10. Gemini Flash fallback when pdfplumber text is degraded
11. Demo artifact capture script + 8 scripted PDFs
12. Learning badge `"Recognized — [Supplier] ([N]th time)"` on auto-classified rows

## What We'd Add With More Time

- **Retroactive edit from History** — open any past invoice in the same validation UI; saving rewrites the month's .xlsx line and updates supplier memory
- **Settings page** — configurable recap email, timezone, Sage column mapping
- **Delete with Trash** — soft-delete to `/_corbeille/`, with a restore action
- **History filters** — by month, supplier, client file, status, compte
- **Column sort** in History
- **"Send recap now" button** for ad-hoc weekly summaries
- **Composite supplier memory** — key `(supplier, dossier_client)` so the same supplier can map to different accounts per client file
- **Inline edit of Known Suppliers** — change default `compte` or `dossier client` for a supplier
- **Inbox forwarding** — a dedicated email address that auto-ingests attachments
- **OCR for scans / photos** — Tesseract or a vision LLM for image-based PDFs
- **Multi-user with auth** and per-user data isolation
- **Direct Sage API integration** — skip the .xlsx pivot entirely
- **Dark mode**
- **Anomaly detection beyond duplicate/TVA** — unusual-amount flags, frequency drift, etc.
- **Approval workflow** — multi-step validation for large invoices

## Non-Goals

- **OCR of scanned / photographed invoices** — PDF-native only; image quality is a rabbit hole and pdfplumber covers the majority of supplier output.
- **Multi-user, authentication, permissions** — single user in v1; prove value before scaling.
- **Direct integration with Sage / EBP / Pennylane / Cegid** — `.xlsx` stays the pivot; the bookkeeper manually imports it, as today.
- **ML-based learning or fine-tuning** — memory is a plain SQL table `supplier → account`. No trained model.
- **Customer (outgoing) invoices** — supplier (incoming) invoices only.
- **Mobile or native apps** — responsive Tailwind web is sufficient.
- **Advanced anomaly detection** — guard-rails are explicit rules only (duplicate + VAT coherence + known supplier).

## Open Questions

- [ ] **Sage `.xlsx` exact column schema and codes** — the column set above is an assumed standard; needs validation against a real anonymized Sage import file from the interviewed bookkeeper. **Must resolve before `/build` locks the DB + export code** — but can proceed to `/spec` in parallel.
- [ ] **Chart-of-accounts seed list** — exhaustive list of French PCG accounts the dropdown should pre-populate. Can resolve during `/build`.
- [ ] **Keep-alive host** — Render internal cron vs external `cron-job.org`. Resolve in `/spec`.
- [ ] **Demo inbox** — which email address receives the recap during the Devpost demo video? Owner: Diary. Resolve before `/build`.
- [ ] **Supplier SIRET reliability** — how often is SIRET actually printed on French supplier invoices in the sample set? Affects whether SIRET-primary matching carries its weight or stays theoretical. Sample 10 real invoices during `/spec`.

---

## SDD / BMAD Divergence Notes (to carry into /spec and /reflect)

Per learner goal #2 — map where this Devpost SDD flow diverges from BMAD practice. Captured so far:

- **`/scope` fuses analyst + architect roles** — stack was decided here (Groq, FastAPI, Supabase) rather than deferred to a later architecture phase. Pragmatic; the learner is comfortable arbitrating tech early.
- **`/prd` is co-constructed in a tight interview** rather than templated by a PM agent. Learner explicitly preferred this for simplicity. Trade-off: no formal NFR / assumptions / risks registries — only the "Open Questions" section captures unresolveds.
- **Acceptance criteria are human-readable, not QA-parseable** by learner choice. A future QA agent would need reformatting. Acceptable for a demo-grade submission.
- **PRD length deliberately exceeds scope length** — expansion is the step's purpose. Verified.
- **Jury verdict on role separation (BMAD 3-agent vs Devpost 1-agent)** — deferred until after `/build`. Learner "can't tell yet without seeing the product." Revisit in `/reflect`.

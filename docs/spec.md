# Ledgerly — Technical Spec

> Companion to `scope.md` and `prd.md`. Implementation-ready. Every architectural component has its own heading so `/checklist` can address it.

---

## Stack

| Couche | Choix | Rationale |
|---|---|---|
| Langage | **Python 3.12** | learner quotidien; pdfplumber + Groq SDK natifs Python |
| Backend | **FastAPI** (async) + **Uvicorn** | [docs](https://fastapi.tiangolo.com/) — BackgroundTasks suffisent (pas de Celery) |
| Templates | **Jinja2** | intégré FastAPI, match HTMX server-rendered |
| Front | **HTMX 1.9** + **Tailwind CSS** (CLI compilé) | zero SPA, un seul deploy; vendored `htmx.min.js` (pas de CDN) |
| Icons | **Lucide** — SVG inline via macro Jinja | zero runtime JS, pas d'emoji ([feedback global](../memory/feedback_no_emoji_ui.md)) |
| DB | **Supabase Postgres** (free tier) | [docs](https://supabase.com/docs) — 500MB suffisent largement |
| Storage | **Supabase Storage** | même provider, URLs signées 1h |
| LLM principal | **Groq Llama 3.3 70B Versatile** — JSON mode | [docs](https://console.groq.com/docs/model/llama-3.3-70b-versatile) — 315 t/s, free tier rate-limited |
| LLM fallback | **Google Gemini 1.5 Flash** (vision) | [docs](https://ai.google.dev/gemini-api/docs) — quand pdfplumber < 50 chars |
| PDF extract | **pdfplumber** | [repo](https://github.com/jsvine/pdfplumber) — native PDFs, match scope |
| Excel | **openpyxl** | [docs](https://openpyxl.readthedocs.io/) |
| Scheduler | **APScheduler** (in-process, AsyncIOScheduler) | [docs](https://apscheduler.readthedocs.io/) — crons + sweeper + keep-alive |
| Email | **Resend** free tier (3000/mois) | [docs](https://resend.com/docs) |
| Hosting | **Render** web service (free) | [docs](https://render.com/docs) — cold start 30s mitigé par keep-alive maison |
| Env mgmt | **pydantic-settings** | — |
| Tests | **pytest** + **pytest-asyncio** | unités sur matcher/confidence/duplicate |
| Browser automation | **Playwright** (demo script only) | [docs](https://playwright.dev/python/) |

**Coût total visé** : 0 €.

---

## Runtime & Deployment

- **Runtime** : un seul process `uvicorn app.main:app` sur Render (web). APScheduler s'initialise via le `lifespan` FastAPI — cron hebdo + keep-alive + sweeper tous hébergés in-process.
- **Déploiement** : Render free tier depuis `main` via `render.yaml`. Public URL fournie par Render, setter `PUBLIC_URL` en env var pour self-ping keep-alive.
- **Cold start Render ~30s** : mitigé par keep-alive maison (10 min) qui tape `GET /health` + `SELECT 1` Supabase (évite aussi pause DB 7j).
- **Versions** : Python 3.12, Node 20 (build Tailwind uniquement).
- **Secrets (env vars)** : `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `RESEND_API_KEY`, `RECAP_EMAIL`, `PUBLIC_URL`. Exemple dans `.env.example`.

---

## Architecture Overview

```
┌──────────┐   HTMX (polling 2s)   ┌─────────────────┐
│ Browser  │ ────────────────────▶ │  FastAPI app    │
│ Tailwind │ ◀──── partials ────── │  (Jinja2 render)│
└──────────┘                       └────┬──┬────┬────┘
                                        │  │    │
                                        │  │    └──▶ Supabase Storage (PDFs)
                                        │  │             (signed URLs 1h)
                                        │  │
                                        │  └──▶ Supabase Postgres (suppliers, clients, invoices, recap_failures)
                                        │
                                        ▼ BackgroundTask
                             ┌─────────────────────────┐
                             │ pipeline.orchestrator   │
                             │  extractor ─▶ llm ─▶    │
                             │  matcher ─▶ duplicate ─▶│
                             │  confidence ─▶ storage  │
                             └─────────────────────────┘

APScheduler (same process):
  ├─ weekly_recap  (cron Mon 8:00 Europe/Paris → Resend)
  ├─ keepalive     (every 10 min → self-GET /health + SELECT 1)
  └─ sweeper       (every 2 min → stale 'processing' → 'error')
```

### Data flow (invoice lifecycle)

```
1. Drop PDF  ─────▶  POST /upload (multipart, ≤5 PDFs)
                     │
                     ├─ insert invoices(state='pending')
                     ├─ upload to Storage:_inbox/{uuid}.pdf
                     └─ BackgroundTask(process, inv_id)
                     └─ return partial batch_rows.html (hx-trigger every 2s)

2. process(inv_id):
   state='processing'
   ├─ extractor.extract_text(pdf)  → (text, source)
   │    └─ if < 50 chars → Gemini Vision fallback
   ├─ llm.extract_fields(text)     → JSON (Groq JSON mode)
   ├─ matcher.find_supplier(siret, name)  → supplier|None
   ├─ duplicate.check(...)         → dup_invoice|None
   ├─ confidence.evaluate(...)     → ('auto'|'review'|'duplicate', reason)
   │
   ├─ if 'duplicate': state='duplicate', duplicate_of=..., PDF reste _inbox/ (purgé en batch)
   ├─ if 'auto':     state='done', classification='auto',
   │                 copy supplier defaults (compte, dossier_client, journal),
   │                 supplier_memory.bump(), storage.move → /{supplier}/{YYYY-MM}_{supplier}_{amount}.pdf
   └─ if 'review':   state='processing', state_reason=reason, PDF reste _inbox/
                     (UI le montre "To review" tant que state_reason != null)

3. Poll:
   GET /invoices/{id}/status  → partial batch_row.html
   └─ template n'émet plus hx-trigger si state terminal → polling s'arrête

4. Validate (review cases):
   POST /queue/{id}/validate {compte, dossier_client_id, date, libelle, ...}
   └─ RPC Postgres validate_invoice(...)  (transaction):
        - UPDATE invoices SET state='done', classification='manual', state_reason=NULL, <fields>
        - UPSERT suppliers SET default_compte, default_dossier_client_id, invoices_count+=1, last_seen=now()
        - (out-of-tx, idempotent) storage.move PDF
   └─ 303 → /queue/{next_id}  ou /queue si vide

5. Download monthly xlsx (on-demand):
   GET /history/export/factures_{YYYY-MM}.xlsx
   └─ sage_xlsx.build(month) → StreamingResponse
       pour chaque invoice state='done' du mois :
         ligne Débit  = HT   sur compte charge (ex 606)
         ligne Débit  = TVA  sur compte 44566         (si amount_tva > 0)
         ligne Crédit = TTC  sur compte 401 (fournisseur)
```

---

## Routes

### `app/routes/upload.py`
Implements `prd.md > Epic 1`.
- `POST /upload` — multipart ≤5 PDFs; insert `pending`, upload `_inbox/`, schedule BackgroundTask, return `partials/batch_rows.html`.
- `GET /invoices/{id}/status` — return `partials/batch_row.html`. OOB toast quand dernier row du batch devient terminal.
- `GET /batch/status` — partial pour la bannière `"N invoices processing..."`, polling 3s.
- `POST /invoices/{id}/retry` — réinsert BackgroundTask sur invoice `error`.

**Rejet client-side** : JS vanilla 15 lignes dans `upload.html` valide `files.length <= 5` et `type === 'application/pdf'` avant submit.

**Auto-stop polling** : `partials/batch_row.html` n'émet `hx-trigger="every 2s"` que si `state in ('pending','processing')` **et** `state_reason IS NULL`. Dès terminal ou review → pas d'attribut → HTMX arrête.

### `app/routes/validation.py`
Implements `prd.md > Epic 2`.
- `GET /queue` — liste `invoices` où `state='processing' AND state_reason IS NOT NULL`, tri : duplicate > VAT mismatch > new supplier, puis FIFO.
- `GET /queue/{id}` — `validation_detail.html` : `<iframe>` PDF (signed URL Supabase) gauche, form Sage fields droite.
- `POST /queue/{id}/validate` — appelle RPC Postgres `validate_invoice(...)`, redirect 303 next.
- `GET /clients/new-inline` — partial input texte + submit pour créer client à la volée.
- `POST /clients` — crée client, return `<option selected>` HTMX swap.

**Raccourcis clavier** : `<script>` vanilla dans `validation_detail.html` — `Enter` → submit, `Esc` → `/queue`.

**Formattage** : JS handler sur `input[data-type="amount"]` normalise `1 234,56` ↔ `1234.56`. Dates en `pattern="\d{2}/\d{2}/\d{4}"`.

**Compte dropdown** : `<input list="comptes-pcg">` + `<datalist>` avec ~30 codes PCG hardcodés (`606`, `6061`, `6063`, `613`, `6135`, `616`, `6226`, `625`, `6251`, `626`, `627`, `701`, `706`, `707`, `44566`, `401`, ...). Free-text fallback natif.

**Dossier client dropdown** : `<select>` peuplé depuis `clients` + `<option value="__new__">+ Nouveau client</option>` déclenchant swap HTMX.

### `app/routes/history.py`
Implements `prd.md > Epic 3`.
- `GET /history?supplier_id=xxx` — liste read-only triée `invoice_date DESC`, click supplier → filtre.
- `GET /history/export/factures_{YYYY-MM}.xlsx` — stream xlsx Sage 13-col, partie double.
- `GET /history/export/enriched_{YYYY-MM}.csv` — CSV UTF-8 BOM enrichi avec `Dossier client`, `SIRET`, `Classification`.

### `app/routes/suppliers.py`
Implements `prd.md > Epic 4`.
- `GET /suppliers` — liste read-only triée `last_seen DESC`.

### `app/routes/health.py`
- `GET /health` — return `{"ok": true, "db": true}` après `SELECT 1`. Cible du keep-alive.

---

## Pipeline (`app/pipeline/`)

### `extractor.py`
Implements `prd.md > Epic 6 > Extraction pipeline`.
```python
def extract_text(pdf_bytes: bytes) -> tuple[str, Literal['pdfplumber','gemini']]:
    with pdfplumber.open(BytesIO(pdf_bytes)) as pdf:
        text = "\n".join((p.extract_text() or "") for p in pdf.pages)
    if len(text.strip()) >= 50:
        return text, "pdfplumber"
    return gemini_vision_extract(pdf_bytes), "gemini"
```
Tronquer à 30 000 chars avant LLM pour borner les coûts tokens.

### `llm.py`
Groq JSON mode. Schéma stricte, prompt qui demande d'ignorer totaux partiels.

```python
SYSTEM_PROMPT = """Tu extrais les champs comptables d'une facture fournisseur française.
Règles strictes :
- Ignore les totaux partiels, acomptes, reports. Retourne UNIQUEMENT le total final.
- Si plusieurs taux TVA, somme les TVA et retourne le taux majoritaire.
- Dates au format ISO YYYY-MM-DD.
- Montants en nombres (point décimal).
- Champ absent → null (sauf required).
Retourne strictement le JSON conforme au schéma."""

# model: "llama-3.3-70b-versatile", response_format={"type":"json_object"}, temperature=0.1
```

Schéma : `supplier_name`, `siret` (nullable), `invoice_date` (ISO), `invoice_number`, `amount_ht`, `amount_tva`, `amount_ttc`, `tva_rate`.

Fallback Gemini si Groq 429 ou timeout > 15s.

### `matcher.py`
Implements `prd.md > Epic 6 > Supplier matching`. Déterministe, zéro LLM.

1. `siret` non-null → lookup direct `suppliers.siret`.
2. Sinon, normaliser nom : `lower()` + strip accents (`NFKD`) + retirer suffixes légaux (`sarl|sas|sa|eurl|sasu|eirl`) + collapse whitespace.
3. Lookup `suppliers.name_normalized` exact.
4. Fallback : `levenshtein(norm, candidate.name_normalized) < 3` sur tous les suppliers (< 500 rows attendus, full scan OK).

### `duplicate.py`
```sql
SELECT id, invoice_number FROM invoices
WHERE supplier_id = :sid AND state = 'done'
  AND ( invoice_number = :num
        OR (abs(amount_ttc - :ttc) < 0.01 AND abs(invoice_date - :date) <= 7) )
LIMIT 1;
```

### `confidence.py`
Implements `prd.md > Epic 6 > Confidence rules`.
```
if duplicate         → ('duplicate', "Possible duplicate of invoice #{n} dated {d}")
elif supplier is None → ('review', "New supplier")
elif |HT + TVA − TTC| > 0.02 → ('review', "VAT mismatch: …")
else                 → ('auto', None)
```

### `orchestrator.py`
Entrée BackgroundTask. Chaîne `extractor → llm → matcher → duplicate → confidence → storage.move`. Try/except global → `state='error'`, `state_reason=str(e)[:200]`.

---

## Exporters (`app/exporters/`)

### `sage_xlsx.py`
Implements `prd.md > What We're Building #9`. Strict 13 colonnes (schéma réel fourni par comptable) :

`Compte | Date | Journal | N°Piece | Référence | Tiers | Libellés | Lettrage | Débit | Crédit | Solde | Mois | Observation`

**Partie double** générée à la volée (non stockée) :

| Type ligne | Compte | Débit | Crédit | Tiers | Libellés |
|---|---|---|---|---|---|
| Charge | `invoice.compte` (ex 606) | HT | — | supplier.name | `"{Tiers} - {N°Piece}"` |
| TVA (si TVA>0) | `44566` | TVA | — | supplier.name | idem |
| Fournisseur | `401` | — | TTC | supplier.name | idem |

- `Journal` = `"HA"` (v1 hardcodé, v2 = supplier.default_journal)
- `Date` = `JJ/MM/AAAA`
- `Lettrage`, `Solde` = vides (remplis par Sage post-import)
- `Mois` = `MM/AAAA`
- `Observation` = vide sur export Sage strict

### `enriched_csv.py`
Mêmes lignes + colonnes `Dossier client` (via `clients.code`), `SIRET`, `Classification` (auto/manual). UTF-8 BOM.

---

## Services (`app/services/`)

### `storage.py`
Wrapper Supabase Storage : `put_inbox`, `move_to_supplier`, `signed_url(path, ttl=3600)`. Convention path : `_inbox/{uuid}.pdf` → `{supplier_normalized}/{YYYY-MM}_{supplier}_{amount}.pdf`.

### `supplier_memory.py`
Upsert + bump counter/last_seen. Appelé depuis `orchestrator` (auto case) et RPC `validate_invoice` (manual case).

### `xlsx_naming.py`
Filename = `factures_{YYYY-MM}.xlsx`. Month param = `invoice_date` mois dominant (in-query param, pas de state).

---

## Jobs (`app/jobs/`)

### `scheduler.py`
`AsyncIOScheduler` init dans `lifespan` FastAPI. Shutdown propre.

### `weekly_recap.py`
Implements `prd.md > Epic 5`. Cron `mon 08:00 Europe/Paris`.
- Compute stats : count total, auto vs manual, sum TTC, top 3 suppliers par montant, count duplicates, count errors.
- Si 0 invoices cette semaine → skip.
- Render `templates/email/recap.html` (Lucide SVG inline, pas d'emoji).
- `resend.Emails.send(...)`. Try/except → `insert into recap_failures`.

### `keepalive.py`
Cron every 10 min. `GET {PUBLIC_URL}/health` + `SELECT 1`. Double job : évite cold start Render ET pause Supabase 7j.

### `sweeper.py`
Cron every 2 min.
```sql
UPDATE invoices SET state='error', state_reason='Server restart (timeout)'
WHERE state IN ('processing','pending')
  AND processed_at IS NULL
  AND uploaded_at < now() - interval '5 minutes';
```

---

## Templates & Static

### Templates (`app/templates/`)
- `base.html` — layout, Tailwind `dist.css`, `htmx.min.js`, nav (Upload / Queue / History / Suppliers)
- `upload.html` — drop zone, `<script>` JS validation client, batch banner, rows container
- `validation_queue.html` — liste cards, reason badge
- `validation_detail.html` — split-pane : iframe PDF + form Sage fields
- `history.html` — table + month selector + download buttons
- `suppliers.html` — table read-only
- `partials/batch_row.html` — row HTMX (auto-stop polling)
- `partials/batch_rows.html` — container post-upload
- `partials/batch_banner.html` — bannière processing
- `partials/status_badge.html` — mapping state → icon + label
- `partials/toast.html` — toast OOB post-batch
- `macros/icons.html` — `{% macro icon(name, class="") %}` Lucide SVG inline
- `email/recap.html` — template email hebdo

### Static
- `static/css/input.css` — `@tailwind base; @tailwind components; @tailwind utilities;`
- `static/css/dist.css` — output Tailwind CLI (gitignored, build CI)
- `static/js/htmx.min.js` — vendored HTMX 1.9 (SRI pin)

**Pas de Tailwind CDN** (learner choice). Build via `npx tailwindcss -i input.css -o dist.css --minify` dans Dockerfile stage 1.

---

## Data Model

Full schema in `migrations/001_init.sql`.

### `clients`
Table des dossiers clients du cabinet.
```sql
id uuid pk, code text unique, name text, created_at timestamptz
```

### `suppliers`
Mémoire apprenante (clé globale — cf PRD Epic 2 doc limitation).
```sql
id uuid pk
name text                     -- affichage
name_normalized text unique   -- clé matching fallback (lower + sans accents + sans suffixes)
siret text unique nullable    -- clé matching primaire
default_compte text           -- ex '606'
default_dossier_client_id uuid fk → clients(id)
default_journal text default 'HA'
invoices_count int default 0
last_seen timestamptz
created_at timestamptz
```

### `invoices`
Source de vérité unique (pas de table `validation_queue` — `state + state_reason` suffisent).
```sql
id uuid pk
state text                    -- pending|processing|done|error|duplicate
state_reason text nullable    -- non-null → visible dans /queue

uploaded_at timestamptz
processed_at timestamptz nullable
pdf_storage_path text
pdf_original_name text

supplier_id uuid fk → suppliers(id) nullable
supplier_name_raw text        -- avant matching
siret text nullable
invoice_date date
invoice_number text           -- N°Piece
amount_ht numeric(12,2)
amount_tva numeric(12,2)
amount_ttc numeric(12,2)
tva_rate numeric(5,2)

compte text
dossier_client_id uuid fk → clients(id) nullable
journal text default 'HA'
libelle text
observation text

classification text           -- auto|manual
duplicate_of uuid fk → invoices(id) nullable
raw_extraction jsonb          -- payload LLM complet (debug)
```
Indexes : `(state)`, `(supplier_id)`, `(invoice_date)`.

### `recap_failures`
Log erreurs Resend.
```sql
id uuid pk, failed_at timestamptz, error text
```

### RPC `validate_invoice`
Function Postgres `plpgsql` — transaction atomique : update invoice + upsert supplier defaults + bump counter. Move PDF hors-tx (idempotent).

---

## File Structure

```
ledgerly/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI app + lifespan(scheduler)
│   ├── config.py                    # pydantic-settings
│   ├── db.py                        # Supabase client singleton
│   │
│   ├── routes/
│   │   ├── upload.py                # Epic 1
│   │   ├── validation.py            # Epic 2
│   │   ├── history.py               # Epic 3
│   │   ├── suppliers.py             # Epic 4
│   │   └── health.py                # /health keep-alive target
│   │
│   ├── pipeline/
│   │   ├── extractor.py             # pdfplumber + Gemini fallback
│   │   ├── llm.py                   # Groq JSON mode + prompt
│   │   ├── matcher.py               # SIRET → normalisation → Levenshtein
│   │   ├── confidence.py            # règle γ
│   │   ├── duplicate.py             # même num OU (même montant ±7j)
│   │   └── orchestrator.py          # BackgroundTask entrypoint
│   │
│   ├── exporters/
│   │   ├── sage_xlsx.py             # 13 col, partie double
│   │   └── enriched_csv.py
│   │
│   ├── services/
│   │   ├── storage.py               # Supabase Storage wrapper
│   │   ├── supplier_memory.py
│   │   └── xlsx_naming.py
│   │
│   ├── jobs/
│   │   ├── scheduler.py             # APScheduler init
│   │   ├── weekly_recap.py          # Epic 5
│   │   ├── keepalive.py             # /health + SELECT 1
│   │   └── sweeper.py               # stale processing → error
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── upload.html
│   │   ├── validation_queue.html
│   │   ├── validation_detail.html
│   │   ├── history.html
│   │   ├── suppliers.html
│   │   ├── partials/
│   │   │   ├── batch_row.html
│   │   │   ├── batch_rows.html
│   │   │   ├── batch_banner.html
│   │   │   ├── status_badge.html
│   │   │   └── toast.html
│   │   ├── macros/
│   │   │   └── icons.html           # Lucide SVG inline macro
│   │   └── email/
│   │       └── recap.html
│   │
│   └── static/
│       ├── css/
│       │   ├── input.css            # @tailwind directives
│       │   └── dist.css             # build output (gitignored)
│       └── js/
│           └── htmx.min.js          # vendored
│
├── migrations/
│   └── 001_init.sql                 # schéma complet + RPC validate_invoice
│
├── scripts/
│   ├── capture_demo_artifacts.py    # Epic 7 — Playwright + pipeline réelle
│   ├── seed_demo.py                 # 3 clients + wipe DB
│   └── build_css.sh                 # npx tailwindcss --minify
│
├── demo-pdfs/                       # 8 PDFs scénarisés (README.md documente chaque)
├── demo-assets/                     # output screenshots + xlsx de la démo
│
├── tests/
│   ├── test_matcher.py
│   ├── test_confidence.py
│   ├── test_duplicate.py
│   ├── test_sage_xlsx.py            # partie double correcte
│   └── fixtures/
│
├── tailwind.config.js
├── package.json
├── pyproject.toml
├── Dockerfile                       # 2-stage: node(build css) → python:3.12-slim
├── render.yaml
├── .env.example
├── .gitignore
├── README.md
├── process-notes.md
└── docs/
    ├── scope.md
    ├── prd.md
    ├── spec.md                      # this file
    └── learner-profile.md
```

---

## Key Technical Decisions

1. **APScheduler in-process, pas de worker séparé.**
   Tradeoff accepté : si crash FastAPI, crons perdus jusqu'au redémarrage. Volume faible + sweeper corrige les orphelins → OK pour v1. Alternative (Celery + Redis) ajoute un service payant ou une complexité de déploiement hors-sujet.

2. **Partie double générée à l'export (non stockée).**
   On stocke l'**invoice** logique; l'écriture comptable à 2-3 lignes est reconstruite à la volée par `sage_xlsx.py`. Tradeoff : re-règle TVA/comptes sans migration DB; contrepartie : pas d'historique versionné des exports (acceptable, le `.xlsx` produit fait foi).

3. **Matcher déterministe (zéro LLM, zéro `pg_trgm`).**
   SIRET → nom normalisé → Levenshtein<3 en Python sur full scan (<500 rows). Tradeoff : dégradation au-delà de ~10k suppliers, mais scope v1 est un cabinet unique. Gain : reproductible, debuggable, gratuit, migration simple.

4. **`state + state_reason` dans `invoices` plutôt que table `validation_queue`.**
   Un seul endroit à querier. Tradeoff : le statut "review" n'est pas terminal (`state='processing'` avec `state_reason NOT NULL`), sémantiquement un peu torturé. Gain : pas de sync cross-table.

5. **Tailwind CLI compilé en build (pas CDN).**
   Learner choice (cf `/spec` conversation). Tradeoff : Dockerfile 2-stage (Node requis au build). Gain : -50KB au premier load, zero dépendance runtime externe.

6. **`/spec` implémentation-ready, pas greenfield archi.**
   **Divergence BMAD** : stack déjà figée en `/scope`; cette étape détaille composants/data flow/contrats plutôt que de proposer une archi from scratch. Permis par le profil praticien expérimenté du learner.

---

## Dependencies & External Services

| Service | Usage | Free tier | Limites à connaître | API key |
|---|---|---|---|---|
| [Groq](https://console.groq.com/docs) | Extraction LLM principal | Oui, rate-limited | RPD/RPM selon modèle; `llama-3.3-70b-versatile` ~30 RPM en free | `GROQ_API_KEY` |
| [Google Gemini](https://ai.google.dev/) | LLM fallback (vision) | Oui | 15 RPM free tier `gemini-1.5-flash` | `GEMINI_API_KEY` |
| [Supabase](https://supabase.com/docs) | Postgres + Storage | 500MB DB / 1GB storage / 2 projets | **Pause après 7j inactivité** → mitigé par keep-alive SELECT 1 | `SUPABASE_URL`, `SUPABASE_SERVICE_KEY` |
| [Resend](https://resend.com/docs) | Email recap | 3000/mois, 100/jour | Domaine personnalisé requis pour custom from | `RESEND_API_KEY` |
| [Render](https://render.com/docs) | Web hosting | 512MB RAM, cold start ~30s | 750h/mois; cold start mitigé par keep-alive | — |

**Python libs** : `fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart`, `pdfplumber`, `groq`, `google-generativeai`, `httpx`, `supabase`, `openpyxl`, `apscheduler`, `pydantic-settings`, `resend`, `python-Levenshtein`.

**Dev libs** : `pytest`, `pytest-asyncio`, `playwright`, `ruff`.

**Node libs** (build-only) : `tailwindcss`.

---

## Open Issues

Carried from `prd.md > Open Questions`, updated here :

- [x] **Sage `.xlsx` schéma exact** — ✅ résolu : fichier réel fourni, 13 colonnes (`Compte | Date | Journal | N°Piece | Référence | Tiers | Libellés | Lettrage | Débit | Crédit | Solde | Mois | Observation`). Implémenté dans `sage_xlsx.py`. PRD divergence : pas de `Code TVA` (géré via compte 44566), pas de `Dossier client` (→ export CSV enrichi séparé).
- [x] **Keep-alive host** — ✅ résolu : cron maison APScheduler in-process (ping `/health` + `SELECT 1` toutes les 10 min).
- [ ] **Chart-of-accounts seed** — ~30 codes PCG hardcodés dans `<datalist>`. Liste exacte à finaliser en `/build` (demander à la comptable la short-list qu'elle utilise réellement).
- [ ] **Demo inbox** — adresse Resend pour la vidéo démo. Owner : learner. Resolve avant `/build` ou utiliser l'adresse du learner.
- [ ] **SIRET fiabilité** — échantillonner 10 vraies factures en `/build` pour mesurer. Plan B si < 50% : matcher Levenshtein porte tout le poids (déjà couvert par code).

**Self-review items** (non-bloquants, à garder en tête en `/build`) :
- `state='processing' AND state_reason IS NOT NULL` = "review" — sémantique mixte, ajouter un commentaire clair dans la migration + helper `is_in_queue(inv)`.
- RPC `validate_invoice` + move PDF : le move est hors-tx. En cas d'échec move post-commit, invoice est marquée `done` mais PDF reste `_inbox/`. Acceptable v1 (pas de data loss, juste un PDF mal rangé) mais à surveiller.
- Groq 429 : pas de retry/backoff défini. À ajouter en `/build` (simple `tenacity` + fallback Gemini après 2 retries).
- Batch cookie pour toast OOB : session cookie `batch_id` simple, pas de signing. Pas de risque sécu en mono-user v1; revisiter si multi-user.

---

## Divergences BMAD capturées

- `/spec` ici est **implémentation-ready** (composants + contrats + data flow) plutôt qu'architecture greenfield. Chez BMAD, l'architecte partirait d'une page blanche stack; ici `/scope` a déjà tranché.
- Pas de diagrammes C4 formalisés ni NFR registry — ASCII + tableaux + rationale en prose.
- Pas de séparation PM/Architecte/SM : une conversation unique.
- Self-review en `Open Issues` plutôt qu'en cérémonie dédiée.
- Jugement final reporté à `/reflect` (cf learner choice en `/prd`).

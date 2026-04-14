# Build Checklist — Ledgerly

## Build Preferences

- **Build mode:** Autonomous
- **Comprehension checks:** N/A (autonomous mode)
- **Git:** Commit after each completed item. Message format: `feat(step-N): [item title]` (ou `chore`/`fix` selon pertinence). Commits servent de revert points si un item casse.
- **Verification:** Yes. Checkpoints tous les 3-4 items — agent pause, résumé bref, learner vérifie (browser / curl / xlsx ouvert).
- **Check-in cadence:** N/A (autonomous mode)

## Checklist

- [x] **1. Bootstrap app & infrastructure**
  Spec ref: `spec.md > Stack`, `spec.md > Runtime & Deployment`, `spec.md > File Structure`, `spec.md > Data Model`
  What to build: `pyproject.toml` (deps listées §Dependencies), `app/__init__.py`, `app/main.py` (FastAPI + lifespan stub vide), `app/config.py` (pydantic-settings pour tous les env vars du §Runtime), `app/db.py` (Supabase client singleton), `app/routes/health.py` avec `GET /health` → `{"ok":true,"db":true}` après `SELECT 1` Supabase, `migrations/001_init.sql` avec schéma complet (tables `clients`, `suppliers`, `invoices`, `recap_failures`, indexes, RPC `validate_invoice` plpgsql transaction update+upsert). Ajouter `render.yaml`, `.env.example`, `.gitignore`, `README.md` minimal. Exécuter la migration sur le projet Supabase.
  Acceptance: `uvicorn app.main:app` démarre sans erreur ; `GET /health` retourne 200 avec `db:true` ; schéma Supabase visible dans dashboard (4 tables + RPC).
  Verify: `curl localhost:8000/health` → 200 JSON, puis ouvrir Supabase dashboard et confirmer les 4 tables + RPC `validate_invoice`.

- [x] **2. Frontend shell (Tailwind + base template + Lucide)**
  Spec ref: `spec.md > Templates & Static`
  What to build: `package.json`, `tailwind.config.js`, `static/css/input.css` (directives Tailwind), `scripts/build_css.sh` (`npx tailwindcss -i input.css -o dist.css --minify`), download + vendor `static/js/htmx.min.js` v1.9 (SRI pin), `app/templates/base.html` (layout, nav 4 onglets Upload/Queue/History/Suppliers, chargement `dist.css` + `htmx.min.js` locaux, pas de CDN), `app/templates/macros/icons.html` (`{% macro icon(name, class="") %}` qui inline les SVG Lucide nécessaires — `loader`, `check-circle`, `alert-triangle`, `copy`, `x-circle`, `upload`, `inbox`, `book-open`, `users`, `download`). Route racine `GET /` qui redirect vers `/upload`.
  Acceptance: page charge avec Tailwind appliqué, nav affichée, icônes Lucide visibles en SVG inline, zéro emoji dans le DOM.
  Verify: ouvrir `http://localhost:8000/` dans le browser, inspecter le DOM → confirmer `<svg>` Lucide (pas d'emoji), `dist.css` servi en local (pas CDN).

- [x] **3. Pipeline — extraction texte + LLM (Groq JSON mode)**
  Spec ref: `spec.md > Pipeline > extractor.py`, `spec.md > Pipeline > llm.py`, `prd.md > Epic 6 > Extraction pipeline`
  What to build: `app/pipeline/extractor.py` avec `extract_text(pdf_bytes) -> (text, source)` — pdfplumber concat pages, fallback Gemini Vision si <50 chars, tronquer 30k chars. `app/pipeline/llm.py` avec `extract_fields(text) -> dict` appelant Groq `llama-3.3-70b-versatile` en JSON mode, temperature 0.1, SYSTEM_PROMPT strict (ignorer totaux partiels, ISO dates, point décimal). Schéma retour : `supplier_name, siret, invoice_date, invoice_number, amount_ht, amount_tva, amount_ttc, tva_rate`. Fallback Gemini si Groq 429 ou timeout >15s. Placer 1-2 PDFs réels dans `tests/fixtures/`.
  Acceptance: sur une facture PDF native réelle, `extract_text → llm.extract_fields` retourne un dict conforme au schéma avec amounts cohérents (HT+TVA≈TTC).
  Verify: `pytest tests/test_pipeline_smoke.py -s` (smoke test qui print le dict extrait d'une vraie facture fixture) — inspecter visuellement que les montants matchent la facture.

- [x] **4. Pipeline — matcher + duplicate + confidence (+ unit tests déterministes)**
  Spec ref: `spec.md > Pipeline > matcher.py/duplicate.py/confidence.py`, `prd.md > Epic 6 > Supplier matching / Confidence rules`
  What to build: `matcher.py` (SIRET exact → nom normalisé `lower + strip accents NFKD + retirer sarl/sas/sa/eurl/sasu/eirl + collapse ws` → Levenshtein<3 full scan via `python-Levenshtein`). `duplicate.py` (SQL même supplier + même invoice_number OU |amount_ttc diff|<0.01 ET |date diff|≤7j). `confidence.py` (règle γ explicite : duplicate → `('duplicate', reason)` ; supplier None → `('review', "New supplier")` ; |HT+TVA−TTC|>0.02 → `('review', "VAT mismatch: ...")` ; sinon `('auto', None)`). Tests : `tests/test_matcher.py`, `test_duplicate.py`, `test_confidence.py` couvrant chaque branche.
  Acceptance: 100% des unit tests passent ; matcher trouve "EDF SA" == "edf", "E.D.F." == "edf" ; confidence retourne les 4 classes correctement selon fixtures.
  Verify: `pytest tests/test_matcher.py tests/test_duplicate.py tests/test_confidence.py -v` → tout vert.

- [x] **5. Upload UI + orchestrator BackgroundTask + polling HTMX**
  Spec ref: `spec.md > Routes > upload.py`, `spec.md > Pipeline > orchestrator.py`, `prd.md > Epic 1`
  What to build: `app/services/storage.py` (wrapper Supabase Storage : `put_inbox`, `move_to_supplier`, `signed_url`). `app/services/supplier_memory.py` (upsert + bump). `app/pipeline/orchestrator.py` (chaîne extractor→llm→matcher→duplicate→confidence→storage.move, try/except global → state='error'). `app/routes/upload.py` (POST /upload multipart ≤5, insert pending, upload _inbox, BackgroundTask, return partial ; GET /invoices/{id}/status ; GET /batch/status ; POST /invoices/{id}/retry). Templates : `upload.html` (drop zone + JS vanilla 15 lignes client-side validation ≤5 + PDF only), `partials/batch_row.html` (hx-trigger="every 2s" conditionnel auto-stop), `partials/batch_rows.html`, `partials/batch_banner.html`, `partials/status_badge.html`, `partials/toast.html` OOB post-batch. Statuts avec Lucide icons (loader/check-circle/alert-triangle/copy/x-circle).
  Acceptance: drop 1 PDF → row apparaît "Extracting…" → passe à "Auto-classified" (si supplier connu) ou "To review" (si nouveau) en <30s ; polling s'arrête automatiquement ; toast avec chemin storage affiché. Drop 6 PDFs rejeté côté client avec message.
  Verify: Ouvrir `/upload`, drop 3 PDFs demo réels → observer les rows passer de loader à check-circle/alert-triangle sans refresh manuel, toast visible en fin de batch.

- [ ] **6. Validation queue — liste + détail split-pane + RPC validate**
  Spec ref: `spec.md > Routes > validation.py`, `prd.md > Epic 2`
  What to build: `app/routes/validation.py` (GET /queue trié duplicate>VAT>new supplier puis FIFO ; GET /queue/{id} split-pane ; POST /queue/{id}/validate → RPC `validate_invoice` → 303 next_id ou /queue ; GET /clients/new-inline + POST /clients swap option). Templates : `validation_queue.html` (cards + reason badge), `validation_detail.html` (iframe PDF signed URL + form Sage fields : Date JJ/MM/AAAA, Journal, Compte `<input list="comptes-pcg">` + `<datalist>` ~30 codes PCG hardcodés, Libellé, Débit/Crédit, N°pièce, Dossier client `<select>` + option "__new__" → HTMX swap). Scripts inline : Enter=submit, Esc=/queue, handler `input[data-type="amount"]` normalise `1 234,56`↔`1234.56`.
  Acceptance: Queue liste les invoices à reviewer avec reason affichée. Détail charge avec PDF visible à gauche, form pré-rempli à droite. Enter valide et auto-advance au suivant. RPC met à jour invoice + supplier + déplace le PDF à `/{supplier}/YYYY-MM_{supplier}_{amount}.pdf`.
  Verify: Drop d'une facture EDF #1 (new supplier) → apparaît dans /queue → cliquer → valider avec compte 606 + dossier client → confirmer : invoice state='done' en DB, PDF déplacé dans `/EDF/` dans Supabase Storage, redirect sur next/queue vide.

- [ ] **7. History + Sage xlsx export (partie double 13-col) + enriched CSV**
  Spec ref: `spec.md > Routes > history.py`, `spec.md > Exporters`, `prd.md > Epic 3`
  What to build: `app/exporters/sage_xlsx.py` (openpyxl, 13 colonnes exactes `Compte|Date|Journal|N°Piece|Référence|Tiers|Libellés|Lettrage|Débit|Crédit|Solde|Mois|Observation`, partie double 2-3 lignes par invoice : charge HT débit + TVA 44566 débit si >0 + 401 crédit TTC ; Journal=HA v1 ; dates JJ/MM/AAAA ; Mois MM/AAAA). `app/exporters/enriched_csv.py` (UTF-8 BOM + colonnes additionnelles Dossier client/SIRET/Classification). `app/services/xlsx_naming.py` (`factures_{YYYY-MM}.xlsx`). `app/routes/history.py` (GET /history avec filter supplier_id optionnel, GET /history/export/factures_{YYYY-MM}.xlsx StreamingResponse, GET /history/export/enriched_{YYYY-MM}.csv). Template `history.html` (table + month selector + 2 download buttons, supplier click → filter).
  Acceptance: Page /history liste toutes les invoices done, tri date DESC. Click bouton download → fichier `.xlsx` téléchargé, ouvrable dans Excel/LibreOffice, 13 colonnes exactes, partie double vérifiable (somme débits = somme crédits par invoice). CSV enrichi contient Dossier client + SIRET + Classification.
  Verify: Ouvrir le .xlsx téléchargé, confirmer : en-têtes 13 colonnes, pour une invoice de 120€ TTC (100 HT + 20 TVA), 3 lignes = débit 100 sur 606, débit 20 sur 44566, crédit 120 sur 401. Totaux équilibrés.

- [ ] **8. Suppliers read-only page**
  Spec ref: `spec.md > Routes > suppliers.py`, `prd.md > Epic 4`
  What to build: `app/routes/suppliers.py` (GET /suppliers, tri `last_seen DESC`). Template `suppliers.html` (table colonnes Supplier/SIRET/Default compte/Default dossier client/Invoices processed/Last seen).
  Acceptance: Page charge, liste tous les suppliers appris avec leurs defaults et compteur d'invoices.
  Verify: Après avoir traité quelques factures, ouvrir /suppliers → confirmer chaque supplier validé apparaît avec `invoices_count` correct et `last_seen` récent.

- [ ] **9. Jobs — scheduler + keepalive + sweeper + weekly recap email**
  Spec ref: `spec.md > Jobs`, `prd.md > Epic 5`
  What to build: `app/jobs/scheduler.py` (`AsyncIOScheduler` init dans `lifespan` FastAPI, shutdown propre). `app/jobs/keepalive.py` (cron every 10min : `httpx.get({PUBLIC_URL}/health)` + `SELECT 1` Supabase). `app/jobs/sweeper.py` (cron every 2min : UPDATE invoices SET state='error', state_reason='Server restart (timeout)' WHERE state IN (processing,pending) AND uploaded_at < now()-5min). `app/jobs/weekly_recap.py` (cron `mon 08:00 Europe/Paris` : stats semaine — count total, auto/manual split, sum TTC, top 3 suppliers, duplicates count, errors count ; skip si 0 invoices ; render template email ; resend.send ; try/except insert into `recap_failures`). Template `email/recap.html` (Lucide SVG inline, no emoji, bouton download xlsx mois courant).
  Acceptance: Au démarrage, logs APScheduler montrent les 3 jobs enregistrés. Keepalive ping visible dans logs toutes les 10min. Trigger manuel du weekly_recap envoie un mail Resend reçu sur `RECAP_EMAIL`.
  Verify: Démarrer l'app, attendre 10min → voir log keepalive ping. Déclencher manuellement `weekly_recap()` via un script ou REPL → vérifier réception du mail dans la boîte `RECAP_EMAIL`, structure correcte (7 sections), pas d'emoji, lien download fonctionnel.

- [ ] **10. Demo assets — seed + 8 PDFs scénarisés + capture script**
  Spec ref: `prd.md > Epic 7`, `spec.md > File Structure > scripts/`
  What to build: `scripts/seed_demo.py` (wipe DB + insert 3 clients demo). `demo-pdfs/` avec 8 PDFs : 3× EDF (#1 review new supplier, #2 auto-classified avec badge learning, #3 auto), 2× new suppliers (1 clean, 1 VAT mismatch), 1× duplicate EDF, 1× RIB (non-invoice → error), 1× Orange 4 pages. `demo-pdfs/README.md` documente chaque fichier et son comportement attendu. `scripts/capture_demo_artifacts.py` (Playwright async : wipe+seed, ingère les 8 PDFs via /upload réel, valide les cas en queue, trigger weekly_recap vers demo inbox, screenshots des 3 écrans + email + xlsx → `demo-assets/`).
  Acceptance: Run `python scripts/capture_demo_artifacts.py` → DB propre, 8 PDFs ingérés, screenshots générés dans `demo-assets/`, xlsx final présent, email recap reçu.
  Verify: Inspecter `demo-assets/` : 4+ screenshots (Upload avec batch, Queue, History avec download, Suppliers), `factures_2026-04.xlsx` ouvrable, preuve visuelle du "wow moment" EDF#1→#2 (badge Recognized 2nd time visible sur screenshot).

- [ ] **11. Deploy Render + env vars + smoke test URL publique**
  Spec ref: `spec.md > Runtime & Deployment`
  What to build: Créer le service Render web depuis le repo GitHub. Configurer tous les env vars (`SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GROQ_API_KEY`, `GEMINI_API_KEY`, `RESEND_API_KEY`, `RECAP_EMAIL`, `PUBLIC_URL`=URL Render). Dockerfile 2-stage (node build css → python:3.12-slim runtime). Vérifier que `render.yaml` match. Déclencher un deploy. Attendre build green.
  Acceptance: URL publique Render répond, `/health` retourne 200, upload d'une facture fonctionne end-to-end sur l'instance déployée.
  Verify: `curl https://ledgerly-xxxx.onrender.com/health` → 200. Ouvrir l'URL dans browser, drop une facture demo → voir la classification arriver en prod. Log Render montre les jobs APScheduler démarrés.

- [ ] **12. Devpost submission (GitHub repo + page + screenshots + video)**
  Spec ref: `prd.md > Submission Copy`, `prd.md > Epic 7`
  What to build: S'assurer que le repo GitHub est public et à jour (push final). Enregistrer une démo vidéo ≤2 min (drop EDF#1 → validation 1 clic → drop EDF#2 → auto-classified + badge → download xlsx → ouvrir xlsx → recap email), upload YouTube unlisted. Remplir le formulaire Devpost : Title "Ledgerly", Tagline, sections Inspiration/What it does/How we built it/Challenges/Accomplishments/What we learned/What's next (reprendre draft PRD), built-with tags (fastapi/htmx/tailwind/supabase/groq/gemini/python/render/resend), uploader screenshots de `demo-assets/`, attacher xlsx final en asset, lien repo GitHub, lien live Render, lien vidéo YouTube.
  Acceptance: Submission Devpost visible avec badge "Submitted", tous les champs requis remplis, liens (repo/live/video) fonctionnels, screenshots nets.
  Verify: Ouvrir la page submission Devpost, lire la description comme un juge qui ne connaît pas le projet → la valeur (bookkeeper's inbox on autopilot + wow moment learning) doit être évidente en 30 secondes. Cliquer chaque lien → tout fonctionne.

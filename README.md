# Ledgerly

Assistant d'ingestion de factures pour cabinets comptables français. Les collaborateurs déposent des PDF fournisseurs, Ledgerly extrait et classe les écritures automatiquement, puis livre un fichier Excel prêt à importer dans Sage.

> Pipeline zéro-friction : PDF en entrée, écriture comptable vérifiée en sortie, aucun service payant dans la stack.

**Démo en ligne** : https://ledgerly-2l30.onrender.com

---

## Sommaire

- [Pourquoi Ledgerly](#pourquoi-ledgerly)
- [Fonctionnalités](#fonctionnalités)
- [Architecture](#architecture)
- [Stack technique](#stack-technique)
- [Prise en main](#prise-en-main)
- [Configuration](#configuration)
- [Pipeline d'ingestion](#pipeline-dingestion)
- [Structure du projet](#structure-du-projet)
- [Scripts utilitaires](#scripts-utilitaires)
- [Tests](#tests)
- [Déploiement](#déploiement)
- [Documentation](#documentation)

---

## Pourquoi Ledgerly

Les cabinets comptables reçoivent chaque mois des centaines de factures fournisseurs à saisir manuellement dans Sage. Ledgerly automatise l'extraction, la détection de doublons, la mémorisation des comptes fournisseurs récurrents et la génération du fichier d'import — tout en gardant un humain dans la boucle pour valider les cas ambigus.

Objectifs produit :

- **Réduire le temps de saisie** d'un dossier mensuel de plusieurs heures à quelques minutes.
- **Éliminer les doublons** (même facture scannée deux fois, renvoi fournisseur, etc.).
- **Apprendre des fournisseurs récurrents** : un plan comptable affiné à chaque passage.
- **Rester auditable** : toute écriture passe par un écran de validation avant export.

## Fonctionnalités

- Dépôt multi-PDF par drag & drop (HTMX, sans build JS lourd).
- Extraction texte via `pdfplumber`, puis classification par LLM (Groq en primaire, Gemini en secours).
- Score de confiance par champ ; les lignes sous seuil partent en file de validation manuelle.
- Détection de doublons par hash de fichier + heuristique (fournisseur + date + montant).
- Mémoire fournisseurs : association compte comptable ↔ SIREN persistée entre sessions.
- Export Excel Sage-compatible (openpyxl) avec nommage normalisé.
- Historique des lots, recherche, filtres client-side instantanés.
- Dark mode automatique (préférence système).
- Récap e-mail programmé (APScheduler + Resend), déclenchable manuellement.

## Architecture

```
┌────────────┐   upload    ┌──────────────┐   extract    ┌───────────┐
│   Client   │ ──────────▶ │   FastAPI    │ ───────────▶ │ pdfplumber │
│   (HTMX)   │             │   routes/    │              └─────┬──────┘
└─────┬──────┘             └──────┬───────┘                    │
      │                           │ orchestrator               ▼
      │                           ▼                       ┌──────────┐
      │                    ┌──────────────┐   classify    │  Groq /  │
      │                    │  pipeline/   │ ────────────▶ │  Gemini  │
      │                    │ orchestrator │               └────┬─────┘
      │                    └──────┬───────┘                    │
      │                           ▼                            │
      │                   ┌───────────────┐                    │
      │      validate     │  confidence + │ ◀──────────────────┘
      │◀──────────────────│   duplicate   │
      │                   │   matcher     │
      │                   └──────┬────────┘
      │                          ▼
      │                   ┌──────────────┐   xlsx   ┌────────────┐
      └──────────────────▶│   Supabase   │ ───────▶ │  openpyxl  │
                          │  (PG + S3)   │          │   export   │
                          └──────────────┘          └────────────┘
```

## Stack technique

| Couche | Choix | Rôle |
|---|---|---|
| Backend | **FastAPI** (Python 3.12+) | API + rendu serveur Jinja2 |
| Front | **HTMX + Tailwind CSS** | Interactions sans SPA |
| Base de données | **Supabase** (Postgres managé) | Lots, factures, fournisseurs |
| Stockage blobs | **Supabase Storage** | PDF sources |
| LLM | **Groq** (Llama) + **Gemini** fallback | Extraction structurée |
| Parsing PDF | **pdfplumber** | Texte brut + layout |
| Export | **openpyxl** | Fichier Excel Sage |
| Jobs | **APScheduler** | Récaps périodiques |
| E-mail | **Resend** | Transactionnel |
| Hébergement | **Render** | Web service + cron |

## Prise en main

```bash
# 1. Cloner et configurer l'environnement
git clone git@github.com:SiriusRak/ledgerly.git
cd ledgerly
cp .env.example .env
# Renseigner les clés (voir section Configuration)

# 2. Installer les dépendances (Python 3.12+ requis)
pip install -e ".[dev]"

# 3. Appliquer les migrations Supabase
psql "$SUPABASE_DB_URL" -f migrations/001_init.sql

# 4. Compiler le CSS Tailwind
./scripts/build_css.sh

# 5. (Optionnel) Générer des PDF de démo
python scripts/generate_demo_pdfs.py
python scripts/seed_demo.py

# 6. Lancer le serveur
uvicorn app.main:app --reload
```

Ouvrir http://localhost:8000.

## Configuration

Variables d'environnement (`.env`) :

| Variable | Obligatoire | Description |
|---|---|---|
| `SUPABASE_URL` | oui | URL du projet Supabase |
| `SUPABASE_SERVICE_KEY` | oui | Clé service role (backend only) |
| `GROQ_API_KEY` | oui | Clé API Groq pour le LLM primaire |
| `GEMINI_API_KEY` | non | Fallback si Groq indisponible |
| `RESEND_API_KEY` | non | Envoi des récaps e-mail |
| `RECAP_EMAIL` | non | Destinataire du récap périodique |
| `PUBLIC_URL` | oui | URL publique (liens dans les e-mails) |

## Pipeline d'ingestion

Orchestré par `app/pipeline/orchestrator.py` :

1. **Upload** (`routes/upload.py`) — validation MIME, hash SHA-256, upload vers Supabase Storage.
2. **Extraction** (`pipeline/extractor.py`) — texte brut via pdfplumber.
3. **Classification** (`pipeline/llm.py`) — appel LLM structuré : fournisseur, date, HT, TVA, TTC, compte suggéré.
4. **Confiance** (`pipeline/confidence.py`) — score par champ, seuil configurable.
5. **Doublons** (`pipeline/duplicate.py`) — hash exact + fuzzy match (fournisseur + date + montant).
6. **Matcher fournisseur** (`pipeline/matcher.py`) — recherche par SIREN puis Levenshtein sur la raison sociale.
7. **Persistance** — écriture Postgres, statut `pending_validation` ou `ready`.
8. **Validation humaine** (`routes/validation.py`) — UI de correction, feedback réinjecté dans la mémoire fournisseur.
9. **Export** (`exporters/`) — génération XLSX nommé selon `services/xlsx_naming.py`.

## Structure du projet

```
app/
├── main.py              # bootstrap FastAPI + lifespan scheduler
├── config.py            # settings (pydantic-settings)
├── db.py                # client Supabase
├── routes/              # endpoints HTTP (health, upload, validation, history, suppliers)
├── pipeline/            # extraction / LLM / confiance / doublons / matcher
├── services/            # storage, mémoire fournisseur, nommage XLSX
├── exporters/           # génération Excel Sage
├── jobs/                # tâches APScheduler (récap e-mail)
└── templates/           # Jinja2 + HTMX

migrations/              # SQL Supabase
scripts/                 # outils dev (seed, build CSS, génération PDF démo)
tests/                   # pytest + smoke pipeline
docs/                    # PRD, spec, checklist, réflexion
static/                  # CSS compilé, assets
```

## Scripts utilitaires

| Script | Rôle |
|---|---|
| `scripts/build_css.sh` | Compile Tailwind vers `static/css/` |
| `scripts/generate_demo_pdfs.py` | Crée des factures fictives (reportlab) |
| `scripts/generate_fixture_pdf.py` | PDF de test unitaire |
| `scripts/seed_demo.py` | Peuple la base avec un jeu de démo |
| `scripts/capture_demo_artifacts.py` | Screenshots Playwright pour la démo |

## Tests

```bash
pytest                      # suite complète
pytest tests/test_pipeline_smoke.py   # smoke test end-to-end
ruff check .                # lint
```

Les tests couvrent : scoring de confiance, détection de doublons, matcher fournisseur, smoke du pipeline complet avec une fixture PDF.

## Déploiement

Déploiement Render via `render.yaml` (web service + variables d'env depuis le dashboard). Le `Dockerfile` fournit une image alternative pour tout hébergeur compatible.

Checklist pré-prod :

- Migrations Supabase appliquées sur l'environnement cible.
- Bucket Storage `invoices` créé avec policy service-role.
- Variables d'env renseignées côté Render.
- Domaine custom + HTTPS configurés.
- Cron récap programmé (APScheduler interne ou Render cron).

## Documentation

La documentation projet vit dans `docs/` :

- `prd.md` — vision produit et user stories
- `spec.md` — spécification technique détaillée
- `scope.md` — périmètre des itérations
- `checklist.md` — suivi de build
- `reflection.md` — rétrospective
- `learner-profile.md` — contexte utilisateur cible

---

**Licence** : usage interne. Contact : voir `RECAP_EMAIL` configuré.

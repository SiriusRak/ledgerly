# Ledgerly — Assistant d'ingestion de factures pour comptable en cabinet

## Idea
Drop des PDF de factures fournisseurs → extraction + catégorisation intelligente apprenante → rangement automatique → fichier Excel prêt à importer dans le logiciel comptable + récap hebdo par mail. Validation humaine uniquement sur les cas incertains.

## Who It's For

**Comptable en cabinet** (un·e collaborateur·rice qui traite les factures fournisseurs de plusieurs dossiers clients).

**Workflow actuel (réel, source : comptable accessible à l'utilisateur)** :
1. Facture arrive (mail / Drive / scan papier)
2. Ouvrir
3. Vérifier
4. **Saisir manuellement dans Excel** ← douleur principale
5. Importer le fichier Excel dans le logiciel comptable

**L'app remplace l'étape 4 sans toucher au reste.** Le fichier Excel reste le pivot. Le logiciel comptable et les habitudes ne changent pas. Friction d'adoption minimale, ROI immédiat.

## Inspiration & References

- **Pennylane / Dext / Receipt Bank** : références produit du marché, mais payantes et lourdes. On vise le même cœur de valeur (ingestion automatisée) sans la stack SaaS.
- **Sensibilité produit** : clean, sobre, fonctionnel. Pas de fioritures. Le comptable doit comprendre l'app en 30 secondes.
- **Design energy** : Tailwind par défaut, palette neutre, densité d'information assumée (les comptables aiment voir les données).

## Goals

1. **Démontrer (encore) que le SDD permet de produire une vraie app utilisable** — pas un POC, un produit qu'un comptable pourrait utiliser demain.
2. **Cartographier les zones SDD non couvertes par BMAD** — ce process `/scope → /prd → /spec → /checklist → /build → /iterate → /reflect` diverge de la séquence BMAD (analyste → PM → architecte → SM → dev). Documenter les divergences au fil du build.
3. **Toucher du tooling hors-Anthropic** (Groq, Gemini, HTMX) que l'écosystème BMAD pousse moins.
4. **Soumission Devpost** ancrée dans un user réel (comptable interviewée).

## What "Done" Looks Like

Une app web déployée sur Render à une URL publique. Trois écrans :

1. **Upload** : drag & drop de PDF de factures fournisseurs
2. **File de validation** : factures dont l'agent n'est pas confiant — affichage de l'extraction, 1 clic pour valider/corriger
3. **Historique** : factures traitées, filtrable, lien de téléchargement du `.xlsx` courant

**Le moment magique en démo** : drop d'une 1ère facture EDF → l'app demande validation (compte comptable + dossier client). Drop d'une 2e facture EDF → **passe toute seule, ligne ajoutée au .xlsx, PDF rangé**. Effet "elle apprend" évident.

**Critères de "done"** :
- Une vraie facture PDF native d'un vrai fournisseur peut être ingérée end-to-end
- Le `.xlsx` produit a le format colonnes du logiciel comptable cible (à figer au PRD)
- La mémoire fournisseur fonctionne (2e occurrence = auto)
- Détection de doublon fonctionnelle
- Récap hebdo envoyé par mail
- Déployé, accessible publiquement, sans clé de carte bancaire à la racine

## What's Explicitly Cut

| Coupé | Pourquoi |
|---|---|
| **OCR de scans / photos** | PDF natifs uniquement → pdfplumber suffit, pas de galère qualité d'image |
| **Multi-utilisateur / auth / permissions** | Mono-utilisateur en v1, on prouve la valeur avant de scaler |
| **Intégration directe avec Sage/EBP/Pennylane** | On reste sur l'export `.xlsx` que la comptable importe à la main, comme aujourd'hui |
| **Apprentissage par ML / fine-tuning** | Mémoire = simple table SQL "fournisseur → compte". Pas de modèle entraîné. |
| **Gestion des factures clients (sortantes)** | Scope = factures fournisseurs uniquement |
| **Workflow d'approbation multi-niveaux** | Validation = 1 personne, 1 clic |
| **Mobile / app native** | Web responsive Tailwind, suffit |
| **Intégration mail entrant (forward auto)** | Upload manuel uniquement v1. Le forward auto = v2 évidente. |
| **Détection d'anomalie avancée** (montant inhabituel, etc.) | Garde-fous = règles simples : doublon + cohérence TVA + fournisseur connu |

## Loose Implementation Notes

**Stack (validée en deepening B2)** :
- LLM principal : **Groq** (Llama 3.3 70B ou Qwen) — vitesse + free tier généreux
- LLM fallback : **Gemini Flash** — pour les PDFs où pdfplumber rend un texte trop dégradé
- Extraction PDF : **pdfplumber** (Python, gratuit, parfait pour PDF natifs)
- Backend : **FastAPI** (Python, async)
- Front : **HTMX + Tailwind** (server-rendered, mono-déploiement)
- DB : **Supabase** (Postgres free tier) — table fournisseurs, table factures, table file de validation
- Storage PDFs : **Supabase Storage**
- Hébergement : **Render free tier** — note : cold start ~30s à anticiper pour la démo
- Mail : **Resend free tier** (3000 mails/mois) — à confirmer
- Coût total visé : **0 €**

**Logique de confiance (γ — validation sur cas incertains uniquement)** :
- ✅ Confiant si : fournisseur déjà vu **ET** calcul TVA cohérent **ET** pas de doublon détecté
- ⚠️ Pas confiant sinon → file de validation
- Pas de scoring fin, pas de ML. Règles explicites, débuggables.

**Catégorisation = combinaison (a)+(b)+(c)** :
- (a) compte comptable suggéré (606, 613, 625…)
- (b) dossier client du cabinet (matching fournisseur ↔ client connu)
- (c) mémoire apprenante : 1ère fois = humain catégorise, fois suivantes = auto

**Convention de nommage PDFs rangés** : `2026-04_EDF_142.50.pdf` (à confirmer).

**Format de sortie .xlsx** : à figer au PRD une fois le logiciel comptable cible précisé (Sage / EBP / Pennylane / Cegid…). À demander à la comptable interviewée + récupérer un fichier exemple anonymisé si possible.

**Angle SDD à tisser dans les commandes suivantes** : à chaque étape, noter en `process-notes.md` ce qui diverge de la séquence/granularité BMAD (notamment : `/scope` comme phase autonome de discovery vs analyste BMAD, `/spec` vs architecture BMAD, granularité de l'interview, artefacts produits).

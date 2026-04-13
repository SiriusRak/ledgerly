# Process Notes

## /onboard

- **Profil technique** : dev IA/automatisation junior, 42, Python + TS quotidien, Claude Code daily driver. Niveau expérimenté.
- **Objectifs d'apprentissage** : (1) prouver à nouveau qu'on peut produire une belle app en SDD, (2) explorer les chemins SDD non couverts par BMAD — angle comparatif.
- **Sensibilité créative** : pragmatique/frugal — automatisations simples, pas de SaaS payant. Aucune référence culturelle. Défaut : clean & fonctionnel.
- **SDD préalable** : pratique quotidienne via BMAD. Tous les concepts (PRD, spec, context rot, flipped interaction) maîtrisés. Sauter les fondamentaux.
- **Énergie/style** : direct, concis, réponses courtes mais claires. Matcher le rythme — pas de blabla pédagogique.
- **Contexte d'arrivée** : a vu le mail Devpost, ça l'a tenté.

## /scope

**Évolution de l'idée** :
- Point de départ : aucune idée. Contraintes posées en premier (gratuit dev+prod, simple).
- Filtrage cible : automatisation pour non-techs → comptables.
- Sélection rapide parmi 3 directions proposées : "Inbox → ledger" (option #1) choisie d'emblée.
- Affinement : comptable en cabinet (vs TPE/freelance), validation sur cas incertains uniquement (γ), PDF natifs uniquement, sortie .xlsx format logiciel comptable + mail récap.

**Pushback / corrections du learner** :
- Sur le LLM : a contesté ma reco Gemini Flash en proposant Groq. Pertinent → adopté Groq + Gemini fallback. Bon réflexe d'ingénieur.
- Sur le déploiement : a poussé pour "vrai produit web" plutôt que démo Hugging Face Spaces → stack Render + Supabase assumée.

**Références qui ont résonné** :
- Pennylane / Dext implicite (l'option #1 du panel inspirations)
- Workflow réel d'une comptable accessible au learner → ancrage fort

**Deepening rounds** :
- Choisi B1 (ergonomie comptable réelle) puis B2 (stack technique). Skipped B3 (angle SDD comparatif) et B4 (features) → pari : on les traitera dans /prd et /spec.
- B1 a matériellement amélioré le scope : workflow réel (saisie Excel → import logiciel) a permis de cadrer "où l'app s'insère" au lieu de réinventer un workflow théorique. Format .xlsx standard (a) confirmé. Validation γ choisie en cohérence avec la catégo apprenante.
- B2 a tranché toute la stack avant le PRD → /prd et /spec pourront se concentrer sur le produit, pas sur les choix techniques.

**Active shaping** :
- Learner a contribué activement : Groq (proposition originale), pivot vers déploiement "vrai produit", insistance sur la sauvegarde du fichier Excel comme artefact.
- Réponses concises mais directives — pas passif. Matche le profil "expérimenté, direct".
- N'a pas demandé d'explications BMAD-comparatives en cours de route → l'angle comparatif sera à activer plus explicitement dans /prd ou /spec.

**Divergence vs BMAD à noter** :
- `/scope` est une phase autonome de discovery + tranche déjà la stack technique. Chez BMAD, ce travail serait éclaté entre Analyste (brainstorm/research) et Architecte (stack). Ici c'est fusionné en une conversation unique → plus rapide, mais demande au learner d'arbitrer tôt sur la technique.

## /prd

**Ce que le learner a ajouté vs scope** :
- Cible logiciel comptable précisée : **Sage** (scope disait "à figer au PRD"). Format colonnes choisi en "standard supposé" + note "à valider sur fichier réel".
- **UI chrome en anglais, données métier en français** : hybride assumé pour satisfaire juges Devpost + comptable réelle. Split décidé sur pushback learner (il voulait tout anglais au départ).
- **Badge "Recognized — EDF (3rd time)"** ajouté explicitement pour rendre l'apprentissage viscéral en démo.
- **Raccourcis clavier Enter/Tab/Esc** dans la file de validation retenus v1 (pas dans scope).
- **Script `capture_demo_artifacts.py`** + 8 PDFs scénarisés décidés comme livrable build, pas juste démo live.

**"What if" qui ont fait tilt** :
- **Cold start Render ~30s pendant démo** → cron keep-alive toutes les 10 min. Le learner n'y avait pas pensé dans le scope malgré la note "cold start à anticiper".
- **Mémoire globale vs par (fournisseur, dossier_client)** → réponse "yolo" = mémoire globale assumée, limitation documentée pour v2. Bon réflexe frugal.
- **Crash serveur pendant batch** → error + retry manuel (pas de resume auto). Pas vu venir avant la question.
- **SIRET comme clé primaire de matching** (vs nom normalisé seul) → accepté direct, petit insight de robustesse gratuit.

**Pushback notable** :
- **Rejet explicite des emojis "façon vibe coding"** → sauvegardé en mémoire globale feedback. Demande icônes Lucide / Heroicons partout. Signal design fort cohérent avec profil sobre/pragmatique.
- **UI en anglais** poussé initialement — a fallu proposer le split FR/EN pour qu'il valide. Tension Devpost (juges anglophones) vs user réelle (comptable FR).

**Scope guard** :
- Learner a **cut les 5 candidats** proposés (édition rétroactive, Settings, corbeille, filtres, bouton recap manuel) mais **pas par contrainte temps** — "nous ne sommes pas limités par 3-4h". Choix produit pour clarté de démo. Bonne discipline.
- A ajouté 1 v1 que j'avais noté cut potentiel : écran Known Suppliers read-only. Coût faible, valeur démo élevée.

**Deepening rounds** :
- Learner a choisi **"yolo pour a,b,c,d,e"** — tous les rounds. Rythme rafale assumé, réponses courtes en liste a/b/c/d.
- Round A (démo Devpost) : 8 PDFs scénarisés, vidéo 2 min, section "Submission copy" draftée dans PRD.
- Round B (états transitoires) : background tasks FastAPI + HTMX polling, bannière batch confinée à Upload, crash = error sans resume. Le plus gros bénéfice : anticipation d'une classe de bugs MVP classique.
- Round C (mémoire robuste) : SIRET primaire, normalisation + Levenshtein<3 secondaire. Pas d'appel LLM pour matching (déterministe, gratuit).
- Round D (divergences BMAD) : learner préfère l'approche Devpost pour sa simplicité ; réserve son jugement sur séparation des rôles "tant qu'il n'a pas vu le produit". Pragmatique, à rejuger en `/reflect`.
- Round E (polish) : pivot anglais UI, raccourcis clavier v1, badge learning v1, reste defer.

**Active shaping** :
- Learner **a fortement driven** : pivot UI anglais (correction active), rejet emojis (feedback explicite enregistré), limite 5 PDF (choix produit), "yolo" sur mémoire globale (choix frugal assumé).
- Sur les points qu'il ne tranchait pas (statuts comportement, corbeille, badge learning), il a laissé passer mes propositions sans pushback — confiance, pas passivité (il corrige quand il n'est pas d'accord).
- A **refusé de trancher sur divergence BMAD (Round D.b)** avec `"je ne peux pas l'affirmer ici car je ne vois pas encore le produit"` — meilleure réponse que le faux-consensus. À capturer pour `/reflect`.

**Divergences BMAD capturées dans le PRD** (section dédiée en bas du doc) :
- `/scope` empiète sur l'architecte (stack tranchée).
- `/prd` = interview serrée co-construite vs template PM rigide.
- Pas de NFR / assumptions / risks registries formalisés — remplacés par une section "Open Questions" unique.
- Acceptance criteria human-readable (pas QA-parseable) par choix explicite du learner.
- Jugement comparatif rôles reporté à `/reflect`.

## /spec

**Context à l'entrée** : stack déjà tranchée en /scope. /spec pivote en "implémentation-ready" (composants + contrats + file tree + data flow) plutôt que greenfield archi. Divergence BMAD explicite.

**Décisions techniques** :
- APScheduler in-process (pas de worker séparé) — single deploy, tradeoff crons perdus au crash mitigé par sweeper.
- Partie double Sage générée à l'export, non stockée — gain flexibilité règles TVA.
- Matcher déterministe zéro LLM / zéro pg_trgm — Levenshtein<3 full scan, OK <500 suppliers.
- Pas de table `validation_queue` — `state + state_reason` dans invoices suffisent.
- Tailwind CLI compilé (pas CDN) — learner choice, Dockerfile 2-stage.
- RPC Postgres `validate_invoice` pour garantir atomicité update+upsert cross-table (PostgREST ne fait pas transactions cross-table).

**Bouclages Open Questions PRD** :
- Schéma Sage réel fourni pendant /spec (PDF vierge de 13 colonnes) → PRD 9 col assumé invalidé. Mapping décidé : TVA via compte 44566 (partie double), Dossier client → export CSV enrichi séparé (choix learner "on peut avoir 2 exports"). Journal=HA v1 hardcodé.
- Keep-alive : cron maison APScheduler (learner choice "fait maison qui ping chaque 10mn"). Étendu à SELECT 1 Supabase (risque pause 7j découvert pendant research stack).

**Pushbacks / active shaping** :
- Learner a demandé une vraie table `clients` (j'avais proposé string libre). Bonne intuition relationnelle.
- Learner a demandé 2 exports (Sage strict + CSV enrichi) plutôt que de caser dossier_client dans Observation. Choix produit propre.
- Rythme rafale maintenu : réponses "1-ok 2-ok 3-..." systématiques. Matche le profil.

**Deepening rounds** :
- 0 round complet pris. Learner a skippé proposition error-strategy ("ne se soucie pas de ca"). Pari : /build tranchera live.
- Research docs Groq/Supabase/FastAPI/pdfplumber fait par agent (pas learner) et surface a découvert limite Supabase 7j inactivité — matériellement changé le design keep-alive.

**Divergences BMAD consolidées** :
- /spec = implémentation-ready, pas architecture greenfield (stack figée en /scope).
- Pas de C4 diagrams, pas de NFR registry.
- Self-review intégrée en "Open Issues" plutôt que cérémonie séparée.
- RPC Postgres compensant l'absence de transaction cross-table PostgREST → genre de contrainte d'impl qui serait cachée dans "contrats" BMAD; ici exposée explicitement au learner.

## /checklist

**Séquencement retenu** : infra → shell front → pipeline pur (extract+LLM, puis matcher/confidence testables isolés) → upload qui branche → queue → history/export → suppliers → jobs → demo → deploy → Devpost. Rationale : briques risquées (Groq JSON, matching déterministe) validées tôt sur vrais PDFs avant UI ; deploy en avant-dernier pour tester prod avant submission ; demo assets avant deploy pour que screenshots/xlsx/video soient prêts.

**Méthodologie choisie** :
- Build mode : **autonomous** (learner expérimenté, review > dictée).
- Verification : checkpoints tous les 3-4 items.
- Git : commit après chaque item (revert points).
- Comprehension checks : N/A.

**Granularité** : 12 items, ~5-6h cumul (au-delà du nominal 3-4h mais learner a accepté "ok pour tout" sans chercher à fusionner). Items atomiques ~15-40min, item 6 (validation queue) le plus gros — à surveiller, splittable si /build dérape.

**Submission planning** :
- Wow moment verrouillé : EDF#1 review → EDF#2 auto-classified + badge "Recognized 2nd time" → xlsx → email recap. Script vidéo dérive directement.
- Repo GitHub : à créer au premier commit (item 1). Assumed not existing yet.
- Demo inbox : learner OK (assumé sa propre adresse via `RECAP_EMAIL`, Open Question PRD non-bloquante).
- 4 screenshots cartographiés aux epics 1/2/3/5.

**Active shaping** : learner en mode rafale ("ok", "ok pour tout", "b"). Pas de pushback sur la séquence, pas de permutation demandée, skip deepening rounds comme en /spec. Cohérent avec le profil praticien + déjà 2 docs lourdes (PRD, spec) derrière — checklist = translation, pas re-design.

**Deepening rounds** : 0 (learner a pris l'option b "skip, génère direct"). Confiance dans la structure proposée, assumé par le profil.

**Divergences BMAD** : checklist BMAD (SM agent) découperait par story du PRD avec tasks fines ; ici la découpe est par **couche technique + dépendances** plutôt que par epic narratif. L'item 6 (validation queue) par exemple touche Epic 2 entièrement plus dépendances transversales (RPC DB + storage.move) — granularité plus système, moins user-story. À rejuger en /reflect.

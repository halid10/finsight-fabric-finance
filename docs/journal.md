# Journal de bord

Une entrée par session de travail : ce qui a été fait, décisions, problèmes rencontrés.

## 2026-11-22 — Démarrage

- Cadrage du projet FinSight (groupe fictif Novaris, 4 filiales, 3 devises).
- Choix d'architecture : Lakehouse médaillon + Direct Lake (voir `02-architecture.md`).
- Rédaction du backlog en 6 sprints (`BACKLOG.md`).
- Générateur de données en Python standard (aucune dépendance) pour pouvoir le lancer partout,
  y compris dans la CI.
- Notebooks au format d'intégration Git Fabric (`*.Notebook/notebook-content.py`).
- Mesures DAX fournies sous forme de requête `DEFINE MEASURE` pour être ajoutées en un clic
  depuis la vue Requête DAX.

**Prochaine étape** : vous — Sprint 0 (FS-03 à FS-06) dans votre tenant Fabric.

### Fin de session — livrables du dépôt

- Données : 69 385 lignes de GL, 10 881 factures clients, 2 436 factures fournisseurs, budget 2024-2026.
  Génération reproductible (graine 42) vérifiée par la CI.
- 9 tests de cohérence OK (écritures équilibrées, 411 = factures ouvertes, CA GL = factures, EBITDA 15 %).
- Notebooks nb_01 → nb_04 écrits ; harnais `tests/run_notebooks_local.py` pour les exécuter avec PySpark + Delta en CI
  (pas de Java sur le poste local : la 1re exécution réelle se fait dans GitHub Actions puis dans Fabric).
- Décision : budget de nov.-déc. 2026 converti au dernier taux connu (pas de taux futurs).
- Valeurs de référence : CA 2025 = 52,14 M€, EBITDA 2025 = 15,6 %, DSO au 31/10/2026 = 68 j.

### Publication sur GitHub & première exécution réelle des notebooks

- Dépôt publié : https://github.com/halid10/finsight-fabric-finance
- 1re exécution CI des notebooks (PySpark 3.5 + Delta 3.2) : bug trouvé dans `nb_03` — la fonction `cles()`
  joignait `dim_compte` sur les factures, qui n'ont pas de numéro de compte. Corrigé.
- Les erreurs des notebooks remontent désormais en annotations GitHub (lisibles sans connexion).
- CI verte : Bronze → Silver → Gold → 8 contrôles qualité OK, ingestion Bronze idempotente.

## 2026-11-23 — Schémas Lakehouse

- Décision : un Lakehouse unique **avec schémas** — `bronze`, `silver`, `gold` — au lieu de préfixes dans les noms de tables.
- Tables renommées : `bronze_x` → `bronze.x`, `silver_x` → `silver.x`, `dim_*`/`fact_*`/`dq_resultats` → `gold.*`.
- Chaque notebook crée son schéma (`CREATE SCHEMA IF NOT EXISTS`). Le Lakehouse doit être créé avec l'option « Lakehouse schemas ».
- Modèle sémantique : uniquement le schéma `gold` ; noms de tables et mesures DAX inchangés.

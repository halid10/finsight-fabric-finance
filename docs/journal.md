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

# FinSight — Plateforme d'analyse financière sur Microsoft Fabric & Power BI

> Projet de bout en bout (A → Z) : ingestion des données comptables d'un groupe multi-entités,
> architecture Lakehouse en médaillon (Bronze / Silver / Gold), modèle sémantique Direct Lake
> et rapports Power BI de pilotage financier (P&L, Budget vs Réel, Créances, Trésorerie).

![Fabric](https://img.shields.io/badge/Microsoft%20Fabric-Lakehouse-0078D4)
![Power BI](https://img.shields.io/badge/Power%20BI-Direct%20Lake-F2C811)
![PySpark](https://img.shields.io/badge/PySpark-Delta-E25A1C)
![CI](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF)

---

## 1. Le contexte métier

**Groupe Novaris** (entreprise fictive) est un groupe de services B2B composé de 4 filiales :

| Code entité | Pays | Devise | Activité |
|---|---|---|---|
| NOV-FR | France | EUR | Siège + conseil |
| NOV-BE | Belgique | EUR | Conseil |
| NOV-UK | Royaume-Uni | GBP | Logiciel (SaaS) |
| NOV-MA | Maroc | MAD | Centre de services partagés |

Aujourd'hui, le contrôle de gestion consolide **à la main dans Excel** les extractions de l'ERP de chaque
filiale. Le reporting mensuel prend **8 jours ouvrés** après la clôture, les chiffres diffèrent selon
qui les produit, et la direction n'a aucune visibilité sur le DSO ou la trésorerie en cours de mois.

**Objectif du projet** : livrer une plateforme unique, automatisée et gouvernée dans Microsoft Fabric,
qui produit un reporting financier fiable **à J+1** de chaque clôture.

👉 Détails : [docs/01-cadrage.md](docs/01-cadrage.md)

## 2. L'architecture

```mermaid
flowchart LR
    subgraph Sources["Sources (extractions ERP)"]
        A1[Grand livre<br/>CSV mensuels]
        A2[Factures clients / fournisseurs]
        A3[Budget]
        A4[Référentiels<br/>plan comptable, entités…]
        A5[Taux de change]
    end
    subgraph Fabric["Microsoft Fabric — Workspace FinSight"]
        B[(Lakehouse<br/>Files/raw)] --> C[Bronze<br/>Delta brut]
        C --> D[Silver<br/>nettoyé, typé, dédoublonné]
        D --> E[Gold<br/>schéma en étoile]
        P[[Data Pipeline<br/>orchestration quotidienne]] -.-> C & D & E
        E --> F[Modèle sémantique<br/>Direct Lake]
    end
    Sources --> B
    F --> G[Rapport Power BI<br/>FinSight - Pilotage financier]
    G --> H((Direction, DAF,<br/>contrôleurs))
```

👉 Détails : [docs/02-architecture.md](docs/02-architecture.md)

## 3. Contenu du dépôt

| Dossier | Contenu |
|---|---|
| [`docs/`](docs/) | Cadrage, architecture, modèle de données, guide pas-à-pas, dictionnaire des KPI, gouvernance, journal de bord |
| [`data/generator/`](data/generator/) | Générateur Python (bibliothèque standard uniquement) de données financières réalistes et cohérentes |
| [`data/raw/`](data/raw/) | Jeu de données généré, prêt à charger dans le Lakehouse |
| [`fabric/`](fabric/) | Notebooks PySpark au format Git Fabric (Bronze, Silver, Gold, qualité), pipeline, scripts SQL |
| [`powerbi/`](powerbi/) | Mesures DAX, spécification du modèle sémantique, maquette du rapport, sécurité RLS, thème |
| [`tests/`](tests/) | Tests automatisés de cohérence des données (écritures équilibrées, etc.) |
| [`BACKLOG.md`](BACKLOG.md) | **Toutes les tâches du projet**, par sprint, avec critères d'acceptation |

## 4. Démarrer

1. Lire le [cadrage](docs/01-cadrage.md) puis le [BACKLOG](BACKLOG.md).
2. (Optionnel) Régénérer les données : `python3 data/generator/generate_finance_data.py`
3. Suivre le **[guide d'implémentation pas-à-pas](docs/04-guide-implementation.md)** dans votre tenant Fabric
   (capacité d'essai Fabric gratuite de 60 jours suffisante).

## 5. Indicateurs livrés

Chiffre d'affaires · Marge brute · EBITDA · Résultat net · Budget & écarts · YTD / N-1 ·
DSO · DPO · Balance âgée · Encours clients · Trésorerie — voir le [dictionnaire des KPI](docs/05-dictionnaire-kpi.md).

## 6. Avancement

Le suivi détaillé est dans [BACKLOG.md](BACKLOG.md) et le [journal de bord](docs/journal.md).

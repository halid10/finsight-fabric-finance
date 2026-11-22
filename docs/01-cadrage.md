# 01 — Cadrage du projet FinSight

## 1. Problème

| Constat actuel | Impact |
|---|---|
| Consolidation manuelle de 4 exports ERP dans Excel | 8 jours ouvrés pour produire le reporting mensuel |
| Pas de référentiel unique (comptes, centres de coûts) | Chiffres différents selon l'auteur, perte de confiance |
| Conversion de devises faite « à la main » | Erreurs de change sur l'UK (GBP) et le Maroc (MAD) |
| Aucun suivi des créances en cours de mois | DSO en dérive non détecté (trésorerie tendue) |
| Budget dans un fichier séparé | Analyse Budget vs Réel tardive et partielle |

## 2. Objectifs (SMART)

1. **Réduire le délai de reporting** de J+8 à **J+1** après chargement de la clôture.
2. **Une seule version de la vérité** : 100 % des KPI calculés dans un modèle sémantique certifié.
3. **Fiabilité** : écart entre balance générale source et Gold = **0,00 €** (contrôle automatique).
4. **Pilotage du BFR** : DSO et balance âgée disponibles quotidiennement.
5. **Sécurité** : chaque directeur de filiale ne voit que son entité (RLS).

## 3. Périmètre

**Inclus (v1)**
- 4 entités, historique janvier 2024 → octobre 2026 (34 mois)
- Grand livre (écritures comptables), factures clients (AR), factures fournisseurs (AP)
- Budget annuel mensualisé 2024, 2025, 2026
- Taux de change mensuels (moyen et clôture) vers EUR
- Rapport Power BI de 7 pages + RLS par entité

**Exclus (v2 éventuelle)**
- Éliminations intercompagnies de consolidation
- Prévisions (forecast) par machine learning
- Connexion directe à l'ERP (v1 = fichiers d'extraction déposés)

## 4. Parties prenantes

| Rôle | Personne (fictive) | Attentes |
|---|---|---|
| Sponsor | Directrice Administrative et Financière (DAF) | Reporting J+1, fiabilité |
| Utilisateurs clés | Contrôleurs de gestion (4) | Budget vs Réel, analyse des écarts |
| Utilisateurs | Directeurs de filiales | Vue limitée à leur entité |
| Trésorier | Responsable trésorerie | DSO, DPO, position de cash |
| Équipe data | Data engineer / Analytics engineer (vous) | Construire et maintenir la plateforme |
| IT / Sécurité | Admin tenant Fabric | Gouvernance, accès, capacités |

## 5. Questions métier auxquelles le rapport doit répondre

1. Quel est notre chiffre d'affaires, notre marge et notre EBITDA ce mois-ci et en cumul annuel ?
2. Sommes-nous en avance ou en retard sur le budget ? Sur quels comptes / centres de coûts ?
3. Comment évolue-t-on par rapport à l'année précédente ?
4. Quelle filiale contribue le plus au résultat du groupe (en EUR) ?
5. Combien nos clients nous doivent-ils, et depuis combien de temps (balance âgée) ? Quel est le DSO ?
6. Quels sont les 10 clients les plus en retard ?
7. Combien devons-nous à nos fournisseurs ? Quel est le DPO ?
8. Quelle est notre position de trésorerie et sa tendance ?

## 6. Livrables

| # | Livrable | Emplacement |
|---|---|---|
| L1 | Jeu de données sources réaliste | `data/` |
| L2 | Lakehouse `lh_finsight` avec couches Bronze/Silver/Gold | `fabric/notebooks` |
| L3 | Pipeline d'orchestration quotidien | `fabric/pipelines` |
| L4 | Contrôles qualité automatisés | `fabric/notebooks/nb_04_*` |
| L5 | Modèle sémantique Direct Lake + mesures DAX | `powerbi/semantic-model` |
| L6 | Rapport Power BI 7 pages | `powerbi/report` |
| L7 | Sécurité RLS + gouvernance | `docs/06-gouvernance-securite.md` |
| L8 | Documentation complète | `docs/` |

## 7. Planning (6 sprints d'une semaine)

| Sprint | Thème | Résultat attendu |
|---|---|---|
| 0 | Cadrage & mise en place | Workspace, Lakehouse, Git connecté |
| 1 | Données sources & Bronze | Fichiers chargés en tables Delta brutes |
| 2 | Silver | Données nettoyées, typées, dédoublonnées |
| 3 | Gold & qualité | Schéma en étoile + contrôles de réconciliation |
| 4 | Modèle sémantique | Direct Lake, relations, mesures DAX |
| 5 | Rapport Power BI | 7 pages, RLS, thème |
| 6 | Industrialisation | Pipeline planifié, déploiement Dev→Prod, documentation |

## 8. Risques

| Risque | Probabilité | Mitigation |
|---|---|---|
| Capacité d'essai Fabric expirée | Moyenne | Garder tout le code dans Git → reconstruction en 30 min |
| Mauvaise conversion de devise | Moyenne | Table de taux unique + test de réconciliation |
| Fallback Direct Lake → DirectQuery | Faible | Tables Gold optimisées (V-Order, peu de colonnes) |
| Données sources de mauvaise qualité | Élevée | Couche Silver + notebook de contrôles qualité |

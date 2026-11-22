# BACKLOG — Projet FinSight

Légende :
- 🤖 **Livré dans le dépôt** : le code / la doc existe déjà ici, il reste à l'exécuter ou le relire.
- 🧑‍💻 **À faire dans Fabric / Power BI** : action manuelle de votre côté dans le tenant.
- `[ ]` à faire · `[x]` terminé

Chaque tâche a un identifiant (`FS-xx`) à réutiliser dans les messages de commit et les branches
(ex. `feature/FS-21-silver-gl`).

---

## Sprint 0 — Cadrage & mise en place

| ID | Tâche | Type | Statut |
|---|---|---|---|
| FS-01 | Rédiger le cadrage (problème, objectifs, périmètre, KPI) | 🤖 | [x] |
| FS-02 | Définir l'architecture médaillon et les conventions de nommage | 🤖 | [x] |
| FS-03 | Activer un essai Fabric (ou une capacité F2+) sur votre tenant | 🧑‍💻 | [ ] |
| FS-04 | Créer le workspace `FinSight-DEV` et l'associer à la capacité | 🧑‍💻 | [ ] |
| FS-05 | Créer le Lakehouse `lh_finsight` | 🧑‍💻 | [ ] |
| FS-06 | Connecter le workspace à ce dépôt GitHub (Workspace settings → Git integration, dossier `fabric/`) | 🧑‍💻 | [ ] |

**Critères d'acceptation** : le workspace affiche le Lakehouse vide et le statut Git « Synced ».

## Sprint 1 — Données sources & Bronze

| ID | Tâche | Type | Statut |
|---|---|---|---|
| FS-10 | Écrire le générateur de données financières (GL, AR, AP, budget, FX, référentiels) | 🤖 | [x] |
| FS-11 | Écrire les tests de cohérence (écritures équilibrées, factures ↔ GL) | 🤖 | [x] |
| FS-12 | Charger `data/raw/` dans `Files/raw/` du Lakehouse (upload du dossier) | 🧑‍💻 | [ ] |
| FS-13 | Notebook `nb_01_bronze_ingestion` (CSV → Delta, colonnes techniques, idempotence) | 🤖 | [x] |
| FS-14 | Exécuter `nb_01` et vérifier les 10 tables `bronze_*` | 🧑‍💻 | [ ] |

**Critères d'acceptation** : `bronze_ecritures_gl` contient autant de lignes que la somme des CSV mensuels ;
relancer le notebook ne crée aucun doublon.

## Sprint 2 — Silver

| ID | Tâche | Type | Statut |
|---|---|---|---|
| FS-20 | Notebook `nb_02_silver_transform` : typage, trim, normalisation | 🤖 | [x] |
| FS-21 | Dédoublonnage du GL et des factures (doublons injectés à la source) | 🤖 | [x] |
| FS-22 | Centre de coûts manquant → `NON_AFFECTE` | 🤖 | [x] |
| FS-23 | Conversion en EUR via taux moyen mensuel (P&L) | 🤖 | [x] |
| FS-24 | Exécuter `nb_02` et comparer volumes Bronze vs Silver (le delta = doublons) | 🧑‍💻 | [ ] |

**Critères d'acceptation** : aucune clé dupliquée en Silver ; toutes les lignes ont un `montant_eur` non nul.

## Sprint 3 — Gold & qualité

| ID | Tâche | Type | Statut |
|---|---|---|---|
| FS-30 | Notebook `nb_03_gold_star_schema` : dimensions + faits | 🤖 | [x] |
| FS-31 | `dim_date` complète avec exercice fiscal, trimestre, flags | 🤖 | [x] |
| FS-32 | `dim_compte` avec hiérarchie du compte de résultat (lignes P&L, ordre, signe) | 🤖 | [x] |
| FS-33 | `fact_ar` : jours de retard, tranches de balance âgée | 🤖 | [x] |
| FS-34 | Notebook `nb_04_data_quality` : 8 contrôles + table `dq_resultats` | 🤖 | [x] |
| FS-35 | Exécuter `nb_03` + `nb_04` ; tous les contrôles doivent être `OK` | 🧑‍💻 | [ ] |
| FS-36 | Interroger le SQL analytics endpoint avec `fabric/sql/controles_gold.sql` | 🧑‍💻 | [ ] |

**Critères d'acceptation** : la somme du GL en Gold = somme Silver (écart 0,00) ; chaque fait a ses clés de dimension.

## Sprint 4 — Modèle sémantique

| ID | Tâche | Type | Statut |
|---|---|---|---|
| FS-40 | Spécifier le modèle (tables, relations, colonnes masquées) | 🤖 | [x] |
| FS-41 | Écrire les mesures DAX (P&L, budget, time intelligence, BFR, trésorerie) | 🤖 | [x] |
| FS-42 | Créer le modèle sémantique Direct Lake `sm_finsight` depuis le Lakehouse | 🧑‍💻 | [ ] |
| FS-43 | Créer les relations et marquer `dim_date` comme table de dates | 🧑‍💻 | [ ] |
| FS-44 | Ajouter les mesures via la vue Requête DAX (`powerbi/semantic-model/measures.dax`) | 🧑‍💻 | [ ] |
| FS-45 | Organiser les mesures en dossiers d'affichage, formats, descriptions | 🧑‍💻 | [ ] |

**Critères d'acceptation** : CA 2025 du modèle = CA 2025 calculé en SQL ; aucun fallback DirectQuery.

## Sprint 5 — Rapport Power BI

| ID | Tâche | Type | Statut |
|---|---|---|---|
| FS-50 | Maquette des 7 pages et choix des visuels | 🤖 | [x] |
| FS-51 | Thème JSON aux couleurs FinSight | 🤖 | [x] |
| FS-52 | Page 1 — Synthèse direction | 🧑‍💻 | [ ] |
| FS-53 | Page 2 — Compte de résultat (matrice hiérarchique) | 🧑‍💻 | [ ] |
| FS-54 | Page 3 — Budget vs Réel | 🧑‍💻 | [ ] |
| FS-55 | Page 4 — Créances clients & DSO | 🧑‍💻 | [ ] |
| FS-56 | Page 5 — Fournisseurs & DPO | 🧑‍💻 | [ ] |
| FS-57 | Page 6 — Trésorerie | 🧑‍💻 | [ ] |
| FS-58 | Page 7 — Détail des écritures (drillthrough) | 🧑‍💻 | [ ] |
| FS-59 | Rôles RLS par entité + test « Afficher en tant que » | 🧑‍💻 | [ ] |

**Critères d'acceptation** : un utilisateur du rôle `Directeur NOV-UK` ne voit que NOV-UK ; tous les KPI de la page 1
correspondent à `docs/05-dictionnaire-kpi.md`.

## Sprint 6 — Industrialisation

| ID | Tâche | Type | Statut |
|---|---|---|---|
| FS-60 | Définition du pipeline `pl_finsight_daily` | 🤖 | [x] |
| FS-61 | Créer le pipeline dans Fabric, le planifier à 06:00, alerte e-mail en échec | 🧑‍💻 | [ ] |
| FS-62 | CI GitHub Actions (lint + génération + tests) | 🤖 | [x] |
| FS-63 | Créer les workspaces TEST et PROD + pipeline de déploiement | 🧑‍💻 | [ ] |
| FS-64 | Règles de déploiement (Lakehouse par environnement) | 🧑‍💻 | [ ] |
| FS-65 | Certifier le modèle sémantique, appliquer une étiquette de confidentialité | 🧑‍💻 | [ ] |
| FS-66 | Créer une App Power BI pour les utilisateurs finaux | 🧑‍💻 | [ ] |
| FS-67 | Capturer des écrans du rapport dans `docs/img/` et compléter le README | 🧑‍💻 | [ ] |

## Idées v2 (non planifiées)

- FS-70 Chargement incrémental du GL avec `MERGE` (Delta) au lieu du rechargement complet Silver
- FS-71 Éliminations intercompagnies (refacturations NOV-MA → autres filiales)
- FS-72 Prévision de trésorerie (notebook ML / régression)
- FS-73 Data Activator : alerte si DSO > 60 jours
- FS-74 Paramétrage des notebooks par environnement (variables library)

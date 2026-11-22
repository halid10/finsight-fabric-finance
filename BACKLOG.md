# BACKLOG — Projet FinSight

> 🗂️ **Le suivi vivant est dans Jira** : projet **FinSight** (clé `KAN`).
> Un epic par sprint (`KAN-4` à `KAN-10`, idées v2 `KAN-11`), une tâche par ligne ci-dessous.
> Labels : `claude` = livré dans le dépôt, `fabric` = à faire dans le tenant (assigné à Halid), `sprint-N`, `v2`.
> Convention : citer la clé Jira dans les branches et commits (`feature/KAN-20-upload-raw`, `fix(gold): ... (KAN-28)`)
> pour que l'application *GitHub for Jira* relie automatiquement le code aux tickets.

Légende :
- 🤖 **Livré dans le dépôt** : le code / la doc existe déjà ici, il reste à l'exécuter ou le relire.
- 🧑‍💻 **À faire dans Fabric / Power BI** : action manuelle de votre côté dans le tenant.
- `[ ]` à faire · `[x]` terminé

Chaque tâche a un identifiant historique `FS-xx` et sa clé Jira `KAN-xx` (à utiliser dans les branches et commits).

---

## Sprint 0 — Cadrage & mise en place

| ID | Jira | Tâche | Type | Statut |
|---|---|---|---|---|
| FS-01 | KAN-12 | Rédiger le cadrage (problème, objectifs, périmètre, KPI) | 🤖 | [x] |
| FS-02 | KAN-13 | Définir l'architecture médaillon et les conventions de nommage | 🤖 | [x] |
| FS-03 | KAN-14 | Activer un essai Fabric (ou une capacité F2+) sur votre tenant | 🧑‍💻 | [ ] |
| FS-04 | KAN-15 | Créer le workspace `FinSight-DEV` et l'associer à la capacité | 🧑‍💻 | [ ] |
| FS-05 | KAN-16 | Créer le Lakehouse `lh_finsight` | 🧑‍💻 | [ ] |
| FS-06 | KAN-17 | Connecter le workspace à ce dépôt GitHub (Paramètres → Intégration Git, dossier `fabric/workspace`) | 🧑‍💻 | [ ] |

**Critères d'acceptation** : le workspace affiche le Lakehouse vide et le statut Git « Synced ».

## Sprint 1 — Données sources & Bronze

| ID | Jira | Tâche | Type | Statut |
|---|---|---|---|---|
| FS-10 | KAN-18 | Écrire le générateur de données financières (GL, AR, AP, budget, FX, référentiels) | 🤖 | [x] |
| FS-11 | KAN-19 | Écrire les tests de cohérence (écritures équilibrées, factures ↔ GL) | 🤖 | [x] |
| FS-12 | KAN-20 | Charger `data/raw/` dans `Files/raw/` du Lakehouse (upload du dossier) | 🧑‍💻 | [ ] |
| FS-13 | KAN-21 | Notebook `nb_01_bronze_ingestion` (CSV → Delta, colonnes techniques, idempotence) | 🤖 | [x] |
| FS-14 | KAN-22 | Exécuter `nb_01` et vérifier les 11 tables `bronze_*` | 🧑‍💻 | [ ] |

**Critères d'acceptation** : `bronze_ecritures_gl` contient autant de lignes que la somme des CSV mensuels ;
relancer le notebook ne crée aucun doublon.

## Sprint 2 — Silver

| ID | Jira | Tâche | Type | Statut |
|---|---|---|---|---|
| FS-20 | KAN-23 | Notebook `nb_02_silver_transform` : typage, trim, normalisation | 🤖 | [x] |
| FS-21 | KAN-24 | Dédoublonnage du GL et des factures (doublons injectés à la source) | 🤖 | [x] |
| FS-22 | KAN-25 | Centre de coûts manquant → `NON_AFFECTE` | 🤖 | [x] |
| FS-23 | KAN-26 | Conversion en EUR via taux moyen mensuel (P&L) | 🤖 | [x] |
| FS-24 | KAN-27 | Exécuter `nb_02` et comparer volumes Bronze vs Silver (le delta = doublons) | 🧑‍💻 | [ ] |

**Critères d'acceptation** : aucune clé dupliquée en Silver ; toutes les lignes ont un `montant_eur` non nul.

## Sprint 3 — Gold & qualité

| ID | Jira | Tâche | Type | Statut |
|---|---|---|---|---|
| FS-30 | KAN-28 | Notebook `nb_03_gold_star_schema` : dimensions + faits | 🤖 | [x] |
| FS-31 | KAN-29 | `dim_date` complète avec exercice fiscal, trimestre, flags | 🤖 | [x] |
| FS-32 | KAN-30 | `dim_compte` avec hiérarchie du compte de résultat (lignes P&L, ordre, signe) | 🤖 | [x] |
| FS-33 | KAN-31 | `fact_ar` : jours de retard, tranches de balance âgée | 🤖 | [x] |
| FS-34 | KAN-32 | Notebook `nb_04_data_quality` : 8 contrôles + table `dq_resultats` | 🤖 | [x] |
| FS-35 | KAN-33 | Exécuter `nb_03` + `nb_04` ; tous les contrôles doivent être `OK` | 🧑‍💻 | [ ] |
| FS-37 | KAN-35 | Valeurs de référence des KPI calculées depuis les CSV (`tests/valeurs_reference.py`) | 🤖 | [x] |
| FS-36 | KAN-34 | Interroger le SQL analytics endpoint avec `fabric/sql/controles_gold.sql` | 🧑‍💻 | [ ] |

**Critères d'acceptation** : la somme du GL en Gold = somme Silver (écart 0,00) ; chaque fait a ses clés de dimension.

## Sprint 4 — Modèle sémantique

| ID | Jira | Tâche | Type | Statut |
|---|---|---|---|---|
| FS-40 | KAN-36 | Spécifier le modèle (tables, relations, colonnes masquées) | 🤖 | [x] |
| FS-41 | KAN-37 | Écrire les mesures DAX (P&L, budget, time intelligence, BFR, trésorerie) | 🤖 | [x] |
| FS-42 | KAN-38 | Créer le modèle sémantique Direct Lake `sm_finsight` depuis le Lakehouse | 🧑‍💻 | [ ] |
| FS-43 | KAN-39 | Créer les relations et marquer `dim_date` comme table de dates | 🧑‍💻 | [ ] |
| FS-44 | KAN-40 | Ajouter les mesures via la vue Requête DAX (`powerbi/semantic-model/measures.dax`) | 🧑‍💻 | [ ] |
| FS-45 | KAN-41 | Organiser les mesures en dossiers d'affichage, formats, descriptions | 🧑‍💻 | [ ] |

**Critères d'acceptation** : CA 2025 du modèle = CA 2025 calculé en SQL ; aucun fallback DirectQuery.

## Sprint 5 — Rapport Power BI

| ID | Jira | Tâche | Type | Statut |
|---|---|---|---|---|
| FS-50 | KAN-42 | Maquette des 7 pages et choix des visuels | 🤖 | [x] |
| FS-51 | KAN-43 | Thème JSON aux couleurs FinSight | 🤖 | [x] |
| FS-52 | KAN-44 | Page 1 — Synthèse direction | 🧑‍💻 | [ ] |
| FS-53 | KAN-45 | Page 2 — Compte de résultat (matrice hiérarchique) | 🧑‍💻 | [ ] |
| FS-54 | KAN-46 | Page 3 — Budget vs Réel | 🧑‍💻 | [ ] |
| FS-55 | KAN-47 | Page 4 — Créances clients & DSO | 🧑‍💻 | [ ] |
| FS-56 | KAN-48 | Page 5 — Fournisseurs & DPO | 🧑‍💻 | [ ] |
| FS-57 | KAN-49 | Page 6 — Trésorerie | 🧑‍💻 | [ ] |
| FS-58 | KAN-50 | Page 7 — Détail des écritures (drillthrough) | 🧑‍💻 | [ ] |
| FS-59 | KAN-51 | Rôles RLS par entité + test « Afficher en tant que » | 🧑‍💻 | [ ] |

**Critères d'acceptation** : un utilisateur du rôle `Directeur NOV-UK` ne voit que NOV-UK ; tous les KPI de la page 1
correspondent à `docs/05-dictionnaire-kpi.md`.

## Sprint 6 — Industrialisation

| ID | Jira | Tâche | Type | Statut |
|---|---|---|---|---|
| FS-60 | KAN-52 | Définition du pipeline `pl_finsight_daily` | 🤖 | [x] |
| FS-61 | KAN-53 | Créer le pipeline dans Fabric, le planifier à 06:00, alerte e-mail en échec | 🧑‍💻 | [ ] |
| FS-62 | KAN-54 | CI GitHub Actions (lint + génération + tests + exécution PySpark des notebooks) | 🤖 | [x] |
| FS-63 | KAN-55 | Créer les workspaces TEST et PROD + pipeline de déploiement | 🧑‍💻 | [ ] |
| FS-64 | KAN-56 | Règles de déploiement (Lakehouse par environnement) | 🧑‍💻 | [ ] |
| FS-65 | KAN-57 | Certifier le modèle sémantique, appliquer une étiquette de confidentialité | 🧑‍💻 | [ ] |
| FS-66 | KAN-58 | Créer une App Power BI pour les utilisateurs finaux | 🧑‍💻 | [ ] |
| FS-67 | KAN-59 | Capturer des écrans du rapport dans `docs/img/` et compléter le README | 🧑‍💻 | [ ] |

## Idées v2 (non planifiées)

- FS-70 (KAN-60) Chargement incrémental du GL avec `MERGE` (Delta) au lieu du rechargement complet Silver
- FS-71 (KAN-61) Éliminations intercompagnies (refacturations NOV-MA → autres filiales)
- FS-72 (KAN-62) Prévision de trésorerie (notebook ML / régression)
- FS-73 (KAN-63) Data Activator : alerte si DSO > 60 jours
- FS-75 (KAN-65) Trésorerie convertie au taux de clôture (actuellement taux moyen des mouvements)
- FS-74 (KAN-64) Paramétrage des notebooks par environnement (variables library)

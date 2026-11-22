# 04 — Guide d'implémentation pas à pas

Ce guide suit le [BACKLOG](../BACKLOG.md). Durée estimée : **1 à 2 jours** de travail effectif.
Chaque étape indique la tâche correspondante (`FS-xx`) : cochez-la dans le backlog une fois terminée.

---

## Sprint 0 — Mise en place

### FS-03 · Obtenir une capacité Fabric
1. Aller sur <https://app.fabric.microsoft.com> avec un compte professionnel ou scolaire (Entra ID).
   *Un compte personnel Outlook/Gmail ne fonctionne pas* : utiliser un tenant Microsoft 365 Developer ou celui de votre entreprise.
2. Icône de profil (en haut à droite) → **Démarrer l'essai** (*Start trial*) → capacité d'essai Fabric (60 jours, équivalent F64).

### FS-04 · Créer le workspace
1. **Espaces de travail → + Nouvel espace de travail** → nom `FinSight-DEV`.
2. *Avancé* → mode de licence **Essai** (ou capacité Fabric) → Appliquer.

### FS-05 · Créer le Lakehouse
1. Dans le workspace : **+ Nouvel élément → Lakehouse** → nom `lh_finsight`.
   *Ne cochez pas* « schémas de Lakehouse » (les notebooks utilisent le schéma par défaut `dbo`).

### FS-06 · Connecter Git (GitHub)
1. **Paramètres de l'espace de travail → Intégration Git → GitHub**.
2. Ajouter un compte GitHub : nom d'affichage + **jeton d'accès personnel** *(fine-grained, accès Contents en lecture/écriture sur ce dépôt)* — saisissez-le vous-même.
3. Dépôt : ce dépôt · Branche : `main` · **Dossier Git : `fabric/workspace`** → Connecter et synchroniser.
4. Les 4 notebooks `nb_01` à `nb_04` apparaissent dans le workspace.
5. Ouvrir chaque notebook → panneau **Explorateur** → *Ajouter une source de données* → **Lakehouses existants** → `lh_finsight`
   (il devient le Lakehouse par défaut). Valider le changement dans *Contrôle de code source → Commit*.

✅ *Critère* : statut Git « Synchronisé », 4 notebooks + 1 Lakehouse visibles.

---

## Sprint 1 — Bronze

### FS-12 · Charger les fichiers sources
1. Ouvrir `lh_finsight` → section **Files** → `…` → **Nouveau sous-dossier** → `raw`.
2. Sur `raw` : `…` → **Charger → Charger un dossier** et sélectionnez successivement les 6 dossiers de `data/raw/`
   (`referentiels`, `gl`, `factures_clients`, `factures_fournisseurs`, `budget`, `taux_change`).
   *Alternative* : OneLake File Explorer (Windows) et copier-coller du dossier `raw`.
3. Vérifier : `Files/raw/gl` contient 34 fichiers `ecritures_gl_YYYYMM.csv`.

### FS-14 · Exécuter `nb_01_bronze_ingestion`
1. Ouvrir le notebook → **Exécuter tout**.
2. Résultat attendu : 11 tables `bronze_*` dans **Tables** (rafraîchir l'explorateur).
3. Relancer le notebook : le message doit indiquer « 0 à charger » pour le GL (idempotence).

💡 *À comprendre* : pourquoi tout est en `string` en Bronze ? → pour ne jamais perdre une ligne à cause d'un format inattendu ;
le typage est la responsabilité de Silver.

---

## Sprint 2 — Silver

### FS-24 · Exécuter `nb_02_silver_transform`
1. **Exécuter tout**. La dernière cellule affiche le nombre de doublons supprimés.
2. Attendu : environ **140 doublons** dans le GL et **6** dans les factures clients.
3. Explorer `silver_ecritures_gl` : `code_cc = NON_AFFECTE` sur ~25 lignes, colonnes `*_eur` remplies.

---

## Sprint 3 — Gold & qualité

### FS-35 · Exécuter `nb_03` puis `nb_04`
1. `nb_03_gold_star_schema` → 6 tables `dim_*` + 5 tables `fact_*`. La dernière cellule affiche le P&L annuel.
2. `nb_04_data_quality` → 8 contrôles ✅. En cas de ❌, l'exception indique le contrôle fautif.

### FS-36 · SQL analytics endpoint
1. En haut à droite du Lakehouse : basculer sur **SQL analytics endpoint**.
2. **Nouvelle requête SQL** → coller [`fabric/sql/controles_gold.sql`](../fabric/sql/controles_gold.sql) → exécuter requête par requête.
3. Comparer la requête 1 avec les [valeurs de référence](05-dictionnaire-kpi.md#valeurs-de-référence-pour-valider-le-rapport).

---

## Sprint 4 — Modèle sémantique

### FS-42 · Créer le modèle Direct Lake
1. Dans le Lakehouse : **Nouveau modèle sémantique** → nom `sm_finsight`.
2. Cocher uniquement les tables Gold : `dim_*` et `fact_*` → Confirmer.

### FS-43 · Relations et table de dates
1. Ouvrir le modèle (**Ouvrir le modèle de données**), passer en mode **Modification**.
2. Créer les relations listées dans [`model-spec.md`](../powerbi/semantic-model/model-spec.md#2-relations-toutes-plusieurs-à-un-filtrage-unidirectionnel)
   (glisser la clé du fait vers la clé de la dimension). Les relations sur `date_paiement_key` doivent être **inactives**.
3. Sélectionner `dim_date` → **Marquer comme table de dates** → colonne `date`.
4. Appliquer les tris (*Trier par colonne*) et masquer les colonnes techniques (section 3 de la spec).

### FS-44 · Ajouter les mesures
1. Ouvrir la vue **Requête DAX** (icône en bas à gauche).
2. Coller l'intégralité de [`measures.dax`](../powerbi/semantic-model/measures.dax) → **Exécuter**.
   Le résultat affiche CA, EBITDA, DSO… par année : comparer avec les valeurs de référence.
3. Cliquer **Mettre à jour le modèle avec les modifications** (en haut de la requête) → les ~60 mesures sont créées.

### FS-45 · Finitions
- Dossiers d'affichage et formats selon les commentaires de `measures.dax`.
- Descriptions des mesures (copier la définition du [dictionnaire des KPI](05-dictionnaire-kpi.md)).

✅ *Critère* : `CA` filtré sur 2025 = **52,14 M€**.

---

## Sprint 5 — Rapport

### FS-51 à FS-58 · Construire les pages
1. Depuis le modèle : **Nouveau rapport** (ou Power BI Desktop → *OneLake data hub* → `sm_finsight` → *Se connecter*).
2. **Affichage → Thèmes → Parcourir** → [`theme-finsight.json`](../powerbi/report/theme-finsight.json).
3. Construire les 7 pages selon [`report-spec.md`](../powerbi/report/report-spec.md).
4. Enregistrer sous `FinSight - Pilotage financier` dans `FinSight-DEV`.

### FS-59 · RLS
Suivre [06-gouvernance-securite.md §2](06-gouvernance-securite.md#2-sécurité-au-niveau-des-lignes-rls) puis tester avec « Tester en tant que rôle ».

---

## Sprint 6 — Industrialisation

| Tâche | Où | Guide |
|---|---|---|
| FS-61 Pipeline quotidien | Workspace → Data pipeline | [`pl_finsight_daily.md`](../fabric/pipelines/pl_finsight_daily.md) |
| FS-63 Environnements | Créer `FinSight-TEST`, `FinSight-PROD` + **Pipeline de déploiement** (3 étapes) | [06 §4](06-gouvernance-securite.md#4-cycle-de-vie-alm) |
| FS-64 Règles de déploiement | Pipeline de déploiement → étape TEST → *Règles de déploiement* → modèle sémantique | |
| FS-65 Certification | Paramètres du modèle → Approbation → Certifié | |
| FS-66 App | Workspace PROD → **Créer une application** | |
| FS-67 Captures | `docs/img/` + section « Aperçu » dans le README | |

Après chaque modification dans Fabric (notebook, etc.) : panneau **Contrôle de code source → Commit**, puis `git pull` en local.

---

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `AnalysisException: Path does not exist: Files/raw/...` | Pas de Lakehouse par défaut, ou dossier mal nommé | Attacher `lh_finsight` au notebook, vérifier `Files/raw/gl` |
| `NameError: notebookutils` | Ancien runtime | Paramètres du workspace → Spark → Runtime **1.3** |
| Colonnes `_eur` vides | Taux de change non chargés | Vérifier `bronze_taux_change`, relancer nb_02 |
| Visuels lents / « DirectQuery » dans l'analyseur de performances | Fallback Direct Lake | Vérifier qu'aucune table SQL view n'est utilisée ; réexécuter `OPTIMIZE` |
| Mesure DAX en erreur après « Mettre à jour le modèle » | Nom de table/colonne différent | Comparer avec `dim_*`/`fact_*` du Lakehouse (sensible aux accents) |

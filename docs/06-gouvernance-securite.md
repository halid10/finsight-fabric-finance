# 06 — Gouvernance & sécurité

## 1. Rôles dans les workspaces

| Groupe Entra ID (à créer) | FinSight-DEV | FinSight-TEST | FinSight-PROD |
|---|---|---|---|
| `GRP-FinSight-DataEng` | Administrateur | Membre | Contributeur |
| `GRP-FinSight-Controleurs` | — | Lecteur (recette) | — (accès via l'App) |
| `GRP-FinSight-Lecteurs` | — | — | — (accès via l'App) |

Principe : **personne ne lit les données directement dans le Lakehouse de PROD**, les utilisateurs passent par l'App Power BI.
Le rôle Lecteur du workspace donne accès au SQL endpoint : ne pas l'attribuer aux utilisateurs métier.

## 2. Sécurité au niveau des lignes (RLS)

Définie dans le modèle sémantique (*Gérer les rôles*), sur la table `dim_entite` : le filtre se propage à tous les faits.

| Rôle | Filtre DAX sur `dim_entite` | Membres |
|---|---|---|
| `Groupe` | *(aucun filtre)* | DAF, contrôleurs groupe |
| `Directeur NOV-FR` | `[code_entite] = "NOV-FR"` | Directeur France |
| `Directeur NOV-BE` | `[code_entite] = "NOV-BE"` | Directeur Belgique |
| `Directeur NOV-UK` | `[code_entite] = "NOV-UK"` | Directeur UK |
| `Directeur NOV-MA` | `[code_entite] = "NOV-MA"` | Directeur Maroc |

**Test** : Modèle sémantique → *Sécurité* → *Tester en tant que rôle* → `Directeur NOV-UK` : seules les données NOV-UK apparaissent
et le CA « groupe » devient celui de NOV-UK.

### Option avancée : RLS dynamique (une seule règle)

1. Ajouter un fichier `referentiels/securite_acces.csv` (`email;code_entite`) et une table Gold `dim_securite`.
2. Relation `dim_securite[code_entite]` → `dim_entite[code_entite]` (filtrage bidirectionnel + « Appliquer le filtre de sécurité dans les deux sens »).
3. Rôle unique `Accès entité` : `dim_securite` → `[email] = USERPRINCIPALNAME()`.

### Point d'attention Direct Lake

Avec RLS, si le modèle bascule en DirectQuery (fallback), la sécurité du SQL endpoint s'applique aussi.
Configurer le modèle avec une **connexion cloud à identité fixe** (*Paramètres → Informations d'identification de la source*)
pour que seule la RLS du modèle s'applique.

## 3. Étiquettes de confidentialité & certification

- Étiquette **Confidentiel – Finance** sur le Lakehouse, le modèle sémantique et le rapport (héritée en aval).
- Modèle sémantique **certifié** (badge) une fois la recette validée → source unique pour les rapports libre-service.
- Approbation (*endorsement*) « Promu » sur le rapport.

## 4. Cycle de vie (ALM)

| Étape | Outil | Règle |
|---|---|---|
| Développement | Branche `feature/FS-xx-...` | Une branche par tâche du backlog |
| Revue | Pull Request GitHub | CI verte obligatoire + 1 relecture |
| Intégration | `main` synchronisée avec `FinSight-DEV` | Bouton *Update all* dans le panneau Source control |
| Recette | Pipeline de déploiement DEV → TEST | Validation par un contrôleur |
| Production | TEST → PROD | Fenêtre de déploiement après la clôture mensuelle |

Règles de déploiement : le modèle sémantique de chaque environnement pointe vers le Lakehouse de son workspace.

## 5. Surveillance

- Table `gold.dq_resultats` : historique des contrôles qualité, à exposer dans une page « Santé des données » (optionnel).
- Pipeline : alerte e-mail (activité *Office 365 Outlook*) en cas d'échec.
- *Monitoring hub* Fabric : durée des exécutions, consommation de la capacité (Fabric Capacity Metrics app).

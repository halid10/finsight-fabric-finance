# Maquette du rapport « FinSight - Pilotage financier »

Format de page : 16:9 (1280 × 720). Thème : [`theme-finsight.json`](theme-finsight.json).
Bandeau commun à toutes les pages : titre de la page à gauche, mesure `[Titre rapport]` à droite,
segments **Année**, **Entité** et **Mois** synchronisés entre les pages (Affichage → Synchroniser les segments).

Règle de couleur : **vert = favorable, rouge = défavorable** (écarts positifs = favorables, cf. convention de signe).

---

## Page 1 — Synthèse direction

*Question : « Où en sommes-nous ce mois-ci et depuis le début de l'année ? »*

```
┌──────────────────────────────────────────────────────────────────────────────┐
│ Synthèse direction                            FinSight — arrêté au 31/10/2026 │
│ [Année ▼] [Entité ▼] [Mois ▼]                                                 │
├────────────┬────────────┬────────────┬────────────┬────────────┬─────────────┤
│ CA YTD     │ EBITDA YTD │ EBITDA %   │ Rés. net   │ DSO        │ Trésorerie  │
│ vs N-1 ▲   │ vs budget  │            │ YTD        │ (jours)    │             │
├────────────┴────────────┴──────┬─────┴────────────┴────────────┴─────────────┤
│ CA mensuel : Réel (colonnes)   │ EBITDA par entité (barres horizontales)      │
│ vs Budget (ligne) vs N-1       │                                              │
├────────────────────────────────┼──────────────────────────────────────────────┤
│ Cascade (waterfall) CA → RN    │ Carte des entités (pays) : CA                │
└────────────────────────────────┴──────────────────────────────────────────────┘
```

| Visuel | Champs |
|---|---|
| 6 cartes KPI (nouveau visuel *Card*) | `CA YTD` + référence `CA YTD N-1` · `EBITDA YTD` + `Budget YTD` · `EBITDA %` · `Résultat net YTD` · `DSO (jours)` · `Trésorerie` |
| Graphique combiné | Axe `dim_date[annee_mois]` ; colonnes `CA` ; lignes `CA Budget`, `CA N-1` |
| Barres horizontales | Axe `dim_entite[code_entite]` ; valeur `EBITDA` ; info-bulle `EBITDA %` |
| Cascade | Catégorie `dim_compte[ligne_pnl]` ; valeur `Montant P&L` |
| Carte remplie | Emplacement `dim_entite[pays]` ; saturation `CA` |

## Page 2 — Compte de résultat

*Question : « Comment se construit notre résultat ? »*

| Visuel | Champs |
|---|---|
| Matrice | Lignes : hiérarchie `dim_compte` (Ligne P&L → Compte) ; Colonnes : `dim_date[mois_court]` ; Valeur : `Montant P&L` ; sous-totaux de lignes activés |
| Matrice (variante) | Lignes : Ligne P&L ; Valeurs : `Réel`, `Budget à date`, `Écart budget à date`, `Écart budget %`, `CA N-1` |
| Segment | `dim_entite[code_entite]`, `dim_centre_cout[departement]` |

Mise en forme conditionnelle : icônes sur `Écart budget %` (▲ vert si ≥ 0, ▼ rouge sinon).

## Page 3 — Budget vs Réel

*Question : « Où dérivons-nous par rapport au budget ? »*

| Visuel | Champs |
|---|---|
| Jauge | Valeur `CA YTD` ; cible `Budget YTD` (filtré sur CA) |
| Barres groupées | Axe `dim_centre_cout[libelle_cc]` ; valeurs `Réel`, `Budget à date` (charges) |
| Tableau Top écarts | `dim_compte[compte_libelle]`, `Réel`, `Budget à date`, `Écart budget à date` trié par écart croissant (pires d'abord) |
| Courbe | Axe mois ; `Écart YTD` cumulé |
| Arbre de décomposition | Analyser `Écart budget à date` par Entité → Département → Compte |

## Page 4 — Créances clients & DSO

*Questions : « Combien nos clients nous doivent-ils ? Qui paie en retard ? »*

| Visuel | Champs |
|---|---|
| Cartes | `Encours clients`, `% Encours échu`, `DSO (jours)`, `Nb factures ouvertes` |
| Courbe | Axe `annee_mois` ; `DSO (jours)` (ligne de référence constante à 60 j) |
| Histogramme empilé (balance âgée) | Axe `fact_factures_clients[tranche_age]` (sans « Réglée ») ; valeur `Encours à l'arrêté` ; légende `dim_entite[code_entite]` |
| Tableau Top 10 clients en retard | `dim_client[raison_sociale]`, `segment`, `Encours à l'arrêté`, `Retard moyen de paiement (jours)` ; filtre Top N = 10 sur `Encours à l'arrêté` et `tranche_age` ≠ Non échue |
| Nuage de points | X `Retard moyen de paiement (jours)` ; Y `CA facturé TTC` ; détail `dim_client[raison_sociale]` ; légende `segment` |

## Page 5 — Fournisseurs & DPO

| Visuel | Champs |
|---|---|
| Cartes | `Encours fournisseurs`, `DPO (jours)`, `Achats TTC` |
| Barres | Axe `dim_fournisseur[categorie]` ; valeur `Achats TTC` |
| Courbe | DSO vs DPO par mois (écart = besoin de financement) |
| Tableau | Fournisseurs : `raison_sociale`, `categorie`, `Achats TTC`, `Encours fournisseurs` |

## Page 6 — Trésorerie

| Visuel | Champs |
|---|---|
| Aires | Axe `annee_mois` ; `Trésorerie` (fin de mois) par entité |
| Colonnes | `Entrées de trésorerie` vs `Sorties de trésorerie` par mois |
| Cartes | `Trésorerie`, `Variation de trésorerie`, `BFR clients - fournisseurs` |
| Courbe | `Encaissements clients` vs `Décaissements fournisseurs` |

## Page 7 — Détail des écritures (drillthrough)

- Page masquée, **extraction** (drillthrough) sur `dim_compte[compte_libelle]`, `dim_entite[code_entite]`, `dim_date[annee_mois]`.
- Tableau : `num_ecriture`, `dim_date[date]`, `journal`, `libelle`, `reference_piece`, `dim_centre_cout[libelle_cc]`, `Réel`.
- Bouton « Retour ».

## Navigation & accessibilité

- Navigateur de pages (visuel *Page navigator*) en haut de chaque page.
- Info-bulles de page sur les visuels mensuels : `CA`, `EBITDA %`, `Écart budget %`.
- Texte alternatif sur chaque visuel, contraste conforme (thème testé), ordre de tabulation défini.

# Données sources

Données **fictives** générées par [`generator/generate_finance_data.py`](generator/generate_finance_data.py)
(graine fixe `42` → résultat reproductible). Elles imitent des extractions d'ERP d'un groupe à 4 filiales.

```bash
python3 data/generator/generate_finance_data.py            # régénère data/raw (≈ 1 seconde)
python3 -m unittest discover -s tests -v                  # vérifie la cohérence
```

## Arborescence `raw/` (à charger tel quel dans `Files/raw/` du Lakehouse)

| Dossier / fichier | Lignes | Description |
|---|---|---|
| `referentiels/entites.csv` | 4 | Filiales, pays, devise |
| `referentiels/plan_comptable.csv` | 31 | Comptes (classe, nature PRODUIT/CHARGE/ACTIF/PASSIF) |
| `referentiels/mapping_pnl.csv` | 18 | Compte → ligne du compte de résultat + ordre d'affichage |
| `referentiels/centres_couts.csv` | 8 | Centres de coûts et département |
| `referentiels/clients.csv` | 300 | Clients (secteur, segment, délai de paiement) |
| `referentiels/fournisseurs.csv` | ~120 | Fournisseurs par catégorie d'achat |
| `gl/ecritures_gl_YYYYMM.csv` | ~70 000 au total | Grand livre, **1 fichier par mois** (janv. 2024 → oct. 2026) |
| `factures_clients/factures_clients.csv` | ~10 900 | Factures de vente + date de paiement |
| `factures_fournisseurs/factures_fournisseurs.csv` | ~2 400 | Factures d'achat + date de paiement |
| `budget/budget_YYYY.csv` | ~4 900 au total | Budget mensuel entité × compte × centre de coûts |
| `taux_change/taux_change.csv` | 102 | Taux moyen et de clôture mensuels → EUR (1 unité devise = x EUR) |

## Format

- Séparateur **`;`**, décimales avec **virgule** (`12974,41`), UTF-8.
- Dates du GL : `yyyy-MM-dd` ; dates des factures : `dd/MM/yyyy`.
- Montants en **devise locale** de l'entité (EUR, GBP ou MAD).
- Date d'extraction : **31/10/2026** — les factures non réglées à cette date ont le statut `OUVERTE`.

## Règles comptables simulées

| Flux | Journal | Écriture |
|---|---|---|
| Bilan d'ouverture | AN | 512 + 218 / 101 + 106 + 164 |
| Facture client | VT | D 411 (TTC) / C 706 (HT) + C 44571 (TVA) |
| Encaissement | BQ | D 512 / C 411 |
| Facture fournisseur | AC | D 6xx (HT) + D 44566 (TVA) / C 401 (TTC) |
| Paiement fournisseur | BQ | D 401 / C 512 |
| Paie | PA | D 641 + 645 / C 421 + 431 |
| Amortissements | OD | D 681 / C 2818 |
| Impôt sur les sociétés | OD | D 695 / C 444 |

Toutes les écritures sont équilibrées, le solde du 411 = encours des factures ouvertes (vérifié par les tests).

## Anomalies volontaires (à traiter en Silver)

| Anomalie | Où | Traitement attendu |
|---|---|---|
| Lignes dupliquées (~0,2 %) | `gl/*.csv` | Dédoublonnage sur `num_ecriture` + `num_ligne` |
| 6 factures exportées en double | `factures_clients.csv` | Dédoublonnage sur `num_facture` |
| Espaces parasites | `clients.raison_sociale` | `trim` |
| Codes clients en minuscules (~1 %) | `factures_clients.code_client` | `upper` |
| Centre de coûts vide (~1 % des achats) | `gl` (journal AC) | Remplacer par `NON_AFFECTE` |
| Décimales à virgule | partout | Conversion en `decimal(18,2)` |

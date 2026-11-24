# 05 — Dictionnaire des KPI

Toutes les valeurs sont en **EUR**, converties au taux moyen du mois comptable.
Convention : produits positifs, charges négatives ; un écart positif est **favorable**.
Les formules DAX complètes (et ces définitions, en description de chaque mesure) sont dans le script
[`powerbi/semantic-model/sm_finsight.tmdl`](../powerbi/semantic-model/sm_finsight.tmdl).

## Compte de résultat

| KPI | Définition métier | Calcul |
|---|---|---|
| **Chiffre d'affaires (CA)** | Prestations et abonnements facturés | Σ crédit − débit, comptes 706xxx |
| **Coût des ventes** | Sous-traitance et licences / hébergement revendus | comptes 604, 607 |
| **Marge brute** | CA − coût des ventes | agrégat « Marge brute » |
| **Marge brute %** | Marge brute / CA | |
| **Charges externes** | Loyers, honoraires, marketing, déplacements, logiciels… | comptes 606 à 651 |
| **Charges de personnel** | Salaires bruts + charges sociales | comptes 641, 645 |
| **EBITDA** | Résultat avant amortissements, financier et impôt | Marge brute + charges externes + personnel |
| **EBITDA %** | EBITDA / CA | |
| **Résultat d'exploitation (EBIT)** | EBITDA − dotations aux amortissements | + compte 681 |
| **Résultat net** | Somme de tous les comptes de résultat | classes 6 et 7 |

## Budget

| KPI | Définition |
|---|---|
| **Budget** | Budget mensualisé (même convention de signe que le réel) |
| **Budget à date** | Budget limité aux mois clôturés (≤ date d'arrêté) |
| **Écart budget** | Réel − Budget (positif = favorable) |
| **Écart budget %** | Écart / \|Budget\| |
| **Taux de réalisation CA** | CA réel / CA budget |

## Intelligence temporelle (groupe de calcul `Intelligence temporelle`, colonne `Période`)

Applicable à toutes les mesures numériques ci-dessus.

| KPI | Définition |
|---|---|
| **YTD** | Cumul depuis le 1er janvier de l'année sélectionnée |
| **N-1** | Même période l'année précédente |
| **Var N-1 %** | (N − N-1) / \|N-1\| |
| **12 mois glissants** | Somme des 12 derniers mois jusqu'à la fin de la période sélectionnée |

## BFR et trésorerie

| KPI | Définition | Calcul |
|---|---|---|
| **Encours clients** | Montant TTC dû par les clients à la date de référence | factures émises ≤ date et non réglées à cette date |
| **Encours échu** | Partie de l'encours dont l'échéance est dépassée | + échéance < date |
| **DSO** (Days Sales Outstanding) | Délai moyen d'encaissement | Encours clients / CA TTC 90 derniers jours × 90 |
| **Balance âgée** | Encours à l'arrêté réparti par retard | tranches Non échue, 0-30, 31-60, 61-90, > 90 j |
| **Retard moyen de paiement** | Retard pondéré par le montant (factures réglées) | Σ(retard × TTC) / Σ TTC |
| **Encours fournisseurs** | Montant TTC dû aux fournisseurs | idem côté achats |
| **DPO** (Days Payable Outstanding) | Délai moyen de paiement des fournisseurs | Encours fournisseurs / achats TTC 90 j × 90 |
| **Trésorerie** | Solde du compte 512 à la date de référence | cumul des mouvements 512 |
| **BFR clients − fournisseurs** | Besoin de financement lié au cycle d'exploitation (simplifié) | Encours clients − encours fournisseurs |

*Date de référence* = dernier jour de la période filtrée, plafonné à la date d'arrêté (31/10/2026).

## Valeurs de référence (pour valider le rapport)

Calculées directement sur les CSV par [`tests/valeurs_reference.py`](../tests/valeurs_reference.py), toutes entités :

| Année | CA réel (M€) | CA budget (M€) | EBITDA (M€) | EBITDA % | Résultat net (M€) |
|---|---|---|---|---|---|
| 2024 | 47,43 | 45,80 | 7,30 | 15,4 % | 4,96 |
| 2025 | 52,14 | 51,33 | 8,14 | 15,6 % | 5,59 |
| 2026 (janv.–oct.) | 45,81 | 57,51 *(année entière)* | 7,17 | 15,7 % | 4,86 |

Encours clients au 31/10/2026 : **12,23 M€** — DSO : **68 jours**.

> ✅ Critère d'acceptation FS-42 : la carte `CA` filtrée sur 2025 affiche **52,14 M€**.

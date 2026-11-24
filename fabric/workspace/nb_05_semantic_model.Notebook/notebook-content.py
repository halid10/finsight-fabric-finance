# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_05 — Modèle sémantique sm_finsight (relations, groupe de calcul, mesures)
#
# **Fichier généré** par `powerbi/semantic-model/generate_tmdl.py` — ne pas modifier dans Fabric : modifier le générateur.
#
# Applique au modèle Direct Lake **`sm_finsight`** (via la bibliothèque *semantic-link-labs* / TOM) :
#
# | Étape | Détail |
# |---|---|
# | Paramétrage | mesures implicites découragées, `dim_date` = table de dates, tris, colonnes techniques masquées |
# | Relations | 16 relations (2 inactives sur la date de paiement) — ignorées si elles existent déjà |
# | Groupe de calcul | « Intelligence temporelle » (recréé à chaque exécution) |
# | Mesures | 47 mesures avec description, dossier et format (créées ou mises à jour) |
# | Contrôle | requête DAX : CA, EBITDA, DSO… par année, à comparer aux valeurs de référence |
#
# Idempotent : peut être relancé après chaque modification des définitions.
#
# ⚠️ Prérequis : le modèle `sm_finsight` existe (KAN-38) et contient les tables `dim_*` / `fact_*` du schéma `gold`.

# PARAMETERS CELL ********************

modele = "sm_finsight"   # nom du modèle sémantique
workspace = None          # None = workspace courant


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

# Installation de semantic-link-labs pour la session (bibliothèque Microsoft, PyPI)
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "semantic-link-labs"])


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import json

DEFS = json.loads(r'''{
 "relations": [
  {
   "nom": "fact_gl_date",
   "de": "fact_gl.date_key",
   "vers": "dim_date.date_key",
   "active": true
  },
  {
   "nom": "fact_gl_entite",
   "de": "fact_gl.entite_key",
   "vers": "dim_entite.entite_key",
   "active": true
  },
  {
   "nom": "fact_gl_compte",
   "de": "fact_gl.compte_key",
   "vers": "dim_compte.compte_key",
   "active": true
  },
  {
   "nom": "fact_gl_centre_cout",
   "de": "fact_gl.cc_key",
   "vers": "dim_centre_cout.cc_key",
   "active": true
  },
  {
   "nom": "fact_budget_date",
   "de": "fact_budget.date_key",
   "vers": "dim_date.date_key",
   "active": true
  },
  {
   "nom": "fact_budget_entite",
   "de": "fact_budget.entite_key",
   "vers": "dim_entite.entite_key",
   "active": true
  },
  {
   "nom": "fact_budget_compte",
   "de": "fact_budget.compte_key",
   "vers": "dim_compte.compte_key",
   "active": true
  },
  {
   "nom": "fact_budget_centre_cout",
   "de": "fact_budget.cc_key",
   "vers": "dim_centre_cout.cc_key",
   "active": true
  },
  {
   "nom": "fact_factures_clients_date_facture",
   "de": "fact_factures_clients.date_key",
   "vers": "dim_date.date_key",
   "active": true
  },
  {
   "nom": "fact_factures_clients_date_paiement",
   "de": "fact_factures_clients.date_paiement_key",
   "vers": "dim_date.date_key",
   "active": false
  },
  {
   "nom": "fact_factures_clients_entite",
   "de": "fact_factures_clients.entite_key",
   "vers": "dim_entite.entite_key",
   "active": true
  },
  {
   "nom": "fact_factures_clients_tiers",
   "de": "fact_factures_clients.client_key",
   "vers": "dim_client.client_key",
   "active": true
  },
  {
   "nom": "fact_factures_fournisseurs_date_facture",
   "de": "fact_factures_fournisseurs.date_key",
   "vers": "dim_date.date_key",
   "active": true
  },
  {
   "nom": "fact_factures_fournisseurs_date_paiement",
   "de": "fact_factures_fournisseurs.date_paiement_key",
   "vers": "dim_date.date_key",
   "active": false
  },
  {
   "nom": "fact_factures_fournisseurs_entite",
   "de": "fact_factures_fournisseurs.entite_key",
   "vers": "dim_entite.entite_key",
   "active": true
  },
  {
   "nom": "fact_factures_fournisseurs_tiers",
   "de": "fact_factures_fournisseurs.fournisseur_key",
   "vers": "dim_fournisseur.fournisseur_key",
   "active": true
  }
 ],
 "groupe_calcul": {
  "nom": "Intelligence temporelle",
  "colonne": "Période",
  "precedence": 10,
  "description": "Variantes temporelles applicables à toutes les mesures numériques (YTD, N-1, variations, 12 mois glissants).",
  "elements": [
   {
    "nom": "Période",
    "expression": "SELECTEDMEASURE ()",
    "format": null,
    "description": "Valeur de la période filtrée (comportement par défaut)."
   },
   {
    "nom": "YTD",
    "expression": "IF (\n\tISSELECTEDMEASURE ( [Titre rapport], [Libellé période], [Date d'arrêté], [Date de référence], [Écart budget indicateur] ),\n\tSELECTEDMEASURE (),\n\tCALCULATE ( SELECTEDMEASURE (), DATESYTD ( dim_date[date] ) )\n)",
    "format": null,
    "description": "Cumul depuis le 1er janvier jusqu'à la fin de la période filtrée."
   },
   {
    "nom": "N-1",
    "expression": "IF (\n\tISSELECTEDMEASURE ( [Titre rapport], [Libellé période], [Date d'arrêté], [Date de référence], [Écart budget indicateur] ),\n\tSELECTEDMEASURE (),\n\tCALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dim_date[date] ) )\n)",
    "format": null,
    "description": "Même période l'année précédente."
   },
   {
    "nom": "YTD N-1",
    "expression": "IF (\n\tISSELECTEDMEASURE ( [Titre rapport], [Libellé période], [Date d'arrêté], [Date de référence], [Écart budget indicateur] ),\n\tSELECTEDMEASURE (),\n\tCALCULATE ( SELECTEDMEASURE (), DATESYTD ( SAMEPERIODLASTYEAR ( dim_date[date] ) ) )\n)",
    "format": null,
    "description": "Cumul annuel de l'année précédente, à date équivalente."
   },
   {
    "nom": "Var N-1",
    "expression": "IF (\n\tISSELECTEDMEASURE ( [Titre rapport], [Libellé période], [Date d'arrêté], [Date de référence], [Écart budget indicateur] ),\n\tSELECTEDMEASURE (),\n\tVAR _n = SELECTEDMEASURE ()\n\tVAR _n1 = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dim_date[date] ) )\n\tRETURN IF ( NOT ISBLANK ( _n ) && NOT ISBLANK ( _n1 ), _n - _n1 )\n)",
    "format": null,
    "description": "Écart en valeur avec la même période de l'année précédente (N − N-1)."
   },
   {
    "nom": "Var N-1 %",
    "expression": "IF (\n\tISSELECTEDMEASURE ( [Titre rapport], [Libellé période], [Date d'arrêté], [Date de référence], [Écart budget indicateur] ),\n\tSELECTEDMEASURE (),\n\tVAR _n = SELECTEDMEASURE ()\n\tVAR _n1 = CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dim_date[date] ) )\n\tRETURN DIVIDE ( _n - _n1, ABS ( _n1 ) )\n)",
    "format": "\"+0.0 %;-0.0 %;0.0 %\"",
    "description": "Écart relatif avec la même période de l'année précédente : (N − N-1) / |N-1|."
   },
   {
    "nom": "12 mois glissants",
    "expression": "IF (\n\tISSELECTEDMEASURE ( [Titre rapport], [Libellé période], [Date d'arrêté], [Date de référence], [Écart budget indicateur] ),\n\tSELECTEDMEASURE (),\n\tCALCULATE ( SELECTEDMEASURE (), DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH ) )\n)",
    "format": null,
    "description": "Somme des 12 derniers mois jusqu'à la fin de la période filtrée."
   }
  ]
 },
 "mesures": [
  {
   "table": "fact_gl",
   "nom": "Réel",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Montant du compte de résultat en EUR : crédit − débit (produits positifs, charges négatives) sur les comptes filtrés.",
   "expression": "SUM ( fact_gl[montant_pnl_eur] )"
  },
  {
   "table": "fact_gl",
   "nom": "CA",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Chiffre d'affaires : prestations et abonnements facturés (comptes 706xxx).",
   "expression": "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Chiffre d'affaires\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Coût des ventes",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Sous-traitance, licences et hébergement revendus (comptes 604, 607). Valeur négative.",
   "expression": "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Coût des ventes\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Marge brute",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Chiffre d'affaires + coût des ventes.",
   "expression": "CALCULATE ( [Réel], dim_compte[agregat] = \"Marge brute\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Charges externes",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Loyers, honoraires, marketing, déplacements, télécoms, logiciels… (comptes 606 à 651). Valeur négative.",
   "expression": "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Charges externes\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Charges de personnel",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Salaires bruts + charges sociales (comptes 641, 645). Valeur négative.",
   "expression": "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Charges de personnel\" )"
  },
  {
   "table": "fact_gl",
   "nom": "EBITDA",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Résultat avant amortissements, résultat financier et impôt.",
   "expression": "CALCULATE ( [Réel], dim_compte[agregat] IN { \"Marge brute\", \"EBITDA\" } )"
  },
  {
   "table": "fact_gl",
   "nom": "Résultat d'exploitation",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "EBITDA − dotations aux amortissements (EBIT).",
   "expression": "CALCULATE ( [Réel], dim_compte[agregat] IN { \"Marge brute\", \"EBITDA\", \"Résultat d'exploitation\" } )"
  },
  {
   "table": "fact_gl",
   "nom": "Résultat net",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Somme de tous les comptes de résultat (classes 6 et 7).",
   "expression": "CALCULATE ( [Réel], dim_compte[est_compte_resultat] = TRUE () )"
  },
  {
   "table": "fact_gl",
   "nom": "Montant P&L",
   "dossier": "1. Compte de résultat",
   "format": "#,##0 €",
   "description": "Pour la matrice du compte de résultat : masque les comptes de bilan ; le total général vaut le résultat net.",
   "expression": "CALCULATE ( [Réel], KEEPFILTERS ( dim_compte[est_compte_resultat] = TRUE () ) )"
  },
  {
   "table": "fact_gl",
   "nom": "Marge brute %",
   "dossier": "1. Compte de résultat\\Ratios",
   "format": "0.0 %",
   "description": "Marge brute / chiffre d'affaires.",
   "expression": "DIVIDE ( [Marge brute], [CA] )"
  },
  {
   "table": "fact_gl",
   "nom": "EBITDA %",
   "dossier": "1. Compte de résultat\\Ratios",
   "format": "0.0 %",
   "description": "EBITDA / chiffre d'affaires.",
   "expression": "DIVIDE ( [EBITDA], [CA] )"
  },
  {
   "table": "fact_gl",
   "nom": "Résultat net %",
   "dossier": "1. Compte de résultat\\Ratios",
   "format": "0.0 %",
   "description": "Résultat net / chiffre d'affaires.",
   "expression": "DIVIDE ( [Résultat net], [CA] )"
  },
  {
   "table": "fact_gl",
   "nom": "Personnel % CA",
   "dossier": "1. Compte de résultat\\Ratios",
   "format": "0.0 %",
   "description": "Charges de personnel / chiffre d'affaires (en valeur positive).",
   "expression": "DIVIDE ( - [Charges de personnel], [CA] )"
  },
  {
   "table": "fact_gl",
   "nom": "CA N-1",
   "dossier": "3. Temps",
   "format": "#,##0 €",
   "description": "Chiffre d'affaires de la même période l'an dernier (raccourci du groupe de calcul, utile dans les graphiques combinés).",
   "expression": "CALCULATE ( [CA], 'Intelligence temporelle'[Période] = \"N-1\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Trésorerie",
   "dossier": "6. Trésorerie",
   "format": "#,##0 €",
   "description": "Solde du compte 512 (banque) à la date de référence. Mouvements convertis au taux moyen du mois.",
   "expression": "VAR _d = [Date de référence]\nRETURN\n    CALCULATE (\n        SUM ( fact_gl[montant_eur] ),\n        dim_compte[numero_compte] = \"512000\",\n        REMOVEFILTERS ( dim_date ),\n        dim_date[date] <= _d\n    )"
  },
  {
   "table": "fact_gl",
   "nom": "Variation de trésorerie",
   "dossier": "6. Trésorerie",
   "format": "#,##0 €",
   "description": "Mouvements nets du compte 512 sur la période.",
   "expression": "CALCULATE ( SUM ( fact_gl[montant_eur] ), dim_compte[numero_compte] = \"512000\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Entrées de trésorerie",
   "dossier": "6. Trésorerie",
   "format": "#,##0 €",
   "description": "Encaissements sur le compte 512 (hors à-nouveaux).",
   "expression": "CALCULATE ( SUM ( fact_gl[debit_eur] ), dim_compte[numero_compte] = \"512000\", fact_gl[journal] <> \"AN\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Sorties de trésorerie",
   "dossier": "6. Trésorerie",
   "format": "#,##0 €",
   "description": "Décaissements sur le compte 512 (valeur négative).",
   "expression": "CALCULATE ( - SUM ( fact_gl[credit_eur] ), dim_compte[numero_compte] = \"512000\" )"
  },
  {
   "table": "fact_gl",
   "nom": "BFR clients - fournisseurs",
   "dossier": "6. Trésorerie",
   "format": "#,##0 €",
   "description": "Besoin en fonds de roulement simplifié : encours clients − encours fournisseurs.",
   "expression": "[Encours clients] - [Encours fournisseurs]"
  },
  {
   "table": "fact_gl",
   "nom": "Date d'arrêté",
   "dossier": "9. Utilitaires",
   "format": "dd/mm/yyyy",
   "description": "Date de la dernière extraction comptable chargée.",
   "expression": "CALCULATE ( MAX ( dim_date[date] ), REMOVEFILTERS ( dim_date ), dim_date[est_avant_arrete] = TRUE () )"
  },
  {
   "table": "fact_gl",
   "nom": "Date de référence",
   "dossier": "9. Utilitaires",
   "format": "dd/mm/yyyy",
   "description": "Dernier jour de la période filtrée, plafonné à la date d'arrêté. Sert aux mesures « à date ».",
   "expression": "MIN ( MAX ( dim_date[date] ), [Date d'arrêté] )"
  },
  {
   "table": "fact_gl",
   "nom": "Titre rapport",
   "dossier": "9. Utilitaires",
   "format": null,
   "description": "Titre dynamique affiché dans le bandeau des pages.",
   "expression": "\"FinSight — données arrêtées au \" & FORMAT ( [Date d'arrêté], \"dd/mm/yyyy\" )"
  },
  {
   "table": "fact_gl",
   "nom": "Libellé période",
   "dossier": "9. Utilitaires",
   "format": null,
   "description": "Période filtrée en clair (ex. « janv. 2025 → oct. 2025 »).",
   "expression": "VAR _min = MIN ( dim_date[date] )\nVAR _max = MIN ( MAX ( dim_date[date] ), [Date d'arrêté] )\nRETURN FORMAT ( _min, \"mmm yyyy\" ) & \" → \" & FORMAT ( _max, \"mmm yyyy\" )"
  },
  {
   "table": "fact_budget",
   "nom": "Budget",
   "dossier": "2. Budget",
   "format": "#,##0 €",
   "description": "Budget mensualisé en EUR, même convention de signe que le réel.",
   "expression": "SUM ( fact_budget[budget_pnl_eur] )"
  },
  {
   "table": "fact_budget",
   "nom": "CA Budget",
   "dossier": "2. Budget",
   "format": "#,##0 €",
   "description": "Chiffre d'affaires budgété.",
   "expression": "CALCULATE ( [Budget], dim_compte[ligne_pnl] = \"Chiffre d'affaires\" )"
  },
  {
   "table": "fact_budget",
   "nom": "EBITDA Budget",
   "dossier": "2. Budget",
   "format": "#,##0 €",
   "description": "EBITDA budgété.",
   "expression": "CALCULATE ( [Budget], dim_compte[agregat] IN { \"Marge brute\", \"EBITDA\" } )"
  },
  {
   "table": "fact_budget",
   "nom": "Résultat net Budget",
   "dossier": "2. Budget",
   "format": "#,##0 €",
   "description": "Résultat net budgété.",
   "expression": "CALCULATE ( [Budget], dim_compte[est_compte_resultat] = TRUE () )"
  },
  {
   "table": "fact_budget",
   "nom": "Budget à date",
   "dossier": "2. Budget",
   "format": "#,##0 €",
   "description": "Budget limité aux mois clôturés (≤ date d'arrêté) : évite de comparer un budget annuel à un réel partiel.",
   "expression": "CALCULATE ( [Budget], KEEPFILTERS ( dim_date[est_avant_arrete] = TRUE () ) )"
  },
  {
   "table": "fact_budget",
   "nom": "Écart budget",
   "dossier": "2. Budget",
   "format": "#,##0 €",
   "description": "Réel − budget. Positif = favorable (plus de produits ou moins de charges).",
   "expression": "[Réel] - [Budget]"
  },
  {
   "table": "fact_budget",
   "nom": "Écart budget à date",
   "dossier": "2. Budget",
   "format": "#,##0 €",
   "description": "Réel − budget à date. Positif = favorable.",
   "expression": "[Réel] - [Budget à date]"
  },
  {
   "table": "fact_budget",
   "nom": "Écart budget %",
   "dossier": "2. Budget",
   "format": "+0.0 %;-0.0 %;0.0 %",
   "description": "Écart budget à date / |budget à date|.",
   "expression": "DIVIDE ( [Écart budget à date], ABS ( [Budget à date] ) )"
  },
  {
   "table": "fact_budget",
   "nom": "Taux de réalisation CA",
   "dossier": "2. Budget",
   "format": "0.0 %",
   "description": "CA réel / CA budgété.",
   "expression": "DIVIDE ( [CA], [CA Budget] )"
  },
  {
   "table": "fact_budget",
   "nom": "Écart budget indicateur",
   "dossier": "2. Budget",
   "format": null,
   "description": "▲ si l'écart budget à date est favorable, ▼ sinon (mise en forme conditionnelle).",
   "expression": "VAR _e = [Écart budget à date]\nRETURN IF ( ISBLANK ( _e ), BLANK (), IF ( _e >= 0, \"▲\", \"▼\" ) )"
  },
  {
   "table": "fact_factures_clients",
   "nom": "CA facturé TTC",
   "dossier": "4. Créances clients",
   "format": "#,##0 €",
   "description": "Montant TTC des factures clients émises sur la période (date de facture).",
   "expression": "SUM ( fact_factures_clients[montant_ttc_eur] )"
  },
  {
   "table": "fact_factures_clients",
   "nom": "Encours clients",
   "dossier": "4. Créances clients",
   "format": "#,##0 €",
   "description": "Montant TTC dû par les clients à la date de référence : factures émises avant cette date et non réglées à cette date.",
   "expression": "VAR _d = [Date de référence]\nRETURN\n    CALCULATE (\n        SUM ( fact_factures_clients[montant_ttc_eur] ),\n        REMOVEFILTERS ( dim_date ),\n        fact_factures_clients[date_facture] <= _d,\n        ISBLANK ( fact_factures_clients[date_paiement] ) || fact_factures_clients[date_paiement] > _d\n    )"
  },
  {
   "table": "fact_factures_clients",
   "nom": "Encours clients échu",
   "dossier": "4. Créances clients",
   "format": "#,##0 €",
   "description": "Partie de l'encours clients dont l'échéance est dépassée à la date de référence.",
   "expression": "VAR _d = [Date de référence]\nRETURN\n    CALCULATE (\n        SUM ( fact_factures_clients[montant_ttc_eur] ),\n        REMOVEFILTERS ( dim_date ),\n        fact_factures_clients[date_facture] <= _d,\n        fact_factures_clients[date_echeance] < _d,\n        ISBLANK ( fact_factures_clients[date_paiement] ) || fact_factures_clients[date_paiement] > _d\n    )"
  },
  {
   "table": "fact_factures_clients",
   "nom": "% Encours échu",
   "dossier": "4. Créances clients",
   "format": "0.0 %",
   "description": "Encours échu / encours clients.",
   "expression": "DIVIDE ( [Encours clients échu], [Encours clients] )"
  },
  {
   "table": "fact_factures_clients",
   "nom": "DSO (jours)",
   "dossier": "4. Créances clients",
   "format": "#,##0",
   "description": "Délai moyen d'encaissement : encours clients / CA TTC des 90 derniers jours × 90.",
   "expression": "VAR _d = [Date de référence]\nVAR _ca90 = CALCULATE ( [CA facturé TTC], DATESINPERIOD ( dim_date[date], _d, -90, DAY ) )\nRETURN DIVIDE ( [Encours clients], _ca90 ) * 90"
  },
  {
   "table": "fact_factures_clients",
   "nom": "Encours à l'arrêté",
   "dossier": "4. Créances clients",
   "format": "#,##0 €",
   "description": "Encours des factures ouvertes à la date d'arrêté (à croiser avec la tranche d'âge pour la balance âgée).",
   "expression": "CALCULATE (\n    SUM ( fact_factures_clients[montant_ttc_eur] ),\n    REMOVEFILTERS ( dim_date ),\n    fact_factures_clients[est_ouverte] = TRUE ()\n)"
  },
  {
   "table": "fact_factures_clients",
   "nom": "Nb factures ouvertes",
   "dossier": "4. Créances clients",
   "format": "#,##0",
   "description": "Nombre de factures clients non réglées à la date d'arrêté.",
   "expression": "CALCULATE ( COUNTROWS ( fact_factures_clients ), REMOVEFILTERS ( dim_date ), fact_factures_clients[est_ouverte] = TRUE () )"
  },
  {
   "table": "fact_factures_clients",
   "nom": "Retard moyen de paiement (jours)",
   "dossier": "4. Créances clients",
   "format": "#,##0.0",
   "description": "Retard moyen pondéré par le montant des factures réglées (date de paiement − échéance).",
   "expression": "CALCULATE (\n    DIVIDE (\n        SUMX ( fact_factures_clients, fact_factures_clients[jours_retard] * fact_factures_clients[montant_ttc_eur] ),\n        SUM ( fact_factures_clients[montant_ttc_eur] )\n    ),\n    fact_factures_clients[est_ouverte] = FALSE ()\n)"
  },
  {
   "table": "fact_factures_clients",
   "nom": "Encaissements clients",
   "dossier": "4. Créances clients",
   "format": "#,##0 €",
   "description": "Montant TTC des factures réglées sur la période (date de paiement).",
   "expression": "CALCULATE (\n    SUM ( fact_factures_clients[montant_ttc_eur] ),\n    USERELATIONSHIP ( fact_factures_clients[date_paiement_key], dim_date[date_key] )\n)"
  },
  {
   "table": "fact_factures_fournisseurs",
   "nom": "Achats TTC",
   "dossier": "5. Dettes fournisseurs",
   "format": "#,##0 €",
   "description": "Montant TTC des factures fournisseurs reçues sur la période.",
   "expression": "SUM ( fact_factures_fournisseurs[montant_ttc_eur] )"
  },
  {
   "table": "fact_factures_fournisseurs",
   "nom": "Encours fournisseurs",
   "dossier": "5. Dettes fournisseurs",
   "format": "#,##0 €",
   "description": "Montant TTC dû aux fournisseurs à la date de référence.",
   "expression": "VAR _d = [Date de référence]\nRETURN\n    CALCULATE (\n        SUM ( fact_factures_fournisseurs[montant_ttc_eur] ),\n        REMOVEFILTERS ( dim_date ),\n        fact_factures_fournisseurs[date_facture] <= _d,\n        ISBLANK ( fact_factures_fournisseurs[date_paiement] ) || fact_factures_fournisseurs[date_paiement] > _d\n    )"
  },
  {
   "table": "fact_factures_fournisseurs",
   "nom": "DPO (jours)",
   "dossier": "5. Dettes fournisseurs",
   "format": "#,##0",
   "description": "Délai moyen de paiement des fournisseurs : encours fournisseurs / achats TTC des 90 derniers jours × 90.",
   "expression": "VAR _d = [Date de référence]\nVAR _achats90 = CALCULATE ( [Achats TTC], DATESINPERIOD ( dim_date[date], _d, -90, DAY ) )\nRETURN DIVIDE ( [Encours fournisseurs], _achats90 ) * 90"
  },
  {
   "table": "fact_factures_fournisseurs",
   "nom": "Décaissements fournisseurs",
   "dossier": "5. Dettes fournisseurs",
   "format": "#,##0 €",
   "description": "Montant TTC des factures fournisseurs payées sur la période.",
   "expression": "CALCULATE (\n    SUM ( fact_factures_fournisseurs[montant_ttc_eur] ),\n    USERELATIONSHIP ( fact_factures_fournisseurs[date_paiement_key], dim_date[date_key] )\n)"
  }
 ],
 "table_dates": [
  "dim_date",
  "date"
 ],
 "tris": [
  [
   "dim_date",
   "mois_nom",
   "mois"
  ],
  [
   "dim_date",
   "mois_court",
   "mois"
  ],
  [
   "dim_date",
   "annee_mois",
   "annee_mois_num"
  ],
  [
   "dim_date",
   "jour_semaine",
   "jour_semaine_num"
  ],
  [
   "dim_compte",
   "ligne_pnl",
   "ordre_pnl"
  ],
  [
   "fact_factures_clients",
   "tranche_age",
   "tranche_age_ordre"
  ],
  [
   "fact_factures_fournisseurs",
   "tranche_age",
   "tranche_age_ordre"
  ]
 ],
 "colonnes_masquees": [
  "debit",
  "credit",
  "debit_eur",
  "credit_eur",
  "montant_devise",
  "montant_eur",
  "montant_pnl_eur",
  "budget_pnl_devise",
  "budget_pnl_eur",
  "montant_ht",
  "montant_tva",
  "montant_ttc",
  "montant_ht_eur",
  "montant_ttc_eur",
  "tranche_age_ordre",
  "ordre_pnl",
  "annee_mois_num",
  "jour_semaine_num"
 ]
}''')
print(len(DEFS['relations']), 'relations ·', len(DEFS['mesures']), 'mesures ·', len(DEFS['groupe_calcul']['elements']), 'éléments de calcul')


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import sempy.fabric as fabric
from sempy_labs.tom import connect_semantic_model


def trouver(collection, nom):
    for objet in collection:
        if objet.Name == nom:
            return objet
    return None


with connect_semantic_model(dataset=modele, readonly=False, workspace=workspace) as tom:
    m = tom.model

    # 1. Paramétrage du modèle et des colonnes
    m.DiscourageImplicitMeasures = True
    table_d, col_d = DEFS["table_dates"]
    try:
        tom.mark_as_date_table(table_name=table_d, column_name=col_d)
        print(f"📅 {table_d}[{col_d}] marquée comme table de dates")
    except Exception as e:  # déjà marquée ou validation refusée
        print(f"⚠️ Table de dates : {e}")
    for table, colonne, par in DEFS["tris"]:
        tom.set_sort_by_column(table_name=table, column_name=colonne, sort_by_column=par)
    nb_masquees = 0
    for t in m.Tables:
        for c in t.Columns:
            if c.Name.endswith("_key") or c.Name in DEFS["colonnes_masquees"]:
                c.IsHidden = True
                nb_masquees += 1
    print(f"🙈 {nb_masquees} colonnes techniques masquées · {len(DEFS['tris'])} tris")

    # 2. Relations (ignorées si une relation relie déjà les mêmes colonnes)
    for r in DEFS["relations"]:
        ft, fc = r["de"].split(".")
        tt, tc = r["vers"].split(".")
        existante = next((x for x in m.Relationships
                          if x.FromTable.Name == ft and x.FromColumn.Name == fc
                          and x.ToTable.Name == tt and x.ToColumn.Name == tc), None)
        if existante is not None:
            existante.IsActive = r["active"]
            continue
        tom.add_relationship(from_table=ft, from_column=fc, to_table=tt, to_column=tc,
                             from_cardinality="Many", to_cardinality="One", is_active=r["active"])
        print(f"🔗 {r['de']} → {r['vers']}" + ("" if r["active"] else " (inactive)"))

    # 3. Groupe de calcul (recréé)
    g = DEFS["groupe_calcul"]
    ancien = trouver(m.Tables, g["nom"])
    if ancien is not None:
        tom.remove_object(object=ancien)
    tom.add_calculation_group(name=g["nom"], precedence=g["precedence"], description=g["description"])
    for c in m.Tables[g["nom"]].Columns:
        if c.SourceColumn == "Name":
            c.Name = g["colonne"]
    for i, el in enumerate(g["elements"]):
        tom.add_calculation_item(table_name=g["nom"], calculation_item_name=el["nom"], expression=el["expression"],
                                 ordinal=i, description=el["description"], format_string_expression=el["format"])
    print(f"🧮 Groupe de calcul « {g['nom']} » : {len(g['elements'])} éléments")

    # 4. Mesures (créées ou mises à jour)
    crees, maj = 0, 0
    for d in DEFS["mesures"]:
        table = m.Tables[d["table"]]
        mesure = trouver(table.Measures, d["nom"])
        if mesure is None:
            tom.add_measure(table_name=d["table"], measure_name=d["nom"], expression=d["expression"],
                            format_string=d["format"], display_folder=d["dossier"], description=d["description"])
            crees += 1
        else:
            mesure.Expression = d["expression"]
            mesure.FormatString = d["format"] or ""
            mesure.DisplayFolder = d["dossier"]
            mesure.Description = d["description"]
            maj += 1
    print(f"📐 Mesures : {crees} créées, {maj} mises à jour")

print("💾 Modifications enregistrées dans le modèle")


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Recadrage Direct Lake et contrôle des valeurs
#
# Attendu : CA 2024 = 47,43 M€ · CA 2025 = 52,14 M€ · EBITDA 2025 = 8,14 M€ · DSO 2026 ≈ 68 j.

# CELL ********************

fabric.refresh_dataset(dataset=modele, workspace=workspace, refresh_type="full")

controle = fabric.evaluate_dax(dataset=modele, workspace=workspace, dax_string='''
EVALUATE
SUMMARIZECOLUMNS (
    dim_date[annee],
    "CA", [CA],
    "CA N-1", [CA N-1],
    "CA Var N-1 %", CALCULATE ( [CA], 'Intelligence temporelle'[Période] = "Var N-1 %" ),
    "CA Budget", [CA Budget],
    "EBITDA", [EBITDA],
    "EBITDA %", [EBITDA %],
    "Résultat net", [Résultat net],
    "DSO (jours)", [DSO (jours)],
    "Trésorerie", [Trésorerie]
)
ORDER BY dim_date[annee]
''')
display(controle)


# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

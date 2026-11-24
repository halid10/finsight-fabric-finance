#!/usr/bin/env python3
"""
Génère, depuis une source unique, la définition du modèle sémantique sm_finsight :
  - fabric/workspace/nb_05_semantic_model.Notebook : notebook Fabric qui applique tout via semantic-link-labs (recommandé)
  - powerbi/semantic-model/sm_finsight.tmdl : script TMDL équivalent (référence / Power BI Desktop)

Source unique de vérité pour : relations, groupe de calcul « Intelligence temporelle »,
mesures (expression, description, dossier d'affichage, format).

    python3 powerbi/semantic-model/generate_tmdl.py

Le fichier généré se colle dans la vue TMDL (Power BI Desktop ou édition web du modèle) puis « Appliquer ».
Ne pas modifier sm_finsight.tmdl à la main : modifier ce fichier et régénérer (la CI vérifie la synchro).
"""
from pathlib import Path

SORTIE = Path(__file__).with_name("sm_finsight.tmdl")
T = "\t"

EUR = "#,##0 €"
PCT = "0.0 %"
PCT_SIGNE = "+0.0 %;-0.0 %;0.0 %"
JOURS = "#,##0"
DATE = "dd/mm/yyyy"
ENTIER = "#,##0"

# --------------------------------------------------------------------------------------
# Relations : (nom, de, vers, active)
# --------------------------------------------------------------------------------------
RELATIONS = []
for fait in ["fact_gl", "fact_budget"]:
    RELATIONS += [
        (f"{fait}_date", f"{fait}.date_key", "dim_date.date_key", True),
        (f"{fait}_entite", f"{fait}.entite_key", "dim_entite.entite_key", True),
        (f"{fait}_compte", f"{fait}.compte_key", "dim_compte.compte_key", True),
        (f"{fait}_centre_cout", f"{fait}.cc_key", "dim_centre_cout.cc_key", True),
    ]
for fait, dim, cle in [("fact_factures_clients", "dim_client", "client_key"),
                       ("fact_factures_fournisseurs", "dim_fournisseur", "fournisseur_key")]:
    RELATIONS += [
        (f"{fait}_date_facture", f"{fait}.date_key", "dim_date.date_key", True),
        (f"{fait}_date_paiement", f"{fait}.date_paiement_key", "dim_date.date_key", False),
        (f"{fait}_entite", f"{fait}.entite_key", "dim_entite.entite_key", True),
        (f"{fait}_tiers", f"{fait}.{cle}", f"{dim}.{cle}", True),
    ]

# --------------------------------------------------------------------------------------
# Groupe de calcul « Intelligence temporelle »
# --------------------------------------------------------------------------------------
# Mesures non numériques : le groupe de calcul les laisse intactes
NON_NUMERIQUES = "[Titre rapport], [Libellé période], [Date d'arrêté], [Date de référence], [Écart budget indicateur]"
N1 = "CALCULATE ( SELECTEDMEASURE (), SAMEPERIODLASTYEAR ( dim_date[date] ) )"


def garde(expr: str) -> str:
    return f"IF (\n{T}ISSELECTEDMEASURE ( {NON_NUMERIQUES} ),\n{T}SELECTEDMEASURE (),\n{T}{expr}\n)"


ELEMENTS_TEMPS = [
    # (nom, expression, format dynamique, description)
    ("Période", "SELECTEDMEASURE ()", None, "Valeur de la période filtrée (comportement par défaut)."),
    ("YTD", garde("CALCULATE ( SELECTEDMEASURE (), DATESYTD ( dim_date[date] ) )"), None,
     "Cumul depuis le 1er janvier jusqu'à la fin de la période filtrée."),
    ("N-1", garde(N1), None, "Même période l'année précédente."),
    ("YTD N-1", garde("CALCULATE ( SELECTEDMEASURE (), DATESYTD ( SAMEPERIODLASTYEAR ( dim_date[date] ) ) )"), None,
     "Cumul annuel de l'année précédente, à date équivalente."),
    ("Var N-1", garde(f"VAR _n = SELECTEDMEASURE ()\n{T}VAR _n1 = {N1}\n{T}RETURN IF ( NOT ISBLANK ( _n ) && NOT ISBLANK ( _n1 ), _n - _n1 )"),
     None, "Écart en valeur avec la même période de l'année précédente (N − N-1)."),
    ("Var N-1 %", garde(f"VAR _n = SELECTEDMEASURE ()\n{T}VAR _n1 = {N1}\n{T}RETURN DIVIDE ( _n - _n1, ABS ( _n1 ) )"),
     f'"{PCT_SIGNE}"', "Écart relatif avec la même période de l'année précédente : (N − N-1) / |N-1|."),
    ("12 mois glissants", garde("CALCULATE ( SELECTEDMEASURE (), DATESINPERIOD ( dim_date[date], MAX ( dim_date[date] ), -12, MONTH ) )"),
     None, "Somme des 12 derniers mois jusqu'à la fin de la période filtrée."),
]

# --------------------------------------------------------------------------------------
# Mesures : table -> [(nom, dossier, format, description, expression)]
# --------------------------------------------------------------------------------------
F_PNL = "1. Compte de résultat"
F_RATIO = "1. Compte de résultat\\Ratios"
F_BUD = "2. Budget"
F_TEMPS = "3. Temps"
F_AR = "4. Créances clients"
F_AP = "5. Dettes fournisseurs"
F_TRESO = "6. Trésorerie"
F_UTIL = "9. Utilitaires"

ENCOURS = """VAR _d = [Date de référence]
RETURN
    CALCULATE (
        SUM ( {t}[montant_ttc_eur] ),
        REMOVEFILTERS ( dim_date ),
        {t}[date_facture] <= _d,{extra}
        ISBLANK ( {t}[date_paiement] ) || {t}[date_paiement] > _d
    )"""

MESURES = {
    "fact_gl": [
        ("Réel", F_PNL, EUR,
         "Montant du compte de résultat en EUR : crédit − débit (produits positifs, charges négatives) "
         "sur les comptes filtrés.",
         "SUM ( fact_gl[montant_pnl_eur] )"),
        ("CA", F_PNL, EUR, "Chiffre d'affaires : prestations et abonnements facturés (comptes 706xxx).",
         "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Chiffre d'affaires\" )"),
        ("Coût des ventes", F_PNL, EUR, "Sous-traitance, licences et hébergement revendus (comptes 604, 607). Valeur négative.",
         "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Coût des ventes\" )"),
        ("Marge brute", F_PNL, EUR, "Chiffre d'affaires + coût des ventes.",
         "CALCULATE ( [Réel], dim_compte[agregat] = \"Marge brute\" )"),
        ("Charges externes", F_PNL, EUR,
         "Loyers, honoraires, marketing, déplacements, télécoms, logiciels… (comptes 606 à 651). Valeur négative.",
         "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Charges externes\" )"),
        ("Charges de personnel", F_PNL, EUR, "Salaires bruts + charges sociales (comptes 641, 645). Valeur négative.",
         "CALCULATE ( [Réel], dim_compte[ligne_pnl] = \"Charges de personnel\" )"),
        ("EBITDA", F_PNL, EUR, "Résultat avant amortissements, résultat financier et impôt.",
         "CALCULATE ( [Réel], dim_compte[agregat] IN { \"Marge brute\", \"EBITDA\" } )"),
        ("Résultat d'exploitation", F_PNL, EUR, "EBITDA − dotations aux amortissements (EBIT).",
         "CALCULATE ( [Réel], dim_compte[agregat] IN { \"Marge brute\", \"EBITDA\", \"Résultat d'exploitation\" } )"),
        ("Résultat net", F_PNL, EUR, "Somme de tous les comptes de résultat (classes 6 et 7).",
         "CALCULATE ( [Réel], dim_compte[est_compte_resultat] = TRUE () )"),
        ("Montant P&L", F_PNL, EUR,
         "Pour la matrice du compte de résultat : masque les comptes de bilan ; le total général vaut le résultat net.",
         "CALCULATE ( [Réel], KEEPFILTERS ( dim_compte[est_compte_resultat] = TRUE () ) )"),
        ("Marge brute %", F_RATIO, PCT, "Marge brute / chiffre d'affaires.", "DIVIDE ( [Marge brute], [CA] )"),
        ("EBITDA %", F_RATIO, PCT, "EBITDA / chiffre d'affaires.", "DIVIDE ( [EBITDA], [CA] )"),
        ("Résultat net %", F_RATIO, PCT, "Résultat net / chiffre d'affaires.", "DIVIDE ( [Résultat net], [CA] )"),
        ("Personnel % CA", F_RATIO, PCT, "Charges de personnel / chiffre d'affaires (en valeur positive).",
         "DIVIDE ( - [Charges de personnel], [CA] )"),
        ("CA N-1", F_TEMPS, EUR,
         "Chiffre d'affaires de la même période l'an dernier (raccourci du groupe de calcul, utile dans les graphiques combinés).",
         "CALCULATE ( [CA], 'Intelligence temporelle'[Période] = \"N-1\" )"),
        ("Trésorerie", F_TRESO, EUR,
         "Solde du compte 512 (banque) à la date de référence. Mouvements convertis au taux moyen du mois.",
         """VAR _d = [Date de référence]
RETURN
    CALCULATE (
        SUM ( fact_gl[montant_eur] ),
        dim_compte[numero_compte] = "512000",
        REMOVEFILTERS ( dim_date ),
        dim_date[date] <= _d
    )"""),
        ("Variation de trésorerie", F_TRESO, EUR, "Mouvements nets du compte 512 sur la période.",
         "CALCULATE ( SUM ( fact_gl[montant_eur] ), dim_compte[numero_compte] = \"512000\" )"),
        ("Entrées de trésorerie", F_TRESO, EUR, "Encaissements sur le compte 512 (hors à-nouveaux).",
         "CALCULATE ( SUM ( fact_gl[debit_eur] ), dim_compte[numero_compte] = \"512000\", fact_gl[journal] <> \"AN\" )"),
        ("Sorties de trésorerie", F_TRESO, EUR, "Décaissements sur le compte 512 (valeur négative).",
         "CALCULATE ( - SUM ( fact_gl[credit_eur] ), dim_compte[numero_compte] = \"512000\" )"),
        ("BFR clients - fournisseurs", F_TRESO, EUR,
         "Besoin en fonds de roulement simplifié : encours clients − encours fournisseurs.",
         "[Encours clients] - [Encours fournisseurs]"),
        ("Date d'arrêté", F_UTIL, DATE, "Date de la dernière extraction comptable chargée.",
         "CALCULATE ( MAX ( dim_date[date] ), REMOVEFILTERS ( dim_date ), dim_date[est_avant_arrete] = TRUE () )"),
        ("Date de référence", F_UTIL, DATE,
         "Dernier jour de la période filtrée, plafonné à la date d'arrêté. Sert aux mesures « à date ».",
         "MIN ( MAX ( dim_date[date] ), [Date d'arrêté] )"),
        ("Titre rapport", F_UTIL, None, "Titre dynamique affiché dans le bandeau des pages.",
         "\"FinSight — données arrêtées au \" & FORMAT ( [Date d'arrêté], \"dd/mm/yyyy\" )"),
        ("Libellé période", F_UTIL, None, "Période filtrée en clair (ex. « janv. 2025 → oct. 2025 »).",
         """VAR _min = MIN ( dim_date[date] )
VAR _max = MIN ( MAX ( dim_date[date] ), [Date d'arrêté] )
RETURN FORMAT ( _min, "mmm yyyy" ) & " → " & FORMAT ( _max, "mmm yyyy" )"""),
    ],
    "fact_budget": [
        ("Budget", F_BUD, EUR, "Budget mensualisé en EUR, même convention de signe que le réel.",
         "SUM ( fact_budget[budget_pnl_eur] )"),
        ("CA Budget", F_BUD, EUR, "Chiffre d'affaires budgété.",
         "CALCULATE ( [Budget], dim_compte[ligne_pnl] = \"Chiffre d'affaires\" )"),
        ("EBITDA Budget", F_BUD, EUR, "EBITDA budgété.",
         "CALCULATE ( [Budget], dim_compte[agregat] IN { \"Marge brute\", \"EBITDA\" } )"),
        ("Résultat net Budget", F_BUD, EUR, "Résultat net budgété.",
         "CALCULATE ( [Budget], dim_compte[est_compte_resultat] = TRUE () )"),
        ("Budget à date", F_BUD, EUR,
         "Budget limité aux mois clôturés (≤ date d'arrêté) : évite de comparer un budget annuel à un réel partiel.",
         "CALCULATE ( [Budget], KEEPFILTERS ( dim_date[est_avant_arrete] = TRUE () ) )"),
        ("Écart budget", F_BUD, EUR, "Réel − budget. Positif = favorable (plus de produits ou moins de charges).",
         "[Réel] - [Budget]"),
        ("Écart budget à date", F_BUD, EUR, "Réel − budget à date. Positif = favorable.", "[Réel] - [Budget à date]"),
        ("Écart budget %", F_BUD, PCT_SIGNE, "Écart budget à date / |budget à date|.",
         "DIVIDE ( [Écart budget à date], ABS ( [Budget à date] ) )"),
        ("Taux de réalisation CA", F_BUD, PCT, "CA réel / CA budgété.", "DIVIDE ( [CA], [CA Budget] )"),
        ("Écart budget indicateur", F_BUD, None, "▲ si l'écart budget à date est favorable, ▼ sinon (mise en forme conditionnelle).",
         """VAR _e = [Écart budget à date]
RETURN IF ( ISBLANK ( _e ), BLANK (), IF ( _e >= 0, "▲", "▼" ) )"""),
    ],
    "fact_factures_clients": [
        ("CA facturé TTC", F_AR, EUR, "Montant TTC des factures clients émises sur la période (date de facture).",
         "SUM ( fact_factures_clients[montant_ttc_eur] )"),
        ("Encours clients", F_AR, EUR,
         "Montant TTC dû par les clients à la date de référence : factures émises avant cette date et non réglées à cette date.",
         ENCOURS.format(t="fact_factures_clients", extra="")),
        ("Encours clients échu", F_AR, EUR, "Partie de l'encours clients dont l'échéance est dépassée à la date de référence.",
         ENCOURS.format(t="fact_factures_clients", extra="\n        fact_factures_clients[date_echeance] < _d,")),
        ("% Encours échu", F_AR, PCT, "Encours échu / encours clients.",
         "DIVIDE ( [Encours clients échu], [Encours clients] )"),
        ("DSO (jours)", F_AR, JOURS,
         "Délai moyen d'encaissement : encours clients / CA TTC des 90 derniers jours × 90.",
         """VAR _d = [Date de référence]
VAR _ca90 = CALCULATE ( [CA facturé TTC], DATESINPERIOD ( dim_date[date], _d, -90, DAY ) )
RETURN DIVIDE ( [Encours clients], _ca90 ) * 90"""),
        ("Encours à l'arrêté", F_AR, EUR,
         "Encours des factures ouvertes à la date d'arrêté (à croiser avec la tranche d'âge pour la balance âgée).",
         """CALCULATE (
    SUM ( fact_factures_clients[montant_ttc_eur] ),
    REMOVEFILTERS ( dim_date ),
    fact_factures_clients[est_ouverte] = TRUE ()
)"""),
        ("Nb factures ouvertes", F_AR, ENTIER, "Nombre de factures clients non réglées à la date d'arrêté.",
         "CALCULATE ( COUNTROWS ( fact_factures_clients ), REMOVEFILTERS ( dim_date ), fact_factures_clients[est_ouverte] = TRUE () )"),
        ("Retard moyen de paiement (jours)", F_AR, "#,##0.0",
         "Retard moyen pondéré par le montant des factures réglées (date de paiement − échéance).",
         """CALCULATE (
    DIVIDE (
        SUMX ( fact_factures_clients, fact_factures_clients[jours_retard] * fact_factures_clients[montant_ttc_eur] ),
        SUM ( fact_factures_clients[montant_ttc_eur] )
    ),
    fact_factures_clients[est_ouverte] = FALSE ()
)"""),
        ("Encaissements clients", F_AR, EUR, "Montant TTC des factures réglées sur la période (date de paiement).",
         """CALCULATE (
    SUM ( fact_factures_clients[montant_ttc_eur] ),
    USERELATIONSHIP ( fact_factures_clients[date_paiement_key], dim_date[date_key] )
)"""),
    ],
    "fact_factures_fournisseurs": [
        ("Achats TTC", F_AP, EUR, "Montant TTC des factures fournisseurs reçues sur la période.",
         "SUM ( fact_factures_fournisseurs[montant_ttc_eur] )"),
        ("Encours fournisseurs", F_AP, EUR, "Montant TTC dû aux fournisseurs à la date de référence.",
         ENCOURS.format(t="fact_factures_fournisseurs", extra="")),
        ("DPO (jours)", F_AP, JOURS,
         "Délai moyen de paiement des fournisseurs : encours fournisseurs / achats TTC des 90 derniers jours × 90.",
         """VAR _d = [Date de référence]
VAR _achats90 = CALCULATE ( [Achats TTC], DATESINPERIOD ( dim_date[date], _d, -90, DAY ) )
RETURN DIVIDE ( [Encours fournisseurs], _achats90 ) * 90"""),
        ("Décaissements fournisseurs", F_AP, EUR, "Montant TTC des factures fournisseurs payées sur la période.",
         """CALCULATE (
    SUM ( fact_factures_fournisseurs[montant_ttc_eur] ),
    USERELATIONSHIP ( fact_factures_fournisseurs[date_paiement_key], dim_date[date_key] )
)"""),
    ],
}


# --------------------------------------------------------------------------------------
# Rendu TMDL
# --------------------------------------------------------------------------------------
def nom(n: str) -> str:
    return "'" + n.replace("'", "''") + "'"


def expression(expr: str, niveau: int) -> list:
    """Expression sur une ligne si possible, sinon sur plusieurs lignes indentées."""
    lignes = expr.replace("    ", T).split("\n")
    if len(lignes) == 1:
        return [" " + lignes[0]]
    return [""] + [T * niveau + ligne for ligne in lignes]


def bloc_objet(entete: str, expr: str, niveau: int, proprietes: list, description: str = None) -> list:
    out = []
    if description:
        out.append(T * niveau + "/// " + description)
    rendu = expression(expr, niveau + 2)
    out.append(T * niveau + entete + " =" + rendu[0])
    out += rendu[1:]
    out += [T * (niveau + 1) + p for p in proprietes]
    out.append("")
    return out


def generer() -> str:
    """Un seul `createOrReplace` (la vue TMDL refuse les scripts à plusieurs commandes).
    Tout est appliqué dans une même transaction : l'ordre des références n'importe pas."""
    L = ["createOrReplace", ""]
    for n, de, vers, active in RELATIONS:
        L += [f"{T}relationship {n}"]
        if not active:
            L += [f"{T}{T}isActive: false"]
        L += [f"{T}{T}fromColumn: {de}", f"{T}{T}toColumn: {vers}", ""]

    for table, mesures in MESURES.items():
        L += [f"{T}ref table {table}", ""]
        for n, dossier, fmt, desc, expr in mesures:
            L += rendu_mesure(n, dossier, fmt, desc, expr)

    L += [
        f"{T}/// Variantes temporelles applicables à toutes les mesures numériques (YTD, N-1, variations, 12 mois glissants).",
        f"{T}table 'Intelligence temporelle'",
        "",
        f"{T}{T}calculationGroup",
        f"{T}{T}{T}precedence: 10",
        "",
    ]
    for i, (n, expr, fmt, desc) in enumerate(ELEMENTS_TEMPS):
        props = [f"ordinal: {i}"]
        if fmt:
            props.append(f"formatStringDefinition = {fmt}")
        L += bloc_objet(f"calculationItem {nom(n)}", expr, 3, props, desc)
    L += [
        f"{T}{T}column 'Période'",
        f"{T}{T}{T}dataType: string",
        f"{T}{T}{T}summarizeBy: none",
        f"{T}{T}{T}sourceColumn: Name",
        f"{T}{T}{T}sortByColumn: Ordinal",
        "",
        f"{T}{T}column Ordinal",
        f"{T}{T}{T}dataType: int64",
        f"{T}{T}{T}isHidden",
        f"{T}{T}{T}summarizeBy: none",
        f"{T}{T}{T}sourceColumn: Ordinal",
        "",
        f"{T}{T}partition 'Intelligence temporelle' = calculationGroup",
    ]
    return "\n".join(L).rstrip() + "\n"


def rendu_mesure(n, dossier, fmt, desc, expr) -> list:
    props = []
    if fmt:
        props.append(f"formatString: {fmt}")
    props.append(f"displayFolder: {dossier}")
    return bloc_objet(f"measure {nom(n)}", expr, 2, props, desc)


# --------------------------------------------------------------------------------------
# Paramétrage des colonnes (appliqué par le notebook nb_05)
# --------------------------------------------------------------------------------------
TABLE_DATES = ("dim_date", "date")
TRIS = [  # (table, colonne, trier par)
    ("dim_date", "mois_nom", "mois"),
    ("dim_date", "mois_court", "mois"),
    ("dim_date", "annee_mois", "annee_mois_num"),
    ("dim_date", "jour_semaine", "jour_semaine_num"),
    ("dim_compte", "ligne_pnl", "ordre_pnl"),
    ("fact_factures_clients", "tranche_age", "tranche_age_ordre"),
    ("fact_factures_fournisseurs", "tranche_age", "tranche_age_ordre"),
]
# Colonnes masquées : toutes les clés *_key + colonnes numériques exposées via des mesures
COLONNES_MASQUEES = [
    "debit", "credit", "debit_eur", "credit_eur", "montant_devise", "montant_eur", "montant_pnl_eur",
    "budget_pnl_devise", "budget_pnl_eur", "montant_ht", "montant_tva", "montant_ttc", "montant_ht_eur",
    "montant_ttc_eur", "tranche_age_ordre", "ordre_pnl", "annee_mois_num", "jour_semaine_num",
]

Q3 = "'" * 3  # délimiteur de chaîne brute pour le JSON embarqué
NOTEBOOK = Path(__file__).resolve().parents[2] / "fabric" / "workspace" / "nb_05_semantic_model.Notebook" / "notebook-content.py"
GROUPE = "Intelligence temporelle"


def definitions() -> dict:
    return {
        "relations": [{"nom": n, "de": de, "vers": vers, "active": a} for n, de, vers, a in RELATIONS],
        "groupe_calcul": {
            "nom": GROUPE, "colonne": "Période", "precedence": 10,
            "description": "Variantes temporelles applicables à toutes les mesures numériques (YTD, N-1, variations, 12 mois glissants).",
            "elements": [{"nom": n, "expression": e, "format": f, "description": d} for n, e, f, d in ELEMENTS_TEMPS],
        },
        "mesures": [{"table": t, "nom": n, "dossier": dossier, "format": fmt, "description": d, "expression": e}
                    for t, ms in MESURES.items() for n, dossier, fmt, d, e in ms],
        "table_dates": list(TABLE_DATES),
        "tris": [list(x) for x in TRIS],
        "colonnes_masquees": COLONNES_MASQUEES,
    }


def generer_notebook() -> str:
    import json
    defs = json.dumps(definitions(), ensure_ascii=False, indent=1)
    assert Q3 not in defs
    meta = '\n# METADATA ********************\n\n# META {\n# META   "language": "python",\n# META   "language_group": "synapse_pyspark"\n# META }\n'
    cellules = [
        ("MARKDOWN", """# # nb_05 — Modèle sémantique sm_finsight (relations, groupe de calcul, mesures)
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
# ⚠️ Prérequis : le modèle `sm_finsight` existe (KAN-38) et contient les tables `dim_*` / `fact_*` du schéma `gold`."""),
        ("PARAMETERS CELL", """modele = "sm_finsight"   # nom du modèle sémantique
workspace = None          # None = workspace courant"""),
        ("CELL", """# Installation de semantic-link-labs pour la session (bibliothèque Microsoft, PyPI)
import subprocess
import sys

subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "semantic-link-labs"])"""),
        ("CELL", "import json\n\nDEFS = json.loads(r" + Q3 + defs + Q3 + ")\nprint(len(DEFS['relations']), 'relations ·', len(DEFS['mesures']), 'mesures ·', len(DEFS['groupe_calcul']['elements']), 'éléments de calcul')"),
        ("CELL", """import sempy.fabric as fabric
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

print("💾 Modifications enregistrées dans le modèle")"""),
        ("MARKDOWN", """# ## Recadrage Direct Lake et contrôle des valeurs
#
# Attendu : CA 2024 = 47,43 M€ · CA 2025 = 52,14 M€ · EBITDA 2025 = 8,14 M€ · DSO 2026 ≈ 68 j."""),
        ("CELL", """fabric.refresh_dataset(dataset=modele, workspace=workspace, refresh_type="full")

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
display(controle)"""),
    ]
    out = ["# Fabric notebook source", "", "# METADATA ********************", "", "# META {", '# META   "kernel_info": {',
           '# META     "name": "synapse_pyspark"', "# META   },", '# META   "dependencies": {}', "# META }", ""]
    for kind, body in cellules:
        out += [f"# {kind} ********************", "", body, ""]
        if kind != "MARKDOWN":
            out += [meta]
    return "\n".join(out).rstrip() + "\n"


if __name__ == "__main__":
    SORTIE.write_text(generer(), encoding="utf-8")
    NOTEBOOK.parent.mkdir(parents=True, exist_ok=True)
    NOTEBOOK.write_text(generer_notebook(), encoding="utf-8")
    n = sum(len(v) for v in MESURES.values())
    print(f"✅ {SORTIE.name} + {NOTEBOOK.parent.name} : {len(RELATIONS)} relations, {len(ELEMENTS_TEMPS)} éléments de calcul, {n} mesures")

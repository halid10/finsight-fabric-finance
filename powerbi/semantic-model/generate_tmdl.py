#!/usr/bin/env python3
"""
Génère le script TMDL du modèle sémantique sm_finsight (powerbi/semantic-model/sm_finsight.tmdl).

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


# Mesures qui utilisent le groupe de calcul : créées après lui
MESURES_APRES_GROUPE = {"CA N-1"}

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
    """Ordre des blocs : chaque objet existe avant d'être référencé.
    relations -> mesures -> groupe de calcul (cite des mesures) -> CA N-1 (cite le groupe de calcul)."""
    L = ["createOrReplace", ""]
    for n, de, vers, active in RELATIONS:
        L += [f"{T}relationship {n}"]
        if not active:
            L += [f"{T}{T}isActive: false"]
        L += [f"{T}{T}fromColumn: {de}", f"{T}{T}toColumn: {vers}", ""]

    L += ["", "createOrReplace", ""]
    for table, mesures in MESURES.items():
        L += [f"{T}ref table {table}", ""]
        for n, dossier, fmt, desc, expr in mesures:
            if n in MESURES_APRES_GROUPE:
                continue
            L += rendu_mesure(n, dossier, fmt, desc, expr)

    L += [
        "",
        "createOrReplace",
        "",
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
        "",
        "",
        "createOrReplace",
        "",
    ]
    for table, mesures in MESURES.items():
        apres = [m for m in mesures if m[0] in MESURES_APRES_GROUPE]
        if apres:
            L += [f"{T}ref table {table}", ""]
            for n, dossier, fmt, desc, expr in apres:
                L += rendu_mesure(n, dossier, fmt, desc, expr)
    return "\n".join(L).rstrip() + "\n"


def rendu_mesure(n, dossier, fmt, desc, expr) -> list:
    props = []
    if fmt:
        props.append(f"formatString: {fmt}")
    props.append(f"displayFolder: {dossier}")
    return bloc_objet(f"measure {nom(n)}", expr, 2, props, desc)


if __name__ == "__main__":
    SORTIE.write_text(generer(), encoding="utf-8")
    n = sum(len(v) for v in MESURES.values())
    print(f"✅ {SORTIE.name} : {len(RELATIONS)} relations, {len(ELEMENTS_TEMPS)} éléments de calcul, {n} mesures")

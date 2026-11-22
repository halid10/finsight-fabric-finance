"""
Calcule, à partir des CSV bruts, les valeurs de référence des principaux KPI (en EUR).
Sert à valider le modèle sémantique : les visuels Power BI doivent afficher les mêmes chiffres.

    python3 tests/valeurs_reference.py
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from test_donnees import RAW, charger_gl, dec, dedoublonner, lire

AGREGATS_EBITDA = {"Marge brute", "EBITDA"}


def main():
    taux = {(r["annee_mois"], r["devise"]): dec(r["taux_moyen_eur"])
            for r in lire(RAW / "taux_change" / "taux_change.csv")}
    mapping = {r["numero_compte"]: r for r in lire(RAW / "referentiels" / "mapping_pnl.csv")}
    gl = dedoublonner(charger_gl(), ["num_ecriture", "num_ligne"])

    kpi = defaultdict(lambda: defaultdict(Decimal))
    for r in gl:
        m = mapping.get(r["numero_compte"])
        if not m:
            continue
        t = taux[(r["date_comptable"][:7], r["devise"])]
        pnl = ((dec(r["credit"]) - dec(r["debit"])) * t).quantize(Decimal("0.01"))
        a = r["date_comptable"][:4]
        kpi[a]["Résultat net"] += pnl
        if m["ligne_pnl"] == "Chiffre d'affaires":
            kpi[a]["CA"] += pnl
        if m["agregat"] in AGREGATS_EBITDA:
            kpi[a]["EBITDA"] += pnl

    budget = defaultdict(Decimal)
    dernier = {dev: t for (_, dev), t in sorted(taux.items())}  # dernier taux connu par devise
    for f in sorted((RAW / "budget").glob("*.csv")):
        for r in lire(f):
            if mapping[r["numero_compte"]]["ligne_pnl"] == "Chiffre d'affaires":
                t = taux.get((r["annee_mois"], r["devise"]), dernier[r["devise"]])
                budget[r["annee_mois"][:4]] += (dec(r["montant_budget"]) * t).quantize(Decimal("0.01"))

    # DSO au 31/10/2026 (méthode : encours / CA TTC 90 j × 90)
    arrete = date(2026, 10, 31)
    fc = dedoublonner(lire(RAW / "factures_clients" / "factures_clients.csv"), ["num_facture"])
    encours, ca90 = Decimal(0), Decimal(0)
    for r in fc:
        d = datetime.strptime(r["date_facture"], "%d/%m/%Y").date()
        ttc_eur = (dec(r["montant_ttc"]) * taux[(d.strftime("%Y-%m"), r["devise"])]).quantize(Decimal("0.01"))
        if r["statut"] == "OUVERTE":
            encours += ttc_eur
        if arrete - timedelta(days=89) <= d <= arrete:
            ca90 += ttc_eur

    print("| Année | CA réel (M€) | CA budget (M€) | EBITDA (M€) | EBITDA % | Résultat net (M€) |")
    print("|---|---|---|---|---|---|")
    for a in sorted(kpi):
        k = kpi[a]
        print(f"| {a} | {k['CA'] / 10**6:.2f} | {budget[a] / 10**6:.2f} | {k['EBITDA'] / 10**6:.2f} | "
              f"{k['EBITDA'] / k['CA']:.1%} | {k['Résultat net'] / 10**6:.2f} |")
    print(f"\nEncours clients au {arrete:%d/%m/%Y} : {encours:,.0f} €  —  DSO : {encours / ca90 * 90:.0f} jours")


if __name__ == "__main__":
    main()

"""
Tests de cohérence du jeu de données FinSight (bibliothèque standard uniquement).

Lancer :  python3 -m unittest discover -s tests -v
"""
import csv
import unittest
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"


def lire(chemin: Path):
    with chemin.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def dec(s: str) -> Decimal:
    return Decimal(s.replace(",", ".")) if s else Decimal("0")


def charger_gl():
    lignes = []
    for f in sorted((RAW / "gl").glob("ecritures_gl_*.csv")):
        lignes += lire(f)
    return lignes


def dedoublonner(lignes, cle):
    vus, out = set(), []
    for row in lignes:
        k = tuple(row[c] for c in cle)
        if k not in vus:
            vus.add(k)
            out.append(row)
    return out


class TestDonnees(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.gl_brut = charger_gl()
        cls.gl = dedoublonner(cls.gl_brut, ["num_ecriture", "num_ligne"])
        cls.comptes = {r["numero_compte"]: r for r in lire(RAW / "referentiels" / "plan_comptable.csv")}
        cls.mapping = {r["numero_compte"] for r in lire(RAW / "referentiels" / "mapping_pnl.csv")}
        cls.fc = lire(RAW / "factures_clients" / "factures_clients.csv")
        cls.ff = lire(RAW / "factures_fournisseurs" / "factures_fournisseurs.csv")

    def test_fichiers_presents(self):
        for sous in ["referentiels", "gl", "budget", "taux_change", "factures_clients", "factures_fournisseurs"]:
            self.assertTrue(any((RAW / sous).iterdir()), sous)

    def test_ecritures_equilibrees(self):
        soldes = defaultdict(Decimal)
        for r in self.gl:
            soldes[r["num_ecriture"]] += dec(r["debit"]) - dec(r["credit"])
        desequilibres = {k: v for k, v in soldes.items() if v != 0}
        self.assertEqual(desequilibres, {}, "Des écritures ne sont pas équilibrées")

    def test_doublons_injectes_presents(self):
        # La couche Silver doit avoir du travail : les sources contiennent des doublons.
        self.assertGreater(len(self.gl_brut), len(self.gl))

    def test_comptes_connus(self):
        inconnus = {r["numero_compte"] for r in self.gl} - set(self.comptes)
        self.assertEqual(inconnus, set())

    def test_comptes_resultat_mappes(self):
        resultat = {c for c, r in self.comptes.items() if r["nature"] in ("PRODUIT", "CHARGE")}
        self.assertEqual(resultat - self.mapping, set(), "Compte de résultat sans ligne P&L")

    def test_factures_clients_dans_gl(self):
        ca_gl = defaultdict(Decimal)
        for r in self.gl:
            if r["journal"] == "VT" and r["numero_compte"].startswith("706"):
                ca_gl[r["code_entite"]] += dec(r["credit"])
        ca_fc = defaultdict(Decimal)
        for r in dedoublonner(self.fc, ["num_facture"]):
            ca_fc[r["code_entite"]] += dec(r["montant_ht"])
        self.assertEqual(dict(ca_gl), dict(ca_fc))

    def test_encours_clients_coherent(self):
        """Solde du compte 411 dans le GL = TTC des factures clients ouvertes."""
        solde_411 = sum((dec(r["debit"]) - dec(r["credit"])) for r in self.gl if r["numero_compte"] == "411000")
        ouvert = sum(dec(r["montant_ttc"]) for r in dedoublonner(self.fc, ["num_facture"])
                     if r["statut"] == "OUVERTE")
        self.assertEqual(solde_411, ouvert)

    def test_tresorerie_positive(self):
        solde = defaultdict(Decimal)
        for r in self.gl:
            if r["numero_compte"] == "512000":
                solde[r["code_entite"]] += dec(r["debit"]) - dec(r["credit"])
        for entite, s in solde.items():
            self.assertGreater(s, 0, entite)

    def test_rentabilite_realiste(self):
        """EBITDA entre 5 % et 30 % du CA pour chaque entité."""
        ca, ebitda = defaultdict(Decimal), defaultdict(Decimal)
        hors_ebitda = {"681100", "661100", "768000", "695000"}
        for r in self.gl:
            c = r["numero_compte"]
            if c[0] in "67" and c not in hors_ebitda:
                montant = dec(r["credit"]) - dec(r["debit"])
                ebitda[r["code_entite"]] += montant
                if c.startswith("706"):
                    ca[r["code_entite"]] += montant
        for e in ca:
            marge = ebitda[e] / ca[e]
            self.assertTrue(Decimal("0.05") < marge < Decimal("0.30"), f"{e}: EBITDA {marge:.1%}")


if __name__ == "__main__":
    unittest.main()

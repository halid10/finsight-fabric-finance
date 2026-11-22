#!/usr/bin/env python3
"""
Générateur de données financières réalistes pour le projet FinSight (Groupe Novaris).

Produit des extractions « type ERP » cohérentes entre elles :
  - référentiels : entités, plan comptable, mapping P&L, centres de coûts, clients, fournisseurs
  - grand livre (GL) : un fichier CSV par mois, écritures équilibrées (débit = crédit)
  - factures clients (AR) et fournisseurs (AP), avec leurs paiements reflétés dans le GL
  - budget mensualisé par entité / compte / centre de coûts
  - taux de change mensuels (moyen et clôture) vers l'EUR

Format des fichiers (volontairement « réaliste » pour un export ERP français) :
  - séparateur « ; », décimales avec virgule, encodage UTF-8
  - dates GL au format yyyy-MM-dd, dates de factures au format dd/MM/yyyy
  - quelques anomalies injectées (doublons, espaces, codes en minuscules, centres de coûts vides)
    que la couche Silver doit corriger.

Aucune dépendance externe : bibliothèque standard Python 3.8+ uniquement.

Usage :
    python3 data/generator/generate_finance_data.py --out data/raw --seed 42 --start 2024-01 --end 2026-10
"""
from __future__ import annotations

import argparse
import calendar
import csv
import math
import random
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

# --------------------------------------------------------------------------------------
# Référentiels statiques
# --------------------------------------------------------------------------------------

ENTITES = [
    # code, nom, pays, devise, date_creation
    ("NOV-FR", "Novaris France SAS", "France", "EUR", "2012-03-01"),
    ("NOV-BE", "Novaris Belgium SRL", "Belgique", "EUR", "2016-09-01"),
    ("NOV-UK", "Novaris Software Ltd", "Royaume-Uni", "GBP", "2018-01-15"),
    ("NOV-MA", "Novaris Services Maroc SARL", "Maroc", "MAD", "2020-06-01"),
]

# numero, libelle, classe, nature (PRODUIT/CHARGE/ACTIF/PASSIF)
PLAN_COMPTABLE = [
    ("101000", "Capital social", "1", "PASSIF"),
    ("106000", "Réserves", "1", "PASSIF"),
    ("164000", "Emprunts auprès des établissements de crédit", "1", "PASSIF"),
    ("218300", "Matériel de bureau et informatique", "2", "ACTIF"),
    ("281800", "Amortissements des immobilisations corporelles", "2", "ACTIF"),
    ("401000", "Fournisseurs", "4", "PASSIF"),
    ("411000", "Clients", "4", "ACTIF"),
    ("421000", "Personnel - rémunérations dues", "4", "PASSIF"),
    ("431000", "Sécurité sociale et organismes sociaux", "4", "PASSIF"),
    ("444000", "État - impôt sur les bénéfices", "4", "PASSIF"),
    ("445660", "TVA déductible sur biens et services", "4", "ACTIF"),
    ("445710", "TVA collectée", "4", "PASSIF"),
    ("512000", "Banque", "5", "ACTIF"),
    ("604000", "Achats de sous-traitance", "6", "CHARGE"),
    ("607000", "Achats de licences et hébergement revendus", "6", "CHARGE"),
    ("606100", "Fournitures non stockables", "6", "CHARGE"),
    ("613200", "Locations immobilières", "6", "CHARGE"),
    ("615000", "Entretien et maintenance", "6", "CHARGE"),
    ("622600", "Honoraires", "6", "CHARGE"),
    ("623000", "Publicité et marketing", "6", "CHARGE"),
    ("625100", "Voyages et déplacements", "6", "CHARGE"),
    ("626000", "Frais postaux et télécommunications", "6", "CHARGE"),
    ("651000", "Redevances logiciels et SaaS", "6", "CHARGE"),
    ("641000", "Rémunérations du personnel", "6", "CHARGE"),
    ("645000", "Charges de sécurité sociale", "6", "CHARGE"),
    ("661100", "Intérêts des emprunts", "6", "CHARGE"),
    ("681100", "Dotations aux amortissements", "6", "CHARGE"),
    ("695000", "Impôt sur les bénéfices", "6", "CHARGE"),
    ("706000", "Prestations de services", "7", "PRODUIT"),
    ("706100", "Abonnements SaaS", "7", "PRODUIT"),
    ("768000", "Autres produits financiers", "7", "PRODUIT"),
]

# Mapping des comptes de résultat vers les lignes du compte de résultat (P&L)
# numero, ligne_pnl, ordre_pnl, agregat
MAPPING_PNL = [
    ("706000", "Chiffre d'affaires", 10, "Marge brute"),
    ("706100", "Chiffre d'affaires", 10, "Marge brute"),
    ("604000", "Coût des ventes", 20, "Marge brute"),
    ("607000", "Coût des ventes", 20, "Marge brute"),
    ("606100", "Charges externes", 30, "EBITDA"),
    ("613200", "Charges externes", 30, "EBITDA"),
    ("615000", "Charges externes", 30, "EBITDA"),
    ("622600", "Charges externes", 30, "EBITDA"),
    ("623000", "Charges externes", 30, "EBITDA"),
    ("625100", "Charges externes", 30, "EBITDA"),
    ("626000", "Charges externes", 30, "EBITDA"),
    ("651000", "Charges externes", 30, "EBITDA"),
    ("641000", "Charges de personnel", 40, "EBITDA"),
    ("645000", "Charges de personnel", 40, "EBITDA"),
    ("681100", "Dotations aux amortissements", 50, "Résultat d'exploitation"),
    ("661100", "Résultat financier", 60, "Résultat avant impôt"),
    ("768000", "Résultat financier", 60, "Résultat avant impôt"),
    ("695000", "Impôt sur les sociétés", 70, "Résultat net"),
]

CENTRES_COUTS = [
    ("VEN", "Ventes", "Commercial", "Directeur commercial"),
    ("MKT", "Marketing", "Commercial", "Responsable marketing"),
    ("OPS", "Opérations / Delivery", "Production", "Directeur des opérations"),
    ("RD", "Recherche & Développement", "Production", "Directeur technique"),
    ("FIN", "Finance", "Support", "DAF"),
    ("RH", "Ressources humaines", "Support", "DRH"),
    ("IT", "Informatique interne", "Support", "DSI"),
    ("DIR", "Direction générale", "Support", "Directeur général"),
]


@dataclass
class ProfilEntite:
    code: str
    devise: str
    ca_mensuel_base: float      # CA mensuel de référence en devise locale (janv. 2024)
    croissance_annuelle: float  # croissance réelle
    compte_ca: list             # [(compte, poids)]
    taux_cout_ventes: float
    compte_cout_ventes: str
    taux_charges_ext: float
    taux_personnel: float       # masse salariale brute + charges / CA de base
    taux_charges_sociales: float
    taux_tva: float
    taux_is: float
    facture_moyenne: float
    nb_clients: int
    tresorerie_ouverture: float
    immobilisations: float
    emprunt: float
    taux_interet: float


PROFILS = [
    ProfilEntite("NOV-FR", "EUR", 1_800_000, 0.08, [("706000", 1.0)], 0.18, "604000",
                 0.15, 0.50, 0.42, 0.20, 0.25, 15_000, 130, 2_500_000, 900_000, 1_500_000, 0.045),
    ProfilEntite("NOV-BE", "EUR", 600_000, 0.05, [("706000", 1.0)], 0.25, "604000",
                 0.14, 0.50, 0.30, 0.21, 0.25, 12_000, 50, 700_000, 250_000, 0, 0.0),
    ProfilEntite("NOV-UK", "GBP", 900_000, 0.15, [("706100", 0.8), ("706000", 0.2)], 0.12, "607000",
                 0.20, 0.45, 0.14, 0.20, 0.25, 9_000, 70, 1_200_000, 400_000, 500_000, 0.06),
    ProfilEntite("NOV-MA", "MAD", 4_000_000, 0.10, [("706000", 1.0)], 0.08, "604000",
                 0.15, 0.60, 0.21, 0.20, 0.31, 60_000, 50, 6_000_000, 2_000_000, 0, 0.0),
]

# Saisonnalité du CA (janvier → décembre)
SAISONNALITE = [0.92, 0.95, 1.05, 1.00, 0.98, 1.06, 0.95, 0.60, 1.05, 1.10, 1.12, 1.22]

# Répartition des charges externes : compte -> (poids, centres de coûts possibles, récurrent?)
CHARGES_EXTERNES = {
    "613200": (0.30, ["DIR"], True),
    "651000": (0.18, ["IT", "RD"], True),
    "622600": (0.12, ["FIN", "DIR", "RH"], False),
    "623000": (0.12, ["MKT"], False),
    "625100": (0.12, ["VEN", "OPS"], False),
    "626000": (0.06, ["IT"], True),
    "615000": (0.05, ["IT", "DIR"], False),
    "606100": (0.05, ["DIR", "OPS", "RH"], False),
}

# Répartition de la masse salariale par centre de coûts
POIDS_PERSONNEL = {"OPS": 0.45, "RD": 0.15, "VEN": 0.12, "MKT": 0.05, "FIN": 0.07,
                   "RH": 0.04, "IT": 0.06, "DIR": 0.06}

CATEGORIES_FOURNISSEURS = {
    "604000": "Sous-traitance", "607000": "Hébergement cloud", "613200": "Immobilier",
    "651000": "Éditeur logiciel", "622600": "Conseil & audit", "623000": "Agence marketing",
    "625100": "Agence de voyage", "626000": "Opérateur télécom", "615000": "Maintenance",
    "606100": "Fournitures",
}

SECTEURS = ["Banque", "Assurance", "Industrie", "Distribution", "Santé", "Énergie",
            "Secteur public", "Télécoms", "Transport", "Agroalimentaire"]
NOMS_A = ["Alto", "Bora", "Cerya", "Delta", "Eko", "Fenix", "Gala", "Helio", "Iris", "Jade",
          "Kora", "Lumen", "Mira", "Nexo", "Orba", "Pyra", "Quarto", "Rivo", "Solea", "Tessa",
          "Ulma", "Vega", "Wendo", "Xeno", "Yuma", "Zephir"]
NOMS_B = ["Industries", "Partners", "Solutions", "Group", "Capital", "Logistics", "Systems",
          "Energy", "Health", "Finance", "Retail", "Technologies", "Holding", "Services"]
FORMES = {"France": ["SA", "SAS", "SARL"], "Belgique": ["SA", "SRL"], "Royaume-Uni": ["Ltd", "plc"],
          "Maroc": ["SA", "SARL"]}


# --------------------------------------------------------------------------------------
# Utilitaires
# --------------------------------------------------------------------------------------

def fr_num(x: float) -> str:
    """Format décimal français : virgule, 2 décimales."""
    return f"{x:.2f}".replace(".", ",")


def fr_date(d: date) -> str:
    return d.strftime("%d/%m/%Y")


def iso(d: date) -> str:
    return d.isoformat()


def iter_mois(debut: str, fin: str):
    y, m = map(int, debut.split("-"))
    ye, me = map(int, fin.split("-"))
    while (y, m) <= (ye, me):
        yield y, m
        m += 1
        if m == 13:
            y, m = y + 1, 1


def fin_de_mois(y: int, m: int) -> date:
    return date(y, m, calendar.monthrange(y, m)[1])


def jour_ouvre(d: date) -> date:
    """Décale au lundi suivant si week-end."""
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d


def r2(x: float) -> float:
    return round(x + 1e-9, 2)


def ecrire_csv(chemin: Path, entetes: list, lignes: list):
    chemin.parent.mkdir(parents=True, exist_ok=True)
    with chemin.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(entetes)
        w.writerows(lignes)


# --------------------------------------------------------------------------------------
# Générateur
# --------------------------------------------------------------------------------------

class Generateur:
    def __init__(self, seed: int, debut: str, fin: str):
        self.rnd = random.Random(seed)
        self.debut, self.fin = debut, fin
        y, m = map(int, fin.split("-"))
        self.date_extraction = fin_de_mois(y, m)  # date de coupure des données
        self.gl = defaultdict(list)               # "YYYYMM" -> lignes
        self.seq = defaultdict(int)
        self.factures_clients = []
        self.factures_fournisseurs = []
        self.budget = []
        self.taux = {}                            # (yyyymm, devise) -> (moyen, cloture)
        self.clients = []
        self.fournisseurs = defaultdict(list)     # (entite, compte) -> [codes]
        self.fournisseurs_rows = []
        self.profil_paiement = {}

    # ---------------- écritures ----------------
    def ecriture(self, entite, devise, journal, d: date, lignes, libelle, piece=""):
        """lignes = [(compte, cc, debit, credit)] ; ignore si après la date d'extraction."""
        if d > self.date_extraction:
            return
        td = r2(sum(x[2] for x in lignes))
        tc = r2(sum(x[3] for x in lignes))
        assert abs(td - tc) < 0.005, f"Écriture déséquilibrée {libelle}: {td} vs {tc}"
        cle = d.strftime("%Y%m")
        self.seq[(entite, journal, cle)] += 1
        num = f"{entite}-{journal}-{cle}-{self.seq[(entite, journal, cle)]:05d}"
        for i, (compte, cc, debit, credit) in enumerate(lignes, start=1):
            self.gl[cle].append([num, i, entite, journal, iso(d), compte, cc or "", libelle,
                                 fr_num(debit), fr_num(credit), devise, piece])

    # ---------------- référentiels ----------------
    def nom_societe(self, pays):
        return f"{self.rnd.choice(NOMS_A)} {self.rnd.choice(NOMS_B)} {self.rnd.choice(FORMES[pays])}"

    def generer_tiers(self):
        pays = {e[0]: e[2] for e in ENTITES}
        n = 0
        for p in PROFILS:
            for _ in range(p.nb_clients):
                n += 1
                code = f"CLI-{n:05d}"
                profil = self.rnd.choices(["bon", "moyen", "mauvais"], [0.6, 0.3, 0.1])[0]
                self.profil_paiement[code] = profil
                poids = self.rnd.lognormvariate(0, 1.0)  # loi de Pareto approx. : gros clients
                nom = self.nom_societe(pays[p.code])
                if self.rnd.random() < 0.08:
                    nom = f"  {nom}   "  # anomalie : espaces parasites
                self.clients.append({
                    "code": code, "nom": nom, "pays": pays[p.code],
                    "secteur": self.rnd.choice(SECTEURS),
                    "segment": "Grand compte" if poids > 2.5 else ("ETI" if poids > 0.8 else "PME"),
                    "delai": self.rnd.choice([30, 30, 45, 45, 60]),
                    "entite": p.code, "poids": poids,
                })
        n = 0
        for p in PROFILS:
            comptes = [p.compte_cout_ventes] + list(CHARGES_EXTERNES)
            for compte in comptes:
                for _ in range(self.rnd.randint(2, 5)):
                    n += 1
                    code = f"FRN-{n:05d}"
                    self.fournisseurs[(p.code, compte)].append(code)
                    self.fournisseurs_rows.append([
                        code, self.nom_societe(pays[p.code]), pays[p.code],
                        CATEGORIES_FOURNISSEURS[compte], self.rnd.choice([30, 45, 60]), p.code])

    # ---------------- taux de change ----------------
    def generer_taux(self):
        niveaux = {"EUR": 1.0, "GBP": 1.165, "MAD": 0.0915}
        vol = {"EUR": 0.0, "GBP": 0.012, "MAD": 0.008}
        for y, m in iter_mois(self.debut, self.fin):
            cle = f"{y}{m:02d}"
            for dev in niveaux:
                if dev != "EUR":
                    niveaux[dev] *= math.exp(self.rnd.gauss(0, vol[dev]))
                moyen = niveaux[dev]
                cloture = moyen * math.exp(self.rnd.gauss(0, vol[dev] / 2))
                self.taux[(cle, dev)] = (round(moyen, 6), round(cloture, 6))

    # ---------------- simulation mensuelle ----------------
    def simuler(self):
        y0, m0 = map(int, self.debut.split("-"))
        tva_a_regler = defaultdict(lambda: [0.0, 0.0])  # (entite, yyyymm) -> [collectée, déductible]
        is_a_payer = defaultdict(float)
        sociales_a_payer = defaultdict(float)
        clients_par_entite = defaultdict(list)
        for c in self.clients:
            clients_par_entite[c["entite"]].append(c)

        # À-nouveaux (bilan d'ouverture)
        for p in PROFILS:
            d0 = date(y0, m0, 1)
            fonds_propres = p.tresorerie_ouverture + p.immobilisations - p.emprunt
            capital = r2(fonds_propres * 0.4)
            reserves = r2(fonds_propres - capital)
            lignes = [("512000", "", p.tresorerie_ouverture, 0), ("218300", "", p.immobilisations, 0),
                      ("101000", "", 0, capital), ("106000", "", 0, reserves)]
            if p.emprunt:
                lignes.append(("164000", "", 0, p.emprunt))
            self.ecriture(p.code, p.devise, "AN", d0, lignes, "À-nouveaux d'ouverture")

        for idx, (y, m) in enumerate(iter_mois(self.debut, self.fin)):
            cle = f"{y}{m:02d}"
            fdm = fin_de_mois(y, m)
            for p in PROFILS:
                annees = idx / 12
                base = p.ca_mensuel_base * (1 + p.croissance_annuelle) ** annees
                ca_cible = base * SAISONNALITE[m - 1] * self.rnd.uniform(0.93, 1.07)
                resultat = 0.0

                # ---- Règlement TVA et IS du mois précédent, charges sociales ----
                prev = f"{y - 1}12" if m == 1 else f"{y}{m - 1:02d}"
                coll, ded = tva_a_regler.pop((p.code, prev), [0.0, 0.0])
                if coll or ded:
                    net = r2(coll - ded)
                    lignes = [("445710", "", r2(coll), 0), ("445660", "", 0, r2(ded))]
                    lignes.append(("512000", "", 0, net) if net >= 0 else ("512000", "", -net, 0))
                    self.ecriture(p.code, p.devise, "BQ", jour_ouvre(date(y, m, 15)), lignes,
                                  f"Règlement TVA {prev}")
                montant_is = r2(is_a_payer.pop((p.code, prev), 0.0))
                if montant_is > 0:
                    self.ecriture(p.code, p.devise, "BQ", jour_ouvre(date(y, m, 20)),
                                  [("444000", "", montant_is, 0), ("512000", "", 0, montant_is)],
                                  f"Acompte IS {prev}")
                soc = r2(sociales_a_payer.pop((p.code, prev), 0.0))
                if soc > 0:
                    self.ecriture(p.code, p.devise, "BQ", jour_ouvre(date(y, m, 15)),
                                  [("431000", "", soc, 0), ("512000", "", 0, soc)],
                                  f"Charges sociales {prev}")

                # ---- Ventes ----
                clients = clients_par_entite[p.code]
                poids = [c["poids"] for c in clients]
                ca_restant = ca_cible
                while ca_restant >= 100:
                    ht = r2(min(ca_restant, max(500.0, self.rnd.lognormvariate(
                        math.log(p.facture_moyenne), 0.6))))
                    ca_restant -= ht
                    c = self.rnd.choices(clients, poids)[0]
                    compte = self.rnd.choices([x[0] for x in p.compte_ca], [x[1] for x in p.compte_ca])[0]
                    d_fact = jour_ouvre(date(y, m, self.rnd.randint(1, 28)))
                    tva = r2(ht * p.taux_tva)
                    ttc = r2(ht + tva)
                    num = f"FC-{p.code[-2:]}-{cle}-{len(self.factures_clients) + 1:06d}"
                    self.ecriture(p.code, p.devise, "VT", d_fact,
                                  [("411000", "", ttc, 0), (compte, "VEN", 0, ht), ("445710", "", 0, tva)],
                                  f"Facture {num}", num)
                    tva_a_regler[(p.code, cle)][0] += tva
                    resultat += ht
                    echeance = d_fact + timedelta(days=c["delai"])
                    profil = self.profil_paiement[c["code"]]
                    if self.rnd.random() < 0.015:
                        d_paie = None  # litige : jamais payée
                    else:
                        decalage = {"bon": self.rnd.gauss(-2, 5), "moyen": self.rnd.gauss(15, 10),
                                    "mauvais": self.rnd.gauss(50, 25)}[profil]
                        d_paie = jour_ouvre(echeance + timedelta(days=int(max(-20, decalage))))
                    if d_paie and d_paie <= self.date_extraction:
                        self.ecriture(p.code, p.devise, "BQ", d_paie,
                                      [("512000", "", ttc, 0), ("411000", "", 0, ttc)],
                                      f"Encaissement {num}", num)
                        statut = "PAYEE"
                    else:
                        d_paie, statut = None, "OUVERTE"
                    code_client = c["code"].lower() if self.rnd.random() < 0.01 else c["code"]
                    self.factures_clients.append([
                        num, p.code, code_client, fr_date(d_fact), fr_date(echeance), fr_num(ht),
                        fr_num(tva), fr_num(ttc), p.devise, fr_date(d_paie) if d_paie else "", statut])

                # ---- Achats (coût des ventes + charges externes) ----
                achats = [(p.compte_cout_ventes, ca_cible * p.taux_cout_ventes, ["OPS"], False)]
                base_charges = base * p.taux_charges_ext
                for compte, (poids_c, ccs, recurrent) in CHARGES_EXTERNES.items():
                    montant = base_charges * poids_c * (1 if recurrent else self.rnd.uniform(0.7, 1.3))
                    if compte == "625100" and m == 8:
                        montant *= 0.4
                    achats.append((compte, montant, ccs, recurrent))
                for compte, montant, ccs, recurrent in achats:
                    nb = 1 if recurrent else self.rnd.randint(1, 4)
                    for part in self._repartir(montant, nb):
                        ht = r2(part)
                        if ht <= 0:
                            continue
                        frn = self.rnd.choice(self.fournisseurs[(p.code, compte)])
                        cc = self.rnd.choice(ccs)
                        if self.rnd.random() < 0.01:
                            cc = ""  # anomalie : centre de coûts non renseigné
                        d_fact = jour_ouvre(date(y, m, self.rnd.randint(1, 28)))
                        tva = r2(ht * p.taux_tva)
                        ttc = r2(ht + tva)
                        num = f"FF-{p.code[-2:]}-{cle}-{len(self.factures_fournisseurs) + 1:06d}"
                        self.ecriture(p.code, p.devise, "AC", d_fact,
                                      [(compte, cc, ht, 0), ("445660", "", tva, 0), ("401000", "", 0, ttc)],
                                      f"Facture fournisseur {num}", num)
                        tva_a_regler[(p.code, cle)][1] += tva
                        resultat -= ht
                        delai = 45 if compte != "613200" else 0
                        echeance = d_fact + timedelta(days=delai)
                        d_paie = jour_ouvre(echeance + timedelta(days=int(self.rnd.gauss(3, 6))))
                        if d_paie < d_fact:
                            d_paie = d_fact
                        if d_paie <= self.date_extraction:
                            self.ecriture(p.code, p.devise, "BQ", d_paie,
                                          [("401000", "", ttc, 0), ("512000", "", 0, ttc)],
                                          f"Paiement {num}", num)
                            statut = "PAYEE"
                        else:
                            d_paie, statut = None, "OUVERTE"
                        self.factures_fournisseurs.append([
                            num, p.code, frn, fr_date(d_fact), fr_date(echeance), fr_num(ht), fr_num(tva),
                            fr_num(ttc), p.devise, fr_date(d_paie) if d_paie else "", statut])

                # ---- Paie ----
                masse = base * p.taux_personnel / (1 + p.taux_charges_sociales)
                if m == 12:
                    masse *= 1.5  # 13e mois / primes
                lignes, net_total, org_total = [], 0.0, 0.0
                for cc, w in POIDS_PERSONNEL.items():
                    brut = r2(masse * w * self.rnd.uniform(0.98, 1.02))
                    charges = r2(brut * p.taux_charges_sociales)
                    lignes += [("641000", cc, brut, 0), ("645000", cc, charges, 0)]
                    net = r2(brut * 0.78)
                    net_total += net
                    org_total += r2(brut - net) + charges
                    resultat -= brut + charges
                lignes += [("421000", "", 0, r2(net_total)), ("431000", "", 0, r2(org_total))]
                self.ecriture(p.code, p.devise, "PA", fdm, lignes, f"Paie {m:02d}/{y}")
                self.ecriture(p.code, p.devise, "BQ", fdm,
                              [("421000", "", r2(net_total), 0), ("512000", "", 0, r2(net_total))],
                              f"Virement salaires {m:02d}/{y}")
                sociales_a_payer[(p.code, cle)] += org_total

                # ---- Amortissements ----
                dot = r2(p.immobilisations / 60)
                self.ecriture(p.code, p.devise, "OD", fdm,
                              [("681100", "IT", dot, 0), ("281800", "", 0, dot)], f"Dotation amortissements {cle}")
                resultat -= dot

                # ---- Financier ----
                if p.emprunt:
                    interets = r2(p.emprunt * p.taux_interet / 12)
                    self.ecriture(p.code, p.devise, "BQ", fdm,
                                  [("661100", "FIN", interets, 0), ("512000", "", 0, interets)],
                                  f"Intérêts emprunt {cle}")
                    resultat -= interets
                produits_fin = r2(p.tresorerie_ouverture * 0.01 / 12 * self.rnd.uniform(0.5, 1.5))
                self.ecriture(p.code, p.devise, "BQ", fdm,
                              [("512000", "", produits_fin, 0), ("768000", "FIN", 0, produits_fin)],
                              f"Produits de placement {cle}")
                resultat += produits_fin

                # ---- Impôt sur les sociétés ----
                impot = r2(max(0.0, resultat) * p.taux_is)
                if impot > 0:
                    self.ecriture(p.code, p.devise, "OD", fdm,
                                  [("695000", "FIN", impot, 0), ("444000", "", 0, impot)], f"Provision IS {cle}")
                    is_a_payer[(p.code, cle)] += impot

                # ---- Budget (établi en début d'année, un peu optimiste) ----
                self._budget(p, y, m, idx)

        # Le budget couvre l'année complète, y compris les mois postérieurs à l'extraction
        ye, me = map(int, self.fin.split("-"))
        for m in range(me + 1, 13):
            idx = (ye - y0) * 12 + (m - m0)
            for p in PROFILS:
                self._budget(p, ye, m, idx)

    def _repartir(self, montant, nb):
        poids = [self.rnd.uniform(0.5, 1.5) for _ in range(nb)]
        s = sum(poids)
        return [montant * w / s for w in poids]

    def _budget(self, p: ProfilEntite, y, m, idx):
        annee_mois = f"{y}-{m:02d}"
        idx_janvier = idx - (m - 1)
        base = p.ca_mensuel_base * (1 + p.croissance_annuelle * 1.25) ** (max(idx_janvier, 0) / 12)
        ca = base * SAISONNALITE[m - 1]
        rows = []
        for compte, w in p.compte_ca:
            rows.append((compte, "VEN", ca * w))
        rows.append((p.compte_cout_ventes, "OPS", ca * p.taux_cout_ventes * 0.97))
        for compte, (poids_c, ccs, _) in CHARGES_EXTERNES.items():
            montant = base * p.taux_charges_ext * poids_c * 0.95
            for cc in ccs:
                rows.append((compte, cc, montant / len(ccs)))
        masse = base * p.taux_personnel / (1 + p.taux_charges_sociales) * (1.5 if m == 12 else 1.0) * 0.98
        for cc, w in POIDS_PERSONNEL.items():
            rows.append(("641000", cc, masse * w))
            rows.append(("645000", cc, masse * w * p.taux_charges_sociales))
        rows.append(("681100", "IT", p.immobilisations / 60))
        if p.emprunt:
            rows.append(("661100", "FIN", p.emprunt * p.taux_interet / 12))
        produits = sum(r[2] for r in rows if r[0].startswith("7"))
        charges = sum(r[2] for r in rows if r[0].startswith("6"))
        rows.append(("695000", "FIN", max(0.0, produits - charges) * p.taux_is))
        for compte, cc, montant in rows:
            self.budget.append([p.code, compte, cc, annee_mois, fr_num(r2(montant)), p.devise])

    # ---------------- anomalies & export ----------------
    def ecrire(self, out: Path):
        ref = out / "referentiels"
        ecrire_csv(ref / "entites.csv", ["code_entite", "nom_entite", "pays", "devise", "date_creation"],
                   [list(e) for e in ENTITES])
        ecrire_csv(ref / "plan_comptable.csv", ["numero_compte", "libelle_compte", "classe", "nature"],
                   [list(c) for c in PLAN_COMPTABLE])
        ecrire_csv(ref / "mapping_pnl.csv", ["numero_compte", "ligne_pnl", "ordre_pnl", "agregat"],
                   [list(c) for c in MAPPING_PNL])
        ecrire_csv(ref / "centres_couts.csv", ["code_cc", "libelle_cc", "departement", "responsable"],
                   [list(c) for c in CENTRES_COUTS])
        ecrire_csv(ref / "clients.csv",
                   ["code_client", "raison_sociale", "pays", "secteur", "segment", "delai_paiement_jours",
                    "code_entite"],
                   [[c["code"], c["nom"], c["pays"], c["secteur"], c["segment"], c["delai"], c["entite"]]
                    for c in self.clients])
        ecrire_csv(ref / "fournisseurs.csv",
                   ["code_fournisseur", "raison_sociale", "pays", "categorie", "delai_paiement_jours",
                    "code_entite"], self.fournisseurs_rows)

        ecrire_csv(out / "taux_change" / "taux_change.csv",
                   ["annee_mois", "devise", "taux_moyen_eur", "taux_cloture_eur"],
                   [[f"{k[0][:4]}-{k[0][4:]}", k[1], f"{v[0]:.6f}".replace(".", ","),
                     f"{v[1]:.6f}".replace(".", ",")] for k, v in sorted(self.taux.items())])

        par_annee = defaultdict(list)
        for row in self.budget:
            par_annee[row[3][:4]].append(row)
        for annee, rows in par_annee.items():
            ecrire_csv(out / "budget" / f"budget_{annee}.csv",
                       ["code_entite", "numero_compte", "code_cc", "annee_mois", "montant_budget", "devise"], rows)

        # Anomalie : quelques factures exportées en double
        fc = self.factures_clients + self.rnd.sample(self.factures_clients, 6)
        ecrire_csv(out / "factures_clients" / "factures_clients.csv",
                   ["num_facture", "code_entite", "code_client", "date_facture", "date_echeance", "montant_ht",
                    "montant_tva", "montant_ttc", "devise", "date_paiement", "statut"], fc)
        ecrire_csv(out / "factures_fournisseurs" / "factures_fournisseurs.csv",
                   ["num_facture", "code_entite", "code_fournisseur", "date_facture", "date_echeance",
                    "montant_ht", "montant_tva", "montant_ttc", "devise", "date_paiement", "statut"],
                   self.factures_fournisseurs)

        entetes_gl = ["num_ecriture", "num_ligne", "code_entite", "journal", "date_comptable", "numero_compte",
                      "code_cc", "libelle", "debit", "credit", "devise", "reference_piece"]
        for cle, lignes in sorted(self.gl.items()):
            # Anomalie : ~0,2 % de lignes dupliquées par l'export ERP
            doublons = self.rnd.sample(lignes, max(1, len(lignes) // 500))
            ecrire_csv(out / "gl" / f"ecritures_gl_{cle}.csv", entetes_gl, lignes + doublons)

    def resume(self):
        nb_gl = sum(len(v) for v in self.gl.values())
        return (f"{nb_gl} lignes GL sur {len(self.gl)} mois, {len(self.factures_clients)} factures clients, "
                f"{len(self.factures_fournisseurs)} factures fournisseurs, {len(self.budget)} lignes de budget, "
                f"{len(self.clients)} clients, {len(self.fournisseurs_rows)} fournisseurs")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "raw"))
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--start", default="2024-01")
    ap.add_argument("--end", default="2026-10")
    args = ap.parse_args()

    g = Generateur(args.seed, args.start, args.end)
    g.generer_tiers()
    g.generer_taux()
    g.simuler()
    g.ecrire(Path(args.out))
    print(f"✅ Données générées dans {args.out}\n   {g.resume()}")


if __name__ == "__main__":
    main()

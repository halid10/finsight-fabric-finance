# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_04 — Contrôles qualité & réconciliation
#
# Chaque contrôle écrit une ligne dans la table **`dq_resultats`** (historisée).
# Si au moins un contrôle est `KO`, le notebook **lève une exception** → le pipeline échoue et alerte.
#
# | # | Contrôle | Pourquoi |
# |---|---|---|
# | 1 | Lignes GL Silver = clés distinctes Bronze | Aucune perte, doublons supprimés |
# | 2 | Pas de clé dupliquée en Silver | Dédoublonnage effectif |
# | 3 | Toutes les écritures équilibrées | Intégrité comptable |
# | 4 | Σ montant Gold = Σ montant Silver (EUR) | Pas de perte entre Silver et Gold |
# | 5 | Aucune clé -1 dans `fact_gl` | Référentiels complets |
# | 6 | Taux de change présent pour chaque ligne | Conversion EUR fiable |
# | 7 | CA du GL = CA des factures clients | Cohérence AR ↔ comptabilité |
# | 8 | Solde 411 = encours des factures ouvertes | Cohérence balance âgée ↔ comptabilité |

# CELL ********************

from datetime import datetime, timezone

from pyspark.sql import functions as F

run_ts = datetime.now(timezone.utc)
resultats = []


def controle(nom: str, attendu, obtenu, tolerance: float = 0.0):
    ok = abs(float(attendu or 0) - float(obtenu or 0)) <= tolerance
    resultats.append((run_ts, nom, "OK" if ok else "KO", str(attendu), str(obtenu)))
    print(f"{'✅' if ok else '❌'} {nom:<55} attendu={attendu}  obtenu={obtenu}")


def scalaire(sql: str):
    return spark.sql(sql).collect()[0][0]

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

controle("01 GL : lignes Silver = clés distinctes Bronze",
         scalaire("SELECT COUNT(DISTINCT num_ecriture, num_ligne) FROM bronze_ecritures_gl"),
         scalaire("SELECT COUNT(*) FROM silver_ecritures_gl"))

controle("02 GL : aucune clé dupliquée en Silver", 0,
         scalaire("""SELECT COUNT(*) FROM (SELECT num_ecriture, num_ligne FROM silver_ecritures_gl
                     GROUP BY 1, 2 HAVING COUNT(*) > 1)"""))

controle("03 GL : écritures déséquilibrées", 0,
         scalaire("""SELECT COUNT(*) FROM (SELECT num_ecriture FROM silver_ecritures_gl
                     GROUP BY num_ecriture HAVING SUM(montant) <> 0)"""))

controle("04 Σ montant_pnl_eur Gold = Silver",
         scalaire("SELECT SUM(montant_pnl_eur) FROM silver_ecritures_gl"),
         scalaire("SELECT SUM(montant_pnl_eur) FROM fact_gl"), tolerance=0.01)

controle("05 fact_gl : lignes avec une clé inconnue (-1)", 0,
         scalaire("""SELECT COUNT(*) FROM fact_gl
                     WHERE date_key = -1 OR entite_key = -1 OR compte_key = -1 OR (cc_key = -1 AND compte_key IN
                     (SELECT compte_key FROM dim_compte WHERE est_compte_resultat))"""))

controle("06 Lignes GL sans taux de change", 0,
         scalaire("SELECT COUNT(*) FROM silver_ecritures_gl WHERE taux_moyen_eur IS NULL"))

controle("07 CA GL (706, journal VT) = Σ HT factures clients",
         scalaire("SELECT SUM(montant_ht) FROM silver_factures_clients"),
         scalaire("""SELECT SUM(credit) FROM silver_ecritures_gl
                     WHERE journal = 'VT' AND numero_compte LIKE '706%'"""), tolerance=0.01)

controle("08 Solde 411 = TTC des factures clients ouvertes",
         scalaire("SELECT SUM(montant_ttc) FROM silver_factures_clients WHERE date_paiement IS NULL"),
         scalaire("SELECT SUM(montant) FROM silver_ecritures_gl WHERE numero_compte = '411000'"), tolerance=0.01)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## Historisation et verdict

# CELL ********************

df = spark.createDataFrame(resultats, "run_ts timestamp, controle string, statut string, attendu string, obtenu string")
df.write.format("delta").mode("append").saveAsTable("dq_resultats")
display(df)

nb_ko = df.filter(F.col("statut") == "KO").count()
if nb_ko:
    raise Exception(f"{nb_ko} contrôle(s) qualité en échec — voir la table dq_resultats")
print("Tous les contrôles qualité sont OK ✅")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_03 — Couche Gold (schéma en étoile)
#
# | Dimensions | Faits |
# |---|---|
# | `dim_date`, `dim_entite`, `dim_compte`, `dim_centre_cout`, `dim_client`, `dim_fournisseur` | `fact_gl`, `fact_budget`, `fact_factures_clients`, `fact_factures_fournisseurs`, `fact_taux_change` |
#
# - Clés de substitution entières (`*_key`), membre **-1 « Inconnu »** dans chaque dimension.
# - Clé de date au format `yyyymmdd` (entier).
# - Tables optimisées pour **Direct Lake** (V-Order + `OPTIMIZE`).

# PARAMETERS CELL ********************

date_arrete = "2026-10-31"   # date d'extraction des données (calcul des retards / balance âgée)
date_debut = "2024-01-01"
date_fin = "2026-12-31"

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

from pyspark.sql import DataFrame
from pyspark.sql import functions as F
from pyspark.sql.window import Window

spark.conf.set("spark.sql.parquet.vorder.enabled", "true")   # V-Order (lecture Direct Lake optimale)


def ecrire(df: DataFrame, table: str):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(table)
    spark.sql(f"OPTIMIZE {table}")
    print(f"  {table:<30} {spark.table(table).count():>8} lignes")


def avec_cle(df: DataFrame, nom_cle: str, ordre: str, inconnu: dict) -> DataFrame:
    """Ajoute une clé de substitution + une ligne -1 « Inconnu »."""
    df = df.withColumn(nom_cle, F.row_number().over(Window.orderBy(ordre)))
    ligne = {c: inconnu.get(c) for c in df.columns}
    ligne[nom_cle] = -1
    inconnu_df = spark.createDataFrame([tuple(ligne[f.name] for f in df.schema.fields)], schema=df.schema)
    return inconnu_df.unionByName(df).select(nom_cle, *[c for c in df.columns if c != nom_cle])


def date_key(col):
    return F.coalesce(F.date_format(col, "yyyyMMdd").cast("int"), F.lit(-1))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1. dim_date

# CELL ********************

mois_fr = F.array(*[F.lit(m) for m in ["Janvier", "Février", "Mars", "Avril", "Mai", "Juin", "Juillet",
                                         "Août", "Septembre", "Octobre", "Novembre", "Décembre"]])
jours_fr = F.array(*[F.lit(j) for j in ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]])

dim_date = (
    spark.sql(f"SELECT explode(sequence(to_date('{date_debut}'), to_date('{date_fin}'), interval 1 day)) AS date")
    .withColumn("date_key", date_key("date"))
    .withColumn("annee", F.year("date"))
    .withColumn("trimestre", F.concat(F.lit("T"), F.quarter("date")))
    .withColumn("annee_trimestre", F.concat(F.year("date"), F.lit("-T"), F.quarter("date")))
    .withColumn("mois", F.month("date"))
    .withColumn("mois_nom", F.element_at(mois_fr, F.month("date")))
    .withColumn("mois_court", F.substring(F.element_at(mois_fr, F.month("date")), 1, 4))
    .withColumn("annee_mois", F.date_format("date", "yyyy-MM"))
    .withColumn("annee_mois_num", (F.year("date") * 100 + F.month("date")).cast("int"))
    .withColumn("jour", F.dayofmonth("date"))
    .withColumn("jour_semaine_num", ((F.dayofweek("date") + 5) % 7 + 1).cast("int"))   # 1 = lundi
    .withColumn("jour_semaine", F.element_at(jours_fr, F.col("jour_semaine_num")))
    .withColumn("est_jour_ouvre", F.col("jour_semaine_num") <= 5)
    .withColumn("est_fin_de_mois", F.col("date") == F.last_day("date"))
    .withColumn("est_avant_arrete", F.col("date") <= F.lit(date_arrete).cast("date"))
    .select("date_key", "date", "annee", "trimestre", "annee_trimestre", "mois", "mois_nom", "mois_court",
            "annee_mois", "annee_mois_num", "jour", "jour_semaine_num", "jour_semaine",
            "est_jour_ouvre", "est_fin_de_mois", "est_avant_arrete")
)
ecrire(dim_date, "dim_date")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. Dimensions métier

# CELL ********************

INC = "Inconnu"

ecrire(avec_cle(spark.table("silver_entites").drop("date_creation"), "entite_key", "code_entite",
                {"code_entite": "N/A", "nom_entite": INC, "pays": INC, "devise": "EUR"}), "dim_entite")

dim_compte = (
    spark.table("silver_plan_comptable")
    .withColumn("est_compte_resultat", F.col("nature").isin("PRODUIT", "CHARGE"))
    .withColumn("compte_libelle", F.concat_ws(" - ", "numero_compte", "libelle_compte"))
    .withColumn("ligne_pnl", F.coalesce("ligne_pnl", F.lit("Bilan")))
    .withColumn("ordre_pnl", F.coalesce("ordre_pnl", F.lit(999)))
)
ecrire(avec_cle(dim_compte, "compte_key", "numero_compte",
                {"numero_compte": "N/A", "libelle_compte": INC, "compte_libelle": INC, "classe": "?",
                 "nature": INC, "ligne_pnl": INC, "ordre_pnl": 999, "agregat": INC,
                 "est_compte_resultat": False}), "dim_compte")

ecrire(avec_cle(spark.table("silver_centres_couts"), "cc_key", "code_cc",
                {"code_cc": "N/A", "libelle_cc": INC, "departement": INC, "responsable": INC}), "dim_centre_cout")

ecrire(avec_cle(spark.table("silver_clients"), "client_key", "code_client",
                {"code_client": "N/A", "raison_sociale": INC, "pays": INC, "secteur": INC, "segment": INC,
                 "delai_paiement_jours": 0, "code_entite": "N/A"}), "dim_client")

ecrire(avec_cle(spark.table("silver_fournisseurs"), "fournisseur_key", "code_fournisseur",
                {"code_fournisseur": "N/A", "raison_sociale": INC, "pays": INC, "categorie": INC,
                 "delai_paiement_jours": 0, "code_entite": "N/A"}), "dim_fournisseur")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3. Faits comptables : fact_gl et fact_budget

# CELL ********************

def cles(df: DataFrame) -> DataFrame:
    """Remplace les codes métier par les clés de substitution (left join + -1 si absent)."""
    ent = spark.table("dim_entite").select("entite_key", "code_entite")
    cpt = spark.table("dim_compte").select("compte_key", "numero_compte")
    cc = spark.table("dim_centre_cout").select("cc_key", "code_cc")
    df = df.join(ent, "code_entite", "left").join(cpt, "numero_compte", "left")
    if "code_cc" in df.columns:
        df = df.join(cc, "code_cc", "left")
    for k in ["entite_key", "compte_key", "cc_key"]:
        if k in df.columns:
            df = df.withColumn(k, F.coalesce(k, F.lit(-1)))
    return df


fact_gl = cles(spark.table("silver_ecritures_gl")).select(
    date_key("date_comptable").alias("date_key"),
    "entite_key", "compte_key", "cc_key",
    "journal", "num_ecriture", "num_ligne", "libelle", "reference_piece", "devise",
    "debit", "credit",
    F.col("montant").alias("montant_devise"),
    "debit_eur", "credit_eur",
    "montant_eur",
    "montant_pnl_eur",
)
ecrire(fact_gl, "fact_gl")

fact_budget = cles(spark.table("silver_budget")).select(
    date_key("date_mois").alias("date_key"),
    "entite_key", "compte_key", "cc_key", "devise",
    F.col("montant_budget_pnl").alias("budget_pnl_devise"),
    F.col("montant_budget_pnl_eur").alias("budget_pnl_eur"),
)
ecrire(fact_budget, "fact_budget")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4. Faits de factures (créances et dettes)
#
# - `jours_retard` : facture payée → date paiement − échéance ; facture ouverte → date d'arrêté − échéance.
# - `tranche_age` (factures ouvertes uniquement) : *Non échue*, *0-30 j*, *31-60 j*, *61-90 j*, *> 90 j*.
# - Les dates restent aussi en colonnes `date` pour les mesures « à date » (encours, DSO).

# CELL ********************

arrete = F.lit(date_arrete).cast("date")


def fact_factures(table: str, col_tiers: str, dim_tiers: str, cle_tiers: str) -> DataFrame:
    tiers = spark.table(dim_tiers).select(cle_tiers, col_tiers)
    df = cles(spark.table(table)).join(tiers, col_tiers, "left").withColumn(cle_tiers, F.coalesce(cle_tiers, F.lit(-1)))
    est_ouverte = F.col("date_paiement").isNull()
    retard = F.when(est_ouverte, F.datediff(arrete, "date_echeance")).otherwise(F.datediff("date_paiement", "date_echeance"))
    return df.select(
        "num_facture",
        date_key("date_facture").alias("date_key"),
        date_key("date_echeance").alias("date_echeance_key"),
        date_key("date_paiement").alias("date_paiement_key"),
        "entite_key", cle_tiers,
        "date_facture", "date_echeance", "date_paiement",
        "devise", "montant_ht", "montant_tva", "montant_ttc", "montant_ht_eur", "montant_ttc_eur",
        "statut",
        est_ouverte.alias("est_ouverte"),
        retard.alias("jours_retard"),
        F.datediff(F.coalesce("date_paiement", arrete), "date_facture").alias("delai_reglement_jours"),
        F.when(~est_ouverte, F.lit("Réglée"))
         .when(retard <= 0, F.lit("Non échue"))
         .when(retard <= 30, F.lit("0-30 j"))
         .when(retard <= 60, F.lit("31-60 j"))
         .when(retard <= 90, F.lit("61-90 j"))
         .otherwise(F.lit("> 90 j")).alias("tranche_age"),
        F.when(~est_ouverte, F.lit(0))
         .when(retard <= 0, F.lit(1)).when(retard <= 30, F.lit(2)).when(retard <= 60, F.lit(3))
         .when(retard <= 90, F.lit(4)).otherwise(F.lit(5)).alias("tranche_age_ordre"),
    )


ecrire(fact_factures("silver_factures_clients", "code_client", "dim_client", "client_key"), "fact_factures_clients")
ecrire(fact_factures("silver_factures_fournisseurs", "code_fournisseur", "dim_fournisseur", "fournisseur_key"),
       "fact_factures_fournisseurs")

ecrire(
    spark.table("silver_taux_change").select(
        date_key(F.to_date(F.concat("annee_mois", F.lit("-01")))).alias("date_key"),
        "devise", "taux_moyen_eur", "taux_cloture_eur"),
    "fact_taux_change",
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 5. Aperçu : compte de résultat annuel du groupe (EUR)

# CELL ********************

display(spark.sql("""
    SELECT d.annee, c.ordre_pnl, c.ligne_pnl, ROUND(SUM(f.montant_pnl_eur) / 1e6, 2) AS montant_m_eur
    FROM fact_gl f
    JOIN dim_compte c ON f.compte_key = c.compte_key
    JOIN dim_date d   ON f.date_key = d.date_key
    WHERE c.est_compte_resultat
    GROUP BY d.annee, c.ordre_pnl, c.ligne_pnl
    ORDER BY d.annee, c.ordre_pnl
"""))

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

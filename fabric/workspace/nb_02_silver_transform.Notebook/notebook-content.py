# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_02 — Transformation Silver
#
# **Rôle** : produire des données **fiables et typées** à partir de Bronze.
#
# | Règle | Détail |
# |---|---|
# | Typage | décimales `,` → `decimal(18,2)`, dates `yyyy-MM-dd` / `dd/MM/yyyy` → `date` |
# | Nettoyage | `trim` sur les libellés, `upper` sur les codes |
# | Dédoublonnage | GL sur (`num_ecriture`, `num_ligne`), factures sur `num_facture` |
# | Valeurs manquantes | centre de coûts vide sur un compte de résultat → `NON_AFFECTE` |
# | Signe | `montant` = débit − crédit ; `montant_pnl` = crédit − débit (produits +, charges −) |
# | Devise | conversion en EUR au **taux moyen** du mois comptable |
#
# Mode : rechargement complet (`overwrite`). Le passage en `MERGE` incrémental est l'idée FS-70.

# CELL ********************

from pyspark.sql import DataFrame
from pyspark.sql import functions as F


def dec(col: str, scale: int = 2):
    """'12974,41' -> Decimal(18, scale)."""
    return F.regexp_replace(F.trim(F.col(col)), ",", ".").cast(f"decimal(18,{scale})")


def vide_en_null(col):
    """'' ou espaces -> NULL (compatible Spark 3.4+)."""
    c = F.trim(F.col(col)) if isinstance(col, str) else col
    return F.when(c == "", F.lit(None)).otherwise(c)


def date_fr(col: str):
    return F.to_date(vide_en_null(col), "dd/MM/yyyy")


def code(col: str):
    return F.upper(F.trim(F.col(col)))


def ecrire(df: DataFrame, table: str):
    df.write.format("delta").mode("overwrite").option("overwriteSchema", True).saveAsTable(table)
    print(f"  {table:<32} {spark.table(table).count():>8} lignes")


TECH = ["_source_file", "_ingestion_ts", "_batch_id"]

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1. Référentiels

# CELL ********************

ecrire(
    spark.table("bronze_entites").select(
        code("code_entite").alias("code_entite"),
        F.trim("nom_entite").alias("nom_entite"),
        F.trim("pays").alias("pays"),
        code("devise").alias("devise"),
        F.to_date("date_creation").alias("date_creation"),
    ),
    "silver_entites",
)

plan = spark.table("bronze_plan_comptable").select(
    F.trim("numero_compte").alias("numero_compte"),
    F.trim("libelle_compte").alias("libelle_compte"),
    F.trim("classe").alias("classe"),
    code("nature").alias("nature"),
)
mapping = spark.table("bronze_mapping_pnl").select(
    F.trim("numero_compte").alias("numero_compte"),
    F.trim("ligne_pnl").alias("ligne_pnl"),
    F.col("ordre_pnl").cast("int").alias("ordre_pnl"),
    F.trim("agregat").alias("agregat"),
)
ecrire(plan.join(mapping, "numero_compte", "left"), "silver_plan_comptable")

centres = spark.table("bronze_centres_couts").select(
    code("code_cc").alias("code_cc"),
    F.trim("libelle_cc").alias("libelle_cc"),
    F.trim("departement").alias("departement"),
    F.trim("responsable").alias("responsable"),
)
non_affecte = spark.createDataFrame(
    [("NON_AFFECTE", "Non affecté", "Non affecté", "À corriger")], centres.columns
)
ecrire(centres.unionByName(non_affecte), "silver_centres_couts")

ecrire(
    spark.table("bronze_clients").select(
        code("code_client").alias("code_client"),
        F.trim("raison_sociale").alias("raison_sociale"),
        F.trim("pays").alias("pays"),
        F.trim("secteur").alias("secteur"),
        F.trim("segment").alias("segment"),
        F.col("delai_paiement_jours").cast("int").alias("delai_paiement_jours"),
        code("code_entite").alias("code_entite"),
    ).dropDuplicates(["code_client"]),
    "silver_clients",
)

ecrire(
    spark.table("bronze_fournisseurs").select(
        code("code_fournisseur").alias("code_fournisseur"),
        F.trim("raison_sociale").alias("raison_sociale"),
        F.trim("pays").alias("pays"),
        F.trim("categorie").alias("categorie"),
        F.col("delai_paiement_jours").cast("int").alias("delai_paiement_jours"),
        code("code_entite").alias("code_entite"),
    ).dropDuplicates(["code_fournisseur"]),
    "silver_fournisseurs",
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. Taux de change
#
# `taux_moyen_eur` = valeur en EUR d'une unité de devise (ex. 1 GBP = 1,17 EUR).
# Une ligne EUR = 1 existe pour chaque mois, ce qui simplifie les jointures.

# CELL ********************

taux = spark.table("bronze_taux_change").select(
    F.trim("annee_mois").alias("annee_mois"),
    code("devise").alias("devise"),
    dec("taux_moyen_eur", 6).alias("taux_moyen_eur"),
    dec("taux_cloture_eur", 6).alias("taux_cloture_eur"),
)
ecrire(taux, "silver_taux_change")
taux = spark.table("silver_taux_change")


def convertir(df: DataFrame, col_date: str, colonnes: list) -> DataFrame:
    """Ajoute <col>_eur pour chaque colonne, au taux moyen du mois de col_date."""
    df = df.withColumn("_annee_mois", F.date_format(col_date, "yyyy-MM"))
    t = taux.select(F.col("annee_mois").alias("_annee_mois"), "devise", "taux_moyen_eur")
    df = df.join(t, ["_annee_mois", "devise"], "left")
    for c in colonnes:
        df = df.withColumn(f"{c}_eur", (F.col(c) * F.col("taux_moyen_eur")).cast("decimal(18,2)"))
    return df.drop("_annee_mois")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3. Grand livre

# CELL ********************

natures = spark.table("silver_plan_comptable").select("numero_compte", "nature")

gl = (
    spark.table("bronze_ecritures_gl")
    .dropDuplicates(["num_ecriture", "num_ligne"])               # doublons de l'export ERP
    .select(
        F.trim("num_ecriture").alias("num_ecriture"),
        F.col("num_ligne").cast("int").alias("num_ligne"),
        code("code_entite").alias("code_entite"),
        code("journal").alias("journal"),
        F.to_date("date_comptable", "yyyy-MM-dd").alias("date_comptable"),
        F.trim("numero_compte").alias("numero_compte"),
        code("code_cc").alias("code_cc"),
        F.trim("libelle").alias("libelle"),
        dec("debit").alias("debit"),
        dec("credit").alias("credit"),
        code("devise").alias("devise"),
        vide_en_null("reference_piece").alias("reference_piece"),
        "_source_file",
    )
    .join(natures, "numero_compte", "left")
    .withColumn(
        "code_cc",
        F.when(F.col("nature").isin("PRODUIT", "CHARGE") & (F.coalesce("code_cc", F.lit("")) == ""),
               F.lit("NON_AFFECTE"))
         .otherwise(vide_en_null("code_cc")),
    )
    .withColumn("montant", (F.col("debit") - F.col("credit")).cast("decimal(18,2)"))
    .withColumn("montant_pnl", (-F.col("montant")).cast("decimal(18,2)"))
)
gl = convertir(gl, "date_comptable", ["debit", "credit", "montant", "montant_pnl"])
ecrire(gl, "silver_ecritures_gl")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 4. Budget
#
# Le budget source est saisi en valeur positive. On applique la même convention que `montant_pnl` :
# produits **positifs**, charges **négatives**.

# CELL ********************

budget = (
    spark.table("bronze_budget")
    .select(
        code("code_entite").alias("code_entite"),
        F.trim("numero_compte").alias("numero_compte"),
        code("code_cc").alias("code_cc"),
        F.to_date(F.concat(F.trim("annee_mois"), F.lit("-01"))).alias("date_mois"),
        dec("montant_budget").alias("montant_budget_saisi"),
        code("devise").alias("devise"),
    )
    .join(natures, "numero_compte", "left")
    .withColumn(
        "montant_budget_pnl",
        F.when(F.col("nature") == "CHARGE", -F.col("montant_budget_saisi"))
         .otherwise(F.col("montant_budget_saisi")).cast("decimal(18,2)"),
    )
)
ecrire(convertir(budget, "date_mois", ["montant_budget_pnl"]), "silver_budget")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 5. Factures clients et fournisseurs

# CELL ********************

def factures(table_bronze: str, col_tiers: str) -> DataFrame:
    df = (
        spark.table(table_bronze)
        .withColumn("num_facture", F.trim("num_facture"))
        .dropDuplicates(["num_facture"])
        .select(
            "num_facture",
            code("code_entite").alias("code_entite"),
            code(col_tiers).alias(col_tiers),
            date_fr("date_facture").alias("date_facture"),
            date_fr("date_echeance").alias("date_echeance"),
            date_fr("date_paiement").alias("date_paiement"),
            dec("montant_ht").alias("montant_ht"),
            dec("montant_tva").alias("montant_tva"),
            dec("montant_ttc").alias("montant_ttc"),
            code("devise").alias("devise"),
            code("statut").alias("statut"),
        )
    )
    return convertir(df, "date_facture", ["montant_ht", "montant_ttc"])


ecrire(factures("bronze_factures_clients", "code_client"), "silver_factures_clients")
ecrire(factures("bronze_factures_fournisseurs", "code_fournisseur"), "silver_factures_fournisseurs")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 6. Bilan Bronze → Silver (doublons supprimés)

# CELL ********************

for b, s in [("bronze_ecritures_gl", "silver_ecritures_gl"),
             ("bronze_factures_clients", "silver_factures_clients"),
             ("bronze_factures_fournisseurs", "silver_factures_fournisseurs")]:
    nb, ns = spark.table(b).count(), spark.table(s).count()
    print(f"{b:<30} {nb:>8}  →  {s:<30} {ns:>8}   (doublons supprimés : {nb - ns})")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

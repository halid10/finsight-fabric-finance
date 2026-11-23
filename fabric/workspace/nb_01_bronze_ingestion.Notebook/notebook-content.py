# Fabric notebook source

# METADATA ********************

# META {
# META   "kernel_info": {
# META     "name": "synapse_pyspark"
# META   },
# META   "dependencies": {}
# META }

# MARKDOWN ********************

# # nb_01 — Ingestion Bronze
#
# **Rôle** : copier les fichiers CSV déposés dans `Files/raw/` vers des tables Delta `bronze.*`,
# **sans transformation métier** (toutes les colonnes restent en `string`).
#
# | Source | Table | Mode |
# |---|---|---|
# | `referentiels/*.csv` | `bronze_<nom>` | overwrite |
# | `taux_change`, `budget`, `factures_*` | `bronze_<nom>` | overwrite |
# | `gl/ecritures_gl_YYYYMM.csv` | `bronze.ecritures_gl` | **append incrémental** (seuls les nouveaux fichiers) |
#
# Colonnes techniques ajoutées : `_source_file`, `_ingestion_ts`, `_batch_id`.
#
# ⚠️ Prérequis : Lakehouse **lh_finsight** créé avec l'option *Lakehouse schemas* et attaché comme Lakehouse par défaut.
# Les tables sont écrites dans le schéma **`bronze`** (créé s'il n'existe pas).

# PARAMETERS CELL ********************

# Paramètres (cellule marquée « Toggle parameter cell » pour le pipeline)
raw_path = "Files/raw"
batch_id = ""

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# CELL ********************

import uuid
from datetime import datetime, timezone

from pyspark.sql import DataFrame
from pyspark.sql import functions as F

batch_id = batch_id or datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S") + "-" + uuid.uuid4().hex[:6]
print(f"Batch : {batch_id}")

# Lakehouse avec schémas : chaque couche a son schéma (bronze / silver / gold)
spark.sql("CREATE SCHEMA IF NOT EXISTS bronze")


def lire_csv(chemin: str) -> DataFrame:
    """Lit un ou plusieurs CSV « export ERP » : séparateur ;, en-tête, tout en string."""
    return (
        spark.read.format("csv")
        .option("header", True)
        .option("sep", ";")
        .option("encoding", "UTF-8")
        .option("inferSchema", False)
        .load(chemin)
        .select("*", F.col("_metadata.file_path").alias("_chemin"))
    )


def ajouter_colonnes_techniques(df: DataFrame) -> DataFrame:
    return (
        df.withColumn("_source_file", F.element_at(F.split("_chemin", "/"), -1))
        .withColumn("_ingestion_ts", F.current_timestamp())
        .withColumn("_batch_id", F.lit(batch_id))
        .drop("_chemin")
    )


def charger(chemin: str, table: str, mode: str = "overwrite") -> int:
    df = ajouter_colonnes_techniques(lire_csv(chemin))
    (df.write.format("delta").mode(mode).option("overwriteSchema", mode == "overwrite").saveAsTable(table))
    n = df.count()
    print(f"  {table:<32} {mode:<9} {n:>8} lignes")
    return n

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 1. Référentiels, taux, budget, factures (rechargement complet)

# CELL ********************

sources_completes = {
    "bronze.entites": "referentiels/entites.csv",
    "bronze.plan_comptable": "referentiels/plan_comptable.csv",
    "bronze.mapping_pnl": "referentiels/mapping_pnl.csv",
    "bronze.centres_couts": "referentiels/centres_couts.csv",
    "bronze.clients": "referentiels/clients.csv",
    "bronze.fournisseurs": "referentiels/fournisseurs.csv",
    "bronze.taux_change": "taux_change/*.csv",
    "bronze.budget": "budget/*.csv",
    "bronze.factures_clients": "factures_clients/*.csv",
    "bronze.factures_fournisseurs": "factures_fournisseurs/*.csv",
}

for table, relatif in sources_completes.items():
    charger(f"{raw_path}/{relatif}", table)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 2. Grand livre — chargement incrémental par fichier mensuel
#
# On ne charge que les fichiers `ecritures_gl_*.csv` qui ne sont pas encore présents dans
# `bronze.ecritures_gl` (colonne `_source_file`). Relancer le notebook est donc **idempotent**.

# CELL ********************

table_gl = "bronze.ecritures_gl"
fichiers = sorted(f.name for f in notebookutils.fs.ls(f"{raw_path}/gl") if f.name.endswith(".csv"))

if spark.catalog.tableExists(table_gl):
    deja_charges = {r[0] for r in spark.table(table_gl).select("_source_file").distinct().collect()}
else:
    deja_charges = set()

nouveaux = [f for f in fichiers if f not in deja_charges]
print(f"{len(fichiers)} fichiers GL trouvés, {len(deja_charges)} déjà chargés, {len(nouveaux)} à charger")

if nouveaux:
    charger([f"{raw_path}/gl/{f}" for f in nouveaux], table_gl, mode="append")

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

# MARKDOWN ********************

# ## 3. Contrôle rapide

# CELL ********************

display(
    spark.sql("""
        SELECT _source_file, COUNT(*) AS nb_lignes, MAX(_ingestion_ts) AS derniere_ingestion
        FROM bronze.ecritures_gl
        GROUP BY _source_file
        ORDER BY _source_file DESC
    """)
)

# METADATA ********************

# META {
# META   "language": "python",
# META   "language_group": "synapse_pyspark"
# META }

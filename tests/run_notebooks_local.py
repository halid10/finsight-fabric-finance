"""
Exécute les notebooks Fabric (fabric/workspace/*.Notebook) en local avec PySpark + Delta Lake,
pour valider toute la chaîne Bronze → Silver → Gold → Qualité sans tenant Fabric.

Utilisé par la CI GitHub Actions. En local (Java 17 requis) :
    pip install pyspark==3.5.3 delta-spark==3.2.1
    python3 tests/run_notebooks_local.py

Ce que fait le harnais :
  - crée une session Spark locale avec Delta Lake (comme le runtime Fabric) ;
  - simule le Lakehouse : dossier temporaire contenant Files/raw -> data/raw ;
  - simule `notebookutils.fs.ls` et `display` ;
  - extrait les cellules de code de chaque notebook-content.py et les exécute dans l'ordre.
"""
import os
import re
import sys
import tempfile
import traceback
import types
from pathlib import Path

from delta import configure_spark_with_delta_pip
from pyspark.sql import SparkSession

RACINE = Path(__file__).resolve().parents[1]
NOTEBOOKS = sorted((RACINE / "fabric" / "workspace").glob("nb_*.Notebook"))
MARQUEUR = re.compile(r"^# (CELL|PARAMETERS CELL|MARKDOWN|METADATA) \*+\s*$")


def cellules_code(chemin: Path):
    bloc, type_bloc = [], None
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        m = MARQUEUR.match(ligne)
        if m:
            if type_bloc in ("CELL", "PARAMETERS CELL"):
                yield "\n".join(bloc)
            bloc, type_bloc = [], m.group(1)
        else:
            bloc.append(ligne)
    if type_bloc in ("CELL", "PARAMETERS CELL"):
        yield "\n".join(bloc)


def main():
    lakehouse = Path(tempfile.mkdtemp(prefix="lh_finsight_"))
    (lakehouse / "Files").mkdir()
    os.symlink(RACINE / "data" / "raw", lakehouse / "Files" / "raw")
    os.chdir(lakehouse)

    builder = (
        SparkSession.builder.master("local[2]").appName("finsight-ci")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog")
        .config("spark.sql.warehouse.dir", str(lakehouse / "Tables"))
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.ui.enabled", "false")
    )
    spark = configure_spark_with_delta_pip(builder).getOrCreate()
    spark.sparkContext.setLogLevel("ERROR")

    def ls(chemin):
        return [types.SimpleNamespace(name=n, path=str(Path(chemin) / n)) for n in sorted(os.listdir(chemin))]

    notebookutils = types.SimpleNamespace(fs=types.SimpleNamespace(ls=ls))

    def display(df):
        df.show(30, truncate=False)

    for nb in NOTEBOOKS:
        print(f"\n{'=' * 80}\n▶ {nb.name}\n{'=' * 80}")
        contexte = {"spark": spark, "notebookutils": notebookutils, "display": display, "__name__": "__main__"}
        for i, code in enumerate(cellules_code(nb / "notebook-content.py"), start=1):
            try:
                exec(compile(code, f"{nb.name}[cellule {i}]", "exec"), contexte)
            except Exception:
                print(f"❌ Échec dans {nb.name}, cellule {i}")
                if os.environ.get("GITHUB_ACTIONS"):
                    # Annotation GitHub : visible sur la page du run sans être connecté
                    tb = traceback.format_exc()[-3500:]
                    tb = tb.replace("%", "%25").replace("\r", "").replace("\n", "%0A")
                    print(f"::error title={nb.name} cellule {i}::{tb}")
                raise

    # Idempotence de l'ingestion Bronze : une 2e exécution ne doit rien ajouter
    avant = spark.table("bronze.ecritures_gl").count()
    contexte = {"spark": spark, "notebookutils": notebookutils, "display": display}
    for code in cellules_code(NOTEBOOKS[0] / "notebook-content.py"):
        exec(code, contexte)
    apres = spark.table("bronze.ecritures_gl").count()
    assert avant == apres, f"Ingestion non idempotente : {avant} -> {apres}"
    print(f"\n✅ Chaîne complète exécutée, ingestion idempotente ({apres} lignes bronze GL)")
    spark.stop()
    return 0


if __name__ == "__main__":
    sys.exit(main())

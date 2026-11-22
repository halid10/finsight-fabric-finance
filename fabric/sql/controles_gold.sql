-- =====================================================================
--  FinSight — Requêtes de contrôle sur le SQL analytics endpoint (T-SQL)
--  Lakehouse lh_finsight → SQL analytics endpoint → Nouvelle requête SQL
-- =====================================================================

-- 1. Compte de résultat annuel du groupe (M€) — à comparer avec docs/05-dictionnaire-kpi.md
SELECT d.annee,
       c.ordre_pnl,
       c.ligne_pnl,
       CAST(SUM(f.montant_pnl_eur) / 1e6 AS DECIMAL(10, 2)) AS montant_m_eur
FROM dbo.fact_gl f
JOIN dbo.dim_compte c ON f.compte_key = c.compte_key
JOIN dbo.dim_date d   ON f.date_key   = d.date_key
WHERE c.est_compte_resultat = 1
GROUP BY d.annee, c.ordre_pnl, c.ligne_pnl
ORDER BY d.annee, c.ordre_pnl;

-- 2. CA, EBITDA et EBITDA % par entité et par année
SELECT e.code_entite,
       d.annee,
       SUM(CASE WHEN c.ligne_pnl = 'Chiffre d''affaires' THEN f.montant_pnl_eur END)        AS ca_eur,
       SUM(CASE WHEN c.agregat IN ('Marge brute', 'EBITDA') THEN f.montant_pnl_eur END)    AS ebitda_eur,
       SUM(CASE WHEN c.agregat IN ('Marge brute', 'EBITDA') THEN f.montant_pnl_eur END)
         / NULLIF(SUM(CASE WHEN c.ligne_pnl = 'Chiffre d''affaires' THEN f.montant_pnl_eur END), 0) AS ebitda_pct
FROM dbo.fact_gl f
JOIN dbo.dim_compte c ON f.compte_key = c.compte_key
JOIN dbo.dim_entite e ON f.entite_key = e.entite_key
JOIN dbo.dim_date d   ON f.date_key   = d.date_key
GROUP BY e.code_entite, d.annee
ORDER BY e.code_entite, d.annee;

-- 3. Réel vs budget 2025 par ligne P&L
WITH reel AS (
    SELECT f.compte_key, SUM(f.montant_pnl_eur) AS reel
    FROM dbo.fact_gl f JOIN dbo.dim_date d ON f.date_key = d.date_key
    WHERE d.annee = 2025 GROUP BY f.compte_key
), bud AS (
    SELECT b.compte_key, SUM(b.budget_pnl_eur) AS budget
    FROM dbo.fact_budget b JOIN dbo.dim_date d ON b.date_key = d.date_key
    WHERE d.annee = 2025 GROUP BY b.compte_key
)
SELECT c.ordre_pnl, c.ligne_pnl,
       SUM(r.reel) AS reel, SUM(b.budget) AS budget, SUM(r.reel) - SUM(b.budget) AS ecart
FROM dbo.dim_compte c
LEFT JOIN reel r ON r.compte_key = c.compte_key
LEFT JOIN bud  b ON b.compte_key = c.compte_key
WHERE c.est_compte_resultat = 1
GROUP BY c.ordre_pnl, c.ligne_pnl
ORDER BY c.ordre_pnl;

-- 4. Balance âgée clients à la date d'arrêté
SELECT tranche_age, tranche_age_ordre,
       COUNT(*)                AS nb_factures,
       SUM(montant_ttc_eur)    AS encours_eur
FROM dbo.fact_factures_clients
WHERE est_ouverte = 1
GROUP BY tranche_age, tranche_age_ordre
ORDER BY tranche_age_ordre;

-- 5. Top 10 clients par encours échu
SELECT TOP 10 cl.raison_sociale, cl.segment, e.code_entite,
       SUM(f.montant_ttc_eur) AS encours_echu_eur,
       MAX(f.jours_retard)    AS retard_max_jours
FROM dbo.fact_factures_clients f
JOIN dbo.dim_client cl ON f.client_key = cl.client_key
JOIN dbo.dim_entite e  ON f.entite_key = e.entite_key
WHERE f.est_ouverte = 1 AND f.jours_retard > 0
GROUP BY cl.raison_sociale, cl.segment, e.code_entite
ORDER BY encours_echu_eur DESC;

-- 6. Dernière exécution des contrôles qualité
SELECT *
FROM dbo.dq_resultats
WHERE run_ts = (SELECT MAX(run_ts) FROM dbo.dq_resultats)
ORDER BY controle;

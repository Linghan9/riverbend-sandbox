-- Scratch pad. Point VS Code's SQLite extension at ../data/riverbend.db
--
-- Everything in this database is TEXT. That is deliberate: SQLite will
-- happily let you compare '10' < '9' and return true. Cast explicitly.

SELECT name FROM sqlite_master WHERE type = 'table';

-- Every spelling of department currently in the raw table:
SELECT department, COUNT(*) AS n
FROM raw_encounters
GROUP BY department
ORDER BY n DESC;

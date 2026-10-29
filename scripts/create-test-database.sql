-- Run with psql connected to the source database:
-- psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f scripts/create-test-database.sql
-- The connection URL must use postgresql://, not postgresql+psycopg://.
-- The target is created with the source database name followed by _test.
-- This copies database-level ownership and grants, not data or object privileges.

\set ON_ERROR_STOP on

SELECT current_database() AS source_db,
       current_database() || '_test' AS target_db,
       pg_get_userbyid(datdba) AS source_owner
FROM pg_database WHERE datname = current_database()
\gset

SELECT EXISTS (SELECT FROM pg_database WHERE datname = :'target_db') AS target_exists
\gset
\if :target_exists
  \echo 'Target database already exists; refusing to change it:' :target_db
  \quit 1
\endif

SELECT format('CREATE DATABASE %I OWNER %I TEMPLATE template0',
              :'target_db', :'source_owner')
\gexec

-- Start from no PUBLIC grants, then replay the source ACL (including defaults).
SELECT format('REVOKE ALL PRIVILEGES ON DATABASE %I FROM PUBLIC', :'target_db')
\gexec

SELECT format('GRANT %s ON DATABASE %I TO %s%s',
              privilege_type,
              :'target_db',
              CASE WHEN grantee = 0 THEN 'PUBLIC' ELSE quote_ident(pg_get_userbyid(grantee)) END,
              CASE WHEN is_grantable THEN ' WITH GRANT OPTION' ELSE '' END)
FROM pg_database d,
     LATERAL aclexplode(COALESCE(d.datacl, acldefault('d', d.datdba))) acl
WHERE d.datname = :'source_db'
  AND acl.grantee <> d.datdba
ORDER BY acl.grantee, acl.privilege_type
\gexec

\echo 'Created test database:' :target_db

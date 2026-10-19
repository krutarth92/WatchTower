\set ON_ERROR_STOP on

\if :{?migration_role}
\else
\echo 'Set migration_role with -v migration_role=watchtower_migration'
\quit
\endif

\if :{?runtime_role}
\else
\echo 'Set runtime_role with -v runtime_role=watchtower_runtime'
\quit
\endif

REVOKE CREATE ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON DATABASE :DBNAME FROM PUBLIC;

GRANT CONNECT ON DATABASE :DBNAME TO :"runtime_role";
GRANT USAGE ON SCHEMA public TO :"runtime_role";
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO :"runtime_role";
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO :"runtime_role";

ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_role" IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO :"runtime_role";
ALTER DEFAULT PRIVILEGES FOR ROLE :"migration_role" IN SCHEMA public
  GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO :"runtime_role";

REVOKE CREATE ON SCHEMA public FROM :"runtime_role";

# PostgreSQL role bootstrap

Run `roles.sql` as the RDS migration owner after migrations have created the
application objects. Supply existing login-role names through psql variables;
the script never creates credentials or prints secrets.

```bash
psql "$WATCHTOWER_MIGRATION_DATABASE_URL" \
  -v migration_role=watchtower_migration \
  -v runtime_role=watchtower_runtime \
  -f infra/aws/postgres/roles.sql
```

The CloudFormation template creates separate generated secrets for
`watchtower_migration` and `watchtower_runtime`. Before this grant script, use a
secret-safe administration process to create the runtime `LOGIN` role with the
generated password; never place the password on a command line or in this
repository. The RDS master/migration role owns the schema and runs Alembic only
during deployment. The runtime role is used by the API and workers and receives
data access through the explicit and default grants in the script. Rotate both
credentials through AWS Secrets Manager. Confirm with a runtime-role session
that table reads/writes work and `CREATE SCHEMA`, `CREATE EXTENSION`, and
`CREATE ROLE` fail.

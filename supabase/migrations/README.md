# supabase/migrations

Database migrations for DocuMind AI.

## Status

**No migrations created yet.**

Migrations will be added during the **database implementation phase** when the application schema is ready to be applied to a Supabase project.

## Schema Reference

The full intended database schema is documented in:

```
DATABASE_SCHEMA.md
```

This includes all tables, columns, foreign keys, indexes, RLS policies, and open decisions.

## When to add migrations

Before adding any migration:

1. Read `DATABASE_SCHEMA.md` to understand the full intended schema.
2. Read `AGENTS.md` → Database Conventions section.
3. Test migrations against a local Supabase instance first.
4. Review migrations before applying to any non-local environment.
5. Never auto-migrate in production.

## Naming convention

```
<timestamp>_<description>.sql
```

Example:
```
20240601120000_create_profiles_table.sql
20240601120001_create_documents_table.sql
```

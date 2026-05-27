"""Persistence layer for harness run results.

Two writers ship in the package:

- PostgresWriter (primary): writes via psycopg. Works against both the local
  Postgres stack (docker compose -f postgres-compose.yml up) and Supabase
  projects via direct connection URL.
- SupabaseWriter (legacy): writes via supabase-py. Kept for projects that
  prefer the Supabase SDK over a direct DB connection.

Both implement the same `.write(...)` signature.
"""

from vt_agent_redteam.storage.postgres_writer import PostgresConfig, PostgresWriter
from vt_agent_redteam.storage.supabase_writer import SupabaseConfig, SupabaseWriter

__all__ = [
    "PostgresConfig",
    "PostgresWriter",
    "SupabaseConfig",
    "SupabaseWriter",
]

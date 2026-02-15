# cfg/config.yaml

Purpose: centralized configuration for database connection, API server, and authentication settings. Read by `src/main.py` and all backend modules.

## Structure

### database
- `host`: MySQL/MariaDB server hostname or IP (e.g., `127.0.0.1` or `db` in Docker).
- `port`: MySQL port (default `3306`).
- `name`: fallback database name used by the `/api/setup` endpoints. **Not used by API login**; API creates user-specific databases via the pattern `finiaDB_<username>`.
- `sql_file`: path to SQL dump for schema initialization (default `./db/finia_draft.sql`).
- `init_data`: path to YAML seed data (default `./cfg/data.yaml`).

Example:
```yaml
database:
  host: 127.0.0.1
  port: 3306
  name: FiniA_seed
  sql_file: ./db/finia_draft.sql
  init_data: ./cfg/data.yaml
```

### api
- `host`: API bind address (`0.0.0.0` for Docker/all interfaces, `127.0.0.1` for localhost only).
- `port`: API listen port (default `8000`).
- `log_level` (optional): logging verbosity (e.g., `info`, `debug`).

Example:
```yaml
api:
  host: 0.0.0.0
  port: 8000
```

### auth
- `jwt_expiry_hours`: JWT token lifetime in hours (default `24`).
- `session_timeout_seconds`: inactivity timeout before session invalidation (default `3600` = 1 hour).
- `pool_size`: connection pool size per user session for parallel requests (default `10`).
- `username_prefix`: prefix for database usernames (legacy; not currently used).
- `database_prefix`: prefix applied to each login username to create per-user database (e.g., `finiaDB_<username>`).
- `max_login_attempts`: consecutive failed logins before rate-limiting (default `5`).
- `rate_limit_window_minutes`: duration of rate-limit window after max attempts (default `15`).

Example:
```yaml
auth:
  jwt_expiry_hours: 24
  session_timeout_seconds: 3600
  pool_size: 10
  username_prefix: "finia_"
  database_prefix: "finiaDB_"
  max_login_attempts: 5
  rate_limit_window_minutes: 15
```

### setup
- `token`: optional shared secret for `/api/setup` endpoints.
  If empty, no token is required. Can be overridden via `FINIA_SETUP_TOKEN`.
- `allow_localhost`: allow `127.0.0.1` and `::1` without token (default `true`).

Example:
```yaml
setup:
  token: "changeme"
  allow_localhost: true
```

### Key design points
- **No secrets in config**: DB credentials are passed via `/api/setup` for schema/data setup; API users log in with their own DB credentials (in-memory sessions).
- **Per-user databases**: Each API user gets their own database (`finiaDB_<username>`), created on first login.
- **Auth keys**: JWT signing keys are generated at server start and held in memory only; no static key material in config.
- **Local development**: set `api.host: 127.0.0.1` to bind only to localhost; in Docker, use `0.0.0.0`.
- **Setup protection**: set `setup.token` or `FINIA_SETUP_TOKEN` for `/api/setup` endpoints.

## Customization
1. Adjust database `host`/`port` if running MariaDB on a non-standard address.
2. Change `api.port` if `8000` is already in use.
3. Increase `session_timeout_seconds` to keep users logged in longer.
4. Tighten rate-limiting by lowering `max_login_attempts` or `rate_limit_window_minutes`.

## Notes
- Keep filenames in `docs/` lowercase (except top-level README).
- For Docker deployments, typically only `host`, `port`, and auth settings need adjustment.

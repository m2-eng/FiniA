# Authentication

FiniA uses a memory-only, in-process authentication system with per-user database patterns. No static credentials are stored; login is validated against the MySQL database, and sessions hold encrypted credentials for connection pooling.

## Overview

- **Login flow**: User supplies MySQL credentials (username + password); system validates against live database, creates an in-memory session with encrypted credentials.
- **Session storage**: `SessionStore` keeps credentials encrypted in RAM; sessions have inactivity timeouts (default 1 hour).
- **JWT tokens**: Upon successful login, a short-lived JWT token is issued containing a `session_id`.
- **Per-user databases**: Each API user connects to a database following the pattern `finiaDB_<username>` (configurable via `database_prefix` in config).
- **Connection pooling**: `ConnectionPoolManager` maintains a pool of connections per user session to handle concurrent requests.
- **Rate limiting**: Login attempts are throttled per username to prevent brute-force attacks.

## Key components

### SessionStore (`src/auth/session_store.py`)
Stores active sessions in memory with:
- **Encrypted credentials**: Passwords are encrypted with Fernet (symmetric encryption) before storing in RAM.
- **Inactivity timeout**: Sessions are automatically considered expired after `session_timeout_seconds` (default 3600 = 1 hour) of inactivity.
- **Cleanup**: Expired sessions are deleted; passwords in RAM are overwritten with null bytes.

Methods:
- `create_session(username, password, database)` → session_id
- `get_credentials(session_id)` → {username, password, database}
- `update_activity(session_id)` → refreshes last_activity timestamp
- `delete_session(session_id)` → securely removes session
- `cleanup_expired_sessions()` → prunes old sessions (called periodically by the API)

### ConnectionPoolManager (`src/auth/connection_pool_manager.py`)
Maintains connection pools per session:
- Creates and reuses MySQL connections using the decrypted credentials from a session.
- Pool size is configured via `auth.pool_size` in `cfg/config.yaml` (default 10).
- Connections are tied to a session; when the session expires, its pool is released.

### LoginRateLimiter (`src/auth/rate_limiter.py`)
Protects against brute-force attacks:
- Tracks login attempts per username within a time window (`rate_limit_window_minutes`).
- Blocks further attempts after `max_login_attempts` (default 5) in the window (default 15 minutes).
- Automatically clears old attempts outside the window.

### Auth middleware (`src/api/auth_middleware.py`)
Dependency providers for FastAPI routes:
- `get_current_session()`: extracts and validates JWT token; returns session_id.
- `get_db_connection()`: uses session_id to fetch a connection from the pool.

### Auth router (`src/api/routers/auth.py`)
Endpoints:
- `POST /auth/login`: validates credentials, creates session, issues JWT.
- `POST /auth/logout`: deletes session.
- `GET /auth/status`: returns current user and session metadata.

## Login flow

1. **User submits credentials** via the web login form:
   ```
   POST /auth/login
   {
     "username": "john",
     "password": "secret"
   }
   ```

2. **Validation**: System attempts to connect to `finiaDB_john` using the supplied credentials.
   - On success: Session is created with encrypted credentials stored in memory.
   - On failure: HTTPException 401, attempt is recorded for rate-limiting.

3. **JWT issued**:
   ```json
   {
     "access_token": "<jwt>",
     "token_type": "bearer",
     "expires_in": 86400
   }
   ```
   JWT payload includes `session_id` and expiry time (`jwt_expiry_hours` from config, default 24 hours).

4. **Subsequent requests** include the JWT in the `Authorization: Bearer <token>` header.
   - Middleware validates the token, extracts `session_id`, and refreshes last_activity.
   - Database operations use the connection pool for that session (with decrypted credentials).

5. **Session expiration**: 
   - **Inactivity timeout**: If no request for `session_timeout_seconds`, the session is invalidated on the next attempt.
   - **JWT expiry**: Token itself expires after `jwt_expiry_hours`; user must re-login.

6. **Logout** (optional):
   ```
   POST /auth/logout
   ```
   Manually invalidates the session.

## Configuration

In `cfg/config.yaml`:
```yaml
auth:
  jwt_expiry_hours: 24              # JWT lifetime
  session_timeout_seconds: 3600     # Inactivity timeout (1 hour)
  pool_size: 10                     # Connections per session
  database_prefix: "finiaDB_"       # Database name pattern
  max_login_attempts: 5             # Rate-limit threshold
  rate_limit_window_minutes: 15     # Rate-limit window
```

## Security considerations

- **No static credentials**: Passwords are never written to disk or config files.
- **In-memory encryption**: Credentials are encrypted at rest in RAM using Fernet (AEAD cipher).
- **Short-lived tokens**: JWT tokens expire after `jwt_expiry_hours`; frequent re-authentication is required.
- **Session cleanup**: Expired sessions are regularly purged; passwords in memory are overwritten.
- **Rate limiting**: Repeated failed login attempts are throttled per username.
- **Per-user databases**: Each user connects only to their own database (`finiaDB_<username>`), isolating data.
- **Pool isolation**: Connection pools are per-session and invalidated on logout/expiry.

## Typical issues

**"Session not found" / 401 Unauthorized**
- Session expired due to inactivity; user must re-login.
- JWT token expired; user must re-login.

**"Rate limited" / 429 Too Many Requests**
- Too many failed login attempts; wait for the `rate_limit_window_minutes` to expire.

**"Invalid credentials" / 401 Unauthorized**
- Username or password is incorrect, or the target database (`finiaDB_<username>`) does not exist.

## Future enhancements

- Multi-factor authentication (MFA) support.
- OAuth/OpenID Connect integration.
- LDAP/Active Directory backend for enterprise scenarios.
- Persistent session tokens (encrypted, database-backed).

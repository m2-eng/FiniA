# FiniA Authentication System

## Übersicht

FiniA verwendet ein **Session-basiertes Authentifizierungssystem** mit MySQL-Credentials als Anmeldedaten. Es gibt **keine separate Benutzerverwaltung** – die MySQL-Datenbank-Zugangsdaten dienen gleichzeitig als App-Zugangsdaten.

### Architektur-Prinzipien

1. **DB-Credentials = App-Credentials**: Kein separates User-Management
2. **Multi-Tenancy**: Ein User → Eine dedizierte Datenbank (z.B. `finiaDB_Markus`)
3. **Keine Passwort-Persistierung**: Passwörter werden NUR verschlüsselt im RAM gehalten
4. **Session-basiert**: JWT-Tokens mit Session-IDs, Connection Pooling pro User
5. **Rate Limiting**: Schutz vor Brute-Force-Angriffen

---

## Komponenten

### 1. Session Store (`src/auth/session_store.py`)

Verwaltet aktive User-Sessions im RAM:

- **Verschlüsselung**: Fernet (symmetric encryption) für Passwörter in Sessions
- **Session-Timeout**: Inaktivitäts-basiert (Standard: 1 Stunde)
- **Automatisches Cleanup**: Alte Sessions werden periodisch gelöscht
- **Keine Persistierung**: Sessions existieren nur im Arbeitsspeicher

```python
session_store = SessionStore(
    encryption_key="<FERNET_KEY>",
    session_timeout_seconds=3600
)

session_id = session_store.create_session(username, password, database_name)
username, password, db_name = session_store.get_credentials(session_id)
```

### 2. Connection Pool Manager (`src/auth/connection_pool_manager.py`)

Verwaltet MySQL Connection Pools pro Session:

- **Pool pro User**: Jeder eingeloggte User hat einen eigenen Connection Pool
- **Pool-Größe**: 5 Connections pro User (konfigurierbar)
- **Automatisches Cleanup**: Pools werden beim Logout geschlossen
- **Thread-Safe**: Verwendet `mysql.connector.pooling`

```python
pool_manager = ConnectionPoolManager(
    host="192.168.42.32",
    port=3306,
    pool_size=5
)

pool_manager.create_pool(session_id, username, password, database_name)
connection = pool_manager.get_connection(session_id)
```

### 3. Rate Limiter (`src/auth/rate_limiter.py`)

Schutz vor Brute-Force-Angriffen:

- **Max. Attempts**: 5 Login-Versuche (konfigurierbar)
- **Window**: 15 Minuten (900 Sekunden)
- **Automatisches Reset**: Nach erfolgreicher Anmeldung oder Ablauf des Zeitfensters
- **Username-basiert**: Separate Tracking für jeden User

```python
rate_limiter = LoginRateLimiter(
    max_attempts=5,
    window_seconds=900
)

if rate_limiter.is_allowed(username):
    # Login-Versuch erlaubt
    rate_limiter.record_attempt(username)
```

### 4. Auth Router (`src/api/routers/auth.py`)

FastAPI-Endpunkte für Authentication:

#### `POST /api/auth/login`

Login mit MySQL-Credentials:

**Request:**
```json
{
  "username": "finia_Markus",
  "password": "db_password"
}
```

**Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "username": "finia_Markus",
  "database": "finiaDB_Markus",
  "expires_in": 86400
}
```

**Prozess:**
1. Rate Limiting prüfen
2. Username → Datenbankname ableiten (z.B. `finia_Markus` → `finiaDB_Markus`)
3. MySQL-Verbindung mit Credentials testen
4. Bei Erfolg: Session erstellen, Connection Pool erstellen, JWT-Token generieren
5. Bei Fehler: Login-Versuch aufzeichnen, verbleibende Versuche anzeigen

#### `POST /api/auth/logout`

Logout und Session-Cleanup:

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "message": "Erfolgreich abgemeldet"
}
```

**Prozess:**
1. Session aus JWT-Token extrahieren
2. Session im SessionStore löschen
3. Connection Pool schließen
4. Cookie löschen

#### `GET /api/auth/session`

Aktuelle Session-Informationen abrufen:

**Headers:**
```
Authorization: Bearer <token>
```

**Response:**
```json
{
  "session_id": "abc123...",
  "username": "finia_Markus",
  "database": "finiaDB_Markus",
  "created_at": "2024-01-15T10:30:00",
  "last_activity": "2024-01-15T11:45:00",
  "expires_at": "2024-01-15T12:30:00"
}
```

### 5. Auth Middleware (`src/api/auth_middleware.py`)

FastAPI-Dependency für geschützte Routen:

```python
from api.auth_middleware import get_current_session

@router.get("/protected-endpoint")
def protected_route(session_id: str = Depends(get_current_session)):
    # Nur für authentifizierte User erreichbar
    username, password, db_name = session_store.get_credentials(session_id)
    connection = pool_manager.get_connection(session_id)
    # ...
```

---

## Konfiguration

### 🔐 Secrets & Keys - Memory-Only Authentication

**FiniA verwendet Memory-Only Auth - keine Secrets-Konfiguration erforderlich!**

#### Wie es funktioniert:

- ✅ Auth-Keys werden bei **jedem Server-Start automatisch generiert**
- ✅ Keys existieren **nur im RAM**, niemals auf Disk
- ✅ Alle Sessions werden bei Server-Neustart ungültig (by design)
- ✅ Keine `.env`, `secrets.yaml` oder Setup-Scripts nötig

#### Konsequenzen für User:

- ✅ Normale Arbeit: Token gültig für 24h (während Server läuft)
- ⚠️ Nach Server-Neustart: **Neuanmeldung erforderlich**
- ✅ Maximale Sicherheit: Keine Keys auf Disk = kein Leak-Risiko

**Für Details siehe:** [MEMORY_ONLY_AUTH.md](MEMORY_ONLY_AUTH.md)

### `cfg/config.yaml`

```yaml
auth:
  # Auth-Keys werden bei jedem Server-Start NEU generiert (Memory-Only)
  # KEINE Keys mehr in [config.yaml](http://_vscodecontentref_/3) oder .env nötig!
  # Alle Sessions werden bei Server-Neustart ungültig (by design)
  
  # JWT Token Expiry (in Stunden)
  jwt_expiry_hours: 24
  
  # Session Timeout (in Sekunden)
  session_timeout_seconds: 3600
  
  # Connection Pool Size pro User
  pool_size: 10
  
  # Rate Limiting
  max_login_attempts: 5
  rate_limit_window_minutes: 15
  
  # Username/Database Mapping
  username_prefix: "finia_"
  database_prefix: "finiaDB_"

# JWT Secret
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

**⚠️ WICHTIG:** 
- Diese Keys müssen geheim bleiben!
- Niemals in Git committen!
- Jede Umgebung braucht eigene Keys!

---

## Frontend-Integration

### Login-Seite (`src/web/login.html`)

Einfache Login-Maske mit:
- Username/Password-Feldern
- Fehler-Anzeige mit verbleibenden Versuchen
- Token-Speicherung in `localStorage`
- Automatische Weiterleitung nach erfolgreichem Login

### Auth-Check in jeder Seite

**Option 1: Mit `utils.js`**

```javascript
// Am Anfang jeder Seite
requireAuth();  // Prüft Token, leitet zu /login.html weiter wenn nicht vorhanden

// API-Calls mit Auth
const response = await authenticatedFetch('/api/transactions');
```

**Option 2: Manuell**

```javascript
const token = localStorage.getItem('auth_token');

if (!token) {
    window.location.href = '/login.html';
}

// API-Call mit Token
const response = await fetch('/api/transactions', {
    headers: {
        'Authorization': `Bearer ${token}`
    }
});

// Bei 401 → Session abgelaufen
if (response.status === 401) {
    localStorage.removeItem('auth_token');
    window.location.href = '/login.html';
}
```

### Logout

```javascript
// Logout-Button Handler
document.getElementById('logoutBtn').addEventListener('click', logout);

// Funktion aus utils.js
async function logout() {
    await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
        }
    });
    
    localStorage.removeItem('auth_token');
    localStorage.removeItem('username');
    localStorage.removeItem('database');
    
    window.location.href = '/login.html';
}
```

---

## Datenbank-Struktur

### User-to-Database Mapping

Das System verwendet ein Pattern-basiertes Mapping:

```
Username: finia_Markus   → Database: finiaDB_Markus
Username: finia_Anna     → Database: finiaDB_Anna
Username: finia_TestUser → Database: finiaDB_TestUser
```

**Pattern:**
- Username MUSS mit `finia_` beginnen (konfigurierbar)
- Database wird aus `finiaDB_` + Suffix gebildet (konfigurierbar)

**Beispiel:**

```python
from auth.utils import get_database_name

database = get_database_name(
    "finia_Markus",
    username_prefix="finia_",
    database_prefix="finiaDB_"
)
# Result: "finiaDB_Markus"
```

### MySQL-Berechtigungen

Jeder User benötigt:

```sql
-- Beispiel für finia_Markus
CREATE USER 'finia_Markus'@'%' IDENTIFIED BY 'secure_password';
CREATE DATABASE finiaDB_Markus;

GRANT ALL PRIVILEGES ON finiaDB_Markus.* TO 'finia_Markus'@'%';
FLUSH PRIVILEGES;
```

**⚠️ Wichtig:**
- User hat NUR Zugriff auf seine eigene Datenbank
- Keine Cross-User-Berechtigungen
- Host `%` erlaubt Remote-Zugriff (bei Bedarf einschränken)

---

## Security Features

### 1. Keine Passwort-Persistierung

Passwörter werden **niemals** in der Datenbank oder auf der Festplatte gespeichert:
- ✅ Verschlüsselt im RAM während der Session
- ✅ Automatisch gelöscht bei Logout oder Session-Timeout
- ✅ Kein Password-Recovery möglich (nur MySQL-Admin kann Passwörter ändern)

### 2. Verschlüsselung

- **Session-Passwörter**: Fernet (symmetric encryption, AES-128)
- **JWT-Tokens**: HS256 (HMAC with SHA-256)
- **Cookies**: HttpOnly, Secure (bei HTTPS), SameSite=Strict

### 3. Rate Limiting

- Max. 5 Login-Versuche pro 15 Minuten
- Username-basiertes Tracking
- Automatisches Reset nach erfolgreicher Anmeldung
- Retry-After Header bei Überschreitung

### 4. Session Management

- **Inactivity Timeout**: 1 Stunde (Standard)
- **Absolute Timeout**: 24 Stunden (JWT-Expiry)
- **Automatisches Cleanup**: Alle 5 Minuten
- **Session-ID in JWT**: Kein Passwort im Token

### 5. Connection Pooling

- Keine Connection-Leaks durch Pool-Management
- Automatisches Cleanup bei Logout
- Thread-Safe durch `mysql.connector.pooling`

---

## API-Integration für andere Endpunkte

### Schritt 1: Auth-Dependency importieren

```python
from api.auth_middleware import get_current_session
from api.dependencies import get_db_connection_with_auth
from fastapi import Depends
```

### Schritt 2: Dependency zu Route hinzufügen

**Option A: Mit Connection Pool (empfohlen)**

```python
@router.get("/transactions")
def get_transactions(
    connection = Depends(get_db_connection_with_auth)
):
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()
    cursor.close()
    return transactions
```

**Option B: Mit Session-ID (für manuelle Verarbeitung)**

```python
@router.get("/transactions")
def get_transactions(
    session_id: str = Depends(get_current_session)
):
    # Credentials aus Session abrufen
    from api.dependencies import _session_store, _pool_manager
    
    username, password, db_name = _session_store.get_credentials(session_id)
    connection = _pool_manager.get_connection(session_id)
    
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions")
    transactions = cursor.fetchall()
    cursor.close()
    
    return transactions
```

### Schritt 3: Fehlerbehandlung

FastAPI wirft automatisch `HTTPException` bei:
- Fehlendem Token → `401 Unauthorized`
- Abgelaufenem Token → `401 Unauthorized`
- Ungültiger Session → `401 Unauthorized`
- Session-Timeout → `401 Unauthorized`

---

## Deployment

### 1. Environment Variables (empfohlen für Production)

Statt Secrets in `config.yaml` zu speichern:

```python
# In startup_event():
import os

session_store = SessionStore(
    encryption_key=os.getenv('FINIA_ENCRYPTION_KEY', auth_config.get('encryption_key')),
    session_timeout_seconds=auth_config.get('session_timeout_seconds', 3600)
)
```

### 2. HTTPS konfigurieren

In `src/api/routers/auth.py`, Login-Endpoint:

```python
response.set_cookie(
    key="auth_token",
    value=token,
    httponly=True,
    secure=True,  # ← Auf True setzen!
    samesite="strict",
    max_age=expiry_hours * 3600
)
```

### 3. CORS konfigurieren

In `src/api/main.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-domain.com"],  # ← Spezifische Domain!
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)
```

### 4. Firewall

- MySQL Port `3306` nur für App-Server freigeben
- FastAPI Port `8000` hinter Reverse Proxy (nginx/Apache)

---

## Testing

### 1. Login testen

```bash
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "finia_Markus", "password": "db_password"}'
```

**Expected Response:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "username": "finia_Markus",
  "database": "finiaDB_Markus",
  "expires_in": 86400
}
```

### 2. Session prüfen

```bash
curl -X GET http://localhost:8000/api/auth/session \
  -H "Authorization: Bearer <token>"
```

### 3. Geschützte Route testen

```bash
curl -X GET http://localhost:8000/api/transactions \
  -H "Authorization: Bearer <token>"
```

### 4. Rate Limiting testen

```bash
# 5x falsches Passwort
for i in {1..6}; do
  curl -X POST http://localhost:8000/api/auth/login \
    -H "Content-Type: application/json" \
    -d '{"username": "finia_Test", "password": "wrong"}'
done
```

**Expected 6. Versuch:**
```json
{
  "detail": "Zu viele Login-Versuche. Bitte warten Sie 900 Sekunden."
}
```

---

## Troubleshooting

### Problem: "Too many login attempts"

**Ursache:** Rate Limiter hat zu viele Versuche erkannt.

**Lösung:**
- Warten bis Zeitfenster abgelaufen ist (Standard: 15 Minuten)
- Rate Limiter-Einstellungen in `config.yaml` anpassen
- Für Testing: Rate Limiter deaktivieren (nicht empfohlen)

### Problem: "Session not found"

**Ursache:** Session wurde gelöscht (Timeout, Logout, oder Server-Neustart).

**Lösung:** 
- User muss sich erneut einloggen
- Session-Timeout in `config.yaml` erhöhen

### Problem: Connection Pool Errors

**Ursache:** Zu viele gleichzeitige Connections oder Pool nicht geschlossen.

**Lösung:**
1. Pool-Size erhöhen in `config.yaml`
2. Prüfen ob Connections korrekt geschlossen werden
3. MySQL `max_connections` erhöhen

---

## Migration von Legacy-System

Wenn Sie von einem System ohne Auth migrieren:

### 1. Legacy-Routes optional schützen

Fügen Sie einen "Optional Auth"-Modus hinzu:

```python
from typing import Optional

async def get_optional_session(
    authorization: Optional[str] = Header(None)
) -> Optional[str]:
    """Gibt Session-ID zurück wenn vorhanden, sonst None."""
    if not authorization:
        return None
    
    try:
        return await get_current_session(authorization)
    except HTTPException:
        return None


@router.get("/transactions")
def get_transactions(
    session_id: Optional[str] = Depends(get_optional_session)
):
    if session_id:
        # Auth-basierter Zugriff
        connection = Depends(get_db_connection_with_auth)
    else:
        # Legacy-Zugriff (aus config.yaml)
        connection = Depends(get_db_connection)
    
    # ...
```

### 2. Schrittweise Migration

1. **Phase 1**: Auth-System implementieren, aber nicht erzwingen
2. **Phase 2**: Login-Seite aktivieren, aber Legacy-Zugriff erlauben
3. **Phase 3**: Alle Routes auf Auth umstellen
4. **Phase 4**: Legacy-Zugriff entfernen

---

## Best Practices

1. **Secrets Management**
   - ✅ Verwenden Sie Environment Variables in Production
   - ✅ Rotieren Sie Keys regelmäßig
   - ❌ Committen Sie niemals Secrets in Git

2. **Session Management**
   - ✅ Implementieren Sie automatisches Cleanup
   - ✅ Verwenden Sie angemessene Timeouts
   - ❌ Speichern Sie keine sensitiven Daten in Sessions

3. **Rate Limiting**
   - ✅ Aktivieren Sie Rate Limiting für alle Login-Endpunkte
   - ✅ Loggen Sie verdächtige Login-Versuche
   - ❌ Verwenden Sie keine zu restriktiven Limits (UX!)

4. **Connection Pooling**
   - ✅ Schließen Sie Pools beim Logout
   - ✅ Verwenden Sie angemessene Pool-Größen
   - ❌ Lassen Sie keine Connection-Leaks zu

5. **Frontend Security**
   - ✅ Speichern Sie Tokens in `localStorage` (nicht `sessionStorage`)
   - ✅ Prüfen Sie Token-Gültigkeit bei jedem Seitenwechsel
   - ❌ Loggen Sie niemals Passwörter in der Console

---

## Lizenz

Siehe [LICENSE](../LICENSE) für Details.

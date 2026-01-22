# 🔐 Memory-Only Authentication

## Überblick

FiniA verwendet **Memory-Only Keys** für maximale Sicherheit:

- ✅ **Keine Keys auf Disk** - niemals gespeichert
- ✅ **Neu bei jedem Start** - Keys existieren nur im RAM
- ✅ **Automatisches Cleanup** - Bei Neustart ungültig

---

## Wie funktioniert es?

### Bei jedem Server-Start:

```python
# Neue Keys generieren (nur im RAM!)
encryption_key = Fernet.generate_key()  # Für Session-Verschlüsselung
jwt_secret = secrets.token_urlsafe(32)  # Für JWT-Token-Signierung

# ← NIEMALS auf Disk gespeichert!
# ← Existieren nur im Arbeitsspeicher
# ← Bei Neustart/Crash komplett weg
```

### Konsequenzen:

1. **Server-Start** → Neue Keys generiert
2. **User loggt sich ein** → Session mit RAM-Keys erstellt
3. **User arbeitet** → Token gültig (bis zu 24h)
4. **Server-Neustart** → Keys weg, alle Sessions ungültig
5. **User API-Call** → "Session expired" → **Neuanmeldung erforderlich**

---

## ✅ Vorteile

### Sicherheit
- **Keine Persistierung**: Keys niemals auf Disk
- **Kein Leak-Risiko**: Keine .env, keine config.yaml mit Secrets
- **Auto-Rotation**: Bei jedem Neustart neue Keys
- **Memory-Only**: Bei Container-Kompromittierung → Neustart = clean

### Einfachheit
- **Keine Konfiguration**: Keine .env Datei nötig
- **Keine Secrets Management**: Keine Keys zu verwalten
- **Kein Setup**: Einfach starten, läuft

### Docker-Freundlich
- **Stateless**: Perfekt für Container
- **Keine Volumes**: Keine Keys-Volumes mounten
- **Cloud-Ready**: Funktioniert überall

---

## ⚠️ Was bedeutet das für User?

### Normale Arbeit
- Login mit MySQL-Credentials
- Token gültig für 24 Stunden
- **Keine Änderung** während normaler Nutzung

### Bei Server-Neustart
- **Alle User müssen sich neu einloggen**
- Grund: JWT-Keys wurden neu generiert
- Alte Tokens sind ungültig

### Beispiel-Szenario

```
10:00 - User Markus loggt sich ein
      → Token gültig bis morgen 10:00

10:30 - Server-Neustart (Update/Wartung)
      → Neue Keys generiert
      → Alle Tokens ungültig

10:31 - Markus versucht API-Call
      → "401 Unauthorized - Token expired"
      → Frontend leitet zu /login.html
      
10:32 - Markus loggt sich neu ein
      → Neuer Token, funktioniert wieder
```

---

## 🐳 Docker Deployment

Perfekt für Container-Deployment:

```dockerfile
FROM python:3.11-slim

# Keine Secrets nötig!
# Keys werden automatisch generiert

COPY . /app
WORKDIR /app

RUN pip install -r requirements.txt

CMD ["python", "src/main.py"]
```

### docker-compose.yml

```yaml
services:
  finia:
    image: finia:latest
    ports:
      - "8000:8000"
    # KEINE Environment Variables für Keys nötig!
    # KEINE Volumes für Secrets nötig!
    depends_on:
      - database
      
  database:
    image: mariadb:10.11
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_ROOT_PASSWORD}
    volumes:
      - db_data:/var/lib/mysql

volumes:
  db_data:
```

---

## 🔄 Update-Strategie

### Rolling Updates (Zero Downtime)

Wenn Sie Load Balancer haben:

```yaml
# Strategie für Zero-Downtime
services:
  finia:
    deploy:
      replicas: 2
      update_config:
        parallelism: 1        # Einen nach dem anderen
        delay: 10s            # 10 Sekunden warten
        order: start-first    # Neuen starten bevor alter stoppt
```

**Ablauf:**
1. Container 1 läuft (alte Version)
2. Container 2 startet (neue Version, neue Keys)
3. Neue Logins gehen zu Container 2
4. Nach 24h: Alle Tokens für Container 1 abgelaufen
5. Container 1 kann gestoppt werden

### Wartungsfenster (Empfohlen für Single Instance)

```bash
# Nachts Update durchführen
# 1. User informieren: "Wartung 2:00-2:10 Uhr"
# 2. Update durchführen
# 3. User loggen sich morgens neu ein
```

---

## 📊 Vergleich: Memory-Only vs. Persistent Keys

| Aspekt | Memory-Only | Persistent (.env) |
|--------|-------------|-------------------|
| **Sicherheit** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Keys auf Disk** | ❌ Nein | ✅ Ja (.env) |
| **User-Komfort** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Setup-Aufwand** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **Docker-Ready** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Neustart** | Neuanmeldung | Token bleibt gültig |

---

## 🛠️ Troubleshooting

### "Session expired" nach Neustart

**Normal!** Das ist das erwartete Verhalten:
1. Server neu gestartet → Neue Keys
2. Alte Tokens ungültig
3. User muss sich neu einloggen

**Lösung:** Neu einloggen auf `/login.html`

### Zu häufige Neuanmeldungen

**Ursache:** Server startet zu oft neu.

**Lösungen:**
- Container Restart-Policy anpassen: `restart: unless-stopped`
- Health-Checks optimieren (weniger aggressive Restarts)
- Logs prüfen: Warum startet Container neu?

### Multi-Container-Setup

**Problem:** Jeder Container hat eigene Keys → User-Session nur auf einem Container gültig.

**Lösung:**
- **Option 1**: Sticky Sessions (Load Balancer)
- **Option 2**: Shared Memory Store (Redis) - siehe unten
- **Option 3**: Database-backed Keys (Alternative zu Memory-Only)

---

## 🔮 Zukünftige Erweiterungen

### Option 1: Shared Memory Store (Redis)

Falls Sie später mehrere Container brauchen:

```python
# Keys in Redis statt lokalem RAM
redis_client.set('encryption_key', encryption_key, ex=86400)
redis_client.set('jwt_secret', jwt_secret, ex=86400)

# Alle Container verwenden gleiche Keys aus Redis
# Trotzdem nicht auf Disk (Redis im RAM)
```

### Option 2: Hardware-Token für Admin

```python
# Admin-Operationen mit YubiKey
if user.is_admin:
    require_yubikey_otp()
```

---

## 📝 Konfiguration

### config.yaml

```yaml
auth:
  # Keine Keys nötig!
  # Werden automatisch generiert
  
  # JWT Token Expiry
  jwt_expiry_hours: 24
  
  # Session Timeout
  session_timeout_seconds: 3600
  
  # Rate Limiting
  max_login_attempts: 5
  rate_limit_window_minutes: 15
```

### Keine weiteren Dateien nötig!

- ❌ Keine `.env` Datei
- ❌ Keine `secrets.yaml`
- ❌ Kein `setup_secrets.ps1`
- ✅ Einfach starten!

---

## 🚀 Start

```powershell
# Das war's! Keine Konfiguration nötig
python src/main.py

# Ausgabe:
# ✓ Auth keys generated in memory (never stored on disk)
# ⚠ All sessions will be invalidated on restart (by design)
# ✓ Auth modules initialized
# ✓ Database connected successfully
```

---

## ✅ Best Practices

### Empfehlungen

1. **Wartungsfenster kommunizieren**
   - User vorher informieren
   - Nachts/Wochenende updaten

2. **Health-Checks optimieren**
   - Nicht zu aggressiv (unnötige Restarts)
   - Aber schnell genug (echte Probleme erkennen)

3. **Monitoring**
   - Container-Restarts loggen
   - User-Neuanmeldungen tracken
   - Auffälligkeiten erkennen

4. **Backup-Strategie**
   - Keys nicht backuppen (macht keinen Sinn)
   - Nur Datenbank backuppen
   - User-Sessions sind temporär

### Nicht Empfohlen

1. ❌ Keys in Logs ausgeben
2. ❌ Keys in Monitoring-Tools senden
3. ❌ Keys "zur Sicherheit" doch speichern
4. ❌ Zu häufige Container-Restarts

---

## 📚 Weitere Dokumentation

- **[AUTHENTICATION.md](AUTHENTICATION.md)** - Vollständige Auth-Dokumentation
- **[../README.md](../README.md)** - Projekt-Übersicht

---

**Zusammenfassung:**

FiniA verwendet Memory-Only Keys für maximale Sicherheit. Keys existieren nur im RAM und werden bei jedem Neustart neu generiert. User müssen sich nach Neustart neu einloggen - das ist **by design** und gewünscht für höchste Sicherheit.

✅ **Keine Keys auf Disk - niemals!** 🔐

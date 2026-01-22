# 🔐 Secrets Setup - Quick Start

## ⚠️ WICHTIG: Secrets NIEMALS in Git committen!

Die Auth-Keys (Encryption Key, JWT Secret) werden **NICHT** in `config.yaml` gespeichert, sondern über **Environment Variables** geladen.

---

## 🚀 Schnellstart (neue Installation)

### 1. Setup-Script ausführen

```powershell
.\setup_secrets.ps1
```

Das Script:
- ✅ Generiert automatisch neue sichere Keys
- ✅ Erstellt `.env` Datei
- ✅ Erstellt Backup bei vorhandener `.env`

### 2. Server starten

```powershell
python src/main.py
```

Die Keys werden automatisch aus `.env` geladen!

---

## 📝 Manuelle Einrichtung

### Option 1: .env Datei (empfohlen für Entwicklung)

```bash
# 1. Template kopieren
cp .env.example .env

# 2. Keys generieren
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 3. Keys in .env eintragen
# FINIA_ENCRYPTION_KEY=<generated-fernet-key>
# FINIA_JWT_SECRET=<generated-jwt-secret>
```

### Option 2: Systemumgebung (empfohlen für Production)

**Windows:**
```powershell
[System.Environment]::SetEnvironmentVariable('FINIA_ENCRYPTION_KEY', 'your-key', 'Machine')
[System.Environment]::SetEnvironmentVariable('FINIA_JWT_SECRET', 'your-secret', 'Machine')
```

**Linux/macOS:**
```bash
export FINIA_ENCRYPTION_KEY='your-key'
export FINIA_JWT_SECRET='your-secret'

# Dauerhaft in ~/.bashrc oder /etc/environment
```

### Option 3: Per Command Line

```powershell
# PowerShell
$env:FINIA_ENCRYPTION_KEY = "your-key"
$env:FINIA_JWT_SECRET = "your-secret"
python src/main.py
```

---

## 🔍 Verifikation

Beim Start sollten Sie sehen:

```
✓ Loaded environment variables from C:\...\FiniA\.env
✓ Auth secrets loaded from environment variables
✓ Auth modules initialized
✓ Database connected successfully
```

Bei Fehlern:

```
SECURITY ERROR: Auth secrets not configured!
Please set environment variables:
  - FINIA_ENCRYPTION_KEY (generate with: ...)
  - FINIA_JWT_SECRET (generate with: ...)
```

→ Siehe "Manuelle Einrichtung" oben

---

## 📁 Datei-Struktur

```
FiniA/
├── .env                    # ← Ihre lokalen Secrets (in .gitignore)
├── .env.example            # ← Template zum Kopieren
├── setup_secrets.ps1       # ← Automatisches Setup-Script
├── .gitignore              # ← Enthält .env, secrets.yaml, *.key, *.secret
└── cfg/
    └── config.yaml         # ← KEINE Secrets hier! Nur Struktur
```

---

## 🛡️ Sicherheits-Best-Practices

### ✅ DO (Empfohlen)

- ✅ Verwenden Sie `.env` für lokale Entwicklung
- ✅ Verwenden Sie Systemumgebung für Production
- ✅ Verwenden Sie Cloud Secrets Manager (Azure Key Vault, AWS Secrets Manager)
- ✅ Rotieren Sie Keys regelmäßig
- ✅ Verwenden Sie unterschiedliche Keys für Dev/Test/Prod

### ❌ DON'T (Niemals!)

- ❌ **Niemals** Secrets in `config.yaml` eintragen
- ❌ **Niemals** `.env` in Git committen
- ❌ **Niemals** Keys im Code hard-coden
- ❌ **Niemals** Keys in Logs ausgeben
- ❌ **Niemals** Keys per E-Mail versenden

---

## 🔄 Key-Rotation (regelmäßig durchführen)

```powershell
# 1. Backup der alten .env
Copy-Item .env .env.old

# 2. Neue Keys generieren
.\setup_secrets.ps1

# 3. Server neu starten
# WICHTIG: Alle aktiven Sessions werden ungültig!
```

**Nach Key-Rotation:**
- ⚠️ Alle User müssen sich neu einloggen
- ⚠️ Alte JWT-Tokens werden ungültig
- ⚠️ Sessions müssen neu erstellt werden

---

## 🐳 Docker Deployment

**Option 1: Environment Variables**

```dockerfile
FROM python:3.11

ENV FINIA_ENCRYPTION_KEY=<your-key>
ENV FINIA_JWT_SECRET=<your-secret>

# ... rest of Dockerfile
```

**Option 2: Docker Secrets (empfohlen)**

```yaml
# docker-compose.yml
services:
  finia:
    image: finia:latest
    environment:
      - FINIA_ENCRYPTION_KEY_FILE=/run/secrets/encryption_key
      - FINIA_JWT_SECRET_FILE=/run/secrets/jwt_secret
    secrets:
      - encryption_key
      - jwt_secret

secrets:
  encryption_key:
    file: ./secrets/encryption_key.txt
  jwt_secret:
    file: ./secrets/jwt_secret.txt
```

---

## 📚 Weitere Informationen

- **Vollständige Dokumentation**: [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md)
- **Secrets-Verwaltung**: Dieser Guide
- **API-Referenz**: [docs/AUTHENTICATION.md#api-integration](docs/AUTHENTICATION.md#api-integration)

---

## 🆘 Hilfe

Bei Problemen:

1. **Keys nicht gefunden?** → Prüfen Sie `.env` Datei existiert
2. **Fehler beim Start?** → Prüfen Sie die Fehlermeldung
3. **Keys in config.yaml?** → **SOFORT LÖSCHEN** und in `.env` verschieben!

**Support:** Siehe README.md für Kontaktinformationen

# FiniA Secrets Setup Script
# ===========================
# Generiert neue Encryption Keys und erstellt .env Datei

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  FiniA - Auth Secrets Setup" -ForegroundColor Cyan
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""

# Check if .env already exists
if (Test-Path ".env") {
    Write-Host "⚠ .env Datei existiert bereits!" -ForegroundColor Yellow
    $overwrite = Read-Host "Möchten Sie neue Keys generieren? (j/n)"
    
    if ($overwrite -ne "j" -and $overwrite -ne "J") {
        Write-Host "Abgebrochen." -ForegroundColor Yellow
        exit 0
    }
    
    # Backup erstellen
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    Copy-Item ".env" ".env.backup_$timestamp"
    Write-Host "✓ Backup erstellt: .env.backup_$timestamp" -ForegroundColor Green
}

Write-Host ""
Write-Host "Generiere neue Auth-Keys..." -ForegroundColor Cyan

# Fernet Encryption Key generieren
Write-Host "  - Fernet Encryption Key..."
$encryptionKey = python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Fehler beim Generieren des Encryption Keys!" -ForegroundColor Red
    Write-Host "  Bitte stellen Sie sicher, dass 'cryptography' installiert ist:" -ForegroundColor Yellow
    Write-Host "  pip install cryptography" -ForegroundColor Yellow
    exit 1
}

# JWT Secret generieren
Write-Host "  - JWT Secret..."
$jwtSecret = python -c "import secrets; print(secrets.token_urlsafe(32))"

if ($LASTEXITCODE -ne 0) {
    Write-Host "✗ Fehler beim Generieren des JWT Secrets!" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✓ Keys erfolgreich generiert!" -ForegroundColor Green

# .env Datei erstellen
$envContent = @"
# FiniA Secrets - Environment Variables
# ========================================
# WICHTIG: Diese Datei NIEMALS in Git committen!
# Generiert am: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")

# Auth Secrets
FINIA_ENCRYPTION_KEY=$encryptionKey
FINIA_JWT_SECRET=$jwtSecret

# Optional: Database Credentials Override (für Production)
# FINIA_DB_HOST=192.168.42.32
# FINIA_DB_PORT=3306
"@

$envContent | Out-File -FilePath ".env" -Encoding UTF8
Write-Host ""
Write-Host "✓ .env Datei erstellt!" -ForegroundColor Green
Write-Host ""

# Zusammenfassung
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "  Setup abgeschlossen!" -ForegroundColor Green
Write-Host "==================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Die .env Datei wurde erstellt mit:" -ForegroundColor White
Write-Host "  - Fernet Encryption Key (für Session-Passwörter)" -ForegroundColor White
Write-Host "  - JWT Secret (für Token-Signierung)" -ForegroundColor White
Write-Host ""
Write-Host "WICHTIG:" -ForegroundColor Yellow
Write-Host "  1. Diese Datei ist bereits in .gitignore" -ForegroundColor Yellow
Write-Host "  2. Committen Sie .env NIEMALS in Git!" -ForegroundColor Yellow
Write-Host "  3. Für Production: Verwenden Sie Umgebungsvariablen" -ForegroundColor Yellow
Write-Host ""
Write-Host "Die Keys können nun verwendet werden:" -ForegroundColor Cyan
Write-Host "  python src/main.py" -ForegroundColor White
Write-Host ""

#!/usr/bin/env powershell
<#
.SYNOPSIS
FiniA Docker Deployment Script
.DESCRIPTION
Automation for building, deploying, and managing FiniA in Docker
.PARAMETER Action
build, up, down, logs, clean, backup
#>

param(
    [Parameter(Position=0)]
    [ValidateSet('build', 'up', 'down', 'logs', 'restart', 'clean', 'backup', 'restore')]
    [string]$Action = 'up',
    
    [Parameter()]
    [string]$BackupFile = 'finia_backup.sql'
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

function Test-EnvFile {
    if (-not (Test-Path '.env')) {
        Write-Host "❌ .env file not found!" -ForegroundColor Red
        Write-Host "📋 Creating .env from .env.example..." -ForegroundColor Yellow
        Copy-Item '.env.example' '.env'
        Write-Host "✅ .env created. Please update with your values!" -ForegroundColor Green
        Write-Host "   Edit .env and run the script again."
        exit 1
    }
}

function Build {
    Write-Host "🔨 Building Docker image..." -ForegroundColor Cyan
    docker-compose build --no-cache
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ Build successful!" -ForegroundColor Green
    } else {
        Write-Host "❌ Build failed!" -ForegroundColor Red
        exit 1
    }
}

function Up {
    Test-EnvFile
    Write-Host "🚀 Starting FiniA services..." -ForegroundColor Cyan
    docker-compose up -d
    
    Write-Host "`n⏳ Waiting for services to be ready..." -ForegroundColor Yellow
    Start-Sleep -Seconds 5
    
    docker-compose ps
    
    Write-Host "`n✅ FiniA is running!" -ForegroundColor Green
    Write-Host "   🌐 Web UI: http://localhost:8000" -ForegroundColor Green
    Write-Host "   📚 API Docs: http://localhost:8000/api/docs" -ForegroundColor Green
    Write-Host "   🗄️  Database: localhost:3306" -ForegroundColor Green
}

function Down {
    Write-Host "🛑 Stopping FiniA services..." -ForegroundColor Yellow
    docker-compose down
    Write-Host "✅ Services stopped!" -ForegroundColor Green
}

function Logs {
    Write-Host "📋 Following logs (Ctrl+C to exit)..." -ForegroundColor Cyan
    docker-compose logs -f api
}

function Restart {
    Write-Host "🔄 Restarting FiniA services..." -ForegroundColor Cyan
    docker-compose restart
    Write-Host "✅ Services restarted!" -ForegroundColor Green
}

function Clean {
    Write-Host "🧹 Cleaning up Docker resources..." -ForegroundColor Yellow
    Write-Host "   Removing stopped containers..." -ForegroundColor Gray
    docker-compose down -v
    
    Write-Host "   Removing dangling images..." -ForegroundColor Gray
    docker image prune -f
    
    Write-Host "✅ Cleanup complete!" -ForegroundColor Green
}

function Backup {
    Test-EnvFile
    
    # Load .env
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
        }
    }
    
    Write-Host "💾 Creating database backup..." -ForegroundColor Cyan
    Write-Host "   Output: $BackupFile" -ForegroundColor Gray
    
    $timestamp = Get-Date -Format "yyyy-MM-dd_HH-mm-ss"
    $backupPath = "$($BackupFile -replace '\.sql$', "")_$timestamp.sql"
    
    docker exec finia-db mariadb-dump `
        -u$env:DB_USER `
        -p$env:DB_PASSWORD `
        $env:DB_NAME | Out-File -FilePath $backupPath -Encoding UTF8
    
    $size = (Get-Item $backupPath).Length / 1MB
    Write-Host "✅ Backup complete! Size: $([math]::Round($size, 2)) MB" -ForegroundColor Green
    Write-Host "   File: $backupPath" -ForegroundColor Green
}

function Restore {
    if (-not (Test-Path $BackupFile)) {
        Write-Host "❌ Backup file not found: $BackupFile" -ForegroundColor Red
        exit 1
    }
    
    Test-EnvFile
    
    # Load .env
    Get-Content .env | ForEach-Object {
        if ($_ -match '^([^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
        }
    }
    
    Write-Host "♻️  Restoring database from backup..." -ForegroundColor Cyan
    Write-Host "   File: $BackupFile" -ForegroundColor Gray
    Write-Host "⚠️  This will overwrite existing data!" -ForegroundColor Yellow
    
    $confirm = Read-Host "Continue? (yes/no)"
    if ($confirm -ne 'yes') {
        Write-Host "Cancelled." -ForegroundColor Yellow
        exit 0
    }
    
    Get-Content $BackupFile | docker exec -i finia-db mariadb `
        -u$env:DB_USER `
        -p$env:DB_PASSWORD `
        $env:DB_NAME
    
    Write-Host "✅ Restore complete!" -ForegroundColor Green
}

# Execute action
switch ($Action) {
    'build'   { Build }
    'up'      { Up }
    'down'    { Down }
    'logs'    { Logs }
    'restart' { Restart }
    'clean'   { Clean }
    'backup'  { Backup }
    'restore' { Restore }
    default   { Write-Host "Unknown action: $Action" -ForegroundColor Red; exit 1 }
}

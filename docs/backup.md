# Backup Strategy

FiniA uses external MySQL/MariaDB databases with per-user patterns (`finiaDB_<username>`). Backup strategies depend on your database setup and deployment environment.

## Database backup approaches

### 1. Existing database backup

If you already have MariaDB/MySQL backup processes in place (e.g., on a NAS with automated snapshots), FiniA databases are included automatically since they reside in the same instance.

**Example (Synology NAS):**
```
Scheduled Task: Daily full DB backup at 2 AM
├── Includes: All databases (finiaDB_*)
├── Retention: 30 days rolling
└── Restore: Via phpMyAdmin or mysql CLI
```

### 2. docker-deploy.ps1 backup command

For Docker deployments on Windows, the PowerShell script provides manual backup:

```powershell
.\docker-deploy.ps1 backup
# Creates: finia_backup_<timestamp>.sql
```

This uses `mysqldump` to export all FiniA databases. Store backups in a safe location (NAS, cloud storage, etc.).

**Restore:**
```powershell
.\docker-deploy.ps1 restore finia_backup_20260123.sql
```

### 3. Makefile backup (Linux/Mac)

```bash
make backup
# Creates timestamped SQL dump
```

### 4. Manual mysqldump

For ad-hoc or scripted backups:

```bash
# Single user database
mysqldump -h <host> -u <user> -p finiaDB_john > finiaDB_john_backup.sql

# All FiniA databases
mysqldump -h <host> -u root -p --databases $(mysql -h <host> -u root -p -e "SHOW DATABASES LIKE 'finiaDB_%';" -s -N) > finia_all_backup.sql
```

**Restore:**
```bash
mysql -h <host> -u <user> -p < finiaDB_john_backup.sql
```

## Configuration backup

The `cfg/` folder contains all configuration files and should be backed up separately:

```
cfg/
├── config.yaml          # Database/API/auth settings
├── data.yaml            # Seed data for init
└── import_formats.yaml  # CSV import mappings
```

**Backup strategy:**
- Version-controlled in Git (safe to commit with placeholders)
- Copy to NAS/cloud storage for redundancy
- Include in project-wide backups

**Example (automated):**
```bash
# Daily backup script
cp -r /path/to/FiniA/cfg /backup/finia_cfg_$(date +%Y%m%d)
```

## Retention policy

**Recommended:**
- **Daily backups:** Retain 30 days
- **Weekly backups:** Retain 12 weeks
- **Monthly backups:** Retain 12 months

Adjust based on data volume, compliance requirements, and storage capacity.

## Backup verification

Periodically test restore procedures:

1. Restore backup to a test database
2. Start FiniA API pointing to test database
3. Verify data integrity (accounts, transactions, categories)
4. Check for missing or corrupted entries

## Disaster recovery

**Scenario: Complete data loss**

1. Restore latest database backup:
   ```bash
   mysql -h <host> -u root -p < finia_backup_latest.sql
   ```

2. Restore configuration files:
   ```bash
   cp -r /backup/finia_cfg_latest/* ./cfg/
   ```

3. Restart FiniA:
   ```bash
   docker-compose up -d
   # or
   python src/main.py --api --config cfg/config.yaml
   ```

4. Verify user login and data access

**Scenario: Single user database corruption**

1. Drop corrupted database:
   ```sql
   DROP DATABASE finiaDB_john;
   ```

2. Restore from backup:
   ```bash
   mysql -h <host> -u root -p < finiaDB_john_backup.sql
   ```

3. User can log in immediately (no API restart needed)

## Security notes

- **Encrypt backups** if stored off-site or in cloud
- **Restrict access** to backup files (database credentials can be extracted)
- **Automate backup tasks** to avoid manual errors
- **Monitor backup success** (alerts on failure)

## Cloud backup options

**AWS S3:**
```bash
aws s3 cp finia_backup.sql s3://my-bucket/backups/finia/$(date +%Y%m%d).sql
```

**Azure Blob Storage:**
```bash
az storage blob upload --container backups --file finia_backup.sql --name finia/$(date +%Y%m%d).sql
```

**Google Cloud Storage:**
```bash
gsutil cp finia_backup.sql gs://my-bucket/backups/finia/$(date +%Y%m%d).sql
```

## Backup checklist

- [ ] Database backups automated (daily/weekly)
- [ ] Configuration files (`cfg/`) backed up
- [ ] Backup retention policy defined
- [ ] Restore procedure tested successfully
- [ ] Backup monitoring/alerts configured
- [ ] Off-site or cloud backup for disaster recovery
- [ ] Backups encrypted (if required by policy)

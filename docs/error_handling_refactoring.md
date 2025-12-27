# Fehlerbehandlungs-Überarbeitung - FiniA API

## Datum: 26. Dezember 2025

## Übersicht
Umfassende Überarbeitung der Fehlerbehandlung im gesamten FiniA-Projekt für erhöhte Stabilität und konsistentes Error-Handling.

## Geänderte Dateien

### 1. Neue Zentrale Fehlerbehandlung
**src/api/error_handling.py** (NEU)
- `handle_db_errors()` - Decorator für einheitliche Fehlerbehandlung in allen API-Endpunkten
- `get_cursor_with_retry()` - Cursor-Erstellung mit automatischem Retry (max 3 Versuche)
- `execute_query_with_retry()` - SQL-Query-Ausführung mit Retry bei Connection-Fehlern
- `safe_commit()` - Sichere Commit-Operation mit Fehlerbehandlung
- `safe_rollback()` - Sichere Rollback-Operation

### 2. Database.py - Robustere Connection-Verwaltung
**src/Database.py**
- Hinzugefügt: `_connection_attempts` und `_max_connection_attempts` Tracking
- Hinzugefügt: `time.sleep()` bei Retry-Versuchen
- `connect()`: Retry-Logik mit bis zu 3 Versuchen, alte Connection wird geschlossen
- `close()`: Sichere Schließung mit Exception-Handling
- `is_connected()`: Neue Methode zur Überprüfung der Connection
- `get_cursor()`: Umfassendes Retry-System (3 Versuche) mit Ping und Reconnect
- `commit()`: Sichere Commit-Operation
- `rollback()`: Neue Methode für sichere Rollbacks

### 3. Dependencies.py - Verbesserte Cursor/Connection-Bereitstellung
**src/api/dependencies.py**
- `get_db_cursor()`: Vollständige Neuimplementierung mit:
  - Max 3 Retry-Versuche
  - Detaillierte Exception-Behandlung (RuntimeError, OperationalError, InterfaceError, DatabaseError)
  - Traceback-Logging für Debugging
  - Sauberes Cursor-Cleanup
  - HTTPException 503 bei Verbindungsfehlern
- `get_db_connection()`: Verbessert mit:
  - Connection-Check vor Yield
  - Automatisches Rollback bei Fehlern
  - Exception-Handling für DB-Errors

### 4. Router mit zentraler Fehlerbehandlung

#### src/api/routers/transactions.py
- Import: `error_handling` Modul
- `get_transactions()`: `@handle_db_errors("fetch transactions")` Decorator
- `get_transaction()`: `@handle_db_errors("fetch transaction")` Decorator
- `update_transaction_entries()`: `@handle_db_errors("update transaction entries")` Decorator
  - Ersetzt manuelle try-except-Blöcke
  - Verwendet `safe_commit()` und `safe_rollback()`

#### src/api/routers/categories.py
- Import: `error_handling` Modul
- Alle GET-Endpunkte mit `@handle_db_errors()` Decorator:
  - `get_categories()` - "fetch categories"
  - `get_categories_hierarchy()` - "fetch category hierarchy"
  - `get_category()` - "fetch category"
- Alle Mutations-Endpunkte mit Decorator + safe_commit/rollback:
  - `create_category()` - "create category"
  - `update_category()` - "update category"
  - `delete_category()` - "delete category"

#### src/api/routers/years.py
- Import: `error_handling` Modul
- `get_available_years()`: `@handle_db_errors("fetch available years")` Decorator

#### src/api/routers/year_overview.py
- Import: `error_handling` Modul mit `get_cursor_with_retry`, `execute_query_with_retry`
- `get_account_balances()`: 
  - `@handle_db_errors("fetch account balances")` Decorator
  - Ersetzt manuelle `_cursor()` und `_execute_with_retry()` Funktionen
  - Verwendet zentrale `get_cursor_with_retry()` und `execute_query_with_retry()`
- `get_account_balances_monthly()`:
  - `@handle_db_errors("fetch monthly account balances")` Decorator
  - Gleiche Vereinheitlichung wie oben

## Vorteile der neuen Architektur

### 1. Konsistenz
- Alle Endpunkte verwenden identisches Error-Handling
- Einheitliche HTTP-Status-Codes (503 für DB-Connection, 500 für Server-Fehler)
- Gleiche Fehlermeldungsformate

### 2. Robustheit
- Automatische Retry-Logik auf mehreren Ebenen:
  - Database.connect(): 3 Versuche
  - Database.get_cursor(): 3 Versuche
  - get_db_cursor() Dependency: 3 Versuche
  - execute_query_with_retry(): 2 Versuche
- Sichere Cursor-Cleanup-Operation
- Automatisches Rollback bei Fehlern

### 3. Wartbarkeit
- Zentraler Code für Fehlerbehandlung
- Änderungen an Error-Handling nur an einer Stelle nötig
- Decorator-Pattern reduziert Boilerplate-Code
- Klare Trennung von Business-Logik und Error-Handling

### 4. Debugging
- Detailliertes Logging mit `traceback.print_exc()`
- Aussagekräftige Operationsnamen in Fehlermeldungen
- Console-Ausgaben für alle Retry-Versuche

### 5. Stabilität
- API stürzt nicht mehr bei DB-Connection-Fehlern ab
- HTTPExceptions werden korrekt durchgereicht (404, etc.)
- Unterscheidung zwischen retriable und non-retriable Errors
- Sichere Connection-Verwaltung mit is_connected() Checks

## Error-Handling-Flow

```
1. Request → Router-Endpunkt
2. @handle_db_errors Decorator fängt alle Exceptions
3. get_db_cursor() Dependency:
   - Versucht Cursor zu bekommen (3 Retries)
   - Database.get_cursor() mit eigenem Retry
4. Bei Query-Ausführung:
   - execute_query_with_retry() für 2 Versuche
5. Bei Mutations:
   - safe_commit() für sichere Commits
   - safe_rollback() bei Fehlern
6. Decorator übersetzt alle Exceptions in HTTPExceptions
```

## Testing-Checkliste

- [x] API startet ohne Fehler
- [ ] Jahresübersicht lädt beide Tabellen
- [ ] Import & Datenprüfung lädt Transaktionen
- [ ] Kategorien-Seite funktioniert
- [ ] Transaktionen können bearbeitet werden
- [ ] Connection-Drop wird automatisch recovered
- [ ] Keine API-Abstürze bei Seitenwechsel

## Nächste Schritte

1. Umfassendes Testing aller Seiten
2. Monitoring der Console-Logs bei Connection-Issues
3. Ggf. Retry-Counts anpassen basierend auf Produktions-Erfahrung
4. Erweiterte Error-Metriken für Monitoring (optional)

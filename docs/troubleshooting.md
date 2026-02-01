# 🪲 fixed bugs 

## [issue #55](https://github.com/m2-eng/FiniA/issues/55): MariaDB JSON Update Not Persisting When Using `cursor.execute()` in Python

### Summary

This change fixes an issue where updating a JSON field in MariaDB using Python (`cursor.execute()` + `connection.commit()`) did not persist the updated value. While Python returned `rowcount = 1` and reading the value back showed the updated JSON, phpMyAdmin and the application continued to display the old data.

### Root Cause

The issue was caused by a combination of three factors:

#### 1. Autocommit was disabled
`autocommit = False` caused Python to run inside an implicit long-lived
transaction. The UPDATE was executed, but the transaction was never fully committed, even when calling `connection.commit()`.

Python therefore saw its **own uncommitted writes**, but the update never became visible to other clients.

#### 2. Transaction isolation level: `REPEATABLE-READ`
With `REPEATABLE-READ`, the session continues to read from the same snapshot for the entire transaction. Because autocommit was off, the transaction remained open, and Python consistently read the updated (but uncommitted) version.

#### 3. MariaDB Query Cache enabled
The server had:
```
query_cache_type = ON
query_cache_size > 0
```

This caused phpMyAdmin and the application to receive cached query results, which still contained the old JSON value.

### Combined Effect

- Python `UPDATE` appeared successful (`rowcount = 1`)
- Python `SELECT` returned the new value (uncommitted)
- phpMyAdmin returned cached or committed old data
- The application read the old value again on reload

This made it seem like the UPDATE was "ignored" or "reverted", even though it was simply never committed.

### Resolution

Autocommit was enabled explicitly:

```python
connection.autocommit = True
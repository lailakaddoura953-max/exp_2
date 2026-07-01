# Database Write Tables - Current Limitation & Setup Guide

## Current Status

The monitoring system **reads** eligible strads from the remote SQL Server successfully
(via DSN `Db_test` with ODBC Driver 18). However, **write operations fail** because the
tables needed to store results don't exist on that server, and the current credentials
lack CREATE TABLE permissions.

### What's Affected

| Operation | Table Name | Impact of Missing Table |
|-----------|-----------|------------------------|
| Store classification result | `classification_results` | Results not persisted (logged to console/file only) |
| Track check history (cooldown) | `strad_action_check_by_id_and_timestamp` | Same strad may be selected again next cycle |
| Exclude critical strads | `critical_strad_exclusions` | Critical strads not excluded from future selection |

### What Still Works

- Strad selection from remote database ✓
- IP address lookup from `ip_addresses.json` ✓
- Web capture (headless browser screenshot) ✓
- Classification via DL model ✓
- Logging of all results to file ✓
- Cycle completes without crashing ✓

The errors are logged but handled gracefully — the system continues processing.

---

## Fix: When You Get Database Permissions

When you (or a DBA) can create tables on the target database, run the script at:

```
scripts/create_monitoring_tables.sql
```

### How to Run

**Option A: Via SSMS**
1. Open SQL Server Management Studio
2. Connect to the server that the `Db_test` DSN points to
3. Select the correct database
4. Open `scripts/create_monitoring_tables.sql`
5. Execute (F5)

**Option B: Via sqlcmd**
```cmd
sqlcmd -D Db_test -C -i scripts\create_monitoring_tables.sql
```
The `-C` flag trusts the server certificate (required by ODBC Driver 18).

**Option C: Ask a DBA**
Send `scripts/create_monitoring_tables.sql` to whoever manages the database and
ask them to run it against the target database.

### What the Script Creates

Three tables with `IF NOT EXISTS` guards (safe to run multiple times):

1. **`classification_results`** — stores each classification output
   - `strad_id` (VARCHAR 10)
   - `classification` ('none', 'moderate', 'critical')
   - `confidence` (FLOAT 0.0-1.0)
   - `snapshot_path` (for critical photos)
   - `timestamp`, `created_at`

2. **`strad_action_check_by_id_and_timestamp`** — tracks last-checked time per strad
   - `strad_id` (VARCHAR 10, PRIMARY KEY)
   - `last_check_timestamp` (DATETIME)

3. **`critical_strad_exclusions`** — holds critical strads excluded from selection
   - `strad_id` (VARCHAR 10, UNIQUE)
   - `exclusion_timestamp` (DATETIME)
   - `reason` (VARCHAR 500)

---

## Alternative: Local Database (If Remote Permissions Never Granted)

If creating tables on the remote server is never possible, the alternative is
to use a local SQL Server Express LocalDB instance for writes:

1. Install SQL Server Express LocalDB (same version as your SSMS)
2. Create a local database for monitoring results
3. Run `scripts/create_monitoring_tables.sql` against the local instance
4. Add a second connection string in `system_config.json` for the local write DB
5. Modify `database_interface.py` to route writes to the local connection

This keeps reads on the remote server (via DSN) and writes local (full permissions).
Connection string for LocalDB would be:
```
DRIVER={ODBC Driver 18 for SQL Server};Server=(LocalDB)\MSSQLLocalDB;Database=StradMonitoring;Trusted_Connection=yes;TrustServerCertificate=yes
```

---

## Summary

For now, the system runs fine without the write tables — errors are logged but
don't stop the monitoring cycle. The capture + classify pipeline is fully
functional. Result persistence is the only thing deferred until table creation
permissions are available.

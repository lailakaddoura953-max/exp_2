# Local Testing Guide: Fallback Mechanism

## Overview

This system includes a **local testing fallback mechanism** that allows full end-to-end testing without requiring a connection to the production SQL Server database. This is essential for:

- **Local development** on machines without SQL Server access
- **Testing Excel → VLC → DL classification workflow** independently
- **CI/CD pipelines** that don't have database credentials
- **Demonstration purposes** using sample data

---

## How It Works

### Production Mode (SQL Server Available)

```
1. Program starts
2. Connects to SQL Server
3. Calls stored procedure: strad_action_check_by_id_and_timestamp
4. Returns real strad IDs from production database
5. Proceeds with Excel → VLC → Classification → Storage
```

### Fallback Mode (SQL Server Unavailable)

```
1. Program starts
2. Attempts SQL Server connection → FAILS
3. Detects failure and switches to fallback
4. Loads test strad IDs from local source (KITTI, CSV, or random)
5. Proceeds with Excel → VLC → Classification → (Mock storage)
```

---

## Configuration

Edit `system_config.json` to enable fallback:

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server;DATABASE=StradMonitoring;Trusted_Connection=yes",
  
  "enable_local_testing_mode": true,
  "fallback_data_path": "C:\\test_data\\strad_list.csv",
  "fallback_data_source": "local_folder"
}
```

### Configuration Options

| Parameter | Description | Values |
|-----------|-------------|--------|
| `enable_local_testing_mode` | Enable fallback when SQL Server unavailable | `true` / `false` |
| `fallback_data_path` | Path to local test data | File path or `null` |
| `fallback_data_source` | Which fallback method to use | `"kitti"`, `"local_folder"`, `"random"` |

---

## Fallback Options

### Option 0: SQLite Test Database (RECOMMENDED)

**Use Case:** You want the most realistic local testing with actual database structure and queries

**Configuration:**
```json
{
  "fallback_data_source": "sqlite",
  "use_sqlite_fallback": true,
  "sqlite_db_path": "tests/test.db"
}
```

**Database Details:**
- **Location:** `tests/test.db`
- **Table:** `container_demo`
- **Records:** 20 realistic test records
- **CHE Values:** SC001, SC006, SC012, SC027, SC028, SC031, SC039, SC049, SC052, SC062, SC063, SC083, SC085, SC095, SC110, SC111, SC115, SC127

**How It Works:**
- Connects to local SQLite database (no SQL Server required)
- Queries `container_demo` table for CHE values
- Returns random unique strad IDs from the test data
- Most realistic fallback - mimics actual database queries

**Setup:**
```bash
# Database already created! Just use it.
# To recreate from scratch:
cd tests
sqlite3 test.db < test_table_create.sql
sqlite3 test.db < populate_test.sql
```

---

### Option 1: KITTI Dataset

**Use Case:** You want to test with realistic camera data from the KITTI dataset

**Configuration:**
```json
{
  "fallback_data_source": "kitti",
  "fallback_data_path": "C:\\exp_2\\kitti_data"
}
```

**How It Works:**
- Scans KITTI dataset directory for available sequences
- Maps KITTI sequence IDs to strad IDs (e.g., sequence_0001 → SC001)
- Returns 10 random strad IDs based on available KITTI data

---

### Option 2: Local CSV/JSON File

**Use Case:** You want to test with custom strad scenarios (specific timestamps, critical strads, etc.)

**Configuration:**
```json
{
  "fallback_data_source": "local_folder",
  "fallback_data_path": "C:\\test_data\\strad_list.csv"
}
```

**File Format (CSV):**
```csv
strad_id,last_check_timestamp,is_critical
SC001,2024-01-15 10:00:00,false
SC042,2024-01-15 11:00:00,false
SC078,2024-01-15 09:30:00,true
SC115,2024-01-15 12:00:00,false
...
```

**File Format (JSON):**
```json
{
  "strads": [
    {"strad_id": "SC001", "last_check_timestamp": "2024-01-15 10:00:00", "is_critical": false},
    {"strad_id": "SC042", "last_check_timestamp": "2024-01-15 11:00:00", "is_critical": false},
    {"strad_id": "SC078", "last_check_timestamp": "2024-01-15 09:30:00", "is_critical": true}
  ]
}
```

**How It Works:**
- Reads CSV/JSON file from specified path
- Applies same filtering logic as SQL Server (1-hour cooldown, critical exclusion)
- Returns eligible strad IDs

---

### Option 3: Random Generation

**Use Case:** Quick testing without any external data files

**Configuration:**
```json
{
  "fallback_data_source": "random",
  "fallback_data_path": null
}
```

**How It Works:**
- Generates random strad IDs from SC001 to SC135
- No filtering applied (assumes all strads eligible)
- Simple and fast for basic workflow testing

---

## Code Location

All fallback logic is in: `src/strad_monitoring/database/database_interface.py`

### Key Methods

```python
# Main method with fallback
def get_eligible_strads(self, count: int = 10) -> List[str]:
    try:
        # PRIMARY PATH: Production SQL Server
        return self._query_production_server(count)
    except ConnectionError:
        # FALLBACK PATH: Local Testing Mode
        return self._get_fallback_strads(count)

# Fallback Option 0 (NEW - RECOMMENDED!)
def _load_strads_from_sqlite(self, count: int) -> List[str]:
    """Load from SQLite test database (tests/test.db)"""
    pass

# Fallback Option 1
def _load_strads_from_kitti(self, count: int) -> List[str]:
    """Load from KITTI dataset"""
    pass

# Fallback Option 2
def _load_strads_from_local_folder(self, count: int) -> List[str]:
    """Load from CSV/JSON file"""
    pass

# Fallback Option 3
def _generate_random_test_strads(self, count: int) -> List[str]:
    """Generate random test IDs"""
    pass
```

---

## Clear Code Comments

All fallback code includes these comments for easy navigation:

```python
# ========================================
# PRIMARY PATH: Production SQL Server
# ========================================
# Calls stored procedure: strad_action_check_by_id_and_timestamp

# ========================================
# FALLBACK PATH: Local Testing Mode
# ========================================
# Used when SQL Server is unavailable

# FALLBACK OPTION 0: SQLite test database (RECOMMENDED!)
# FALLBACK OPTION 1: Load from KITTI dataset
# FALLBACK OPTION 2: Load from local CSV/JSON file
# FALLBACK OPTION 3: Generate random test IDs
```

**Any developer can search for "PRIMARY PATH" or "FALLBACK" to find relevant code sections.**

---

## Testing the Fallback

### Test 0: Use SQLite Test Database (RECOMMENDED)

1. Ensure SQLite database exists at `tests/test.db`

2. Configure:
   ```json
   "enable_local_testing_mode": true,
   "use_sqlite_fallback": true,
   "fallback_data_source": "sqlite",
   "sqlite_db_path": "tests/test.db"
   ```

3. Run program: Should load strad IDs from SQLite database
   - Expected output: CHE values like SC001, SC006, SC012, SC027, etc.
   - Most realistic testing option!

### Test 1: Disable SQL Server Connection

1. Set invalid connection string in `system_config.json`:
   ```json
   "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=invalid-server;..."
   ```

2. Enable fallback:
   ```json
   "enable_local_testing_mode": true,
   "fallback_data_source": "random"
   ```

3. Run program: Should use random fallback without errors

### Test 2: Use KITTI Data

1. Ensure KITTI dataset exists in `kitti_data/`

2. Configure:
   ```json
   "fallback_data_source": "kitti",
   "fallback_data_path": "C:\\exp_2\\kitti_data"
   ```

3. Run program: Should load strad IDs from KITTI

### Test 3: Use Custom Test Data

1. Create `test_data/strad_list.csv` with sample strads

2. Configure:
   ```json
   "fallback_data_source": "local_folder",
   "fallback_data_path": "C:\\test_data\\strad_list.csv"
   ```

3. Run program: Should load strads from CSV

---

## Logging

When fallback is active, you'll see these log messages:

**SQLite Fallback (OPTION 0):**
```
[WARNING] SQL Server unavailable: [Error details]. Using local testing fallback: sqlite
[INFO] Loading strads from SQLite database: tests/test.db
[INFO] Selected 10 strads from SQLite: ['SC001', 'SC006', 'SC012', ...]
```

**KITTI Fallback (OPTION 1):**
```
[WARNING] SQL Server unavailable. Using local testing fallback: kitti
[INFO] Loading strads from KITTI dataset: C:\\exp_2\\kitti_data
[INFO] Selected 10 strads from KITTI: ['SC001', 'SC042', ...]
```

**Local File Fallback (OPTION 2):**
```
[WARNING] SQL Server unavailable. Using local testing fallback: local_folder
[INFO] Loading strads from local file: C:\\test_data\\strad_list.csv
[INFO] Selected 10 eligible strads from CSV: ['SC001', 'SC042', ...]
```

**Random Fallback (OPTION 3):**
```
[WARNING] SQL Server unavailable. Using local testing fallback: random
[INFO] Generated 10 random test strads: ['SC001', 'SC042', ...]
```

When production mode is active:

```
[INFO] Retrieved 10 eligible strads from SQL Server
```

---

## Production Deployment

For production deployment, **disable the fallback**:

```json
{
  "enable_local_testing_mode": false
}
```

This ensures the system fails fast if SQL Server is unavailable, rather than silently using test data.

---

## Questions?

See `design.md` Section 2.2 "Database Interface with SQL Server connectivity" for full technical details.

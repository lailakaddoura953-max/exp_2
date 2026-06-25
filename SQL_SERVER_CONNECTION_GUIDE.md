# SQL Server Database Connection Guide
## Microsoft SQL Server Management Studio (SSMS) Configuration

**Last Updated:** 2024  
**Purpose:** Guide for connecting the strad monitoring system to your SQL Server database

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Finding Your SQL Server Connection String](#finding-your-sql-server-connection-string)
3. [Configuring system_config.json](#configuring-systemconfigjson)
4. [Database Schema Requirements](#database-schema-requirements)
5. [Testing the Connection](#testing-the-connection)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Microsoft SQL Server** (2016 or later)
   - Express, Standard, or Enterprise edition
   - Running on local machine or network server

2. **SQL Server Management Studio (SSMS)**
   - Download from: https://docs.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms
   - Used to manage database and find connection details

3. **ODBC Driver 17 for SQL Server**
   - Usually installed with SQL Server
   - Required for Python connection via pyodbc

### Check ODBC Driver Installation

```cmd
# List installed ODBC drivers
odbcad32.exe

# Or check from PowerShell
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"}
```

**Common Driver Names:**
- `ODBC Driver 17 for SQL Server` (recommended)
- `ODBC Driver 18 for SQL Server` (newer)
- `SQL Server Native Client 11.0` (older)

---

## Finding Your SQL Server Connection String

### Method 1: Using SQL Server Management Studio (SSMS)

**Step 1: Open SSMS and Connect**

1. Open SQL Server Management Studio
2. In the "Connect to Server" dialog, note these details:
   - **Server type:** Database Engine
   - **Server name:** This is what you need!
   - **Authentication:** Windows Authentication or SQL Server Authentication

**Common Server Name Formats:**
```
# Local instance (default)
localhost
(local)
.

# Named instance on local machine
localhost\SQLEXPRESS
localhost\INSTANCENAME
.\SQLEXPRESS

# Remote server (network)
SERVERNAME
SERVERNAME\INSTANCENAME
192.168.1.100
192.168.1.100\SQLEXPRESS

# Fully qualified domain name
server.domain.com
server.domain.com\INSTANCENAME
```

**Step 2: Find Database Name**

1. After connecting, expand "Databases" in Object Explorer
2. Find your strad monitoring database
3. Note the exact database name (case-sensitive in some configurations)

**Common Database Names:**
- `StradMonitoring`
- `StradCarrierTracking`
- `ProductionDB`
- `VideoEncoderData`

---

### Method 2: Check Windows Services

```cmd
# Open Services (Run as Administrator)
services.msc

# Look for services starting with "SQL Server ("
# Example: SQL Server (SQLEXPRESS)
# The text in parentheses is your instance name
```

---

### Method 3: Query Registry (Advanced)

```powershell
# Find SQL Server instances on local machine
Get-ItemProperty -Path 'HKLM:\SOFTWARE\Microsoft\Microsoft SQL Server' -Name InstalledInstances
```

---

## Configuring system_config.json

### File Location

```
c:\Users\Miles\Desktop\exp_2\system_config.json
```

### Connection String Format

The connection string is in the `database_connection_string` field. Here's the format:

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=<SERVER_NAME>;DATABASE=<DATABASE_NAME>;Trusted_Connection=yes"
}
```

### Configuration Examples

#### Example 1: Local SQL Server with Windows Authentication (Most Common)

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes"
}
```

**When to use:**
- SQL Server installed on your local machine
- Using Windows Authentication (your Windows login)
- Default instance (not a named instance)

---

#### Example 2: Local Named Instance (SQL Express)

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=StradMonitoring;Trusted_Connection=yes"
}
```

**When to use:**
- Using SQL Server Express edition
- Instance name is SQLEXPRESS (or another custom name)

**Important:** Use double backslash (`\\`) in JSON!

---

#### Example 3: Remote Server with Windows Authentication

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=PROD-SERVER-01;DATABASE=StradMonitoring;Trusted_Connection=yes"
}
```

**When to use:**
- SQL Server on a different machine in your network
- Using Windows Authentication
- Server name is PROD-SERVER-01 (replace with your actual server name)

---

#### Example 4: SQL Server Authentication (Username/Password)

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;UID=strad_user;PWD=YourPasswordHere"
}
```

**When to use:**
- Using SQL Server Authentication instead of Windows Authentication
- Have a specific SQL login username and password

**Security Warning:** Don't commit passwords to source control!

---

#### Example 5: IP Address with Port

```json
{
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=192.168.1.100,1433;DATABASE=StradMonitoring;Trusted_Connection=yes"
}
```

**When to use:**
- Connecting via IP address
- Using non-default port (default is 1433)
- Format: `IP_ADDRESS,PORT_NUMBER`

---

### Full system_config.json Example

```json
{
  "_comment_header": "===== STRAD CARRIER MONITORING AUTOMATION - SYSTEM CONFIGURATION =====",
  "_comment_instructions": "Update paths and connection strings for your environment before running",
  
  "_comment_database": "===== DATABASE CONFIGURATION =====",
  "_database_instructions": "STEP 1: Update this connection string with your SQL Server details",
  "_database_example_1": "Local default instance: DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "_database_example_2": "SQL Express: DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\\\SQLEXPRESS;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "_database_example_3": "Remote server: DRIVER={ODBC Driver 17 for SQL Server};SERVER=SERVERNAME;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes",
  
  "_comment_paths": "===== FILE PATHS =====",
  "excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx",
  "model_checkpoint_path": "C:\\Models\\misalignment_detector_v2.pth",
  "temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
  "permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots",
  "log_file_path": "C:\\StradMonitoring\\logs",
  
  "_comment_timing": "===== TIMING CONFIGURATION =====",
  "cycle_schedule_cron": "0 * * * *",
  "strad_selection_count": 10,
  "cooldown_hours": 1,
  "classification_timeout_seconds": 10,
  
  "_comment_snapshot": "===== SNAPSHOT CONFIGURATION =====",
  "snapshot_min_width": 640,
  "snapshot_min_height": 480,
  "snapshot_retention_days": 30,
  "log_retention_days": 14,
  
  "_comment_fallback": "===== LOCAL TESTING FALLBACK CONFIGURATION =====",
  "enable_local_testing_mode": true,
  "use_sqlite_fallback": true,
  "sqlite_db_path": "tests/test.db",
  "fallback_data_source": "sqlite",
  "fallback_data_path": "C:\\test_data\\strad_list.csv",
  
  "_comment_dl_model": "===== DEEP LEARNING MODEL CONFIGURATION =====",
  "dl_model_config": {
    "flow_network": "liteflownet2",
    "target_resolution": [640, 640],
    "confidence_threshold": 0.5,
    "enable_uncertainty": false
  }
}
```

---

## Database Schema Requirements

### Required Tables

The system expects the following tables in your SQL Server database:

#### 1. `container_demo` Table (or equivalent strad tracking table)

```sql
CREATE TABLE container_demo (
    CHE VARCHAR(10) PRIMARY KEY,          -- Strad ID (e.g., SC001, SC042)
    last_check_time DATETIME NULL,        -- Last monitoring check timestamp
    is_critical_excluded BIT DEFAULT 0    -- Critical exclusion flag
);
```

**Sample Data:**
```sql
INSERT INTO container_demo (CHE, last_check_time, is_critical_excluded)
VALUES 
    ('SC001', NULL, 0),
    ('SC042', NULL, 0),
    ('SC083', NULL, 0);
```

---

#### 2. `classification_results` Table

```sql
CREATE TABLE classification_results (
    id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(10) NOT NULL,
    classification VARCHAR(20) NOT NULL,   -- 'none', 'moderate', 'critical'
    confidence FLOAT NOT NULL,
    snapshot_path NVARCHAR(500) NULL,
    timestamp DATETIME DEFAULT GETDATE(),
    processing_time_ms FLOAT NULL
);
```

**Sample Data:**
```sql
INSERT INTO classification_results (strad_id, classification, confidence, snapshot_path)
VALUES 
    ('SC042', 'moderate', 0.65, '2024-01-15/SC042_143025.jpg'),
    ('SC083', 'none', 0.92, NULL),
    ('SC001', 'critical', 0.88, '2024-01-15/SC001_145530.jpg');
```

---

#### 3. `moderate_classification_tracking` Table

```sql
CREATE TABLE moderate_classification_tracking (
    id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(10) NOT NULL,
    classification VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    timestamp DATETIME DEFAULT GETDATE()
);

CREATE INDEX idx_strad_timestamp ON moderate_classification_tracking(strad_id, timestamp);
```

---

### Creating the Database Schema

**Option 1: Run in SSMS**

1. Open SQL Server Management Studio
2. Connect to your server
3. Click "New Query"
4. Paste the CREATE TABLE statements above
5. Click "Execute" or press F5

**Option 2: Run from Python**

```python
import pyodbc

# Connection string
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes"

# Connect and create tables
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Execute CREATE TABLE statements
cursor.execute("""
    CREATE TABLE container_demo (
        CHE VARCHAR(10) PRIMARY KEY,
        last_check_time DATETIME NULL,
        is_critical_excluded BIT DEFAULT 0
    );
""")

conn.commit()
conn.close()
print("✓ Tables created successfully")
```

---

### Stored Procedure (Optional but Recommended)

The system can use a stored procedure `strad_action_check_by_id_and_timestamp`:

```sql
CREATE PROCEDURE strad_action_check_by_id_and_timestamp
    @strad_id VARCHAR(10),
    @timestamp DATETIME
AS
BEGIN
    -- Check if strad exists and return relevant data
    SELECT 
        CHE,
        last_check_time,
        is_critical_excluded
    FROM container_demo
    WHERE CHE = @strad_id;
END;
```

**Create in SSMS:**
1. New Query
2. Paste the CREATE PROCEDURE statement
3. Execute

---

## Testing the Connection

### Test 1: Using Python Test Script

```cmd
# Save this as test_sql_connection.py
```

```python
import pyodbc

# YOUR connection string (update this!)
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes"

try:
    print("Attempting to connect to SQL Server...")
    conn = pyodbc.connect(conn_str, timeout=5)
    
    print("✓ Connection successful!")
    
    # Test query
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION")
    version = cursor.fetchone()[0]
    print(f"✓ SQL Server version: {version[:50]}...")
    
    # Check if database exists
    cursor.execute("SELECT DB_NAME()")
    db_name = cursor.fetchone()[0]
    print(f"✓ Connected to database: {db_name}")
    
    # List tables
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    
    tables = cursor.fetchall()
    if tables:
        print(f"✓ Found {len(tables)} tables:")
        for table in tables:
            print(f"  - {table[0]}")
    else:
        print("⚠ No tables found in database")
    
    cursor.close()
    conn.close()
    
except pyodbc.Error as e:
    print(f"✗ Connection failed: {e}")
    print("\nTroubleshooting steps:")
    print("1. Check server name is correct")
    print("2. Verify SQL Server is running (services.msc)")
    print("3. Check firewall allows SQL Server connections")
    print("4. Verify database name exists")
    print("5. Ensure you have permission to access the database")
```

**Run the test:**
```cmd
python test_sql_connection.py
```

---

### Test 2: Using the System's Database Interface

```cmd
python -c "from src.strad_monitoring.config.system_config import ConfigurationManager; from src.strad_monitoring.database.database_interface import DatabaseInterface; config = ConfigurationManager.load_config('system_config.json'); db = DatabaseInterface(connection_string=config.database_connection_string, enable_fallback=False, fallback_data_path='', fallback_data_source=''); print('✓ Connected!' if db.health_check() else '✗ Connection failed')"
```

---

### Test 3: Direct Query Test

```cmd
# Test specific table
python -c "import pyodbc; conn = pyodbc.connect('DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes'); cursor = conn.cursor(); cursor.execute('SELECT COUNT(*) FROM container_demo'); count = cursor.fetchone()[0]; print(f'✓ Found {count} strads in container_demo table')"
```

---

## Troubleshooting

### Error: "Data source name not found and no default driver specified"

**Cause:** ODBC driver not installed or wrong driver name

**Solution:**
1. Check installed drivers: `odbcad32.exe`
2. Update driver name in connection string:
   ```json
   "DRIVER={ODBC Driver 18 for SQL Server}"  # If you have version 18
   "DRIVER={SQL Server Native Client 11.0}"   # If you have older version
   ```

---

### Error: "Login failed for user"

**Cause:** Authentication issue

**Solution:**

**For Windows Authentication:**
1. Ensure SQL Server allows Windows Authentication
2. Your Windows account must have access to the database
3. Check in SSMS: Security → Logins → [Your Windows User]

**For SQL Authentication:**
1. Verify username and password are correct
2. Check SQL Server allows SQL Authentication:
   - SSMS → Server Properties → Security
   - Enable "SQL Server and Windows Authentication mode"
   - Restart SQL Server service

---

### Error: "Cannot open database 'StradMonitoring' requested by the login"

**Cause:** Database doesn't exist or user doesn't have access

**Solution:**
1. Check database exists:
   ```sql
   SELECT name FROM sys.databases
   ```
2. Create database if needed:
   ```sql
   CREATE DATABASE StradMonitoring
   ```
3. Grant access to user:
   ```sql
   USE StradMonitoring;
   CREATE USER [DOMAIN\Username] FOR LOGIN [DOMAIN\Username];
   GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO [DOMAIN\Username];
   ```

---

### Error: "A network-related or instance-specific error occurred"

**Cause:** Cannot reach SQL Server

**Solution:**
1. **Check SQL Server is running:**
   ```cmd
   services.msc
   # Look for "SQL Server (MSSQLSERVER)" or "SQL Server (SQLEXPRESS)"
   # Status should be "Running"
   ```

2. **Check SQL Server Browser is running** (for named instances):
   ```cmd
   # Start SQL Server Browser service
   net start SQLBrowser
   ```

3. **Enable TCP/IP protocol:**
   - SQL Server Configuration Manager
   - SQL Server Network Configuration
   - Protocols for [Instance Name]
   - Enable TCP/IP
   - Restart SQL Server service

4. **Check firewall:**
   ```cmd
   # Allow SQL Server through firewall
   netsh advfirewall firewall add rule name="SQL Server" dir=in action=allow protocol=TCP localport=1433
   ```

---

### Error: "The server was not found or was not accessible"

**Cause:** Server name incorrect or network issue

**Solution:**
1. Verify server name:
   ```cmd
   sqlcmd -L
   # Lists all SQL Server instances on network
   ```

2. Try different formats:
   ```
   localhost
   .\SQLEXPRESS
   (local)\SQLEXPRESS
   127.0.0.1
   COMPUTERNAME\INSTANCENAME
   ```

3. Test with sqlcmd:
   ```cmd
   sqlcmd -S localhost -E
   # Should connect if SQL Server is running
   ```

---

## Quick Reference

### Connection String Components

```
DRIVER={...}           # ODBC driver name
SERVER=...             # Server name or IP
DATABASE=...           # Database name
Trusted_Connection=yes # Windows Authentication
UID=...                # SQL username (if using SQL auth)
PWD=...                # SQL password (if using SQL auth)
```

### Common Server Names

| Format | Example | When to Use |
|--------|---------|-------------|
| `localhost` | `localhost` | Default instance on local machine |
| `.\INSTANCE` | `.\SQLEXPRESS` | Named instance on local machine |
| `SERVER` | `PROD-SERVER-01` | Remote server (default instance) |
| `SERVER\INSTANCE` | `PROD-SERVER-01\SQLEXPRESS` | Remote named instance |
| `IP,PORT` | `192.168.1.100,1433` | IP address with port |

### Testing Commands

```cmd
# Check SQL Server services
services.msc

# List ODBC drivers
odbcad32.exe

# Test connection with sqlcmd
sqlcmd -S localhost -E

# List SQL Server instances
sqlcmd -L

# Test Python connection
python test_sql_connection.py
```

---

## Summary

**Steps to Configure:**

1. ✅ Find your SQL Server name (SSMS or services.msc)
2. ✅ Find your database name (SSMS Object Explorer)
3. ✅ Check ODBC driver installed (odbcad32.exe)
4. ✅ Update `system_config.json` with connection string
5. ✅ Create required tables (if they don't exist)
6. ✅ Test connection (python test_sql_connection.py)
7. ✅ Enable fallback mode if testing without SQL Server

**Files to Edit:**
- `c:\Users\Miles\Desktop\exp_2\system_config.json` → `database_connection_string` field

**Support:**
- Test script: `test_sql_connection.py`
- System test: `python -m src.strad_monitoring.main --config system_config.json`
- Fallback mode: Set `enable_local_testing_mode: true` in config

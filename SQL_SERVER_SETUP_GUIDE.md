# Microsoft SQL Server Connection Setup Guide
## Strad Carrier Monitoring Automation

**Last Updated:** 2024  
**Purpose:** Configure connection to Microsoft SQL Server database  
**Status:** Production Configuration (Requires POC Approval)

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Finding Your SQL Server Information](#finding-your-sql-server-information)
3. [Configuration File Setup](#configuration-file-setup)
4. [Database Schema Requirements](#database-schema-requirements)
5. [Testing Your Connection](#testing-your-connection)
6. [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Software

1. **Microsoft SQL Server** (2016 or later recommended)
   - SQL Server Express (free) or Standard/Enterprise
   - Must be accessible from your machine

2. **SQL Server Management Studio (SSMS)** (recommended)
   - Download from: https://aka.ms/ssmsfullsetup
   - Used to test queries and verify database structure

3. **ODBC Driver for SQL Server**
   - ODBC Driver 17 or 18 for SQL Server
   - Check installed drivers: Windows Key → "ODBC Data Sources (64-bit)"

### Required Information

You need to know:
- ✓ SQL Server hostname or IP address
- ✓ Database name
- ✓ Authentication method (Windows Authentication OR SQL Server Authentication)
- ✓ Login credentials (if using SQL Server Authentication)
- ✓ Port number (default: 1433)

---

## Finding Your SQL Server Information

### Step 1: Open SQL Server Management Studio (SSMS)

1. Launch SSMS
2. Look at the "Connect to Server" dialog

### Step 2: Identify Your Server Name

**Server name format examples:**
- `localhost` - SQL Server on your local machine
- `DESKTOP-ABC123` - Local machine with named instance
- `DESKTOP-ABC123\SQLEXPRESS` - SQL Server Express instance
- `192.168.1.100` - Remote server by IP address
- `prod-server.company.com` - Remote server by hostname
- `prod-server.company.com\INSTANCE1` - Remote server with named instance

**To find your server name:**
```sql
-- Run this query in SSMS (after connecting)
SELECT @@SERVERNAME AS ServerName
```

### Step 3: Identify Authentication Type

**Windows Authentication (Recommended for domain environments):**
- Uses your Windows login credentials
- No username/password needed in connection string
- Connection string uses: `Trusted_Connection=yes`

**SQL Server Authentication:**
- Uses SQL Server-specific username and password
- Connection string includes: `UID=username;PWD=password`
- Less secure than Windows Authentication

### Step 4: Find Database Name

**In SSMS:**
1. Connect to server
2. Expand "Databases" folder
3. Look for your strad monitoring database

**Common names:**
- `StradMonitoring`
- `ContainerMonitoring`
- `ProductionDB`

**To list all databases:**
```sql
-- Run this query in SSMS
SELECT name FROM sys.databases
ORDER BY name
```

### Step 5: Check ODBC Driver Version

**Open ODBC Data Source Administrator:**
1. Windows Key → Type "ODBC"
2. Select "ODBC Data Sources (64-bit)"
3. Go to "Drivers" tab
4. Look for "ODBC Driver XX for SQL Server"

**Available drivers:**
- `ODBC Driver 17 for SQL Server` (recommended)
- `ODBC Driver 18 for SQL Server` (newer)
- `SQL Server Native Client 11.0` (older, still works)

---

## Configuration File Setup

### File to Edit

**Location:** `system_config.json` (in the root directory of the project)

**IMPORTANT:** This file already exists with default values. You need to UPDATE the existing values with your actual database connection details.

### Current Configuration Structure

The file uses a flat structure with these database-related fields:

```json
{
  "_comment_database": "===== DATABASE CONFIGURATION =====",
  "database_connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server;DATABASE=StradMonitoring;Trusted_Connection=yes",
  
  "_comment_paths": "===== FILE PATHS =====",
  "excel_file_path": "C:\\VideoEncoder\\spreader_encoder.xlsx",
  ...
}
```

### How to Update

Open `system_config.json` and find the `"database_connection_string"` field (around line 5). Replace the default value with your actual SQL Server connection details.

### Complete Configuration File Example

Here's what your complete `demo_config\system_config.json` should look like after adding database configuration:

```json
{
  "database": {
    "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER_NAME;DATABASE=YOUR_DATABASE_NAME;Trusted_Connection=yes",
    "stored_procedure": "strad_action_check_by_id_and_timestamp"
  },
  "excel": {
    "file_path": "C:\\Users\\YourName\\Documents\\video_feeds.xlsx",
    "sheet_name": "VideoFeeds"
  },
  "cameras": {
    "0": {
      "stream_url": "rtsp://camera0.local/stream",
      "resolution": [640, 480],
      "fps": 30,
      "thresholds": {
        "position_threshold_m": 0.05,
        "angle_threshold_deg": 5.0,
        "flow_inconsistency_threshold": 0.3,
        "confidence_threshold": 0.7
      }
    }
  },
  "alert_channels": [
    {
      "type": "dashboard",
      "enabled": true,
      "config": {}
    }
  ],
  "processing_params": {
    "frame_sync_tolerance_ms": 50.0,
    "frame_buffer_size": 100,
    "min_feature_count": 100,
    "target_processing_rate_hz": 10.0,
    "sustained_detection_frames": 2
  }
}
```

### Connection String Format

#### Option 1: Windows Authentication (Recommended)

```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER_NAME;DATABASE=YOUR_DATABASE_NAME;Trusted_Connection=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Replace:**
- `YOUR_SERVER_NAME` → Your SQL Server name (e.g., `localhost`, `DESKTOP-ABC123\SQLEXPRESS`, `prod-server.company.com`)
- `YOUR_DATABASE_NAME` → Your database name (e.g., `StradMonitoring`)

**Examples:**

**Local SQL Server Express:**
```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost\\SQLEXPRESS;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Local SQL Server (default instance):**
```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Remote SQL Server:**
```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server.company.com;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Remote SQL Server with Port:**
```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server.company.com,1433;DATABASE=StradMonitoring;Trusted_Connection=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

#### Option 2: SQL Server Authentication

```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER_NAME;DATABASE=YOUR_DATABASE_NAME;UID=YOUR_USERNAME;PWD=YOUR_PASSWORD",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Replace:**
- `YOUR_SERVER_NAME` → Your SQL Server name
- `YOUR_DATABASE_NAME` → Your database name
- `YOUR_USERNAME` → SQL Server login username
- `YOUR_PASSWORD` → SQL Server login password

**Examples:**

**Local SQL Server with SQL Authentication:**
```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=localhost;DATABASE=StradMonitoring;UID=strad_user;PWD=SecurePassword123!",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Remote SQL Server with SQL Authentication:**
```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=prod-server.company.com;DATABASE=StradMonitoring;UID=strad_user;PWD=SecurePassword123!",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

#### Option 3: Using Different ODBC Driver

**ODBC Driver 18:**
```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 18 for SQL Server};SERVER=YOUR_SERVER_NAME;DATABASE=YOUR_DATABASE_NAME;Trusted_Connection=yes;TrustServerCertificate=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Note:** ODBC Driver 18 requires `TrustServerCertificate=yes` for non-SSL connections

**SQL Server Native Client:**
```json
"database": {
  "connection_string": "DRIVER={SQL Server Native Client 11.0};SERVER=YOUR_SERVER_NAME;DATABASE=YOUR_DATABASE_NAME;Trusted_Connection=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

---

## Database Schema Requirements

### Required Tables

The system expects the following database objects to exist:

#### 1. Stored Procedure: `strad_action_check_by_id_and_timestamp`

**Purpose:** Query strad carrier data for eligibility checking

**Expected Parameters:**
- `@strad_id` (VARCHAR) - Strad carrier ID (e.g., 'SC042')
- `@timestamp` (DATETIME) - Current timestamp

**Expected Return Columns:**
- `CHE` (VARCHAR) - Strad carrier ID (SCXXX format)
- `last_check_time` (DATETIME) - Last time this strad was checked
- Other columns as needed

**Example Call:**
```sql
EXEC strad_action_check_by_id_and_timestamp 
    @strad_id = 'SC042',
    @timestamp = '2024-01-15 14:30:00'
```

#### 2. Table: `classification_results` (Created by System)

**Purpose:** Store classification results

**Schema:**
```sql
CREATE TABLE classification_results (
    id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(10) NOT NULL,
    classification VARCHAR(20) NOT NULL,  -- 'none', 'moderate', 'critical'
    confidence FLOAT NOT NULL,
    snapshot_path VARCHAR(500),
    timestamp DATETIME NOT NULL DEFAULT GETDATE(),
    processing_time_ms FLOAT,
    
    INDEX idx_strad_id (strad_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_classification (classification)
)
```

#### 3. Table: `moderate_tracking` (Created by System)

**Purpose:** Track consecutive moderate classifications

**Schema:**
```sql
CREATE TABLE moderate_tracking (
    id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(10) NOT NULL,
    classification VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    timestamp DATETIME NOT NULL DEFAULT GETDATE(),
    consecutive_count INT NOT NULL DEFAULT 1,
    
    INDEX idx_strad_id (strad_id),
    INDEX idx_timestamp (timestamp)
)
```

#### 4. Table: `critical_exclusion_list` (Created by System)

**Purpose:** Track strads with critical misalignment (excluded from regular checks)

**Schema:**
```sql
CREATE TABLE critical_exclusion_list (
    id INT IDENTITY(1,1) PRIMARY KEY,
    strad_id VARCHAR(10) NOT NULL UNIQUE,
    classification VARCHAR(20) NOT NULL,
    confidence FLOAT NOT NULL,
    snapshot_path VARCHAR(500),
    added_timestamp DATETIME NOT NULL DEFAULT GETDATE(),
    adjustment_confirmed BIT NOT NULL DEFAULT 0,
    confirmation_timestamp DATETIME,
    
    INDEX idx_strad_id (strad_id),
    INDEX idx_adjustment_confirmed (adjustment_confirmed)
)
```

### Database Setup Script

**Create the database and tables:**

```sql
-- ============================================================================
-- Strad Carrier Monitoring - Database Setup Script
-- ============================================================================

-- Create database (if it doesn't exist)
IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'StradMonitoring')
BEGIN
    CREATE DATABASE StradMonitoring
END
GO

USE StradMonitoring
GO

-- ============================================================================
-- Table 1: classification_results
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'classification_results')
BEGIN
    CREATE TABLE classification_results (
        id INT IDENTITY(1,1) PRIMARY KEY,
        strad_id VARCHAR(10) NOT NULL,
        classification VARCHAR(20) NOT NULL,
        confidence FLOAT NOT NULL,
        snapshot_path VARCHAR(500),
        timestamp DATETIME NOT NULL DEFAULT GETDATE(),
        processing_time_ms FLOAT,
        
        INDEX idx_strad_id (strad_id),
        INDEX idx_timestamp (timestamp),
        INDEX idx_classification (classification)
    )
    
    PRINT '✓ Table classification_results created'
END
ELSE
BEGIN
    PRINT '✓ Table classification_results already exists'
END
GO

-- ============================================================================
-- Table 2: moderate_tracking
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'moderate_tracking')
BEGIN
    CREATE TABLE moderate_tracking (
        id INT IDENTITY(1,1) PRIMARY KEY,
        strad_id VARCHAR(10) NOT NULL,
        classification VARCHAR(20) NOT NULL,
        confidence FLOAT NOT NULL,
        timestamp DATETIME NOT NULL DEFAULT GETDATE(),
        consecutive_count INT NOT NULL DEFAULT 1,
        
        INDEX idx_strad_id (strad_id),
        INDEX idx_timestamp (timestamp)
    )
    
    PRINT '✓ Table moderate_tracking created'
END
ELSE
BEGIN
    PRINT '✓ Table moderate_tracking already exists'
END
GO

-- ============================================================================
-- Table 3: critical_exclusion_list
-- ============================================================================
IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'critical_exclusion_list')
BEGIN
    CREATE TABLE critical_exclusion_list (
        id INT IDENTITY(1,1) PRIMARY KEY,
        strad_id VARCHAR(10) NOT NULL UNIQUE,
        classification VARCHAR(20) NOT NULL,
        confidence FLOAT NOT NULL,
        snapshot_path VARCHAR(500),
        added_timestamp DATETIME NOT NULL DEFAULT GETDATE(),
        adjustment_confirmed BIT NOT NULL DEFAULT 0,
        confirmation_timestamp DATETIME,
        
        INDEX idx_strad_id (strad_id),
        INDEX idx_adjustment_confirmed (adjustment_confirmed)
    )
    
    PRINT '✓ Table critical_exclusion_list created'
END
ELSE
BEGIN
    PRINT '✓ Table critical_exclusion_list already exists'
END
GO

-- ============================================================================
-- Stored Procedure: strad_action_check_by_id_and_timestamp
-- ============================================================================
-- NOTE: This is a PLACEHOLDER - you must replace this with your actual
-- stored procedure that queries your existing strad carrier data
-- ============================================================================

IF EXISTS (SELECT * FROM sys.procedures WHERE name = 'strad_action_check_by_id_and_timestamp')
BEGIN
    DROP PROCEDURE strad_action_check_by_id_and_timestamp
END
GO

CREATE PROCEDURE strad_action_check_by_id_and_timestamp
    @strad_id VARCHAR(10) = NULL,
    @timestamp DATETIME = NULL
AS
BEGIN
    SET NOCOUNT ON
    
    -- ========================================================================
    -- IMPORTANT: REPLACE THIS WITH YOUR ACTUAL QUERY
    -- ========================================================================
    -- This is a placeholder that returns mock data
    -- You need to replace this with a query to your actual container/strad table
    -- ========================================================================
    
    -- Example placeholder query (REPLACE THIS):
    SELECT 
        'SC001' AS CHE,
        DATEADD(hour, -2, GETDATE()) AS last_check_time,
        'Camera_URL_1' AS camera_url,
        'Active' AS status
    UNION ALL
    SELECT 'SC042', DATEADD(hour, -3, GETDATE()), 'Camera_URL_2', 'Active'
    UNION ALL
    SELECT 'SC127', DATEADD(hour, -5, GETDATE()), 'Camera_URL_3', 'Active'
    
    -- Your actual query should look something like:
    -- SELECT 
    --     CHE,
    --     last_check_time,
    --     camera_url,
    --     status
    -- FROM your_container_table
    -- WHERE (@strad_id IS NULL OR CHE = @strad_id)
    --   AND status = 'Active'
    --   AND last_check_time < DATEADD(hour, -1, @timestamp)
END
GO

PRINT '✓ Stored procedure strad_action_check_by_id_and_timestamp created'
PRINT ''
PRINT '================================================================================
PRINT 'DATABASE SETUP COMPLETE'
PRINT '================================================================================
PRINT ''
PRINT 'IMPORTANT: Update the stored procedure strad_action_check_by_id_and_timestamp'
PRINT 'to query your actual container/strad data instead of the placeholder query'
PRINT ''
PRINT 'Tables created:'
PRINT '  ✓ classification_results'
PRINT '  ✓ moderate_tracking'
PRINT '  ✓ critical_exclusion_list'
PRINT ''
PRINT 'Next steps:'
PRINT '  1. Update system_config.json with your connection string'
PRINT '  2. Test connection: python test_database_connection.py'
PRINT '  3. Run system: python -m src.strad_monitoring.main'
PRINT '================================================================================'
GO
```

**To run this script:**
1. Open SQL Server Management Studio
2. Connect to your server
3. Click "New Query"
4. Copy and paste the script above
5. Click "Execute" (F5)

---

## Testing Your Connection

### Method 1: Using Python Test Script

The test script `test_database_connection.py` reads from `demo_config/system_config.json`:

```python
"""Test SQL Server connection"""
import pyodbc
import sys
import json

# Load connection string from demo_config/system_config.json
with open('demo_config/system_config.json', 'r') as f:
    config = json.load(f)

# Get database configuration
if 'database' not in config:
    print("ERROR: No 'database' section in system_config.json")
    print("You need to add the database configuration section.")
    print("See SQL_SERVER_SETUP_GUIDE.md for instructions.")
    sys.exit(1)

connection_string = config['database']['connection_string']

print("=" * 70)
print("SQL SERVER CONNECTION TEST")
print("=" * 70)
print(f"\nConnection string: {connection_string}")
print("\nAttempting to connect...")

try:
    # Connect to database
    conn = pyodbc.connect(connection_string, timeout=10)
    print("✓ Connection successful!")
    
    # Test query
    cursor = conn.cursor()
    cursor.execute("SELECT @@VERSION AS version")
    row = cursor.fetchone()
    
    print("\nSQL Server Information:")
    print(row[0][:100] + "...")
    
    # List tables
    cursor.execute("""
        SELECT TABLE_NAME 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_TYPE = 'BASE TABLE'
        ORDER BY TABLE_NAME
    """)
    
    print("\nAvailable tables:")
    for row in cursor.fetchall():
        print(f"  - {row[0]}")
    
    cursor.close()
    conn.close()
    
    print("\n" + "=" * 70)
    print("✓ CONNECTION TEST PASSED")
    print("=" * 70)
    sys.exit(0)
    
except pyodbc.Error as e:
    print(f"\n✗ Connection failed!")
    print(f"\nError: {e}")
    print("\nTroubleshooting steps:")
    print("  1. Check server name is correct")
    print("  2. Check database name exists")
    print("  3. Verify ODBC driver is installed")
    print("  4. Check firewall allows connection")
    print("  5. Verify SQL Server is running")
    print("\n" + "=" * 70)
    sys.exit(1)
```

**Run the test:**
```cmd
python test_database_connection.py
```

### Method 2: Using SSMS

1. Open SQL Server Management Studio
2. Connect to your server
3. Run this query:
```sql
-- Test connection and check database
SELECT 
    @@SERVERNAME AS ServerName,
    DB_NAME() AS CurrentDatabase,
    SYSTEM_USER AS CurrentUser,
    GETDATE() AS CurrentTime
```

---

## Troubleshooting

### Error: "Login failed for user"

**Possible causes:**
1. Incorrect username/password (SQL Server Authentication)
2. User doesn't have permission to access database
3. User doesn't exist on server

**Solutions:**
```sql
-- Grant permissions (run as admin)
USE StradMonitoring
GO

-- For Windows Authentication user
CREATE USER [DOMAIN\username] FOR LOGIN [DOMAIN\username]
GO
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO [DOMAIN\username]
GO

-- For SQL Server Authentication user
CREATE LOGIN strad_user WITH PASSWORD = 'SecurePassword123!'
GO
USE StradMonitoring
GO
CREATE USER strad_user FOR LOGIN strad_user
GO
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO strad_user
GO
```

### Error: "SQL Server does not exist or access denied"

**Possible causes:**
1. Incorrect server name
2. SQL Server not running
3. Firewall blocking connection
4. TCP/IP not enabled

**Solutions:**

**Check SQL Server is running:**
1. Windows Key → "Services"
2. Look for "SQL Server (MSSQLSERVER)" or "SQL Server (SQLEXPRESS)"
3. Status should be "Running"

**Enable TCP/IP:**
1. Open "SQL Server Configuration Manager"
2. Expand "SQL Server Network Configuration"
3. Click "Protocols for MSSQLSERVER" (or your instance name)
4. Right-click "TCP/IP" → Enable
5. Restart SQL Server service

**Check firewall:**
```cmd
# Test if port is open
telnet YOUR_SERVER_NAME 1433

# Or use PowerShell
Test-NetConnection -ComputerName YOUR_SERVER_NAME -Port 1433
```

### Error: "Driver not found"

**Possible causes:**
1. ODBC driver not installed
2. Wrong driver name in connection string

**Solutions:**

**Install ODBC Driver 17:**
1. Download from: https://go.microsoft.com/fwlink/?linkid=2223304
2. Run installer
3. Restart computer

**Check installed drivers:**
```cmd
# List ODBC drivers
odbcconf /q /lq
```

**Or use PowerShell:**
```powershell
Get-OdbcDriver | Where-Object {$_.Name -like "*SQL Server*"} | Select-Object Name
```

### Error: "Cannot open database requested by the login"

**Possible causes:**
1. Database name is incorrect
2. Database doesn't exist
3. User doesn't have access to database

**Solutions:**

**List available databases:**
```sql
SELECT name FROM sys.databases ORDER BY name
```

**Check user has access:**
```sql
USE StradMonitoring
GO
SELECT * FROM sys.database_principals WHERE name = 'your_username'
```

---

## Summary Checklist

Before running the system, verify:

- [ ] SQL Server is running
- [ ] Database exists
- [ ] Required tables exist (classification_results, moderate_tracking, critical_exclusion_list)
- [ ] Stored procedure exists (strad_action_check_by_id_and_timestamp)
- [ ] User has permissions (SELECT, INSERT, UPDATE, DELETE, EXECUTE)
- [ ] ODBC driver installed
- [ ] Connection string updated in demo_config/system_config.json
- [ ] Connection test passes

---

## Quick Reference

### Connection String Template (Windows Auth)
```
DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DB;Trusted_Connection=yes
```

### Connection String Template (SQL Auth)
```
DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DB;UID=YOUR_USER;PWD=YOUR_PASS
```

### Test Connection
```cmd
python test_database_connection.py
```

### Create Database Schema
```sql
-- Run the database setup script in SSMS (see section above)
```

### Grant Permissions
```sql
USE StradMonitoring
GO
GRANT SELECT, INSERT, UPDATE, DELETE, EXECUTE ON SCHEMA::dbo TO your_user
GO
```

---

## Support

For questions or issues:
1. Check DEPLOYMENT.md for additional troubleshooting
2. Review LOCAL_TESTING_GUIDE.md for SQLite fallback options
3. Consult SQL Server documentation: https://docs.microsoft.com/sql/

**Remember:** This system requires official POC approval before production deployment!

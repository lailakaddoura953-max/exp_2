# SQL Server Database Integration Plan

## Status: PLANNED - Pending Database Schema Information

**Created:** 2026-06-22  
**Priority:** Medium  
**Blocked By:** Need database schema details and event ID structure

---

## Overview

Integrate the Camera Misalignment Detection System with SQL Server Management Studio database to:
- Store misalignment detection events with timestamps
- Log system status and health metrics
- Query historical camera movement events by event ID
- Correlate detection events with database records

---

## Current System Architecture

**Existing Components:**
- Python/C++ hybrid system
- Frame acquisition, feature extraction, optical flow analysis
- SLAM position tracking
- Misalignment detection logic
- Alert system (current implementation TBD)
- Database logger placeholder (not yet implemented)

**Location:** `src/` directory structure

---

## Database Use Cases

### Primary Use Cases:
1. **Event Logging** - Store each misalignment detection event with:
   - Camera ID
   - Timestamp (detection time)
   - Severity level (LOW, MEDIUM, HIGH, CRITICAL)
   - Pose data (position, orientation)
   - Optical flow metrics
   - Diagnostic information

2. **Historical Queries** - Query past events by:
   - Event ID (from existing database)
   - Camera ID
   - Time range
   - Severity level

3. **Event Correlation** - Cross-reference:
   - Detection system events with database event IDs
   - Identify exact timing of camera movements
   - Match physical impacts with detected misalignment

4. **System Health Monitoring** - Log:
   - Processing frame rate
   - Camera connection status
   - Feature tracking quality
   - SLAM tracking state

---

## Integration Architecture (Proposed)

### Option 1: Direct Connection (Python)
```
Camera System → Database Logger (Python) → SQL Server (pyodbc/pymssql)
```

**Pros:**
- Simple, direct connection
- Easy to implement in existing Python code
- Good for synchronous logging

**Cons:**
- Blocking I/O could slow down real-time processing
- Needs connection pooling for performance

### Option 2: Async Queue (Recommended)
```
Camera System → Queue (asyncio/threading) → Background Worker → SQL Server
```

**Pros:**
- Non-blocking, maintains real-time performance
- Resilient to temporary database outages
- Can batch inserts for efficiency

**Cons:**
- More complex implementation
- Requires queue management

### Option 3: External Service
```
Camera System → REST API / Message Queue → Separate Service → SQL Server
```

**Pros:**
- Decouples systems completely
- Can scale independently
- Multiple systems can share the service

**Cons:**
- Additional infrastructure complexity
- Network latency considerations

---

## Database Schema Requirements (TO BE DEFINED)

### Information Needed:
- [ ] Existing database structure
- [ ] Event table schema (columns, data types, constraints)
- [ ] Event ID format and generation strategy
- [ ] Primary keys and indexes
- [ ] Stored procedures (if any)
- [ ] Connection string format
- [ ] Authentication method (Windows Auth / SQL Auth)
- [ ] Database name and server address

### Expected Tables:
1. **Events Table** - Stores misalignment events
   - event_id (INT/BIGINT/UUID?)
   - camera_id (INT)
   - timestamp (DATETIME2)
   - severity (VARCHAR/ENUM)
   - position_x, position_y, position_z (FLOAT)
   - rotation_x, rotation_y, rotation_z (FLOAT)
   - flow_magnitude_mean (FLOAT)
   - flow_magnitude_std (FLOAT)
   - description (VARCHAR/TEXT)
   - [Other fields TBD]

2. **System Health Table** - System status logs
   - log_id (INT/BIGINT)
   - timestamp (DATETIME2)
   - component (VARCHAR)
   - status (VARCHAR)
   - frame_rate (FLOAT)
   - message (TEXT)

3. **Camera Status Table** - Camera connection state
   - camera_id (INT)
   - timestamp (DATETIME2)
   - is_connected (BIT)
   - frame_count (INT)
   - last_frame_time (DATETIME2)

---

## Python Libraries for SQL Server

### Recommended: `pyodbc`
```python
import pyodbc

# Connection example
conn = pyodbc.connect(
    'DRIVER={ODBC Driver 17 for SQL Server};'
    'SERVER=your_server;'
    'DATABASE=your_database;'
    'Trusted_Connection=yes;'
)
```

**Pros:**
- Industry standard
- Good performance
- Wide compatibility
- Supports connection pooling

### Alternative: `pymssql`
```python
import pymssql

conn = pymssql.connect(
    server='your_server',
    database='your_database',
    user='username',
    password='password'
)
```

**Pros:**
- Pure Python (easier to install)
- Simpler API
- Good for basic operations

### ORM Option: `SQLAlchemy`
```python
from sqlalchemy import create_engine

engine = create_engine(
    'mssql+pyodbc://server/database?driver=ODBC+Driver+17+for+SQL+Server'
)
```

**Pros:**
- Abstraction layer
- Easy model definition
- Built-in connection pooling
- Migration support

---

## Implementation Steps (When Ready)

### Phase 1: Setup & Connection (1-2 hours)
1. Install SQL Server ODBC driver on system
2. Install Python library (`pyodbc` or `pymssql`)
3. Create configuration file for connection settings
4. Test basic connection and query
5. Set up connection pooling

### Phase 2: Database Logger Module (2-3 hours)
1. Create `src/database/db_logger.py` module
2. Implement connection manager
3. Create event insertion methods
4. Add error handling and retry logic
5. Write unit tests with mock database

### Phase 3: Integration (2-3 hours)
1. Integrate logger into misalignment detector
2. Add async queue for non-blocking writes
3. Update alert system to log events
4. Add system health logging
5. Test with real detection events

### Phase 4: Query Interface (1-2 hours)
1. Create query methods for historical events
2. Add filtering by camera, time, severity
3. Implement event ID lookup
4. Create correlation helpers
5. Write query examples and documentation

### Phase 5: Testing & Deployment (2-3 hours)
1. End-to-end integration tests
2. Performance testing (write throughput)
3. Failover testing (database down scenarios)
4. Load testing (high event rate)
5. Documentation and runbook

**Total Estimated Time:** 8-13 hours

---

## Configuration Example (Future)

```yaml
# config/database.yaml
database:
  type: sqlserver
  server: YOUR_SERVER_NAME
  database: YOUR_DATABASE_NAME
  authentication: windows  # or 'sql'
  
  # For SQL authentication (optional)
  # username: your_username
  # password: your_password  # Use environment variable in production
  
  # Connection pooling
  pool_size: 5
  max_overflow: 10
  pool_timeout: 30
  
  # Async queue settings
  async_enabled: true
  queue_size: 1000
  batch_size: 100
  flush_interval: 5  # seconds
  
  # Retry settings
  max_retries: 3
  retry_delay: 1  # seconds
  retry_backoff: 2  # exponential backoff multiplier
```

---

## Security Considerations

- [ ] Use Windows Authentication when possible (more secure)
- [ ] Store credentials in environment variables, not code
- [ ] Use least-privilege database user (INSERT/SELECT only)
- [ ] Enable SSL/TLS for database connections
- [ ] Implement connection timeout and retry limits
- [ ] Log connection attempts for security auditing
- [ ] Sanitize all inputs to prevent SQL injection

---

## Questions to Answer Before Implementation

1. **Database Details:**
   - What is the SQL Server version?
   - What is the server hostname/IP?
   - What is the database name?
   - What authentication method should we use?

2. **Schema Details:**
   - What is the exact event table schema?
   - What columns are required vs optional?
   - What are the data type constraints?
   - Are there any triggers or stored procedures?
   - What is the event ID generation strategy?

3. **Performance Requirements:**
   - What is the expected event rate (events/second)?
   - What is the acceptable write latency?
   - Should we use batching for performance?
   - Are there any network bandwidth constraints?

4. **Integration Points:**
   - Should the webapp also query the database?
   - Should we expose an API for event queries?
   - Do other systems need access to the event data?

5. **Operational:**
   - Who manages the database server?
   - What is the backup/recovery strategy?
   - How should we handle database downtime?
   - What monitoring is in place?

---

## Related Files

- `src/detection/misalignment_detector.py` - Main detection logic
- `src/alerting/` - Alert system (needs database integration)
- `src/models/event.py` - Event data models
- `.kiro/specs/camera-misalignment-detection/` - System spec documents

---

## Next Steps (When Ready to Proceed)

1. **Gather Information:**
   - Get database schema documentation
   - Obtain connection credentials (securely)
   - Understand event ID structure
   - Review existing database queries/procedures

2. **Create Spec:**
   - Create new spec: "SQL Server Database Integration"
   - Document requirements (data to log, query needs)
   - Design database logger architecture
   - Plan async queue implementation
   - Define configuration format

3. **Implementation:**
   - Follow phased implementation plan above
   - Start with Phase 1 (connection test)
   - Iterate through phases
   - Test thoroughly before production use

4. **Documentation:**
   - Update system architecture diagrams
   - Document database schema
   - Create runbook for database operations
   - Add troubleshooting guide

---

## Notes

- The database will enable powerful analytics on camera movement patterns
- Historical event correlation will help identify systematic issues
- Real-time logging should not impact detection performance (use async)
- Consider data retention policies (how long to keep events)
- May want to add data export functionality for analysis
- Could integrate with monitoring/alerting systems (PagerDuty, etc.)

**This is a bookmark/planning document. Implementation will begin once database details are available.**


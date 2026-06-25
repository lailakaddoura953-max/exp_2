# Configuration File Structure Reference

## File Location

**Path:** `demo_config\system_config.json`

This is the ONLY configuration file you need to edit for the strad monitoring system.

---

## Complete Configuration Structure

```json
{
  "database": {
    "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DB;Trusted_Connection=yes",
    "stored_procedure": "strad_action_check_by_id_and_timestamp"
  },
  "excel": {
    "file_path": "C:\\Path\\To\\Your\\spreader_encoder.xlsx",
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

---

## What You Need to Configure

### 1. Database Connection (Required for Production)

```json
"database": {
  "connection_string": "DRIVER={ODBC Driver 17 for SQL Server};SERVER=YOUR_SERVER;DATABASE=YOUR_DB;Trusted_Connection=yes",
  "stored_procedure": "strad_action_check_by_id_and_timestamp"
}
```

**Guide:** See `SQL_SERVER_SETUP_GUIDE.md`

**Examples:**
- Local: `SERVER=localhost;DATABASE=StradMonitoring`
- Remote: `SERVER=prod-server.company.com;DATABASE=StradMonitoring`
- With SQL Auth: `SERVER=localhost;DATABASE=StradMonitoring;UID=username;PWD=password`

**Test:** `python test_database_connection.py`

---

### 2. Excel Video Encoder (Required)

```json
"excel": {
  "file_path": "C:\\Path\\To\\Your\\spreader_encoder.xlsx",
  "sheet_name": "VideoFeeds"
}
```

**Guide:** See `EXCEL_CONFIGURATION_GUIDE.md`

**IMPORTANT:** Use double backslashes (`\\`) in the path!

**Examples:**
- Local: `C:\\VideoEncoder\\spreader_encoder.xlsx`
- Desktop: `C:\\Users\\YourName\\Desktop\\spreader_encoder.xlsx`
- Network: `\\\\Server\\Share\\VideoEncoder\\spreader_encoder.xlsx`

**Test:** `python test_excel_connection.py`

---

### 3. Camera Configuration (Optional - Defaults Provided)

The camera configuration is already set up with default values. You can customize:

```json
"cameras": {
  "0": {
    "stream_url": "rtsp://your-camera.local/stream",
    "resolution": [640, 480],
    "fps": 30,
    "thresholds": {
      "position_threshold_m": 0.05,
      "angle_threshold_deg": 5.0,
      "flow_inconsistency_threshold": 0.3,
      "confidence_threshold": 0.7
    }
  }
}
```

---

## Quick Start Checklist

- [ ] Open `demo_config\system_config.json`
- [ ] Add `database` section with your SQL Server connection string
- [ ] Add `excel` section with your Excel file path (use `\\` not `\`)
- [ ] Test database: `python test_database_connection.py`
- [ ] Test Excel: `python test_excel_connection.py`
- [ ] Run system: `python -m src.strad_monitoring.main`

---

## Common Mistakes

### ❌ Wrong File Path
- **Don't use:** `config_system.json`
- **Don't use:** `system_config.json` (root directory)
- **Use:** `demo_config\system_config.json`

### ❌ Wrong Config Structure
- **Don't use:** `"database_connection_string": "..."`
- **Use:** `"database": { "connection_string": "..." }`

### ❌ Single Backslashes in Paths
- **Don't use:** `C:\Path\To\File.xlsx`
- **Use:** `C:\\Path\\To\\File.xlsx`

### ❌ Missing Section
If you get "section not found" errors, you need to ADD that section to the config file.

---

## Additional Documentation

- **SQL Server Setup:** `SQL_SERVER_SETUP_GUIDE.md`
- **Excel Configuration:** `EXCEL_CONFIGURATION_GUIDE.md`
- **Complete Checklist:** `CONFIGURATION_CHECKLIST.md`
- **All Documentation:** `DOCUMENTATION_INDEX.md`

---

## Support

If configuration tests fail:

1. Check file paths exist
2. Verify double backslashes in JSON
3. Confirm ODBC driver installed (for database)
4. Ensure Excel file is accessible
5. Review detailed guides listed above

# Requirements - JSON-Based Video Feed Automation

## Overview

Replace Excel-based strad/IP mapping with a JSON configuration file (`ip_addresses.json`). System automatically captures one frame from each RTSP stream during monitoring cycles, with credentials stored in config file for full automation.

## User Stories

### 1. Video Feed Configuration
**As** a system administrator  
**I want** to configure strad ID to IP address mappings in a JSON file  
**So that** the monitoring system knows which video stream to capture for each strad

#### Acceptance Criteria
1. `config/ip_addresses.json` contains tab-separated SC# and IP addresses
2. Format: `SC#\tIP_ADDRESS` (one per line, e.g., `001\t192.168.1.100`)
3. File is parsed correctly on system startup
4. Invalid entries logged with clear error messages
5. System validates all IP addresses are reachable during initialization

### 2. RTSP Credentials Management
**As** a system administrator  
**I want** to store RTSP username and password in the config file  
**So that** the monitoring system can authenticate to video streams without manual input

#### Acceptance Criteria
1. `system_config.json` has `rtsp_username` and `rtsp_password` fields
2. Credentials used for all RTSP connections
3. Credentials not logged or exposed in error messages
4. System fails gracefully if credentials are missing or invalid

### 3. Automated Screenshot Capture
**As** a monitoring operator  
**I want** the system to automatically capture one frame from each video stream  
**So that** I don't need to manually interact with Excel or VLC

#### Acceptance Criteria
1. For each strad in the monitoring cycle:
   - Look up IP address from `ip_addresses.json`
   - Connect to RTSP stream using credentials
   - Capture first/latest frame from stream
   - Save with filename: `SC{strad_id}_{YYYYMMDD}_{HHMMSS}.jpg`
   - Validate file exists and is readable
2. Capture timeout after 10 seconds (configurable)
3. If capture fails, log error and skip to next strad
4. Store screenshots in permanent snapshot directory

### 4. Monitoring Cycle Integration
**As** the monitoring orchestrator  
**I want** automated screenshot capture integrated into the hourly monitoring cycle  
**So that** the entire process is fully automated without operator interaction

#### Acceptance Criteria
1. Monitoring cycle (run_cycle) calls screenshot capture for 10 eligible strads
2. Each screenshot processed through classifier immediately
3. Results stored in database (critical/moderate/none)
4. Temporary screenshots cleared after cycle
5. Critical photos retained in permanent storage
6. Cycle completes within 50 minutes for 10 strads

### 5. Error Handling & Recovery
**As** a system operator  
**I want** graceful error handling when video streams are unavailable  
**So that** one failed stream doesn't stop the entire monitoring cycle

#### Acceptance Criteria
1. If strad IP not found in JSON: skip strad, log warning, continue
2. If RTSP connection fails: retry up to 3 times (1s delay), then skip
3. If screenshot capture timeout: skip strad, log error, continue
4. If screenshot dimensions invalid: skip strad, log error, continue
5. Failed strads tracked and reported in cycle summary
6. System continues processing remaining strads after failures

### 6. Configuration Validation
**As** a system administrator  
**I want** configuration errors detected at startup  
**So that** issues are found before affecting production monitoring

#### Acceptance Criteria
1. Validate `ip_addresses.json` file exists and is readable
2. Validate JSON format (tab-separated values)
3. Validate all IP addresses are in valid format
4. Validate RTSP credentials present in config
5. Validate snapshot directory exists and is writable
6. Clear error messages for any validation failures

## Non-Functional Requirements

### Performance
- Screenshot capture: <10 seconds per strad (including RTSP connection)
- 10 strads: <2 minutes total capture time
- Full cycle: <50 minutes (10 strads + classification + database)
- Network latency tolerance: RTSP connections timeout after 10s

### Reliability
- No data loss on network failures (skip strad, continue cycle)
- Consistent frame capture (same strad, same time each cycle)
- Automatic retry on transient failures (up to 3 attempts)
- Comprehensive logging for troubleshooting

### Security
- Credentials stored only in config file (not logged)
- RTSP connections authenticated with stored credentials
- No credentials exposed in error messages or logs
- File permissions verified for config file

### Scalability
- Support 135+ strads in IP mapping file
- Handle multiple simultaneous screenshot captures if needed
- Efficient JSON parsing (lazy-load only needed strad IPs)

## Scope

### In Scope
- JSON configuration file for strad/IP mapping
- RTSP stream connection with authentication
- Single-frame screenshot capture from stream
- Integration with monitoring orchestrator
- Error handling and retry logic
- Configuration validation

### Out of Scope
- Web interface for IP address management
- Real-time video streaming
- Advanced video processing (only single frame capture)
- VLC integration (replaced by RTSP)
- Excel integration (completely removed)

## Configuration Example

### `config/ip_addresses.json`
```
SC#	IP_Address
001	192.168.1.100
002	192.168.1.101
003	192.168.1.102
...
135	192.168.1.234
```

### `system_config.json` additions
```json
{
  "rtsp_username": "admin",
  "rtsp_password": "password123",
  "rtsp_port": 554,
  "rtsp_stream_path": "/stream",
  "screenshot_timeout_seconds": 10,
  "screenshot_max_retries": 3
}
```

## Success Criteria

✅ Monitoring cycle fully automated (no operator interaction needed)
✅ Screenshots captured directly from RTSP streams
✅ One frame per strad per cycle
✅ Credentials stored securely in config
✅ No Excel dependencies
✅ Error handling for stream failures
✅ Consistent filename format
✅ Integration with classifier pipeline
✅ Results stored in database
✅ Critical photos retained long-term

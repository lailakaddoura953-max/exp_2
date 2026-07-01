# Design - JSON-Based Video Feed Automation

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                  Monitoring Orchestrator                     │
│                  (Hourly at XX:00:00)                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Query 10 eligible strads from database                  │
│  2. Load ip_addresses.json                                  │
│  3. For each strad:                                         │
│     ├─ Get IP from JSON                                    │
│     ├─ RTSPCapture.capture_frame(ip, credentials)          │
│     ├─ Save screenshot to file                             │
│     ├─ DLClassifier.classify(screenshot)                   │
│     └─ Store result in database                            │
│  4. Clear temporary screenshots                            │
│  5. Log cycle completion                                   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         ↓              ↓              ↓              ↓
    ┌─────────┐  ┌──────────────┐  ┌──────────┐  ┌────────┐
    │ Database│  │RTSPCapture   │  │Classifier│  │Storage │
    │         │  │              │  │          │  │        │
    │ Strads  │  │Connect→Frame │  │DL Model  │  │Critical│
    │ Query   │  │Save→Validate │  │Classify  │  │Photos  │
    └─────────┘  └──────────────┘  └──────────┘  └────────┘
```

## Component Design

### 1. IP Address Configuration Module
**File**: `src/strad_monitoring/config/ip_address_loader.py`

```python
class IPAddressLoader:
    """Load and validate strad to IP address mappings from JSON file"""
    
    def __init__(self, json_path: str):
        """
        Load IP addresses from tab-separated JSON file
        
        Args:
            json_path: Path to ip_addresses.json
            
        Format:
            SC#\tIP_Address
            001\t192.168.1.100
            002\t192.168.1.101
        """
        pass
    
    def get_ip(self, strad_id: str) -> str:
        """Get IP address for strad ID"""
        pass
    
    def validate(self) -> List[str]:
        """Validate all IPs and return list of errors (empty if valid)"""
        pass
    
    def get_all_mappings(self) -> Dict[str, str]:
        """Return complete strad->IP mapping"""
        pass
```

**Key Methods**:
- `__init__()` - Parse tab-separated JSON
- `get_ip(strad_id)` - Return IP for given strad
- `validate()` - Check all IPs are reachable
- `get_all_mappings()` - Return dict of strad→IP

**Error Handling**:
- Missing file → FileNotFoundError
- Invalid format → ValueError with line number
- Invalid IP → ValueError with strad ID
- IP unreachable → Warning (log, don't fail)

---

### 2. RTSP Screenshot Capture Module
**File**: `src/strad_monitoring/video_capture/rtsp_capture.py`

```python
class RTSPCapture:
    """Capture single frame from RTSP stream"""
    
    def __init__(
        self,
        rtsp_username: str,
        rtsp_password: str,
        rtsp_port: int = 554,
        rtsp_stream_path: str = "/stream",
        timeout_seconds: int = 10,
        max_retries: int = 3
    ):
        """Initialize RTSP capture parameters"""
        pass
    
    def capture_frame(
        self,
        ip_address: str,
        strad_id: str,
        snapshot_dir: str
    ) -> Tuple[Optional[str], bool]:
        """
        Capture single frame from RTSP stream at IP address
        
        Args:
            ip_address: IP address of RTSP stream (e.g., 192.168.1.100)
            strad_id: Strad ID for filename (e.g., SC001)
            snapshot_dir: Directory to save screenshot
            
        Returns:
            (filepath, success) tuple
            - filepath: Path to saved screenshot if successful, None if failed
            - success: True if capture and save successful
            
        Filename format: SC{strad_id}_{YYYYMMDD}_{HHMMSS}.jpg
        Example: SC001_20250630_140530.jpg
        """
        pass
    
    def _build_rtsp_url(self, ip_address: str) -> str:
        """Build RTSP URL from IP address"""
        # rtsp://username:password@ip:port/stream_path
        pass
    
    def _capture_with_ffmpeg(self, rtsp_url: str, timeout: int) -> Optional[np.ndarray]:
        """Capture frame using FFmpeg"""
        pass
    
    def _validate_frame(self, frame: np.ndarray) -> bool:
        """Validate captured frame (non-empty, valid dimensions)"""
        pass
    
    def _save_frame(self, frame: np.ndarray, filepath: str) -> bool:
        """Save frame to JPEG file"""
        pass
```

**Key Methods**:
- `capture_frame()` - Main method, returns (filepath, success)
- `_build_rtsp_url()` - Construct RTSP URL with credentials
- `_capture_with_ffmpeg()` - Use FFmpeg to grab single frame
- `_validate_frame()` - Verify frame is valid
- `_save_frame()` - Save to JPEG with timestamp

**Implementation Details**:
- Use FFmpeg command: `ffmpeg -i rtsp://... -vframes 1 -f image2 output.jpg`
- Timeout: 10 seconds per capture (configurable)
- Retry: 3 attempts with 1s delay between
- Filename: `SC{strad_id}_{YYYYMMDD}_{HHMMSS}.jpg`
- Save to: `permanent_snapshot_path`

---

### 3. Orchestrator Integration
**File**: `src/strad_monitoring/orchestration/orchestrator.py`

```python
class MonitoringOrchestrator:
    """Main orchestrator - modified for JSON-based video capture"""
    
    def run_cycle(self) -> Dict:
        """
        Execute one monitoring cycle (10 strads)
        
        Workflow:
        1. Query database for 10 eligible strads
        2. Load ip_addresses.json
        3. For each strad:
           a. Get IP from JSON
           b. Capture frame from RTSP stream
           c. Classify screenshot
           d. Store result in database
        4. Clear temporary screenshots
        5. Return cycle statistics
        """
        pass
    
    def _capture_screenshot_from_rtsp(
        self,
        strad_id: str,
        ip_address: str
    ) -> Tuple[Optional[str], bool]:
        """Capture screenshot from RTSP stream at IP"""
        pass
    
    def _process_screenshot(
        self,
        strad_id: str,
        filepath: str
    ) -> Dict:
        """Process screenshot through classifier and store results"""
        pass
```

**Changes to run_cycle()**:
```python
def run_cycle(self):
    # ... existing code ...
    
    # Load IP addresses
    ip_loader = IPAddressLoader(self.config.ip_addresses_json_path)
    
    for strad_id in eligible_strads:
        ip_address = ip_loader.get_ip(strad_id)
        
        # Capture frame from RTSP stream
        filepath, success = self._capture_screenshot_from_rtsp(strad_id, ip_address)
        
        if success and filepath:
            # Process through classifier
            result = self._process_screenshot(strad_id, filepath)
            strad_results.append(result)
        else:
            # Log failure, continue with next strad
            logger.warning(f"Failed to capture screenshot for {strad_id}")
```

---

### 4. Configuration Schema
**File**: `system_config.json`

```json
{
  "database_connection_string": "...",
  "excel_file_path": "[REMOVED]",
  
  "rtsp_config": {
    "username": "admin",
    "password": "password123",
    "port": 554,
    "stream_path": "/stream",
    "timeout_seconds": 10,
    "max_retries": 3
  },
  
  "ip_addresses_json_path": "config/ip_addresses.json",
  
  "temp_snapshot_path": "C:\\StradMonitoring\\temp_snapshots",
  "permanent_snapshot_path": "D:\\StradMonitoring\\critical_snapshots",
  
  "...": "other existing config"
}
```

---

### 5. IP Address Configuration File
**File**: `config/ip_addresses.json`

```
SC#	IP_Address
001	192.168.1.100
002	192.168.1.101
003	192.168.1.102
004	192.168.1.103
...
135	192.168.1.234
```

**Format**:
- Tab-separated values (SC# \t IP_Address)
- One mapping per line
- Descending order (001, 002, ..., 135)
- No header line (or header ignored)
- IP addresses in standard dotted-quad format

---

## Data Flow

### Screenshot Capture Process
```
run_cycle()
  ├─ get_eligible_strads() → ['SC001', 'SC042', ...]
  ├─ ip_loader = IPAddressLoader('config/ip_addresses.json')
  └─ For each strad:
     ├─ ip = ip_loader.get_ip('SC001') → '192.168.1.100'
     ├─ rtsp_capture.capture_frame('192.168.1.100', 'SC001', snapshot_dir)
     │  ├─ Build URL: rtsp://admin:pass@192.168.1.100:554/stream
     │  ├─ FFmpeg: ffmpeg -i rtsp://... -vframes 1 output.jpg
     │  ├─ Validate frame
     │  ├─ Save: SC001_20250630_140530.jpg
     │  └─ Return (filepath, True)
     ├─ classifier.classify(filepath)
     │  └─ Return {severity, confidence}
     ├─ database.store_result(strad_id, classification)
     └─ [Repeat for all 10 strads]
```

---

## Error Scenarios & Recovery

### Scenario 1: IP Not Found in JSON
```
strad_id = 'SC001'
ip_loader.get_ip('SC001') → KeyError

Recovery:
- Catch exception
- Log: "SC001 not found in ip_addresses.json"
- Skip strad
- Continue with next strad
- Mark strad_failed += 1
```

### Scenario 2: RTSP Connection Timeout
```
FFmpeg command hangs or times out after 10s

Recovery:
- Timeout caught
- Log: "RTSP connection timeout for SC001 at 192.168.1.100"
- Retry up to 3 times (1s delay)
- If all retries fail: skip strad, continue
- Mark strad_failed += 1
```

### Scenario 3: Frame Capture Fails
```
FFmpeg executes but returns invalid data

Recovery:
- Validate frame (check if valid numpy array, non-empty)
- If invalid: log error, skip strad
- Mark strad_failed += 1
- Continue with next strad
```

### Scenario 4: File Save Fails
```
Disk full or permission denied

Recovery:
- Catch exception
- Log: "Failed to save screenshot: {error}"
- Skip strad
- Continue with next strad
- Mark strad_failed += 1
```

---

## Dependencies

### New Required Packages
- `ffmpeg-python` or direct FFmpeg command execution
- `opencv-python` (for frame validation)
- `numpy` (already in project)
- `Pillow` (already in project)

### Installation
```bash
pip install ffmpeg-python opencv-python
```

### System Requirements
- FFmpeg installed and in PATH
- RTSP stream access from server
- Network connectivity to all camera IP addresses

---

## File Changes

### Files to Create
1. `src/strad_monitoring/config/ip_address_loader.py` (~150 lines)
2. `src/strad_monitoring/video_capture/rtsp_capture.py` (~250 lines)
3. `config/ip_addresses.json` (template)

### Files to Modify
1. `src/strad_monitoring/orchestration/orchestrator.py`
   - Remove: Excel automation code
   - Add: RTSP capture integration
   - Modify: run_cycle() method
   
2. `src/strad_monitoring/config/system_config.py`
   - Add: rtsp_config section
   - Add: ip_addresses_json_path
   - Remove: excel_file_path (or keep as deprecated)

3. `system_config.json`
   - Add: rtsp configuration section
   - Add: ip_addresses_json_path
   - Remove: excel_file_path usage

### Files to Delete
1. `src/strad_monitoring/excel_automation/` (entire directory)
2. All Excel-related test files

---

## Performance Expectations

### Timing per Strad
- RTSP connection: 1-2 seconds
- Frame capture: 1-2 seconds
- Frame validation: <100ms
- File save: <500ms
- Total per strad: 2-5 seconds
- 10 strads: 20-50 seconds

### Total Cycle Time
- Strad selection: <1 second
- Screenshot capture (10 strads): 20-50 seconds
- Classification (10 strads): 10-20 seconds
- Database updates: 5-10 seconds
- **Total: 35-80 seconds** (well within 50-minute target)

---

## Success Criteria

✅ JSON file loaded successfully at startup
✅ All strad/IP mappings validated
✅ RTSP connections established with credentials
✅ Single frame captured per strad
✅ Filename format consistent: `SC{id}_{YYYYMMDD}_{HHMMSS}.jpg`
✅ Screenshots saved to permanent storage
✅ Classification pipeline works unchanged
✅ Results stored in database
✅ Error handling doesn't stop cycle
✅ Cycle completes within timing targets
✅ No Excel dependencies
✅ Full automation (no operator interaction)

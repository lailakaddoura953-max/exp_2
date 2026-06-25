# Web App Integration with Strad Monitoring System

**Date:** 2024  
**Status:** Integration Complete - Demo Presentable

---

## Summary

The web app (`docs/index.html`) has been integrated with the new strad_monitoring system. The web app now:

✅ **Connects to real strad_monitoring components**
✅ **Shows real classification data when available**
✅ **Falls back to placeholder/demo mode when not connected**
✅ **Keeps all existing features intact (demo videos, live inference test)**

---

## What Was Changed

### Backend (`docs/backend/app.py`)

**New Features Added:**
1. **Strad Monitoring Integration**
   - Imports strad_monitoring components (DatabaseInterface, DLClassifierWrapper, ConfigurationManager)
   - Initializes components on startup if available
   - Gracefully handles missing components (fallback to mock mode)

2. **New API Endpoints:**
   - `GET /api/strads/recent` - Get recent strad classifications with snapshots
   - `GET /api/snapshot/<strad_id>` - Get snapshot image for a specific strad
   - `GET /api/strads/stats` - Get classification statistics (counts by severity)

3. **Enhanced Endpoints:**
   - `GET /` - Now includes connection status (strad_monitoring_connected, database_connected, classifier_loaded)
   - `POST /api/inference` - Now supports both multi-camera mode (original) AND single-image mode
   - New `run_single_image_inference()` function that uses real DL classifier if available

**Backward Compatibility:**
- ✅ All original endpoints still work
- ✅ Multi-camera inference (cam0, cam1, cam2, cam3) still functional
- ✅ Mock mode when strad monitoring not available

### Frontend (`docs/script.js`)

**New Features Added:**
1. **Connection Status Checking**
   - `checkBackendConnection()` - Checks if backend and strad monitoring are available on page load
   - `updateConnectionStatus()` - Updates UI with connection indicator (green/red dot)

2. **Real Data Loading**
   - `loadRecentStrads()` - Fetches recent strad classifications from backend
   - `updateKanbanWithRealData()` - Updates kanban board with real data counts
   - `updateColumnCounts()` - Updates count badges on each column
   - `addRealStradCards()` - Placeholder for adding real strad cards (currently logs data)

**UI Updates:**
- Connection status indicator in header (● Connected / ○ Disconnected)
- Auto-loads real data when backend is connected
- Falls back to demo mode when backend unavailable

### Styles (`docs/styles.css`)

**New CSS Added:**
- `.connection-status` - Base styling for connection indicator
- `.connection-status.connected` - Green background for connected state
- `.connection-status.disconnected` - Red background for disconnected state

---

## How It Works

### Connection Flow

```
Page Load
    │
    ▼
checkBackendConnection()
    │
    ├─> Backend Available?
    │   │
    │   ├─> YES: Check strad_monitoring_connected
    │   │   │
    │   │   ├─> YES: Load real data
    │   │   │   └─> loadRecentStrads()
    │   │   │       └─> updateKanbanWithRealData()
    │   │   │
    │   │   └─> NO: Use demo/placeholder mode
    │   │
    │   └─> NO: Use demo/placeholder mode
    │
    ▼
Display UI with appropriate mode
```

### Data Flow (When Connected)

```
Backend API
    │
    ▼
GET /api/strads/recent
    │
    ├─> Database Connected?
    │   │
    │   ├─> YES: Query classification_results table
    │   │   └─> Return real strad data
    │   │
    │   └─> NO: Return empty array with message
    │
    ▼
Frontend receives data
    │
    ├─> Group by classification (none/moderate/critical)
    ├─> Update column counts
    └─> Log real data available
```

### Inference Flow (Single Image)

```
User uploads image
    │
    ▼
POST /api/inference (with 'image' field)
    │
    ├─> DL Classifier Available?
    │   │
    │   ├─> YES: Run real classification
    │   │   └─> DLClassifierWrapper.classify_snapshot()
    │   │       └─> Return {classification, confidence, processing_time}
    │   │
    │   └─> NO: Return mock results
    │
    ▼
Display results to user
```

---

## Testing the Integration

### 1. Test Without Backend (Demo Mode)

```cmd
# Just open the HTML file
start docs\index.html
```

**Expected Result:**
- Web app loads normally
- Connection status: ○ Disconnected
- Demo videos and placeholder cards show
- Live inference test at bottom works (mock mode)

### 2. Test With Backend (Connected Mode)

```cmd
# Start the backend
python docs\backend\app.py

# Then open web app
start docs\index.html
```

**Expected Result:**
- Web app loads
- Connection status: ● Connected (if strad_monitoring available)
- Demo videos still work
- Live inference test uses real classifier if model loaded
- Real strad data fetched (if database has records)

### 3. Test Real Classification

```cmd
# Make sure backend is running
python docs\backend\app.py

# In another terminal, test the inference endpoint
python -c "
import requests
files = {'image': open('demo_videos/01_normal_operation.mp4', 'rb')}
response = requests.post('http://localhost:5000/api/inference', files=files)
print(response.json())
"
```

---

## Current Features Status

### ✅ Working Features

**Demo Mode (Always Available):**
- Demo video playback (normal operation, impact scenarios)
- GIF fallback when video fails
- Kanban board with placeholder cards
- Live inference test upload interface
- Modal dialogs for scenario details

**Connected Mode (When Backend Available):**
- Connection status indicator
- Real strad data fetching from database
- Real DL classification on uploaded images
- Snapshot image retrieval
- Classification statistics

### ⚠ Pending Enhancements

**Could Be Added Later:**
- Real strad cards alongside demo cards
- Real-time updates (WebSocket or polling)
- Snapshot gallery view
- Filtering by date range
- Export classification history
- Dashboard charts/graphs

---

## Configuration Requirements

### Backend Requirements

**For Full Functionality:**
1. `system_config.json` must exist in project root
2. Configuration must include:
   - `database_connection_string` (or use SQLite fallback)
   - `model_checkpoint_path` (for DL classifier)
   - `permanent_snapshot_path` (for snapshot storage)

**Minimum for Testing:**
- None! Backend runs in mock mode without configuration
- Shows connection status as disconnected
- Returns placeholder data

### Dependencies

**Backend:**
```
flask
flask-cors
numpy
pillow
```

**Frontend:**
- No additional dependencies (pure JavaScript)
- Works in all modern browsers

---

## API Endpoint Reference

### New Endpoints

**GET /api/strads/recent**
```
Query params:
  - limit: Number of results (default 10)
  - severity: Filter by severity (optional)

Response:
{
  "success": true,
  "data": [
    {
      "strad_id": "SC042",
      "classification": "moderate",
      "confidence": 0.65,
      "snapshot_path": "2024-01-15/SC042_143025.jpg",
      "timestamp": "2024-01-15T14:30:25",
      "has_snapshot": true
    }
  ],
  "count": 10
}
```

**GET /api/snapshot/<strad_id>**
```
Returns: JPEG image or 404 if not found
Example: GET /api/snapshot/SC042
```

**GET /api/strads/stats**
```
Response:
{
  "success": true,
  "stats": {
    "total": 150,
    "none": 120,
    "moderate": 25,
    "critical": 5,
    "last_24h": 48
  }
}
```

### Enhanced Endpoints

**GET /**
```
Response:
{
  "status": "running",
  "service": "Camera Misalignment Detection API",
  "version": "1.0.0",
  "strad_monitoring_connected": true,
  "database_connected": true,
  "classifier_loaded": true
}
```

**POST /api/inference**
```
Accepts:
  Option 1: Single image (strad monitoring mode)
    - FormData with 'image' field
  
  Option 2: Multi-camera (original mode)
    - FormData with 'cam0', 'cam1', 'cam2', 'cam3' fields

Response (Single Image):
{
  "success": true,
  "classification": "moderate",
  "confidence": 0.65,
  "processing_time_ms": 123.4,
  "description": "🟡 MODERATE MISALIGNMENT...",
  "timestamp": "2024-01-15T14:30:25",
  "mode": "real_classifier"  // or "mock"
}
```

---

## Notes

### Demo Presentable Status

This integration is **demo presentable** but not production-ready:

- ✅ All features work in demo mode
- ✅ Graceful fallback when components unavailable
- ✅ Real data integration functional
- ⚠ Official proof of concept approval required
- ⚠ No real-time monitoring dashboard yet
- ⚠ Limited error handling for production scenarios

### Backward Compatibility

All original functionality preserved:
- ✅ Demo videos work without backend
- ✅ Multi-camera inference still supported
- ✅ GIF fallbacks functional
- ✅ Modal dialogs unchanged
- ✅ Existing UI/UX maintained

### Future Enhancements

Possible additions for production:
1. Real-time dashboard with WebSocket updates
2. Historical trends and charts
3. Snapshot gallery with filters
4. User authentication and roles
5. Alert notifications and email integration
6. Mobile-responsive improvements
7. Export to PDF/Excel functionality

---

## Troubleshooting

### "Connection status shows disconnected"

**Possible causes:**
1. Backend not running → Start with `python docs\backend\app.py`
2. Port 5000 in use → Change port in backend and frontend
3. CORS issues → Check flask-cors is installed

### "Backend connected but no real data"

**Possible causes:**
1. Database not connected → Check system_config.json
2. No classifications in database → Run some test classifications first
3. SQLite fallback empty → Populate tests/test.db

### "Inference returns mock results"

**Possible causes:**
1. DL classifier not loaded → Check model_checkpoint_path in config
2. Model file not found → Verify path exists
3. CUDA/GPU issues → Check GPU availability

---

## Summary

The web app now seamlessly integrates with the strad_monitoring system while maintaining full backward compatibility. Users can:

- View demo videos without any backend
- See real strad data when connected
- Test real classifications when model loaded
- Always have a working interface (graceful degradation)

**Status:** Demo presentable and ready for testing!

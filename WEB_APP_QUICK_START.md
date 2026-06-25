# Web App Quick Start Guide
## Strad Carrier Monitoring - Visual Interface

**Last Updated:** 2024  
**Status:** Demo Presentable  
**Location:** `docs/index.html`

---

## 🚀 Quick Start

### Option A: Automatic Launcher (Easiest)

```cmd
cd c:\Users\Miles\Desktop\exp_2
start_web_app.bat
```

This will:
1. Start backend server (port 5000) in new window
2. Start frontend server (port 8000) in new window
3. Open web app in browser at http://localhost:8000

**Keep both server windows open!**

### Option B: Manual Start (3 Steps)

#### Step 1: Start Backend Server

```cmd
cd c:\Users\Miles\Desktop\exp_2
.venv\Scripts\activate
python docs\backend\app.py
```

**Expected:** Backend starts on port 5000. **Keep this terminal open!**

#### Step 2: Start Frontend Server (New Terminal)

```cmd
cd c:\Users\Miles\Desktop\exp_2
.venv\Scripts\activate
python start_frontend_server.py
```

**Expected:** Frontend server starts on port 8000. **Keep this terminal open too!**

#### Step 3: Open in Browser

```cmd
start http://localhost:8000
```

Or manually navigate to: **http://localhost:8000**

### Check Connection Status

Look for connection status in top right corner:
- **● Connected** (green) = Backend available, real data mode
- **○ Disconnected** (red) = Demo mode, placeholder data

---

## 📊 What You'll See

### Kanban Board
- **Normal Operation** (left column) - Properly aligned strads
- **Misaligned - Low Priority** (middle) - Minor issues
- **Misaligned - Critical** (right) - Requires immediate attention

Each card has:
- Strad ID and scenario name
- Metrics (rotation, translation, impact type)
- "View Demo" button → plays video
- "Details" button → shows detailed information

### Demo Videos
- **Normal Operation** - All cameras aligned
- **Impact Scenarios** - Various misalignment events
- **Full Timeline** - Complete sequence with all events

Videos automatically play in modal dialog. Press Escape or click X to close.

### Live Inference Test (Bottom of Page)

Upload an image to test real-time classification:

1. **Drag and drop** an image OR **click to browse**
2. Image preview shows
3. Click **"🚀 Run Inference"**
4. Results show:
   - Classification (none/moderate/critical)
   - Confidence score
   - 6-DOF camera pose
   - Uncertainty estimates

**Connected Mode:** Uses real DL classifier  
**Disconnected Mode:** Returns mock results (still works!)

---

## 🔌 Connection Modes

### Demo Mode (Frontend Only)

**What works:**
- ✅ All demo videos
- ✅ Modal dialogs and details
- ✅ UI navigation
- ✅ Image upload interface

**What doesn't work:**
- ❌ Real data from database
- ❌ Real DL classification
- ❌ Snapshot retrieval
- ❌ API calls (CORS errors in console)

**To use:** 
```cmd
python start_frontend_server.py
# Then open: http://localhost:8000
```

**Why frontend server is needed:**
- Opening `docs\index.html` directly (file://) causes CORS errors
- Browser blocks API calls from file:// to http://localhost:5000
- Serving via HTTP server (http://localhost:8000) fixes CORS issues

### Connected Mode (Backend + Frontend)

**What works:**
- ✅ Everything from demo mode
- ✅ Real data from database (if available)
- ✅ Real DL classification (if model loaded)
- ✅ Live connection status
- ✅ API endpoint access
- ✅ No CORS errors

**To use:** 
```cmd
# Terminal 1: Backend
python docs\backend\app.py

# Terminal 2: Frontend
python start_frontend_server.py

# Browser: http://localhost:8000
```

**Or use the automated launcher:**
```cmd
start_web_app.bat
```

---

## 🧪 Testing the Web App

### Test 1: Demo Videos (Always Works)

1. Click "View Demo" on any card
2. Video should play automatically
3. Press Escape or click X to close

**Expected:** Videos play smoothly, modal opens/closes

### Test 2: Scenario Details (Always Works)

1. Click "Details" on any card
2. Modal shows scenario information
3. Events timeline displays

**Expected:** Detailed information appears without video

### Test 3: Connection Status

**With backend running:**
```
● Strad Monitoring: Connected
```

**Without backend:**
```
○ Strad Monitoring: Disconnected
```

**To verify:** Check top right corner of web app

### Test 4: Live Inference Upload

1. Scroll to bottom: "🔬 Test Live Inference"
2. Drag and drop any image file (JPEG or PNG)
3. Image preview should appear
4. Click "🚀 Run Inference"
5. Wait for results (3-5 seconds)

**Expected Results (Connected):**
```
Classification: moderate
Confidence: 65.0%
Processing Time: 123.4 ms
```

**Expected Results (Disconnected):**
```
Classification: none
Confidence: 75.0%
Processing Time: 45.0 ms
(Mock results - backend not connected)
```

### Test 5: Backend API (Optional)

With backend running, test API directly:

```cmd
# Health check
curl http://localhost:5000/

# Get recent strads
curl http://localhost:5000/api/strads/recent

# Get statistics
curl http://localhost:5000/api/strads/stats

# Check model status
curl http://localhost:5000/api/model/status
```

---

## 🎯 What Data You'll See

### When Database is Empty (Default)

**Kanban Board:**
- Normal Operation: 1 card (placeholder)
- Minor Issues: 2 cards (placeholder)
- Critical Alerts: 2 cards (placeholder)

**API Returns:**
- Recent strads: Empty array
- Statistics: All zeros
- Message: "Database not connected - using placeholder mode"

### When Database Has Records

**Kanban Board:**
- Counts update automatically with real numbers
- Real strad data logged in console (F12)

**API Returns:**
- Recent strads: Array of real classifications
- Statistics: Real counts by severity
- Snapshots available for viewing

**To populate database:**
```cmd
# Run test classifications
python test_single_image.py --synthetic

# Results stored in SQLite (tests/test.db) or SQL Server
```

---

## 🔧 Troubleshooting

### Problem: "Backend won't start"

**Check port 5000:**
```cmd
netstat -ano | findstr :5000
```

**Kill process if needed:**
```cmd
taskkill /PID <process_id> /F
```

**Install dependencies:**
```cmd
pip install flask flask-cors numpy pillow
```

### Problem: "Web app shows disconnected"

**Solutions:**
1. Check **both servers** are running:
   - Backend on port 5000 (terminal should show Flask server)
   - Frontend on port 8000 (terminal should show HTTP server)
2. Check you're accessing **http://localhost:8000** (NOT file://)
3. Refresh web page (F5)
4. Check browser console (F12) for CORS errors

**CORS Errors:**
```
Access to fetch at 'http://localhost:5000' from origin 'file://' has been blocked by CORS policy
```
**Fix:** Use frontend server (http://localhost:8000), don't open file directly!

### Problem: "Videos won't play"

**Solutions:**
1. Check video files exist in `docs/` folder
2. Look for: `01_normal_operation.mp4`, `02_impact_scenario.mp4`
3. GIF fallback should load if MP4 fails
4. Check browser console (F12) for errors

### Problem: "Inference shows mock results when connected"

**This is expected if:**
- DL classifier model not loaded
- Backend shows: "DL Classifier Loaded: False"

**To load real classifier:**
1. Create `system_config.json` in project root
2. Set `model_checkpoint_path` to valid model file
3. Restart backend server

### Problem: "No real strad data shown"

**This is expected if:**
- Database has no records yet
- Backend shows: "Database Connected: False"

**To see real data:**
1. Populate database with test data
2. Run: `python test_sqlite_fallback.py`
3. Or run full orchestrator cycle
4. Refresh web app

---

## 📱 Browser Compatibility

**Tested and working on:**
- ✅ Google Chrome 90+
- ✅ Microsoft Edge 90+
- ✅ Mozilla Firefox 88+

**Features used:**
- Fetch API
- Async/await
- ES6+ JavaScript
- CSS Grid and Flexbox
- HTML5 Video

**Note:** Internet Explorer is NOT supported (use Edge instead)

---

## 🎨 UI Features

### Kanban Board
- Drag scrolling on mobile
- Responsive card layout
- Color-coded by severity
- Badge indicators (Low/Critical/No Issues)

### Video Modal
- Autoplay on open
- Controls for pause/play
- Escape key to close
- Click outside to close
- GIF fallback if video fails

### Upload Interface
- Drag and drop support
- Click to browse
- Image preview
- File type validation (JPEG/PNG)
- Size limit (10MB)
- Remove/clear buttons

### Results Display
- Probability bar chart
- Severity badge (color-coded)
- 6-DOF pose table
- Uncertainty metrics
- Download as JSON
- Reset for new inference

---

## 📋 Keyboard Shortcuts

- **Escape** - Close modal dialog
- **Ctrl+O** - Open file (in browser)
- **F5** - Refresh page
- **F12** - Open developer console
- **Ctrl+C** - Stop backend (in terminal)

---

## 🎓 Learning Resources

### Understand the Code

**Frontend Files:**
- `docs/index.html` - Web page structure
- `docs/script.js` - JavaScript logic
- `docs/styles.css` - Styling

**Backend Files:**
- `docs/backend/app.py` - Flask API server

**Integration:**
- `WEB_APP_INTEGRATION_SUMMARY.md` - Technical details
- `HOW_TO_USE_RIGHT_NOW.md` - Complete system guide

### Key Concepts

**SCENARIOS Object (script.js):**
- Defines all demo scenarios
- Maps video files to scenarios
- Contains event timelines
- Includes metrics and details

**Connection Flow:**
1. Page loads → Check backend
2. Backend available → Load real data
3. Backend unavailable → Demo mode
4. Update UI accordingly

**API Integration:**
- REST endpoints for strad data
- Real-time classification
- Snapshot retrieval
- Statistics aggregation

---

## 🚦 Status Indicators

### Connection Status Colors

| Color | Status | Meaning |
|-------|--------|---------|
| 🟢 Green (●) | Connected | Backend available, real data mode |
| 🔴 Red (○) | Disconnected | Demo mode, placeholder data |

### Severity Badge Colors

| Color | Severity | Action Required |
|-------|----------|-----------------|
| 🟢 Green | None | No issues, operational |
| 🟡 Yellow | Moderate | Monitor, track consecutive |
| 🔴 Red | Critical | Immediate attention needed |

### Priority Badge Colors

| Badge | Meaning |
|-------|---------|
| No Issues | System operating normally |
| Low | Minor misalignment, within tolerance |
| Critical | Major misalignment, action required |

---

## 💡 Tips and Tricks

### For Testing

1. **Use browser console (F12)** to see detailed logs
2. **Check Network tab** to see API requests
3. **Use curl commands** to test backend directly
4. **Monitor backend terminal** for server logs

### For Development

1. **Keep backend running** during frontend changes
2. **Refresh page (F5)** to see frontend updates
3. **Check CORS issues** if API calls fail
4. **Use mock mode** when database unavailable

### For Demo

1. **Start with demo mode** (no backend) to show UI
2. **Then start backend** to show real integration
3. **Upload test image** to show live inference
4. **Open console** to show real data loading

---

## 📞 Support

**For questions or issues:**
1. Check this guide first
2. Review `WEB_APP_INTEGRATION_SUMMARY.md`
3. Check `HOW_TO_USE_RIGHT_NOW.md`
4. Look at backend terminal for error messages
5. Check browser console (F12) for client errors

**Common Questions:**

**Q: Can I use the web app without the backend?**  
A: Yes! All demo videos and UI features work. Live inference shows mock results.

**Q: Do I need SQL Server?**  
A: No! Backend uses SQLite fallback with test data in `tests/test.db`.

**Q: Do I need the DL model file?**  
A: No! Backend uses mock classification if model not available.

**Q: Can I deploy this to production?**  
A: Not yet! This is demo presentable. Requires official POC approval first.

---

## ✨ Summary

The web app provides a visual interface for strad carrier monitoring with:
- ✅ Demo videos of normal and impact scenarios
- ✅ Live inference testing with image upload
- ✅ Real data integration when backend connected
- ✅ Graceful fallback to demo mode when offline
- ✅ Clean, responsive UI with kanban board
- ✅ Modal dialogs for detailed information

**Status:** Demo presentable and ready for testing!  
**Next Steps:** Official POC and production deployment approval

# Web App Setup - Issue Fixed

**Date:** 2024  
**Issue:** Web app wouldn't connect to backend when opening `index.html` directly  
**Root Cause:** CORS (Cross-Origin Resource Sharing) restrictions  
**Solution:** Added frontend HTTP server on port 8000

---

## What Was Wrong

### Original Setup (Didn't Work)
```
Browser opens: file:///C:/Users/Miles/Desktop/exp_2/docs/index.html
               ↓
         Tries to fetch: http://localhost:5000/api/...
               ↓
         ❌ BLOCKED by CORS policy
```

**Error in Browser Console:**
```
Access to fetch at 'http://localhost:5000/api/strads/recent' 
from origin 'file://' has been blocked by CORS policy: 
Cross origin requests are only supported for protocol schemes: 
http, data, chrome, chrome-extension, chrome-untrusted, https.
```

### Why This Happened

**CORS Security Policy:**
- Browsers block requests from `file://` to `http://`
- This is a security feature to prevent malicious local files from accessing web services
- The backend (Flask) runs on `http://localhost:5000`
- The frontend opened as `file://` path
- Browser says: "No way! file:// can't talk to http://"

---

## The Solution

### New Setup (Works!)
```
Browser opens: http://localhost:8000
               ↓
    Frontend Server (port 8000) serves: index.html, script.js, styles.css
               ↓
         Frontend fetches: http://localhost:5000/api/...
               ↓
         ✅ ALLOWED (both are HTTP origins)
```

### Two Servers Architecture

**Backend Server (port 5000):**
- Flask API
- Strad monitoring integration
- Database connections
- DL classification

**Frontend Server (port 8000):**
- Simple HTTP file server
- Serves static files (HTML, CSS, JS)
- Enables proper CORS
- Same origin policy satisfied

---

## What Was Added

### 1. Frontend Server Script
**File:** `start_frontend_server.py`

```python
# Simple HTTP server for serving static files
# Runs on port 8000
# Serves files from docs/ directory
```

**Features:**
- Serves files from `docs/` directory
- Adds CORS headers
- Port 8000 by default
- Graceful shutdown with Ctrl+C

### 2. Automated Launcher
**File:** `start_web_app.bat`

**What it does:**
1. Activates virtual environment
2. Starts backend server (port 5000) in new window
3. Starts frontend server (port 8000) in new window
4. Opens browser to `http://localhost:8000`

**Usage:**
```cmd
start_web_app.bat
```

### 3. Updated Documentation

**Files Updated:**
- `WEB_APP_QUICK_START.md` - Complete rewrite with correct instructions
- `HOW_TO_USE_RIGHT_NOW.md` - Added two-server setup explanation
- `docs/README_WEB_APP.md` - New quick reference guide

**Key Changes:**
- Added explanation of why two servers are needed
- Added CORS troubleshooting section
- Updated all "open index.html" instructions to use frontend server
- Added automated launcher instructions

---

## How to Use Now

### Quick Method (Recommended)
```cmd
cd c:\Users\Miles\Desktop\exp_2
start_web_app.bat
```

This opens 3 windows:
1. Launcher (can close after startup)
2. Backend server (keep open)
3. Frontend server (keep open)

Browser opens to: `http://localhost:8000`

### Manual Method
**Terminal 1:**
```cmd
python docs\backend\app.py
```

**Terminal 2:**
```cmd
python start_frontend_server.py
```

**Browser:**
```
http://localhost:8000
```

---

## Testing the Fix

### Before Fix (Broken)
1. Open `docs\index.html` directly
2. Browser shows: `file:///C:/...`
3. Connection status: ○ Disconnected (red)
4. Console shows CORS errors
5. No API calls work

### After Fix (Working)
1. Run `start_web_app.bat` or both servers
2. Browser shows: `http://localhost:8000`
3. Connection status: ● Connected (green)
4. No CORS errors in console
5. API calls work perfectly

### Quick Test
```cmd
# Start both servers
start_web_app.bat

# Open browser to http://localhost:8000
# Check top right corner for green dot (●)
# Press F12, check console for:
#   "Backend connection: {status: 'running', ...}"
#   No CORS errors
```

---

## Technical Details

### CORS Headers

**Frontend Server Response:**
```http
Access-Control-Allow-Origin: *
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type
```

**Backend Server (Flask-CORS):**
```python
from flask_cors import CORS
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
```

### Same-Origin Policy

**Allowed:**
```
http://localhost:8000  →  http://localhost:5000  ✅
(HTTP to HTTP, different ports = OK with CORS headers)
```

**Blocked:**
```
file:///path/to/file  →  http://localhost:5000  ❌
(file:// to HTTP = BLOCKED by browser)
```

### Why This Architecture?

**Separation of Concerns:**
- Backend = API logic, data processing
- Frontend = Static file serving, HTTP hosting

**Security:**
- CORS properly configured
- Same-origin policy respected
- No file:// protocol issues

**Development:**
- Backend can restart independently
- Frontend files can update without affecting API
- Each server has single responsibility

**Production Ready:**
- Same architecture works in production
- Backend → Flask/Gunicorn
- Frontend → Nginx/Apache
- Already using HTTP servers for both

---

## Common Issues and Solutions

### Issue 1: "Connection still shows disconnected"

**Check:**
```cmd
# Backend running?
netstat -ano | findstr :5000

# Frontend running?
netstat -ano | findstr :8000

# Correct URL?
# Should be: http://localhost:8000
# NOT: file:///...
```

### Issue 2: "Port already in use"

**Find process:**
```cmd
netstat -ano | findstr :8000
```

**Kill process:**
```cmd
taskkill /PID <process_id> /F
```

### Issue 3: "Backend can't find modules"

**Solution:**
```cmd
# Make sure virtual environment is activated
.venv\Scripts\activate

# Install dependencies
pip install flask flask-cors numpy pillow
```

### Issue 4: "start_web_app.bat doesn't work"

**Manual alternative:**
```cmd
# Terminal 1
.venv\Scripts\activate
python docs\backend\app.py

# Terminal 2
.venv\Scripts\activate
python start_frontend_server.py

# Browser
start http://localhost:8000
```

---

## Files Added

1. **`start_frontend_server.py`**
   - Frontend HTTP server
   - Port 8000
   - Serves docs/ directory

2. **`start_web_app.bat`**
   - Automated launcher
   - Starts both servers
   - Opens browser

3. **`docs/README_WEB_APP.md`**
   - Quick reference guide
   - CORS explanation
   - Troubleshooting

4. **`WEB_APP_SETUP_FIXED.md`** (this file)
   - Issue documentation
   - Solution explanation
   - Before/after comparison

5. **`test_web_app_backend.py`**
   - Backend API testing script
   - Tests all endpoints
   - Verifies responses

## Files Updated

1. **`WEB_APP_QUICK_START.md`**
   - Rewritten with two-server setup
   - CORS explanation added
   - Automated launcher instructions

2. **`HOW_TO_USE_RIGHT_NOW.md`**
   - Web app section rewritten
   - Frontend server added
   - Troubleshooting expanded

3. **`start_web_app.bat`**
   - Added frontend server startup
   - Opens browser to http://localhost:8000

---

## Summary

**Problem:** CORS blocked `file://` → `http://` requests  
**Solution:** Added frontend HTTP server on port 8000  
**Result:** Web app now connects to backend successfully  

**Before:**
- ❌ file:// → CORS blocked
- ❌ Connection failed
- ❌ API calls didn't work

**After:**
- ✅ http://localhost:8000 → http://localhost:5000
- ✅ Connection successful
- ✅ All API calls work
- ✅ Green dot indicator
- ✅ Real data integration functional

---

## Next Steps

1. **Run the web app:**
   ```cmd
   start_web_app.bat
   ```

2. **Check connection status:**
   - Look for green dot (●) in top right
   - Should say "Connected"

3. **Test features:**
   - View demo videos
   - Upload image for live inference
   - Check browser console (F12) for logs

4. **Verify API calls:**
   ```cmd
   curl http://localhost:5000/
   curl http://localhost:5000/api/strads/stats
   ```

**Status:** ✅ Web app setup fixed and fully functional!

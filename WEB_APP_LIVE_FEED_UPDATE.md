# Web App Update — Live Monitoring Feed & Real Image Support

## Summary

Updated the web app to display real screenshots from monitoring cycles (or augmented dataset samples as fallback), show dynamic strad pool counts, and provide detailed per-strad monitoring info. All existing functionality preserved — nothing removed.

---

## New Features

### 1. Live Monitoring Feed Section
A new section below the existing content displays a grid of real camera screenshots.

- **Priority**: Live critical images from `permanent_snapshots/` → augmented dataset fallback
- **Filters**: Source (live / augmented / auto) and severity (none / moderate / critical)
- **Per-card info**: Strad ID, severity badge (🔴🟡🟢), confidence %, timestamp, source label
- **Actions per card**: "Details" button, "Copy IP" button

### 2. Dynamic Active Strad Count
The "Active Cameras" stat card now shows the real available strad count:
- Total strads from `ip_addresses.json` (e.g., 135)
- Minus critical exclusions from `monitoring_state.json`
- Displays result (e.g., "132") with tooltip showing the breakdown

### 3. Strad Details Modal
Clicking "Details" on any strad card opens a modal showing:
- **Strad ID** and **IP address** (with copy-to-clipboard button)
- **Last checked** timestamp
- **Status**: Active or Critical (excluded from cycling)
- **Critical info**: When marked critical, reason
- **Classification history**: Table of last 10 results (time, severity, confidence)

### 4. Copy IP Address
Each strad card has a "Copy IP" button that copies the camera's IP address to clipboard for quick access (e.g., pasting into a browser to check the live feed manually).

---

## New Backend Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/live/images` | Returns image list with metadata (live + augmented) |
| GET | `/api/live/image/<filename>` | Serves actual JPEG files from disk |
| GET | `/api/live/active-camera-count` | Returns total/excluded/available strad counts |
| GET | `/api/live/strad-details/<strad_id>` | Returns IP, history, critical status |

### `/api/live/images` Query Parameters
- `source`: `auto` (default), `live`, or `augmented`
- `limit`: Number of images (default 10)
- `severity`: Filter by `none`, `moderate`, or `critical`

### Image Source Priority (auto mode)
1. Check `data/monitoring_state.json` for results with snapshot paths
2. Scan `permanent_snapshots/` for critical photos
3. Fall back to `SCFootage_augmented/` or `video_data/` or `test_data/` directories

---

## Files Modified

| File | Change |
|------|--------|
| `docs/backend/app.py` | Added 4 new endpoints + 2 helper functions (nothing removed) |
| `docs/index.html` | Added live monitoring section, strad detail modal, dynamic stat card |
| `docs/script.js` | Added live image loading, detail modal, copy IP, filter handlers |
| `docs/styles.css` | Added styles for live image grid, cards, detail modal |

---

## Files NOT Modified (preserved as-is)

- Inference engine (`/api/inference` endpoint) ✓
- Multi-camera inference mode ✓  
- Single-image classifier mode ✓
- Demo video modals and scenario data ✓
- Kanban board with placeholder cards ✓
- Upload/drag-drop interface ✓
- Results display (probability, severity, 6-DOF pose, uncertainty) ✓
- Model status endpoint ✓
- All existing CSS ✓

---

## How It Works

```
Frontend (localhost:8080)                Backend (localhost:5000)
─────────────────────────               ──────────────────────────
Page loads
  │
  ├─ GET /api/live/active-camera-count ──► IPAddressLoader (total)
  │                                        LocalStateStore (exclusions)
  │                                        ◄── {available: 132}
  │
  ├─ GET /api/live/images?source=auto ───► Check monitoring_state.json
  │                                        Check permanent_snapshots/
  │                                        Fallback: SCFootage_augmented/
  │                                        ◄── [{strad_id, filename, ...}]
  │
  ├─ Render image grid with cards
  │    Each card: <img src="/api/live/image/{filename}">
  │
  └─ User clicks "Details" on SC087 ────► GET /api/live/strad-details/SC087
                                           ◄── {ip, history, critical_info}
       └─ Modal shows full detail
```

---

## Running the Preview

**Terminal 1** — Backend:
```bash
cd docs/backend
python app.py
```

**Terminal 2** — Frontend:
```bash
cd docs
python -m http.server 8080
```

Open: **http://localhost:8080**

---

## Data Sources

| Source | Directory | Content |
|--------|-----------|---------|
| Live critical photos | `permanent_snapshots/` (from config) | Screenshots of critical strads |
| Monitoring results | `data/monitoring_state.json` | Classification history, check times |
| Augmented dataset | `SCFootage_augmented/` (if exists) | Training data images for fallback |
| IP mappings | `config/ip_addresses.json` | SC# → IP address lookup |

---

## Graceful Degradation

| Condition | Behavior |
|-----------|----------|
| Backend not running | Page loads normally, live section shows "Backend not available" |
| No live images yet | Falls back to augmented dataset |
| No augmented dataset | Shows "No images available" message |
| No monitoring_state.json | Active count defaults to 135, details show "Never checked" |
| No ip_addresses.json | Active count defaults to 135 |

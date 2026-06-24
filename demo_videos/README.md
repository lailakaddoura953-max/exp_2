# Camera Misalignment Detection Demo Videos

This directory contains demo videos showcasing the Camera Misalignment Detection System in action.

## Videos

### 1. Normal Operation (`01_normal_operation`)

**Duration**: ~5 seconds (150 frames @ 30 FPS)  
**Size**: 17 MB (MP4) / 6.6 MB (GIF)

Shows the system operating with perfectly aligned cameras:
- ✅ All 4 cameras displaying synchronized footage
- ✅ Diamond alignment markers properly connected at center
- ✅ Feature detection tracking points (green circles)
- ✅ Smooth 60-70 FPS processing
- ✅ No misalignment alerts

**What to look for:**
- The colored diamond triangles (cyan, yellow, magenta, green) connect perfectly at the center junction
- Green feature points being detected and tracked across all cameras
- Synthetic 3D road scene with moving trucks from driver's perspective

---

### 2. Impact Scenario (`02_impact_scenario`)

**Duration**: ~12 seconds (350 frames @ 30 FPS)  
**Size**: 29.4 MB (MP4) / 15.5 MB (GIF)

Demonstrates synthetic impact events causing camera misalignment:

#### Timeline of Events:

**Frame 50** (Minor Impact - Camera 1)
- ⚡ Flash effect with "POTHOLE HIT!" warning
- Small camera shift (rotation ±2°, translation ±15px)
- Diamond stays mostly aligned
- ✅ Within acceptable tolerance - no alert

**Frame 120** (MAJOR Impact - Camera 2)  
- ⚡ Flash effect with "DEBRIS HIT!" warning
- Large camera shift (rotation ±8°, translation ±60px)
- 💔 Diamond breaks apart visibly
- ⚠️ **System triggers ALERT**
- Persistent "⚠ MISALIGNED" warning shown

**Frame 200** (Minor Impact - Camera 0)
- ⚡ Flash effect with "WIND HIT!" warning  
- Small camera shift
- Diamond stays mostly aligned
- ✅ Within acceptable tolerance - no alert

**Frame 300** (MAJOR Impact - Camera 3)
- ⚡ Flash effect with "WIND HIT!" warning
- Large camera shift
- 💔 Diamond breaks apart visibly
- ⚠️ **System triggers ALERT**
- Persistent "⚠ MISALIGNED" warning shown

**What to look for:**
- Flash effects when impacts occur (frames 50, 120, 200, 300)
- Diamond alignment marker breaking apart during major impacts
- Red "⚠ MISALIGNED" text appearing on affected cameras after major impacts
- Feature tracking continues working even when cameras are misaligned
- Console alerts would be triggered for major impacts (frames 120 & 300)

---

## File Formats

### MP4 (Recommended)
- **Best quality** - original 1280x960 resolution
- **Full frame rate** - 30 FPS
- **Larger file size**
- Best for: Presentations, detailed analysis, high-quality demos

### GIF (Web-friendly)
- **Web compatible** - works everywhere (GitHub, docs, etc.)
- **Reduced quality** - 640x480 resolution, 10 FPS
- **Smaller file size**
- Best for: README files, quick previews, web documentation

---

## System Capabilities Demonstrated

### ✅ Real-time Processing
- 60-70 FPS with 4-camera grid display
- Feature extraction on all cameras simultaneously
- Synchronized frame acquisition

### ✅ Visual Alignment Verification
- Diamond marker system (4 colored triangles)
- Instant visual feedback when cameras shift
- Clear distinction between aligned and misaligned states

### ✅ Impact Detection
- Multiple severity levels (minor vs major)
- Different impact types (debris, wind, pothole)
- Smooth impact transitions with visual effects

### ✅ Feature Tracking
- ORB feature detection (green circles)
- Tracks 100+ features per camera
- Continues working during misalignment

### ✅ Alert System
- Threshold-based detection
- Visual warnings on affected cameras
- Console alerts for monitoring

---

## Usage in Documentation

### Markdown (GitHub README)
```markdown
![Normal Operation](demo_videos/01_normal_operation.gif)
![Impact Scenario](demo_videos/02_impact_scenario.gif)
```

### HTML
```html
<video controls width="100%">
  <source src="demo_videos/01_normal_operation.mp4" type="video/mp4">
</video>
```

---

## Technical Details

**Frame Resolution**: 1280x960 (2x2 grid of 640x480 camera feeds)  
**Recording FPS**: 30  
**Feature Detector**: ORB (Oriented FAST and Rotated BRIEF)  
**Alignment Marker**: 4-triangle diamond (120px size per triangle)  
**Impact Physics**: Rotation + translation transforms with easing

**Camera Layout**:
```
┌──────────┬──────────┐
│ Camera 0 │ Camera 1 │  
│  (Cyan)  │ (Yellow) │
├──────────┼──────────┤
│ Camera 2 │ Camera 3 │
│(Magenta) │  (Green) │
└──────────┴──────────┘
```

---

## Regenerating Videos

To record new demo videos:

```bash
# Normal operation (no impacts)
python record_demo.py  # Records both scenarios

# Or record individual scenarios
python -c "from record_demo import record_scenario; record_scenario('normal', 'Normal operation', 150, False)"
python -c "from record_demo import record_scenario; record_scenario('impact', 'Impact scenario', 350, True)"
```

To convert to GIF:

```bash
python convert_to_gif.py
```

---

**Generated**: 2026-06-19  
**System Version**: Phase 10 Complete (398/398 tests passing)

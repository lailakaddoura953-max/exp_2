# Design Document: GitHub Pages Web Application

## Overview

The GitHub Pages Web Application is a standalone static website that showcases the Camera Misalignment Detection System through interactive demonstrations. The application is built entirely with HTML, CSS, and JavaScript—no frameworks, no build process, no dependencies on the main Python/C++ system. It lives in the `docs/` directory and displays pre-recorded demo videos in an interactive Kanban-style interface.

**Key Design Principles:**
- **Zero Dependencies**: Pure HTML/CSS/JavaScript with no external libraries
- **Static Asset Delivery**: All videos and resources served as static files
- **Separation of Concerns**: Complete isolation from the main codebase
- **Progressive Enhancement**: Works without JavaScript for basic content viewing
- **Mobile-First Responsive**: Adapts from 320px to 1920px viewports

## Architecture

### High-Level Structure

```
docs/
├── index.html          # Main HTML structure
├── styles.css          # All styling (CSS variables, layouts, components)
├── script.js           # Interactive behavior (modal, video loading)
├── 01_normal_operation.mp4
├── 01_normal_operation.gif
├── 02_impact_scenario.mp4
└── 02_impact_scenario.gif
```

### Page Load Sequence

1. Browser requests `index.html` from GitHub Pages
2. HTML structure renders immediately (header, stats, Kanban board, cards)
3. CSS loads and applies styling (gradients, shadows, responsive layout)
4. JavaScript loads and attaches event handlers
5. Videos load **only** when user clicks "View Demo" (on-demand loading)

### Technology Stack

- **HTML5**: Semantic structure, video element, modal overlay
- **CSS3**: Grid/Flexbox layouts, CSS variables, animations, media queries
- **Vanilla JavaScript**: DOM manipulation, event handling, modal control
- **GitHub Pages**: Static hosting from `docs/` directory via HTTPS


## Components and Interfaces

### 1. Header Component

**Purpose**: Display branding, system title, and test status badges

**HTML Structure**:
```html
<header class="header">
  <div class="container">
    <div class="header-content">
      <div class="logo">
        <svg class="icon-truck"><!-- Truck icon --></svg>
        <h1>Truck View: Camera Alignment Check</h1>
      </div>
      <div class="system-info">
        <span class="badge badge-success">398/398 Tests Passing</span>
        <span class="badge badge-info">Phase 10 Complete</span>
      </div>
    </div>
  </div>
</header>
```

**CSS Classes**:
- `.header`: Sticky positioned, white background, shadow
- `.logo`: Flex container with truck icon and title
- `.system-info`: Badge container with success/info styling

**Behavior**: Sticky to viewport top, collapses to single column on mobile


### 2. Stats Section Component

**Purpose**: Display key system metrics in visual cards

**HTML Structure**:
```html
<section class="stats-section">
  <div class="stat-card">
    <div class="stat-icon">📹</div>
    <div class="stat-content">
      <div class="stat-value">4</div>
      <div class="stat-label">Active Cameras</div>
    </div>
  </div>
  <!-- 3 more cards: FPS, Features, Diamond -->
</section>
```

**Data Displayed**:
- **Cameras**: 4 active cameras
- **FPS**: 60-70 processing speed
- **Features**: 100+ per camera
- **Alignment**: Diamond marker system

**CSS Layout**: Flexbox with wrap, 4 cards in row on desktop, stacked on mobile


### 3. Kanban Board Component

**Purpose**: Organize scenario cards by operational status

**HTML Structure**:
```html
<section class="kanban-board">
  <div class="kanban-column">
    <div class="column-header status-normal">
      <span class="status-icon">✓</span>
      <h2>Normal Operation</h2>
      <span class="count">1</span>
    </div>
    <div class="column-content">
      <!-- Scenario cards -->
    </div>
  </div>
  <!-- 2 more columns: Warning, Critical -->
</section>
```

**Three Columns**:
1. **Normal Operation** (Green): Aligned cameras, no issues
2. **Misaligned - Low Priority** (Yellow): Minor shifts, within tolerance
3. **Misaligned - Critical** (Red): Major misalignment, alerts triggered

**CSS Layout**: Flexbox with horizontal scroll on desktop, vertical stack on mobile


### 4. Scenario Card Component

**Purpose**: Display individual camera alignment scenarios with action buttons

**HTML Structure**:
```html
<div class="scenario-card" data-scenario="normal">
  <div class="card-header">
    <h3>Aligned Cameras</h3>
    <span class="priority-badge priority-none">No Issues</span>
  </div>
  <div class="card-body">
    <p class="description">All 4 cameras properly aligned. Diamond markers connected.</p>
    <div class="metrics">
      <div class="metric">
        <span class="metric-label">Status:</span>
        <span class="metric-value status-ok">✓ Operational</span>
      </div>
      <!-- More metrics -->
    </div>
  </div>
  <div class="card-actions">
    <button class="btn btn-primary" onclick="viewScenario('normal')">▶ View Demo</button>
    <button class="btn btn-secondary" onclick="showDetails('normal')">Details</button>
  </div>
</div>
```

**Data Attributes**: `data-scenario` identifies which scenario/video to load

**Priority Badges**:
- `priority-none`: Green, for aligned cameras
- `priority-low`: Yellow, for minor misalignment
- `priority-critical`: Red, for major misalignment


### 5. Video Modal Component

**Purpose**: Display demo videos in fullscreen overlay with scenario details

**HTML Structure**:
```html
<div id="videoModal" class="modal">
  <div class="modal-content">
    <div class="modal-header">
      <h2 id="modalTitle">Scenario Playback</h2>
      <button class="modal-close" onclick="closeModal()">&times;</button>
    </div>
    <div class="modal-body">
      <div id="videoContainer" class="video-container">
        <!-- Video element injected by JavaScript -->
      </div>
      <div id="scenarioInfo" class="scenario-info">
        <!-- Scenario details injected by JavaScript -->
      </div>
    </div>
  </div>
</div>
```

**Modal Behavior**:
- Hidden by default (`display: none`)
- Activated via `.active` class (`display: flex`)
- Closes via: close button, outside click, or Escape key
- Video element created dynamically on open, destroyed on close


## Data Models

### Scenario Data Structure

Each scenario is defined as a JavaScript object containing:

```javascript
const SCENARIOS = {
  'normal': {
    title: 'Normal Operation - Aligned Cameras',
    videoFile: '01_normal_operation.mp4',
    gifFallback: '01_normal_operation.gif',
    description: 'All 4 cameras properly aligned with diamond markers connected.',
    details: {
      duration: '~5 seconds (150 frames)',
      alignment: '100% aligned',
      alerts: 'None',
      features: '100+ features per camera',
    }
  },
  'full-timeline': {
    title: 'Complete Impact Scenario Timeline',
    videoFile: '02_impact_scenario.mp4',
    gifFallback: '02_impact_scenario.gif',
    description: 'Full sequence showing all impact events.',
    events: [
      { frame: 50, type: 'Pothole', camera: 1, severity: 'minor' },
      { frame: 120, type: 'Debris', camera: 2, severity: 'critical' },
      { frame: 200, type: 'Wind', camera: 0, severity: 'minor' },
      { frame: 300, type: 'Wind', camera: 3, severity: 'critical' }
    ]
  },
  // ... more scenarios
};
```


### Scenario-to-Video Mapping

| Scenario ID | Video File | Description |
|-------------|------------|-------------|
| `normal` | `01_normal_operation.mp4` | Perfectly aligned cameras, no impacts |
| `minor-1` | `02_impact_scenario.mp4` | Frame 50: Camera 1 pothole (minor) |
| `minor-2` | `02_impact_scenario.mp4` | Frame 200: Camera 0 wind (minor) |
| `critical-1` | `02_impact_scenario.mp4` | Frame 120: Camera 2 debris (critical) |
| `critical-2` | `02_impact_scenario.mp4` | Frame 300: Camera 3 wind (critical) |
| `full-timeline` | `02_impact_scenario.mp4` | All 4 impact events in sequence |

**Note**: Multiple scenarios map to the same video file but show different event details in the modal.

### Event Timeline Structure

For impact scenarios, events are defined as:

```javascript
{
  frame: 120,              // Frame number when impact occurs
  type: 'Debris',          // Impact type (Pothole, Debris, Wind)
  camera: 2,               // Camera index (0-3)
  severity: 'critical',    // 'minor' or 'critical'
  rotation: '±8°',         // Rotation angle
  translation: '±60px',    // Translation distance
  alert: true              // Whether system triggers alert
}
```


## JavaScript Functions

### Core Functions

#### `viewScenario(scenarioId)`

**Purpose**: Open modal and load video for specified scenario

**Parameters**:
- `scenarioId` (string): Scenario identifier ('normal', 'critical-1', etc.)

**Logic**:
1. Look up scenario data from `SCENARIOS` object
2. Create `<video>` element dynamically
3. Set video source to MP4 file
4. Set video attributes: `controls`, `autoplay`, `width="100%"`
5. Inject video into `#videoContainer`
6. Update modal title with scenario title
7. Inject scenario details into `#scenarioInfo`
8. Add `.active` class to modal to display it
9. Focus on modal for accessibility

**Error Handling**:
- If video fails to load, attempt to load GIF fallback
- If GIF also fails, display error message

**Example**:
```javascript
function viewScenario(scenarioId) {
  const scenario = SCENARIOS[scenarioId];
  const modal = document.getElementById('videoModal');
  const videoContainer = document.getElementById('videoContainer');
  const modalTitle = document.getElementById('modalTitle');
  
  // Create video element
  const video = document.createElement('video');
  video.src = scenario.videoFile;
  video.controls = true;
  video.autoplay = true;
  video.style.width = '100%';
  
  // Handle video load error
  video.onerror = () => loadGifFallback(scenario.gifFallback);
  
  // Inject video and show modal
  videoContainer.innerHTML = '';
  videoContainer.appendChild(video);
  modalTitle.textContent = scenario.title;
  renderScenarioDetails(scenario);
  modal.classList.add('active');
}
```


#### `closeModal()`

**Purpose**: Close video modal and clean up resources

**Logic**:
1. Get modal element
2. Remove `.active` class to hide modal
3. Get video container
4. Pause video if playing
5. Clear video container innerHTML (destroys video element)
6. Clear scenario info innerHTML

**Why Clean Up**:
- Prevents videos from playing in background
- Frees memory by destroying video element
- Ensures fresh state for next modal open

**Example**:
```javascript
function closeModal() {
  const modal = document.getElementById('videoModal');
  const videoContainer = document.getElementById('videoContainer');
  const scenarioInfo = document.getElementById('scenarioInfo');
  
  // Pause and remove video
  const video = videoContainer.querySelector('video');
  if (video) {
    video.pause();
  }
  
  // Clear content and hide modal
  videoContainer.innerHTML = '';
  scenarioInfo.innerHTML = '';
  modal.classList.remove('active');
}
```


#### `showDetails(scenarioId)`

**Purpose**: Display detailed scenario information in modal without video

**Parameters**:
- `scenarioId` (string): Scenario identifier

**Logic**:
1. Look up scenario data
2. Build HTML content with detailed metrics and event timeline
3. Inject into modal without video element
4. Show modal

**Use Case**: User clicks "Details" button instead of "View Demo"

#### `renderScenarioDetails(scenario)`

**Purpose**: Generate HTML for scenario information panel

**Returns**: HTML string containing scenario details

**Content Includes**:
- Description paragraph
- Duration and frame count
- Alignment status
- For impact scenarios: event timeline with frame numbers
- System response indicators (alerts triggered, etc.)

**Example Output**:
```html
<h3>Scenario Details</h3>
<p>Full sequence showing all impact events in real-time.</p>
<h4>Timeline of Events:</h4>
<ul>
  <li><strong>Frame 50</strong>: Camera 1 - Pothole (Minor) ✓ No alert</li>
  <li><strong>Frame 120</strong>: Camera 2 - Debris (Critical) ⚠️ ALERT</li>
  ...
</ul>
```


#### `loadGifFallback(gifFile)`

**Purpose**: Load GIF version when MP4 fails

**Parameters**:
- `gifFile` (string): Path to GIF fallback

**Logic**:
1. Create `<img>` element
2. Set `src` to GIF file path
3. Set `style.width = '100%'`
4. Inject into video container
5. Display notice: "Video unavailable, showing GIF version"

### Event Handlers

#### Modal Close Events

```javascript
// Close button click
document.querySelector('.modal-close').addEventListener('click', closeModal);

// Click outside modal content
document.getElementById('videoModal').addEventListener('click', (e) => {
  if (e.target.id === 'videoModal') {
    closeModal();
  }
});

// Escape key press
document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const modal = document.getElementById('videoModal');
    if (modal.classList.contains('active')) {
      closeModal();
    }
  }
});
```


## Video Loading Strategy

### On-Demand Loading

**Problem**: Video files are large (17-29 MB). Loading all videos on page load would be slow.

**Solution**: Lazy loading - videos only load when user clicks "View Demo"

**Implementation**:
1. Page loads with no `<video>` elements in DOM
2. User clicks "View Demo" button
3. JavaScript creates `<video>` element dynamically
4. Browser begins downloading video file
5. Video plays as soon as enough data is buffered
6. When modal closes, video element is destroyed

**Benefits**:
- Faster initial page load
- Reduced bandwidth for users who don't watch videos
- Only requested videos download

### MP4 → GIF Fallback Strategy

**Primary**: MP4 files (high quality, smaller file size with H.264 compression)

**Fallback**: GIF files (universal compatibility, larger size, lower quality)

**Decision Flow**:
```
User clicks "View Demo"
  ↓
Try to load MP4
  ↓
MP4 loads successfully? → Play video
  ↓ (if error)
Catch video.onerror event
  ↓
Load GIF as <img> instead
  ↓
Display: "Showing GIF fallback"
```

**When Fallback Activates**:
- Browser doesn't support MP4/H.264 codec
- File not found (404 error)
- Network interruption during load
- CORS or permission issues


### Video Preloading Attributes

Videos use `preload="none"` to prevent automatic downloading:

```javascript
video.preload = 'none';  // Don't download until user hits play
```

However, when created via JavaScript on button click, the video starts loading immediately, which is desired behavior.

### Video Format Details

**MP4 Files**:
- Container: MP4
- Codec: H.264 (AVC)
- Resolution: 1280x960 (4-camera grid)
- Frame Rate: 30 FPS
- File Size: 17-29 MB
- Compatibility: ~95% of browsers

**GIF Files**:
- Resolution: 640x480 (reduced)
- Frame Rate: 10 FPS (reduced)
- File Size: 6.6-15.5 MB
- Compatibility: 100% of browsers


## File Organization

### Directory Structure

```
docs/                                    # GitHub Pages serves from this directory
├── index.html                           # Main HTML page
├── styles.css                           # All CSS styling
├── script.js                            # JavaScript behavior
├── 01_normal_operation.mp4              # Normal scenario video
├── 01_normal_operation.gif              # Normal scenario fallback
├── 02_impact_scenario.mp4               # Impact scenario video
└── 02_impact_scenario.gif               # Impact scenario fallback
```

### File References

All file references use **relative paths** from the `docs/` directory:

```javascript
// In script.js
videoFile: '01_normal_operation.mp4'    // Relative to docs/
gifFallback: '01_normal_operation.gif'   // Relative to docs/
```

```html
<!-- In index.html -->
<link rel="stylesheet" href="styles.css">
<script src="script.js"></script>
```

**Why Relative Paths**:
- Works both locally (file://) and on GitHub Pages (https://)
- No hardcoded domains or absolute paths
- Portable across different hosting environments


### Copying Videos from demo_videos/

Videos are copied (not moved) from `demo_videos/` to `docs/`:

```bash
# From project root
cp demo_videos/01_normal_operation.mp4 docs/
cp demo_videos/01_normal_operation.gif docs/
cp demo_videos/02_impact_scenario.mp4 docs/
cp demo_videos/02_impact_scenario.gif docs/
```

**Rationale**:
- Keeps original videos in `demo_videos/` for the main system
- Duplicates to `docs/` so GitHub Pages can serve them
- Total size: ~68 MB (4 files)
- GitHub Pages limit: 1 GB per repository (well within limit)

### Asset Loading Order

1. **Critical Path**: HTML → CSS (render immediately)
2. **Non-blocking**: JavaScript (defer or async)
3. **On-demand**: Videos (only when user clicks)

This ensures fast initial page render with interactive functionality loading progressively.


## Deployment Approach

### GitHub Pages Configuration

**Step 1: Enable GitHub Pages**
1. Go to repository Settings
2. Navigate to Pages section
3. Under "Source", select branch: `main` (or `master`)
4. Under "Folder", select `/docs`
5. Click Save

**Step 2: Wait for Deployment**
- GitHub Actions automatically builds and deploys
- Check Actions tab for deployment status
- Deployment typically takes 1-2 minutes

**Step 3: Access the Site**
- URL: `https://[username].github.io/[repository-name]/`
- Example: `https://johndoe.github.io/experimenting/`

### Local Testing Before Deployment

**Option 1: Simple Python Server**
```bash
cd docs
python -m http.server 8000
# Visit: http://localhost:8000
```

**Option 2: Live Server (VS Code Extension)**
1. Install "Live Server" extension
2. Right-click `index.html`
3. Select "Open with Live Server"

**Option 3: Direct File Open**
- Open `docs/index.html` in browser
- Works, but videos may have CORS issues
- Prefer local server for accurate testing


### Deployment Verification Checklist

After deployment, verify:

- [ ] **Page loads**: Site accessible at GitHub Pages URL
- [ ] **Styling applied**: CSS loaded correctly (purple gradient background, cards display)
- [ ] **JavaScript active**: Buttons respond to clicks
- [ ] **Videos load**: Click "View Demo" and video plays in modal
- [ ] **Modal closes**: Close button, outside click, and Escape key all work
- [ ] **Responsive design**: Test on mobile device or browser dev tools
- [ ] **All scenarios work**: Test each card's "View Demo" button
- [ ] **GIF fallback**: Test by temporarily renaming MP4 file (optional)

### Troubleshooting Common Issues

**Issue**: Page shows 404 error
- **Fix**: Ensure "docs" folder is selected in GitHub Pages settings

**Issue**: CSS/JS not loading
- **Fix**: Check that files are in `docs/` directory, not subdirectory

**Issue**: Videos not playing
- **Fix**: Verify video files copied to `docs/`, check browser console for errors

**Issue**: Modal not opening
- **Fix**: Check browser console for JavaScript errors, verify script.js loaded

**Issue**: Styling broken on mobile
- **Fix**: Check viewport meta tag in HTML, test media queries


## CSS Design System

### CSS Variables (Design Tokens)

The application uses CSS custom properties for consistent theming:

```css
:root {
  /* Colors */
  --color-primary: #2563eb;        /* Blue for primary actions */
  --color-success: #10b981;        /* Green for normal status */
  --color-warning: #f59e0b;        /* Yellow for low priority */
  --color-danger: #ef4444;         /* Red for critical status */
  
  /* Grays */
  --color-gray-50: #f9fafb;        /* Lightest gray */
  --color-gray-900: #111827;       /* Darkest gray */
  
  /* Spacing */
  --spacing-xs: 0.25rem;           /* 4px */
  --spacing-sm: 0.5rem;            /* 8px */
  --spacing-md: 1rem;              /* 16px */
  --spacing-lg: 1.5rem;            /* 24px */
  --spacing-xl: 2rem;              /* 32px */
  
  /* Border Radius */
  --radius-sm: 0.25rem;            /* 4px */
  --radius-md: 0.5rem;             /* 8px */
  --radius-lg: 0.75rem;            /* 12px */
  
  /* Shadows */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
}
```


### Layout System

**Container**:
```css
.container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 0 var(--spacing-lg);
}
```

**Flexbox Patterns**:
- `.header-content`: Space-between layout for logo and badges
- `.stats-section`: Flex with wrap for responsive card layout
- `.kanban-board`: Horizontal flex with scroll on desktop
- `.scenario-card`: Vertical flex for card sections

**Grid System**: Not used (flexbox sufficient for this design)

### Responsive Breakpoints

```css
/* Desktop: default styles (1024px+) */

/* Tablet: 1024px and below */
@media (max-width: 1024px) {
  .kanban-board {
    flex-direction: column;  /* Stack columns vertically */
  }
}

/* Mobile: 768px and below */
@media (max-width: 768px) {
  .stats-section {
    flex-direction: column;  /* Stack stat cards */
  }
  .header-content {
    flex-direction: column;  /* Stack header elements */
  }
}
```

**Mobile-First Approach**: Base styles mobile-friendly, media queries enhance for larger screens


### Animation System

**Fade In (Modal)**:
```css
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.modal {
  animation: fadeIn 0.3s;
}
```

**Slide Up (Modal Content)**:
```css
@keyframes slideUp {
  from {
    transform: translateY(50px);
    opacity: 0;
  }
  to {
    transform: translateY(0);
    opacity: 1;
  }
}

.modal-content {
  animation: slideUp 0.3s;
}
```

**Hover Transitions**:
```css
.scenario-card {
  transition: transform 0.2s, box-shadow 0.2s;
}

.scenario-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
}
```

**Performance**: All animations use `transform` and `opacity` for GPU acceleration


## Error Handling

### Video Loading Errors

**Scenario**: MP4 file fails to load

**Handling**:
```javascript
video.onerror = function() {
  console.warn('MP4 failed to load, trying GIF fallback');
  loadGifFallback(scenario.gifFallback);
};
```

**User Experience**: 
- No error message shown if GIF loads successfully
- If GIF also fails: "Video unavailable. Please try again later."

### Scenario Not Found

**Scenario**: `viewScenario()` called with invalid scenario ID

**Handling**:
```javascript
function viewScenario(scenarioId) {
  const scenario = SCENARIOS[scenarioId];
  if (!scenario) {
    console.error('Scenario not found:', scenarioId);
    alert('Scenario not found. Please refresh the page.');
    return;
  }
  // Continue with video loading...
}
```

### Modal Already Open

**Scenario**: User clicks "View Demo" while modal is already open

**Handling**:
- Close existing modal (clean up old video)
- Open new modal with new video
- Ensures no multiple modals or video conflicts


### Browser Compatibility Fallbacks

**CSS Grid/Flexbox**: Supported in all modern browsers (95%+ coverage)

**CSS Variables**: Supported in all browsers except IE11
- **Fallback**: Not needed (IE11 end-of-life Nov 2022)

**HTML5 Video**: Supported in all modern browsers
- **Fallback**: GIF images for unsupported codecs

**ES6 JavaScript**: Template literals, arrow functions, const/let
- **Compatibility**: All browsers from 2017+
- **Fallback**: Not needed (target modern browsers)

## Testing Strategy

### Manual Testing Checklist

**Visual Testing**:
- [ ] Layout renders correctly on desktop (1920px, 1440px, 1024px)
- [ ] Layout renders correctly on mobile (768px, 375px, 320px)
- [ ] All colors match design (purple gradient, status colors)
- [ ] Hover effects work on all interactive elements
- [ ] Animations smooth and complete

**Functional Testing**:
- [ ] All "View Demo" buttons open modal with correct video
- [ ] All "Details" buttons show correct scenario information
- [ ] Modal closes via close button
- [ ] Modal closes via outside click
- [ ] Modal closes via Escape key
- [ ] Video plays with controls
- [ ] Video pauses when modal closes


**Cross-Browser Testing**:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

**Performance Testing**:
- [ ] Initial page load < 2 seconds
- [ ] Video modal opens within 500ms
- [ ] No layout shift during loading
- [ ] Smooth scrolling on mobile
- [ ] No memory leaks from video elements

### Accessibility Considerations

**Semantic HTML**:
- Use `<header>`, `<main>`, `<section>` for structure
- Use `<button>` for interactive elements (not `<div>` with onclick)
- Use proper heading hierarchy (h1, h2, h3)

**Keyboard Navigation**:
- Modal can be closed with Escape key
- All buttons focusable and activatable via Enter/Space
- Focus trapped in modal when open

**Color Contrast**:
- Text on colored backgrounds meets WCAG AA standards
- Status badges have sufficient contrast
- Links/buttons distinguishable from surrounding text


**Screen Reader Support**:
- Add `aria-label` to icon buttons
- Add `role="dialog"` to modal
- Add `aria-modal="true"` when modal is open
- Add `aria-labelledby` referencing modal title

**Example**:
```html
<button class="modal-close" 
        onclick="closeModal()" 
        aria-label="Close modal">
  &times;
</button>

<div id="videoModal" 
     class="modal" 
     role="dialog" 
     aria-modal="true" 
     aria-labelledby="modalTitle">
  <!-- Modal content -->
</div>
```

## Performance Optimization

### Asset Optimization

**Images**: None used (emoji and SVG icons only)

**CSS**: Single file, ~300 lines, <10 KB

**JavaScript**: Single file, ~200 lines, <5 KB

**Videos**: Already optimized H.264 encoding

**Total Initial Load**: ~15 KB (HTML + CSS + JS)

**Total with Videos**: ~68 MB (if all videos watched)


### Loading Performance Strategy

**Critical Rendering Path**:
1. HTML loads (blocking)
2. CSS loads (blocking, render-critical)
3. JavaScript loads (non-blocking with defer)
4. Videos load on-demand (user-initiated)

**JavaScript Loading**:
```html
<script src="script.js" defer></script>
```

Using `defer` ensures:
- Script downloads in parallel with HTML parsing
- Script executes after DOM is ready
- Doesn't block page rendering

**CSS Loading**: Inline in `<head>` or linked early (currently linked)

### Caching Strategy

**GitHub Pages Headers** (automatic):
```
Cache-Control: max-age=600
```

Videos cached for 10 minutes, reducing repeat downloads.

**Browser Caching**: Videos cached by browser, subsequent views instant


## Future Enhancements

### Potential Improvements (Not in Current Design)

**Video Thumbnails**:
- Generate poster images for videos
- Add `poster` attribute to `<video>` elements
- Improves perceived performance

**Loading Indicators**:
- Show spinner while video loads
- Add "Loading video..." message
- Better user feedback during download

**Video Chapters**:
- Add timeline markers for impact events
- Allow jumping to specific frames
- WebVTT cue points for events

**Analytics**:
- Track which videos are viewed most
- Monitor video load failures
- Measure engagement metrics

**Progressive Web App**:
- Add manifest.json
- Add service worker for offline support
- Cache videos for offline viewing

**Dark Mode**:
- Add theme toggle
- CSS variables for light/dark themes
- Respect system preference


## Implementation Notes

### Code Style Guidelines

**HTML**:
- Use semantic elements
- Indent with 4 spaces
- Use double quotes for attributes
- Keep inline event handlers for simplicity (onclick="...")

**CSS**:
- Use CSS variables for colors/spacing
- Group related properties
- Mobile-first media queries
- BEM-like naming (component-element-modifier)

**JavaScript**:
- Use `const` and `let` (no `var`)
- Use template literals for HTML generation
- Keep functions focused and single-purpose
- Add comments for non-obvious logic

### Development Workflow

1. **Local Development**: Edit files in `docs/`
2. **Local Testing**: Use Python server or Live Server
3. **Commit Changes**: Git commit with descriptive message
4. **Push to GitHub**: Git push triggers automatic deployment
5. **Verify Deployment**: Check GitHub Pages URL after 1-2 minutes


### Separation from Main System

**Key Principle**: The web application is completely independent from the main Python/C++ codebase.

**What This Means**:
- No imports from `src/`, `cpp/`, or any other project directories
- No shared configuration files
- No build process dependencies
- Videos are **copies**, not references

**Benefits**:
- Main system changes don't break web app
- Web app updates don't affect main system
- Can be developed/deployed independently
- Clear separation of concerns

**Directory Isolation**:
```
experimenting/
├── src/                  # Main Python code
├── cpp/                  # Main C++ code
├── demo_videos/          # Source videos (for main system)
└── docs/                 # Web app (copies of videos, independent)
```

### File Size Considerations

**Current Total**: ~68 MB (4 video files)

**GitHub Pages Limits**:
- Repository: 1 GB recommended
- File: 100 MB maximum
- Bandwidth: 100 GB/month

**Our Usage**: Well within all limits


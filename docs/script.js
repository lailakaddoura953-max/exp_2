// ============================================================================
// Truck View: Camera Alignment Check - Interactive Web Application
// ============================================================================

// ============================================================================
// SCENARIO DATA STRUCTURE
// ============================================================================
// This object defines all camera alignment scenarios displayed in the UI.
// Each scenario maps to demo videos and includes detailed event information.

const SCENARIOS = {
  'normal': {
    title: 'Normal Operation - Aligned Cameras',
    videoFile: '01_normal_operation.mp4',
    gifFallback: '01_normal_operation.gif',
    description: 'All 4 cameras are properly aligned. Diamond markers connected at center. System operating normally with no detected issues.',
    details: {
      duration: '~5 seconds (150 frames)',
      alignment: '100% aligned',
      alerts: 'None',
      features: '100+ features per camera',
      status: 'Operational'
    }
  },
  
  'minor-1': {
    title: 'Camera 1: Minor Shift - Pothole',
    videoFile: '02_impact_scenario.mp4',
    gifFallback: '02_impact_scenario.gif',
    description: 'Minor misalignment detected on Camera 1 due to pothole impact. Diamond mostly connected. Within acceptable tolerance limits.',
    events: [
      {
        frame: 50,
        type: 'Pothole',
        camera: 1,
        severity: 'minor',
        rotation: '±2°',
        translation: '±15px',
        alert: false
      }
    ]
  },
  
  'minor-2': {
    title: 'Camera 0: Wind Gust Adjustment',
    videoFile: '02_impact_scenario.mp4',
    gifFallback: '02_impact_scenario.gif',
    description: 'Slight adjustment from wind gust affecting Camera 0. System compensating automatically. No action required.',
    events: [
      {
        frame: 200,
        type: 'Wind',
        camera: 0,
        severity: 'minor',
        rotation: '±1.5°',
        translation: '±12px',
        alert: false
      }
    ]
  },
  
  'critical-1': {
    title: 'Camera 2: Debris Impact - CRITICAL',
    videoFile: '02_impact_scenario.mp4',
    gifFallback: '02_impact_scenario.gif',
    description: '⚠️ ALERT: Major misalignment detected on Camera 2 from debris impact! Diamond broken. Immediate recalibration needed.',
    events: [
      {
        frame: 120,
        type: 'Debris',
        camera: 2,
        severity: 'critical',
        rotation: '±8°',
        translation: '±60px',
        alert: true
      }
    ]
  },
  
  'critical-2': {
    title: 'Camera 3: Strong Wind - CRITICAL',
    videoFile: '02_impact_scenario.mp4',
    gifFallback: '02_impact_scenario.gif',
    description: '⚠️ ALERT: Severe displacement detected on Camera 3 from strong wind! Diamond misaligned. Action required.',
    events: [
      {
        frame: 300,
        type: 'Wind',
        camera: 3,
        severity: 'critical',
        rotation: '±7°',
        translation: '±55px',
        alert: true
      }
    ]
  },
  
  'full-timeline': {
    title: 'Complete Impact Scenario Timeline',
    videoFile: '02_impact_scenario.mp4',
    gifFallback: '02_impact_scenario.gif',
    description: 'Full sequence showing all impact events in real-time. Watch how the system detects and responds to both minor and critical misalignments across all four cameras.',
    events: [
      {
        frame: 50,
        type: 'Pothole',
        camera: 1,
        severity: 'minor',
        rotation: '±2°',
        translation: '±15px',
        alert: false
      },
      {
        frame: 120,
        type: 'Debris',
        camera: 2,
        severity: 'critical',
        rotation: '±8°',
        translation: '±60px',
        alert: true
      },
      {
        frame: 200,
        type: 'Wind',
        camera: 0,
        severity: 'minor',
        rotation: '±1.5°',
        translation: '±12px',
        alert: false
      },
      {
        frame: 300,
        type: 'Wind',
        camera: 3,
        severity: 'critical',
        rotation: '±7°',
        translation: '±55px',
        alert: true
      }
    ],
    details: {
      duration: '~12 seconds (350 frames)',
      totalEvents: '4 impacts',
      minorEvents: '2 (Camera 0, Camera 1)',
      criticalEvents: '2 (Camera 2, Camera 3)',
      alertsTriggered: '2'
    }
  }
};

// ============================================================================
// MODAL CONTROL FUNCTIONS
// ============================================================================

/**
 * Opens the video modal and displays the specified scenario
 * 
 * This function:
 * 1. Looks up scenario from SCENARIOS object
 * 2. Creates video element with controls and autoplay
 * 3. Sets video source to scenario.videoFile
 * 4. Adds error handler for video.onerror to trigger GIF fallback
 * 5. Injects video into #videoContainer
 * 6. Updates #modalTitle with scenario title
 * 7. Calls renderScenarioDetails() to populate scenario info
 * 8. Adds 'active' class to modal to display it
 * 
 * @param {string} scenarioId - The ID of the scenario to display (e.g., 'normal', 'critical-1')
 * 
 * Requirements: 4.1, 4.2, 7.5, 11.2, 11.4
 */
function viewScenario(scenarioId) {
  // Look up scenario from SCENARIOS object
  const scenario = SCENARIOS[scenarioId];
  
  // Validate scenario exists
  if (!scenario) {
    console.error('Scenario not found:', scenarioId);
    alert('Scenario not found. Please refresh the page.');
    return;
  }
  
  // Get DOM elements
  const modal = document.getElementById('videoModal');
  const videoContainer = document.getElementById('videoContainer');
  const modalTitle = document.getElementById('modalTitle');
  const scenarioInfo = document.getElementById('scenarioInfo');
  
  // Create video element with controls and autoplay
  const video = document.createElement('video');
  video.src = scenario.videoFile;
  video.controls = true;
  video.autoplay = true;
  video.style.width = '100%';
  
  // Add error handler for video.onerror to trigger GIF fallback
  video.onerror = function() {
    console.warn('MP4 failed to load, trying GIF fallback for scenario:', scenarioId);
    loadGifFallback(scenario.gifFallback);
  };
  
  // Clear previous content and inject video into #videoContainer
  videoContainer.innerHTML = '';
  videoContainer.appendChild(video);
  
  // Update #modalTitle with scenario title
  modalTitle.textContent = scenario.title;
  
  // Call renderScenarioDetails() to populate scenario info
  const detailsHTML = renderScenarioDetails(scenario);
  scenarioInfo.innerHTML = detailsHTML;
  
  // Add 'active' class to modal to display it
  modal.classList.add('active');
  
  // Focus on modal for accessibility
  modal.focus();
}

/**
 * Closes the video modal and cleans up resources
 * 
 * This function:
 * 1. Removes the 'active' class to hide the modal
 * 2. Pauses any playing video
 * 3. Destroys the video element to free memory
 * 4. Clears scenario information
 * 
 * Called when:
 * - User clicks the close button (X)
 * - User clicks outside the modal content (on backdrop)
 * - User presses the Escape key
 * 
 * Requirements: 4.4, 7.4, 11.2
 */
function closeModal() {
  // Get modal element
  const modal = document.getElementById('videoModal');
  
  // Remove 'active' class to hide modal
  modal.classList.remove('active');
  
  // Get video container
  const videoContainer = document.getElementById('videoContainer');
  
  // Find video element and pause if playing
  const video = videoContainer.querySelector('video');
  if (video) {
    video.pause();
  }
  
  // Clear innerHTML of videoContainer to destroy video element
  videoContainer.innerHTML = '';
  
  // Clear innerHTML of scenarioInfo to reset details
  const scenarioInfo = document.getElementById('scenarioInfo');
  scenarioInfo.innerHTML = '';
}

/**
 * Display detailed scenario information in modal without video
 * @param {string} scenarioId - The scenario identifier (e.g., 'normal', 'critical-1')
 */
function showDetails(scenarioId) {
  // Look up scenario from SCENARIOS object
  const scenario = SCENARIOS[scenarioId];
  
  if (!scenario) {
    console.error('Scenario not found:', scenarioId);
    alert('Scenario not found. Please refresh the page.');
    return;
  }
  
  // Get modal elements
  const modal = document.getElementById('videoModal');
  const modalTitle = document.getElementById('modalTitle');
  const videoContainer = document.getElementById('videoContainer');
  const scenarioInfo = document.getElementById('scenarioInfo');
  
  // Update modal title
  modalTitle.textContent = scenario.title;
  
  // Clear video container (no video for details view)
  videoContainer.innerHTML = '';
  
  // Call renderScenarioDetails() to generate HTML
  const detailsHTML = renderScenarioDetails(scenario);
  
  // Inject details into modal
  scenarioInfo.innerHTML = detailsHTML;
  
  // Add 'active' class to modal to display it
  modal.classList.add('active');
  
  // Focus on modal for accessibility
  modal.focus();
}

// ============================================================================
// VIDEO FALLBACK MECHANISM
// ============================================================================

/**
 * Load GIF fallback when MP4 video fails to load
 * 
 * This function is called when video.onerror is triggered. It replaces the
 * failed video element with an image element showing the GIF version of the
 * demo. A notice is displayed to inform the user about the fallback.
 * 
 * @param {string} gifFile - Relative path to the GIF file (e.g., '01_normal_operation.gif')
 */
function loadGifFallback(gifFile) {
  // Get the video container element
  const videoContainer = document.getElementById('videoContainer');
  
  // Clear any existing content in the container
  videoContainer.innerHTML = '';
  
  // Create a notice message
  const notice = document.createElement('p');
  notice.textContent = 'Video unavailable, showing GIF version';
  notice.style.color = '#f59e0b';  // Warning color (yellow)
  notice.style.textAlign = 'center';
  notice.style.marginBottom = '1rem';
  notice.style.fontWeight = 'bold';
  
  // Create the img element for the GIF
  const img = document.createElement('img');
  img.src = gifFile;
  img.style.width = '100%';
  img.alt = 'Demo GIF fallback';
  
  // Inject the notice and image into the video container
  videoContainer.appendChild(notice);
  videoContainer.appendChild(img);
  
  console.log(`Video failed to load. Showing GIF fallback: ${gifFile}`);
}

// ============================================================================
// SCENARIO DETAILS RENDERING
// ============================================================================

/**
 * Generates HTML content for displaying detailed scenario information.
 * Handles both scenarios with 'details' (key-value pairs) and 'events' (timeline).
 * 
 * @param {Object} scenario - The scenario object from SCENARIOS
 * @returns {string} HTML string containing formatted scenario details
 * 
 * Requirements: 5.1, 5.2, 5.3, 5.4, 5.5
 */
function renderScenarioDetails(scenario) {
  let html = '<div class="scenario-details">';
  
  // Add description
  html += `<p class="scenario-description">${scenario.description}</p>`;
  
  // Check if scenario has 'details' property (key-value pairs)
  if (scenario.details) {
    html += '<h3>Scenario Information</h3>';
    html += '<div class="details-grid">';
    
    // Iterate through details object and display key-value pairs
    for (const [key, value] of Object.entries(scenario.details)) {
      // Format key: convert camelCase to Title Case with spaces
      const formattedKey = key
        .replace(/([A-Z])/g, ' $1')
        .replace(/^./, str => str.toUpperCase());
      
      html += `
        <div class="detail-item">
          <span class="detail-label">${formattedKey}:</span>
          <span class="detail-value">${value}</span>
        </div>
      `;
    }
    
    html += '</div>';
  }
  
  // Check if scenario has 'events' property (timeline)
  if (scenario.events && scenario.events.length > 0) {
    html += '<h3>Timeline of Events</h3>';
    html += '<ul class="event-timeline">';
    
    // Iterate through events and generate timeline list
    scenario.events.forEach(event => {
      // Determine alert indicator
      const alertIndicator = event.alert 
        ? '<span class="alert-indicator critical">⚠️ ALERT</span>' 
        : '<span class="alert-indicator normal">✓ No alert</span>';
      
      // Determine severity class for styling
      const severityClass = event.severity === 'critical' ? 'critical' : 'minor';
      
      html += `
        <li class="event-item ${severityClass}">
          <div class="event-header">
            <strong>Frame ${event.frame}</strong> - Camera ${event.camera}
          </div>
          <div class="event-details">
            <span class="event-type">${event.type}</span>
            <span class="event-severity ${severityClass}">(${event.severity})</span>
          </div>
          <div class="event-metrics">
            Rotation: ${event.rotation} | Translation: ${event.translation}
          </div>
          <div class="event-alert">
            ${alertIndicator}
          </div>
        </li>
      `;
    });
    
    html += '</ul>';
  }
  
  html += '</div>';
  
  return html;
}

// ============================================================================
// EVENT LISTENERS - DOM INITIALIZATION
// ============================================================================

/**
 * Set up event listeners when DOM is ready
 * 
 * This ensures all event listeners are attached after the DOM has fully loaded.
 * Event listeners include:
 * - Escape key to close modal
 * 
 * Requirements: 4.4, 11.5
 */
document.addEventListener('DOMContentLoaded', function() {
  
  /**
   * Keyboard event listener for Escape key
   * Closes the modal when Escape is pressed and modal is active
   * 
   * Requirements: 4.4, 11.5
   */
  document.addEventListener('keydown', function(event) {
    // Check if the pressed key is 'Escape'
    if (event.key === 'Escape') {
      // Get the modal element
      const modal = document.getElementById('videoModal');
      
      // Check if modal has 'active' class (is currently open)
      if (modal && modal.classList.contains('active')) {
        // Close the modal
        closeModal();
      }
    }
  });
  
});

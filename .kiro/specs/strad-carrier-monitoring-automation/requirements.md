# Requirements Document

## Introduction

This document specifies requirements for an automated monitoring system that integrates a deep learning misalignment detection system with a production SQL Server database, Excel-based video feed automation, and VLC media player snapshot capture for Strad Carrier (SC) camera monitoring. The system performs hourly monitoring cycles of 10 randomly selected Strad Carriers from a pool of 135 units (SC001-SC135), classifies camera alignment status, and manages check history to prevent redundant monitoring while excluding critical strads from rotation until manual intervention is confirmed.

## Glossary

- **Strad_Carrier**: A vehicle unit identified by unique ID format SCXXX (e.g., SC001 to SC135) equipped with cameras for monitoring
- **Monitoring_System**: The automated system that orchestrates strad selection, video capture, classification, and result storage
- **Database_Interface**: Component that queries and updates SQL Server database
- **Excel_Automation**: Component that controls Excel spreadsheet to open video encoder for selected strads
- **VLC_Capture**: Component that captures snapshots from VLC media player displaying live camera feeds
- **DL_Classifier**: Deep learning misalignment detection program that assigns classification to snapshots
- **Check_History**: Database record tracking which strads were checked and when to enforce 1-hour cooldown
- **Hourly_Cycle**: A monitoring iteration that processes 10 strads, completes classifications, and updates database
- **Classification_Result**: One of three severity levels: none (properly aligned), moderate (minor misalignment), critical (severe misalignment requiring intervention)
- **Critical_Strad**: A Strad_Carrier assigned critical classification, excluded from monitoring rotation until camera adjustment confirmed
- **Snapshot**: Image captured from VLC media player showing current camera feed state
- **CHE_Number**: Strad identification in SCXXX format used for tracking in Check_History
- **Video_Encoder_Button**: Excel interface control labeled "spreader video encoder" that accepts SC ID input
- **Cooldown_Period**: 1-hour time window during which a checked strad SHALL NOT be selected for re-checking
- **Adjustment_Confirmation**: Manual report indicating critical strad cameras have been physically adjusted

## Requirements

### Requirement 1: Strad Selection from Database

**User Story:** As a monitoring operator, I want the system to randomly select 10 unique Strad Carriers from the database that are eligible for checking, so that monitoring coverage is distributed across the fleet without redundant checks.

#### Acceptance Criteria

1. THE Database_Interface SHALL query SQL Server database using 'strad_action_check_by_id_and_timestamp' to retrieve available strad IDs
2. THE Database_Interface SHALL filter strads to exclude any strad with check timestamp within the last 1 hour (Cooldown_Period)
3. THE Database_Interface SHALL filter strads to exclude any strad currently classified as Critical_Strad
4. THE Database_Interface SHALL randomly select exactly 10 unique Strad_Carrier IDs from the eligible pool
5. WHEN fewer than 10 strads are eligible, THE Database_Interface SHALL select all available eligible strads
6. THE Database_Interface SHALL return strad IDs in the format SCXXX where XXX is a number from 001 to 135

### Requirement 2: Excel Video Feed Automation

**User Story:** As a monitoring operator, I want the system to automatically control Excel to open video feeds for selected strads, so that manual navigation through the interface is eliminated.

#### Acceptance Criteria

1. WHEN a Strad_Carrier ID is provided, THE Excel_Automation SHALL open the Excel spreadsheet containing the Video_Encoder_Button
2. THE Excel_Automation SHALL locate the Video_Encoder_Button control labeled "spreader video encoder"
3. THE Excel_Automation SHALL insert the CHE_Number (SCXXX format) into the Video_Encoder_Button input field
4. THE Excel_Automation SHALL activate the Video_Encoder_Button to trigger video feed opening
5. THE Excel_Automation SHALL verify VLC media player window opens displaying the live camera feed
6. WHEN VLC media player fails to open within 30 seconds OR camera feed loads indefinitely, THE Excel_Automation SHALL return an error status and THE Monitoring_System SHALL discard the strad SCXXX ID for the current cycle and retry the same strad at a later point within the same Hourly_Cycle

### Requirement 3: VLC Snapshot Capture

**User Story:** As a monitoring operator, I want the system to capture snapshots from VLC media player displaying live camera feeds, so that images can be analyzed for misalignment.

#### Acceptance Criteria

1. WHEN VLC media player is displaying a camera feed, THE VLC_Capture SHALL wait 5 seconds for feed stabilization
2. THE VLC_Capture SHALL capture a snapshot from the VLC media player active window
3. THE VLC_Capture SHALL store the snapshot in temporary memory storage
4. THE VLC_Capture SHALL associate the snapshot with the corresponding CHE_Number
5. THE VLC_Capture SHALL verify snapshot dimensions are at least 640x480 pixels
6. WHEN snapshot capture fails, THE VLC_Capture SHALL retry up to 3 times with 2-second intervals between attempts

### Requirement 4: Deep Learning Classification

**User Story:** As a monitoring operator, I want captured snapshots to be automatically analyzed by the deep learning system, so that camera alignment status is determined without manual inspection.

#### Acceptance Criteria

1. WHEN a snapshot is available in temporary storage, THE DL_Classifier SHALL load the snapshot image
2. THE DL_Classifier SHALL process the snapshot through the misalignment detection model
3. THE DL_Classifier SHALL assign exactly one Classification_Result: none, moderate, or critical
4. WHEN classification returns a confidence score of 0.0, THE DL_Classifier SHALL send an alert notification to operations technology developers
5. THE DL_Classifier SHALL return the Classification_Result with confidence score between 0.0 and 1.0
6. THE DL_Classifier SHALL complete classification within 10 seconds per snapshot
7. WHEN classification confidence is below 0.6 including zero confidence, THE DL_Classifier SHALL assign "moderate" as a conservative default

### Requirement 5: Temporary Image Memory Management

**User Story:** As a system administrator, I want temporary snapshot storage to be efficiently managed with automatic cleanup, so that memory resources are not exhausted during continuous operation.

#### Acceptance Criteria

1. WHEN available memory exceeds 500 MB, THE Monitoring_System SHALL maintain temporary storage for exactly 10 snapshots at any time during a Hourly_Cycle
2. WHEN available memory drops below 500 MB, THE Monitoring_System SHALL reduce the snapshot count
3. WHEN a snapshot receives its Classification_Result, THE Monitoring_System SHALL remove the snapshot from temporary storage unless classified as critical
4. WHEN a snapshot is classified as critical, THE Monitoring_System SHALL persist the snapshot to permanent storage before removal from temporary storage
5. THE Monitoring_System SHALL clear all temporary snapshot storage at the completion of each Hourly_Cycle
6. THE Monitoring_System SHALL verify available memory exceeds 500 MB before starting a new Hourly_Cycle

### Requirement 6: Classification Result Storage

**User Story:** As a monitoring operator, I want classification results stored in the database with timestamps and associated strad IDs, so that monitoring history is preserved and trends can be analyzed.

#### Acceptance Criteria

1. WHEN a Classification_Result is determined, THE Database_Interface SHALL store the result in SQL Server database
2. THE Database_Interface SHALL associate the Classification_Result with the CHE_Number
3. THE Database_Interface SHALL record the classification timestamp with precision to the second
4. THE Database_Interface SHALL store the confidence score provided by DL_Classifier
5. WHEN classification is critical, THE Database_Interface SHALL store the snapshot file path in the database record
6. THE Database_Interface SHALL update the Check_History to mark the strad as checked with current timestamp

### Requirement 7: Critical Strad Exclusion Management

**User Story:** As a maintenance coordinator, I want strads with critical misalignment automatically excluded from monitoring rotation, so that system resources focus on monitoring properly functioning units until repairs are completed.

#### Acceptance Criteria

1. WHEN a Strad_Carrier is assigned critical Classification_Result, THE Monitoring_System SHALL add the CHE_Number to the Critical_Strad exclusion list
2. THE Monitoring_System SHALL exclude all Critical_Strad entries from future strad selection queries
3. THE Monitoring_System SHALL maintain the exclusion until an Adjustment_Confirmation is received for that CHE_Number
4. WHEN an Adjustment_Confirmation is received, THE Monitoring_System SHALL explicitly remove the CHE_Number from Critical_Strad exclusion list first
5. THE Monitoring_System SHALL allow the previously critical strad to be selected in the next Hourly_Cycle after the CHE_Number has been removed from the exclusion list
6. THE Database_Interface SHALL log all exclusion additions and removals with timestamps

### Requirement 8: Check History and Cooldown Enforcement

**User Story:** As a monitoring operator, I want strads to be excluded from re-checking for 1 hour after they are monitored, so that all strads receive balanced monitoring coverage without wasteful redundant checks.

#### Acceptance Criteria

1. WHEN a strad completes classification, THE Database_Interface SHALL record the current timestamp in Check_History for that CHE_Number
2. THE Database_Interface SHALL calculate elapsed time since last check when querying eligible strads
3. THE Database_Interface SHALL exclude any strad where elapsed time is less than 1 hour (Cooldown_Period)
4. WHEN a strad's Cooldown_Period expires, THE Database_Interface SHALL include it in the eligible pool for selection
5. THE Database_Interface SHALL maintain Check_History records for at least 7 days
6. THE Database_Interface SHALL clean up Check_History records older than 7 days daily at midnight

### Requirement 9: Hourly Cycle Orchestration

**User Story:** As a monitoring operator, I want the system to automatically execute complete monitoring cycles every hour, so that continuous fleet monitoring occurs without manual intervention.

#### Acceptance Criteria

1. THE Monitoring_System SHALL initiate a new Hourly_Cycle at the start of each clock hour (XX:00:00)
2. WHEN a Hourly_Cycle starts, THE Monitoring_System SHALL execute strad selection, snapshot capture, classification, and result storage in sequence for all 10 selected strads
3. THE Monitoring_System SHALL process strads serially, completing one strad before starting the next
4. WHEN a Hourly_Cycle completes successfully, THE Monitoring_System SHALL log the cycle completion with timestamp and count of strads processed
5. WHEN any component encounters an error whether at the cycle level or individual strad level, THE Monitoring_System SHALL log the error, skip the failed strad, and continue with remaining strads
6. WHEN errors cause processing delays that push a cycle past 50 minutes, THE Monitoring_System SHALL allow the delayed cycle to complete all strads even if the cycle exceeds 50 minutes

### Requirement 10: Critical Snapshot Persistence

**User Story:** As a quality assurance analyst, I want snapshots of critical misalignments saved to permanent storage, so that evidence is available for investigation and verification after camera adjustments.

#### Acceptance Criteria

1. WHEN a snapshot is classified as critical, THE Monitoring_System SHALL save the snapshot to permanent file storage
2. THE Monitoring_System SHALL organize snapshots in directories by date (YYYY-MM-DD format)
3. THE Monitoring_System SHALL name snapshot files using the format: {CHE_Number}_{timestamp}.jpg
4. THE Monitoring_System SHALL compress snapshots using JPEG format with quality level 85
5. THE Monitoring_System SHALL verify the saved file is readable before deleting from temporary storage and SHALL allow deletion after initial verification regardless of later file corruption
6. THE Monitoring_System SHALL retain critical snapshots for at least 30 days

### Requirement 11: Moderate Classification Handling

**User Story:** As a monitoring operator, I want strads with moderate misalignment to continue being monitored in regular rotation, so that developing problems are tracked without prematurely removing units from service.

#### Acceptance Criteria

1. WHEN a Strad_Carrier is assigned moderate Classification_Result, THE Monitoring_System SHALL store the result in the database
2. THE Monitoring_System SHALL allow the strad to remain in the eligible selection pool
3. THE Monitoring_System SHALL apply normal Cooldown_Period (1 hour) to moderate classified strads
4. THE Monitoring_System SHALL NOT save snapshots for moderate classifications
5. THE Database_Interface SHALL track consecutive moderate classifications for trend analysis
6. WHEN a strad receives exactly 3 consecutive moderate classifications within 24 hours, THE Monitoring_System SHALL generate a warning notification

### Requirement 12: System Configuration and Initialization

**User Story:** As a system administrator, I want configuration parameters for database connections, file paths, and timing intervals to be externalized, so that deployment across different environments is simplified.

#### Acceptance Criteria

1. THE Monitoring_System SHALL load configuration from a file named system_config.json at startup
2. THE Monitoring_System SHALL validate all required configuration parameters are present before starting operation
3. THE configuration file SHALL include: database connection string, Excel file path, snapshot storage path, DL model path, and cycle timing
4. WHEN required configuration parameters are missing, THE Monitoring_System SHALL successfully log an error and refuse to start only after successful error logging
5. THE Monitoring_System SHALL support configuration reload without full system restart when configuration file is updated
6. THE Monitoring_System SHALL validate database connectivity during initialization and log connection status

### Requirement 13: Error Handling and Logging

**User Story:** As a system administrator, I want comprehensive error logging and graceful error handling, so that issues can be diagnosed and the system continues operating despite individual component failures.

#### Acceptance Criteria

1. WHEN any component encounters an error, THE Monitoring_System SHALL log the error with timestamp, component name, and error details
2. THE Monitoring_System SHALL continue processing remaining strads in a Hourly_Cycle when one strad fails
3. THE Monitoring_System SHALL retry failed operations up to 3 times before marking as failed
4. THE Monitoring_System SHALL write logs to a file named monitoring_log_{date}.txt with daily rotation
5. THE Monitoring_System SHALL maintain log files for at least 14 days
6. WHEN critical errors occur (database unreachable, DL model unavailable), THE Monitoring_System SHALL send alert notifications and pause cycles until resolved

### Requirement 14: Adjustment Confirmation Interface

**User Story:** As a maintenance technician, I want to report camera adjustments through a simple interface, so that critical strads can be returned to monitoring rotation after repairs are completed.

#### Acceptance Criteria

1. THE Monitoring_System SHALL provide a confirmation input mechanism accepting CHE_Number and confirmation timestamp
2. WHEN an Adjustment_Confirmation is submitted for a CHE_Number that exists in the Critical_Strad exclusion list, THE Monitoring_System SHALL record the confirmation timestamp and technician identifier in the database
3. WHEN an Adjustment_Confirmation is submitted for a CHE_Number that exists in the Critical_Strad exclusion list, THE Monitoring_System SHALL remove the CHE_Number from Critical_Strad exclusion list immediately upon confirmation
4. WHEN an Adjustment_Confirmation is submitted for a CHE_Number that exists in the Critical_Strad exclusion list, THE Monitoring_System SHALL reset the Check_History timestamp to allow immediate re-checking in the next cycle
5. WHEN an Adjustment_Confirmation is submitted for a CHE_Number that exists in the Critical_Strad exclusion list, THE Monitoring_System SHALL return a confirmation message indicating the action was processed successfully
6. WHEN a non-critical CHE_Number is submitted for confirmation, THE Monitoring_System SHALL return an informational message indicating no exclusion exists for that CHE_Number


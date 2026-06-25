"""
Moderate Classification Tracker for Strad Monitoring System

This module tracks consecutive moderate classifications per strad and generates
warning notifications when a strad receives 3 consecutive moderate classifications
within a 24-hour window.

Requirements addressed:
- 11.2: Allow strads with moderate classifications to remain in eligible pool
- 11.3: Apply normal cooldown period (1 hour) to moderate classified strads
- 11.5: Track consecutive moderate classifications for trend analysis
- 11.6: Generate warning when 3 consecutive moderates within 24 hours
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Tuple
from collections import defaultdict

from ..utils.alerting import send_consecutive_moderate_alert


class ModerateClassificationTracker:
    """
    Tracks consecutive moderate classifications per strad.
    
    Maintains in-memory counters that track how many consecutive moderate
    classifications each strad has received. The counter resets when:
    - A non-moderate classification (none or critical) occurs
    - Classifications are outside the 24-hour window
    
    When a strad reaches exactly 3 consecutive moderate classifications within
    24 hours, a warning notification is generated.
    """
    
    def __init__(self, database_interface, time_window_hours: int = 24):
        """
        Initialize moderate classification tracker.
        
        Args:
            database_interface: DatabaseInterface instance for querying classification history
            time_window_hours: Time window for tracking consecutive moderates (default: 24 hours)
        """
        self.db = database_interface
        self.time_window_hours = time_window_hours
        self.logger = logging.getLogger("ModerateClassificationTracker")
        
        # In-memory counter: strad_id -> consecutive_moderate_count
        # This is rebuilt from database queries to ensure accuracy
        self._consecutive_counts: Dict[str, int] = defaultdict(int)
    
    def record_classification(
        self,
        strad_id: str,
        classification: str,
        confidence: float,
        timestamp: Optional[datetime] = None
    ) -> None:
        """
        Record a classification and update consecutive moderate tracking.
        
        This method:
        1. Queries database for recent classifications within time window
        2. Counts consecutive moderate classifications
        3. Updates in-memory counter
        4. Generates warning if threshold reached (3 consecutive moderates)
        5. Resets counter if non-moderate classification occurs
        
        Args:
            strad_id: Strad CHE number
            classification: Classification result ('none', 'moderate', 'critical')
            confidence: Classification confidence score (0.0-1.0)
            timestamp: Classification timestamp (default: current time)
        
        Example:
            >>> tracker.record_classification('SC042', 'moderate', 0.65)
            INFO: SC042 has 1 consecutive moderate classification(s)
            
            >>> tracker.record_classification('SC042', 'moderate', 0.58)
            INFO: SC042 has 2 consecutive moderate classification(s)
            
            >>> tracker.record_classification('SC042', 'moderate', 0.62)
            WARNING: SC042 has 3 consecutive moderate classifications - alert sent
        """
        if timestamp is None:
            timestamp = datetime.now()
        
        # Query database for recent classifications within time window
        recent_classifications = self._query_recent_classifications(
            strad_id,
            timestamp
        )
        
        # Count consecutive moderate classifications (including current one)
        consecutive_count = self._count_consecutive_moderates(
            recent_classifications,
            classification
        )
        
        # Update in-memory counter
        self._consecutive_counts[strad_id] = consecutive_count
        
        # Log current count
        if classification == 'moderate':
            self.logger.info(
                f"{strad_id} has {consecutive_count} consecutive moderate classification(s)"
            )
        else:
            self.logger.info(
                f"{strad_id} received '{classification}' classification - moderate counter reset"
            )
        
        # Generate warning if threshold reached (exactly 3 consecutive moderates)
        if consecutive_count == 3:
            self._send_warning_notification(strad_id, consecutive_count)
    
    def _query_recent_classifications(
        self,
        strad_id: str,
        current_timestamp: datetime
    ) -> List[Tuple[str, datetime]]:
        """
        Query database for classifications within 24-hour window.
        
        Retrieves all classification results for the given strad within the
        time window, ordered by timestamp (most recent first).
        
        Args:
            strad_id: Strad CHE number
            current_timestamp: Current timestamp for window calculation
        
        Returns:
            List of tuples: [(classification, timestamp), ...]
            Ordered by timestamp descending (most recent first)
        
        Note:
            If database is unavailable (fallback mode), returns empty list.
            This prevents false warnings during local testing.
        """
        # Check if database is available
        if not self.db._is_database_available:
            self.logger.warning(
                f"Database unavailable - cannot query recent classifications for {strad_id}"
            )
            return []
        
        try:
            conn = self.db._get_connection()
            cursor = conn.cursor()
            
            # Calculate time window threshold
            window_start = current_timestamp - timedelta(hours=self.time_window_hours)
            
            # Query recent classifications within time window
            query = """
                SELECT classification, created_at
                FROM classification_results
                WHERE strad_id = ?
                  AND created_at >= ?
                  AND created_at <= ?
                ORDER BY created_at DESC
            """
            
            cursor.execute(query, (strad_id, window_start, current_timestamp))
            results = cursor.fetchall()
            cursor.close()
            
            # Convert to list of tuples
            classifications = [(row[0], row[1]) for row in results]
            
            self.logger.debug(
                f"Found {len(classifications)} classifications for {strad_id} "
                f"within {self.time_window_hours}h window"
            )
            
            return classifications
            
        except Exception as e:
            self.logger.error(
                f"Failed to query recent classifications for {strad_id}: {e}"
            )
            return []
    
    def _count_consecutive_moderates(
        self,
        recent_classifications: List[Tuple[str, datetime]],
        current_classification: str
    ) -> int:
        """
        Count consecutive moderate classifications.
        
        Starting from the current classification, counts how many consecutive
        moderate classifications exist. Stops counting when:
        - A non-moderate classification is encountered
        - End of classification history is reached
        
        Args:
            recent_classifications: List of (classification, timestamp) tuples
                                   ordered by timestamp descending
            current_classification: Current classification to include in count
        
        Returns:
            Number of consecutive moderate classifications
        
        Example:
            >>> recent = [('moderate', t1), ('moderate', t2), ('none', t3)]
            >>> _count_consecutive_moderates(recent, 'moderate')
            3  # current + 2 recent moderates
            
            >>> recent = [('moderate', t1), ('none', t2)]
            >>> _count_consecutive_moderates(recent, 'moderate')
            2  # current + 1 recent moderate
            
            >>> recent = [('none', t1), ('moderate', t2)]
            >>> _count_consecutive_moderates(recent, 'moderate')
            1  # current only (stopped at 'none')
        """
        # Start with current classification
        if current_classification != 'moderate':
            return 0
        
        consecutive_count = 1  # Count current classification
        
        # Count consecutive moderates from most recent history
        for classification, timestamp in recent_classifications:
            if classification == 'moderate':
                consecutive_count += 1
            else:
                # Stop at first non-moderate classification
                break
        
        return consecutive_count
    
    def _send_warning_notification(
        self,
        strad_id: str,
        consecutive_count: int
    ) -> None:
        """
        Send warning notification for consecutive moderate classifications.
        
        Generates alert when strad reaches exactly 3 consecutive moderate
        classifications within the time window. This indicates persistent
        minor misalignment that may require manual inspection.
        
        Args:
            strad_id: Strad CHE number
            consecutive_count: Number of consecutive moderate classifications
        """
        self.logger.warning(
            f"WARNING: {strad_id} has reached {consecutive_count} consecutive "
            f"moderate classifications within {self.time_window_hours} hours"
        )
        
        # Send alert notification
        success = send_consecutive_moderate_alert(
            strad_id=strad_id,
            consecutive_count=consecutive_count,
            time_window_hours=self.time_window_hours
        )
        
        if success:
            self.logger.info(f"Warning notification sent for {strad_id}")
        else:
            self.logger.error(f"Failed to send warning notification for {strad_id}")
    
    def get_consecutive_count(self, strad_id: str) -> int:
        """
        Get current consecutive moderate count for a strad.
        
        Args:
            strad_id: Strad CHE number
        
        Returns:
            Current consecutive moderate count (0 if none)
        """
        return self._consecutive_counts.get(strad_id, 0)
    
    def reset_counter(self, strad_id: str) -> None:
        """
        Reset consecutive moderate counter for a strad.
        
        This is called when:
        - A non-moderate classification occurs
        - Manual reset is needed (e.g., after maintenance)
        
        Args:
            strad_id: Strad CHE number
        """
        if strad_id in self._consecutive_counts:
            old_count = self._consecutive_counts[strad_id]
            del self._consecutive_counts[strad_id]
            self.logger.info(
                f"Reset moderate counter for {strad_id} (was {old_count})"
            )
        else:
            self.logger.debug(f"No moderate counter to reset for {strad_id}")
    
    def get_all_counts(self) -> Dict[str, int]:
        """
        Get all consecutive moderate counts.
        
        Returns:
            Dictionary mapping strad_id to consecutive moderate count
        """
        return dict(self._consecutive_counts)
    
    def clear_all_counters(self) -> None:
        """
        Clear all consecutive moderate counters.
        
        Used for testing or system reset scenarios.
        """
        count = len(self._consecutive_counts)
        self._consecutive_counts.clear()
        self.logger.info(f"Cleared all moderate counters ({count} strads)")

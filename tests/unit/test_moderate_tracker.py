"""
Unit tests for ModerateClassificationTracker

Tests the moderate classification tracking functionality including:
- Consecutive moderate counting
- Counter reset on non-moderate classifications
- Warning notification generation at threshold
- Database query integration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock, patch
from src.strad_monitoring.database.moderate_tracker import ModerateClassificationTracker


@pytest.fixture
def mock_db_interface():
    """Create mock database interface."""
    db = Mock()
    db._is_database_available = True
    db._get_connection = Mock()
    return db


@pytest.fixture
def tracker(mock_db_interface):
    """Create ModerateClassificationTracker with mock database."""
    return ModerateClassificationTracker(
        database_interface=mock_db_interface,
        time_window_hours=24
    )


class TestModerateClassificationTracker:
    """Test suite for ModerateClassificationTracker."""
    
    def test_initialization(self, mock_db_interface):
        """Test tracker initializes correctly."""
        tracker = ModerateClassificationTracker(
            database_interface=mock_db_interface,
            time_window_hours=24
        )
        
        assert tracker.db == mock_db_interface
        assert tracker.time_window_hours == 24
        assert len(tracker._consecutive_counts) == 0
    
    def test_count_consecutive_moderates_single(self, tracker):
        """Test counting single moderate classification."""
        recent = []
        count = tracker._count_consecutive_moderates(recent, 'moderate')
        assert count == 1
    
    def test_count_consecutive_moderates_multiple(self, tracker):
        """Test counting multiple consecutive moderates."""
        t1 = datetime.now()
        t2 = t1 - timedelta(hours=2)
        t3 = t1 - timedelta(hours=4)
        
        recent = [
            ('moderate', t1),
            ('moderate', t2),
            ('moderate', t3)
        ]
        
        count = tracker._count_consecutive_moderates(recent, 'moderate')
        assert count == 4  # Current + 3 recent
    
    def test_count_consecutive_moderates_stops_at_none(self, tracker):
        """Test counting stops at non-moderate classification."""
        t1 = datetime.now()
        t2 = t1 - timedelta(hours=2)
        t3 = t1 - timedelta(hours=4)
        
        recent = [
            ('moderate', t1),
            ('none', t2),  # Should stop here
            ('moderate', t3)
        ]
        
        count = tracker._count_consecutive_moderates(recent, 'moderate')
        assert count == 2  # Current + 1 recent moderate
    
    def test_count_consecutive_moderates_non_moderate_current(self, tracker):
        """Test returns 0 when current classification is not moderate."""
        recent = [('moderate', datetime.now())]
        count = tracker._count_consecutive_moderates(recent, 'none')
        assert count == 0
    
    def test_get_consecutive_count(self, tracker):
        """Test getting consecutive count for a strad."""
        tracker._consecutive_counts['SC042'] = 2
        
        assert tracker.get_consecutive_count('SC042') == 2
        assert tracker.get_consecutive_count('SC999') == 0
    
    def test_reset_counter(self, tracker):
        """Test resetting counter for a strad."""
        tracker._consecutive_counts['SC042'] = 2
        
        tracker.reset_counter('SC042')
        assert tracker.get_consecutive_count('SC042') == 0
    
    def test_reset_counter_nonexistent(self, tracker):
        """Test resetting counter for strad without counter doesn't error."""
        tracker.reset_counter('SC999')  # Should not raise exception
        assert tracker.get_consecutive_count('SC999') == 0
    
    def test_get_all_counts(self, tracker):
        """Test getting all consecutive counts."""
        tracker._consecutive_counts['SC042'] = 2
        tracker._consecutive_counts['SC078'] = 1
        
        counts = tracker.get_all_counts()
        assert counts == {'SC042': 2, 'SC078': 1}
    
    def test_clear_all_counters(self, tracker):
        """Test clearing all counters."""
        tracker._consecutive_counts['SC042'] = 2
        tracker._consecutive_counts['SC078'] = 1
        
        tracker.clear_all_counters()
        assert len(tracker._consecutive_counts) == 0
    
    @patch('src.strad_monitoring.database.moderate_tracker.send_consecutive_moderate_alert')
    def test_record_classification_first_moderate(self, mock_alert, tracker, mock_db_interface):
        """Test recording first moderate classification."""
        # Mock database query to return no previous classifications
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = []
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        tracker.record_classification('SC042', 'moderate', 0.65)
        
        assert tracker.get_consecutive_count('SC042') == 1
        mock_alert.assert_not_called()  # No alert for 1 consecutive
    
    @patch('src.strad_monitoring.database.moderate_tracker.send_consecutive_moderate_alert')
    def test_record_classification_second_moderate(self, mock_alert, tracker, mock_db_interface):
        """Test recording second consecutive moderate."""
        t1 = datetime.now() - timedelta(hours=2)
        
        # Mock database query to return 1 previous moderate
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('moderate', t1)]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        tracker.record_classification('SC042', 'moderate', 0.58)
        
        assert tracker.get_consecutive_count('SC042') == 2
        mock_alert.assert_not_called()  # No alert for 2 consecutive
    
    @patch('src.strad_monitoring.database.moderate_tracker.send_consecutive_moderate_alert')
    def test_record_classification_third_moderate_triggers_alert(
        self, mock_alert, tracker, mock_db_interface
    ):
        """Test recording third consecutive moderate triggers warning."""
        t1 = datetime.now() - timedelta(hours=2)
        t2 = datetime.now() - timedelta(hours=4)
        
        # Mock database query to return 2 previous moderates
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('moderate', t1),
            ('moderate', t2)
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        mock_alert.return_value = True
        
        tracker.record_classification('SC042', 'moderate', 0.62)
        
        assert tracker.get_consecutive_count('SC042') == 3
        mock_alert.assert_called_once_with(
            strad_id='SC042',
            consecutive_count=3,
            time_window_hours=24
        )
    
    @patch('src.strad_monitoring.database.moderate_tracker.send_consecutive_moderate_alert')
    def test_record_classification_reset_on_none(self, mock_alert, tracker, mock_db_interface):
        """Test counter resets when non-moderate classification occurs."""
        t1 = datetime.now() - timedelta(hours=2)
        
        # Mock database query to return 1 previous moderate
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [('moderate', t1)]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        tracker.record_classification('SC042', 'none', 0.95)
        
        assert tracker.get_consecutive_count('SC042') == 0
        mock_alert.assert_not_called()
    
    def test_query_recent_classifications_database_unavailable(self, tracker, mock_db_interface):
        """Test query returns empty list when database unavailable."""
        mock_db_interface._is_database_available = False
        
        result = tracker._query_recent_classifications('SC042', datetime.now())
        
        assert result == []
    
    def test_query_recent_classifications_database_error(self, tracker, mock_db_interface):
        """Test query handles database errors gracefully."""
        mock_db_interface._get_connection.side_effect = Exception("Connection failed")
        
        result = tracker._query_recent_classifications('SC042', datetime.now())
        
        assert result == []
    
    @patch('src.strad_monitoring.database.moderate_tracker.send_consecutive_moderate_alert')
    def test_fourth_moderate_no_duplicate_alert(self, mock_alert, tracker, mock_db_interface):
        """Test fourth consecutive moderate doesn't send duplicate alert."""
        t1 = datetime.now() - timedelta(hours=2)
        t2 = datetime.now() - timedelta(hours=4)
        t3 = datetime.now() - timedelta(hours=6)
        
        # Mock database query to return 3 previous moderates
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            ('moderate', t1),
            ('moderate', t2),
            ('moderate', t3)
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        tracker.record_classification('SC042', 'moderate', 0.60)
        
        assert tracker.get_consecutive_count('SC042') == 4
        # Alert should NOT be called for 4th consecutive (only on exactly 3)
        mock_alert.assert_not_called()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

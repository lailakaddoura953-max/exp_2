"""
Unit tests for ConfirmationHandler

Tests the adjustment confirmation functionality including:
- Validation of CHE_Number format
- Checking exclusion existence
- Recording confirmation details
- Removing from exclusion list
- Resetting check history
- Handling non-excluded strads
"""

import pytest
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch
from src.strad_monitoring.orchestration.confirmation_handler import (
    ConfirmationHandler,
    ConfirmationResult
)
from src.strad_monitoring.utils.exceptions import DatabaseError


@pytest.fixture
def mock_db_interface():
    """Create mock database interface."""
    db = Mock()
    db._is_database_available = True
    db._get_connection = Mock()
    db.remove_from_critical_exclusion = Mock(return_value=True)
    return db


@pytest.fixture
def handler(mock_db_interface):
    """Create ConfirmationHandler with mock database."""
    return ConfirmationHandler(database_interface=mock_db_interface)


class TestConfirmationResult:
    """Test suite for ConfirmationResult dataclass."""
    
    def test_confirmation_result_creation(self):
        """Test ConfirmationResult initializes correctly."""
        result = ConfirmationResult(
            success=True,
            message="Test message",
            was_excluded=True,
            strad_id="SC042",
            technician_id="TECH123",
            timestamp=datetime.now()
        )
        
        assert result.success is True
        assert result.message == "Test message"
        assert result.was_excluded is True
        assert result.strad_id == "SC042"
        assert result.technician_id == "TECH123"
        assert result.timestamp is not None
    
    def test_confirmation_result_str(self):
        """Test ConfirmationResult string representation."""
        result = ConfirmationResult(
            success=True,
            message="Test",
            was_excluded=True,
            strad_id="SC042"
        )
        
        str_repr = str(result)
        assert "success=True" in str_repr
        assert "SC042" in str_repr


class TestConfirmationHandler:
    """Test suite for ConfirmationHandler."""
    
    def test_initialization(self, mock_db_interface):
        """Test handler initializes correctly."""
        handler = ConfirmationHandler(database_interface=mock_db_interface)
        
        assert handler.db == mock_db_interface
        assert handler.logger is not None
    
    # ========================================================================
    # CHE_Number Validation Tests
    # ========================================================================
    
    def test_validate_che_number_valid_formats(self, handler):
        """Test validation accepts valid CHE_Number formats."""
        valid_numbers = ['SC001', 'SC042', 'SC078', 'SC135']
        
        for che_number in valid_numbers:
            # Should not raise exception
            handler._validate_che_number(che_number)
    
    def test_validate_che_number_empty(self, handler):
        """Test validation rejects empty CHE_Number."""
        with pytest.raises(ValueError, match="cannot be empty"):
            handler._validate_che_number('')
    
    def test_validate_che_number_invalid_prefix(self, handler):
        """Test validation rejects invalid prefix."""
        with pytest.raises(ValueError, match="Invalid CHE_Number format"):
            handler._validate_che_number('XY042')
    
    def test_validate_che_number_wrong_length(self, handler):
        """Test validation rejects wrong length."""
        with pytest.raises(ValueError, match="Invalid CHE_Number format"):
            handler._validate_che_number('SC42')
        
        with pytest.raises(ValueError, match="Invalid CHE_Number format"):
            handler._validate_che_number('SC0042')
    
    def test_validate_che_number_non_numeric(self, handler):
        """Test validation rejects non-numeric suffix."""
        with pytest.raises(ValueError, match="must be digits"):
            handler._validate_che_number('SCABC')
    
    def test_validate_che_number_out_of_range_low(self, handler):
        """Test validation rejects numbers below range."""
        with pytest.raises(ValueError, match="between 001 and 135"):
            handler._validate_che_number('SC000')
    
    def test_validate_che_number_out_of_range_high(self, handler):
        """Test validation rejects numbers above range."""
        with pytest.raises(ValueError, match="between 001 and 135"):
            handler._validate_che_number('SC200')
    
    # ========================================================================
    # Check Exclusion Exists Tests
    # ========================================================================
    
    def test_check_exclusion_exists_true(self, handler, mock_db_interface):
        """Test checking exclusion returns True when strad is excluded."""
        # Mock database query to return count of 1
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        result = handler._check_exclusion_exists('SC042')
        
        assert result is True
        mock_cursor.execute.assert_called_once()
    
    def test_check_exclusion_exists_false(self, handler, mock_db_interface):
        """Test checking exclusion returns False when strad is not excluded."""
        # Mock database query to return count of 0
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [0]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        result = handler._check_exclusion_exists('SC042')
        
        assert result is False
    
    def test_check_exclusion_exists_database_unavailable(self, handler, mock_db_interface):
        """Test checking exclusion returns False when database unavailable."""
        mock_db_interface._is_database_available = False
        
        result = handler._check_exclusion_exists('SC042')
        
        assert result is False
    
    def test_check_exclusion_exists_database_error(self, handler, mock_db_interface):
        """Test checking exclusion raises DatabaseError on query failure."""
        mock_db_interface._get_connection.side_effect = Exception("Connection failed")
        
        with pytest.raises(DatabaseError):
            handler._check_exclusion_exists('SC042')
    
    # ========================================================================
    # Record Confirmation Tests
    # ========================================================================
    
    def test_record_confirmation_success(self, handler, mock_db_interface):
        """Test recording confirmation updates database correctly."""
        mock_cursor = Mock()
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        timestamp = datetime.now()
        handler._record_confirmation('SC042', 'TECH123', timestamp)
        
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        
        # Verify SQL parameters
        call_args = mock_cursor.execute.call_args[0]
        assert 'UPDATE critical_strad_exclusions' in call_args[0]
        assert call_args[1] == (timestamp, 'TECH123', 'SC042')
    
    def test_record_confirmation_database_unavailable(self, handler, mock_db_interface):
        """Test recording confirmation skips when database unavailable."""
        mock_db_interface._is_database_available = False
        
        # Should not raise exception, just logs warning
        handler._record_confirmation('SC042', 'TECH123', datetime.now())
    
    def test_record_confirmation_database_error(self, handler, mock_db_interface):
        """Test recording confirmation raises DatabaseError on failure."""
        mock_db_interface._get_connection.side_effect = Exception("Update failed")
        
        with pytest.raises(DatabaseError):
            handler._record_confirmation('SC042', 'TECH123', datetime.now())
    
    # ========================================================================
    # Reset Check History Tests
    # ========================================================================
    
    def test_reset_check_history_success(self, handler, mock_db_interface):
        """Test resetting check history deletes record."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 1  # 1 row deleted
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        handler._reset_check_history('SC042')
        
        mock_cursor.execute.assert_called_once()
        mock_conn.commit.assert_called_once()
        
        # Verify SQL query
        call_args = mock_cursor.execute.call_args[0]
        assert 'DELETE FROM strad_action_check_by_id_and_timestamp' in call_args[0]
        assert call_args[1] == ('SC042',)
    
    def test_reset_check_history_no_record(self, handler, mock_db_interface):
        """Test resetting check history handles no existing record."""
        mock_cursor = Mock()
        mock_cursor.rowcount = 0  # No rows deleted
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        # Should not raise exception
        handler._reset_check_history('SC042')
        
        mock_cursor.execute.assert_called_once()
    
    def test_reset_check_history_database_unavailable(self, handler, mock_db_interface):
        """Test resetting check history skips when database unavailable."""
        mock_db_interface._is_database_available = False
        
        # Should not raise exception
        handler._reset_check_history('SC042')
    
    def test_reset_check_history_database_error(self, handler, mock_db_interface):
        """Test resetting check history raises DatabaseError on failure."""
        mock_db_interface._get_connection.side_effect = Exception("Delete failed")
        
        with pytest.raises(DatabaseError):
            handler._reset_check_history('SC042')
    
    # ========================================================================
    # Confirm Adjustment Tests (Integration)
    # ========================================================================
    
    def test_confirm_adjustment_successful_confirmation(self, handler, mock_db_interface):
        """Test successful confirmation of excluded strad."""
        # Setup mocks: strad IS excluded
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]  # Exists in exclusion
        mock_cursor.rowcount = 1  # Delete successful
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        mock_db_interface.remove_from_critical_exclusion.return_value = True
        
        timestamp = datetime.now()
        result = handler.confirm_adjustment('SC042', 'TECH123', timestamp)
        
        assert result.success is True
        assert result.was_excluded is True
        assert result.strad_id == 'SC042'
        assert result.technician_id == 'TECH123'
        assert result.timestamp == timestamp
        assert "removed from exclusion list" in result.message
        
        # Verify database operations called
        mock_db_interface.remove_from_critical_exclusion.assert_called_once_with('SC042')
    
    def test_confirm_adjustment_not_excluded(self, handler, mock_db_interface):
        """Test confirmation of non-excluded strad returns informational message."""
        # Setup mocks: strad is NOT excluded
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [0]  # Does not exist in exclusion
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        result = handler.confirm_adjustment('SC042', 'TECH123')
        
        assert result.success is True
        assert result.was_excluded is False
        assert result.strad_id == 'SC042'
        assert "No exclusion exists" in result.message
        
        # Verify removal NOT called
        mock_db_interface.remove_from_critical_exclusion.assert_not_called()
    
    def test_confirm_adjustment_invalid_che_number(self, handler):
        """Test confirmation with invalid CHE_Number raises ValueError."""
        with pytest.raises(ValueError):
            handler.confirm_adjustment('INVALID', 'TECH123')
    
    def test_confirm_adjustment_default_timestamp(self, handler, mock_db_interface):
        """Test confirmation uses current time when timestamp not provided."""
        # Setup mocks
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_cursor.rowcount = 1
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        mock_db_interface.remove_from_critical_exclusion.return_value = True
        
        before = datetime.now()
        result = handler.confirm_adjustment('SC042', 'TECH123')
        after = datetime.now()
        
        assert result.success is True
        assert before <= result.timestamp <= after
    
    def test_confirm_adjustment_removal_fails(self, handler, mock_db_interface):
        """Test confirmation raises error when removal fails."""
        # Setup mocks: exists but removal returns False
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [1]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        mock_db_interface.remove_from_critical_exclusion.return_value = False
        
        with pytest.raises(DatabaseError, match="Failed to remove"):
            handler.confirm_adjustment('SC042', 'TECH123')
    
    def test_confirm_adjustment_database_error(self, handler, mock_db_interface):
        """Test confirmation handles database errors gracefully."""
        mock_db_interface._get_connection.side_effect = Exception("Database error")
        
        with pytest.raises(DatabaseError):
            handler.confirm_adjustment('SC042', 'TECH123')
    
    # ========================================================================
    # Get Exclusion Details Tests
    # ========================================================================
    
    def test_get_exclusion_details_exists(self, handler, mock_db_interface):
        """Test getting exclusion details for excluded strad."""
        timestamp_added = datetime(2024, 1, 15, 10, 0, 0)
        timestamp_confirmed = datetime(2024, 1, 15, 14, 30, 0)
        
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [
            'SC042',
            timestamp_added,
            timestamp_confirmed,
            'TECH123'
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        details = handler.get_exclusion_details('SC042')
        
        assert details is not None
        assert details['strad_id'] == 'SC042'
        assert details['added_at'] == timestamp_added
        assert details['adjustment_confirmed_at'] == timestamp_confirmed
        assert details['technician_id'] == 'TECH123'
    
    def test_get_exclusion_details_not_exists(self, handler, mock_db_interface):
        """Test getting exclusion details for non-excluded strad."""
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = None
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        details = handler.get_exclusion_details('SC042')
        
        assert details is None
    
    def test_get_exclusion_details_database_unavailable(self, handler, mock_db_interface):
        """Test getting exclusion details when database unavailable."""
        mock_db_interface._is_database_available = False
        
        details = handler.get_exclusion_details('SC042')
        
        assert details is None
    
    def test_get_exclusion_details_database_error(self, handler, mock_db_interface):
        """Test getting exclusion details raises DatabaseError on failure."""
        mock_db_interface._get_connection.side_effect = Exception("Query failed")
        
        with pytest.raises(DatabaseError):
            handler.get_exclusion_details('SC042')
    
    def test_get_exclusion_details_partial_confirmation(self, handler, mock_db_interface):
        """Test getting details for strad excluded but not yet confirmed."""
        timestamp_added = datetime(2024, 1, 15, 10, 0, 0)
        
        mock_cursor = Mock()
        mock_cursor.fetchone.return_value = [
            'SC042',
            timestamp_added,
            None,  # No confirmation yet
            None   # No technician yet
        ]
        mock_conn = Mock()
        mock_conn.cursor.return_value = mock_cursor
        mock_db_interface._get_connection.return_value = mock_conn
        
        details = handler.get_exclusion_details('SC042')
        
        assert details is not None
        assert details['strad_id'] == 'SC042'
        assert details['added_at'] == timestamp_added
        assert details['adjustment_confirmed_at'] is None
        assert details['technician_id'] is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

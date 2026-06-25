"""
Simple test to verify ModerateClassificationTracker works correctly
"""

import logging
from datetime import datetime, timedelta
from unittest.mock import Mock

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from src.strad_monitoring.database.moderate_tracker import ModerateClassificationTracker


def create_mock_database():
    """Create a mock database interface for testing."""
    db = Mock()
    db._is_database_available = True
    
    # Store classifications in memory
    db._classification_history = []
    
    def mock_get_connection():
        conn = Mock()
        cursor = Mock()
        
        def mock_execute(query, params):
            strad_id = params[0]
            window_start = params[1]
            window_end = params[2]
            
            # Filter by strad_id and time window
            results = [
                (c[1], c[2])
                for c in db._classification_history
                if c[0] == strad_id and window_start <= c[2] <= window_end
            ]
            cursor.fetchall.return_value = sorted(results, key=lambda x: x[1], reverse=True)
        
        cursor.execute = mock_execute
        conn.cursor.return_value = cursor
        return conn
    
    db._get_connection = mock_get_connection
    return db


def test_scenario():
    """Test scenario with 3 consecutive moderates."""
    print("\n" + "="*70)
    print("Testing ModerateClassificationTracker")
    print("="*70)
    
    db = create_mock_database()
    tracker = ModerateClassificationTracker(db, time_window_hours=24)
    
    # First moderate (no previous history)
    print("\n1. Recording first moderate classification...")
    timestamp1 = datetime.now() - timedelta(hours=4)
    # Don't add to history yet - record_classification will query for previous
    tracker.record_classification('SC042', 'moderate', 0.65, timestamp1)
    # Now add to history for next query
    db._classification_history.append(('SC042', 'moderate', timestamp1))
    count1 = tracker.get_consecutive_count('SC042')
    print(f"   ✓ Consecutive count: {count1} (expected: 1)")
    assert count1 == 1, f"Expected 1, got {count1}"
    
    # Second moderate
    print("\n2. Recording second moderate classification...")
    timestamp2 = datetime.now() - timedelta(hours=2)
    tracker.record_classification('SC042', 'moderate', 0.58, timestamp2)
    db._classification_history.append(('SC042', 'moderate', timestamp2))
    count2 = tracker.get_consecutive_count('SC042')
    print(f"   ✓ Consecutive count: {count2} (expected: 2)")
    assert count2 == 2, f"Expected 2, got {count2}"
    
    # Third moderate - should trigger warning
    print("\n3. Recording third moderate classification (WARNING EXPECTED)...")
    timestamp3 = datetime.now()
    tracker.record_classification('SC042', 'moderate', 0.62, timestamp3)
    db._classification_history.append(('SC042', 'moderate', timestamp3))
    count3 = tracker.get_consecutive_count('SC042')
    print(f"   ✓ Consecutive count: {count3} (expected: 3)")
    assert count3 == 3, f"Expected 3, got {count3}"
    
    # Test reset on non-moderate
    print("\n4. Recording 'none' classification (counter should reset)...")
    timestamp4 = datetime.now() + timedelta(hours=2)
    tracker.record_classification('SC042', 'none', 0.95, timestamp4)
    db._classification_history.append(('SC042', 'none', timestamp4))
    count4 = tracker.get_consecutive_count('SC042')
    print(f"   ✓ Consecutive count: {count4} (expected: 0)")
    assert count4 == 0, f"Expected 0, got {count4}"
    
    print("\n" + "="*70)
    print("✓ All tests passed!")
    print("="*70)


if __name__ == '__main__':
    test_scenario()

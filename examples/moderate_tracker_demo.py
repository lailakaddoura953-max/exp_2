"""
Demonstration of ModerateClassificationTracker functionality

This script demonstrates how the moderate classification tracker works
by simulating a series of classifications and showing how consecutive
moderates are tracked and warnings are generated.
"""

import sys
import os
import logging
from datetime import datetime, timedelta
from unittest.mock import Mock, MagicMock

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

from src.strad_monitoring.database.moderate_tracker import ModerateClassificationTracker


def create_mock_database():
    """Create a mock database interface for demonstration."""
    db = Mock()
    db._is_database_available = True
    
    # Store classifications in memory for demo
    db._classification_history = []
    
    def mock_get_connection():
        conn = Mock()
        cursor = Mock()
        
        def mock_execute(query, params):
            # Return stored classifications
            strad_id = params[0]
            window_start = params[1]
            window_end = params[2]
            
            # Filter classifications by strad_id and time window
            results = [
                (c[1], c[2])  # (classification, timestamp)
                for c in db._classification_history
                if c[0] == strad_id and window_start <= c[2] <= window_end
            ]
            cursor.fetchall.return_value = sorted(
                results,
                key=lambda x: x[1],
                reverse=True
            )
        
        cursor.execute = mock_execute
        conn.cursor.return_value = cursor
        return conn
    
    db._get_connection = mock_get_connection
    
    return db


def simulate_classification(tracker, db, strad_id, classification, confidence, hours_ago=0):
    """
    Simulate a classification and record it in tracker.
    
    Args:
        tracker: ModerateClassificationTracker instance
        db: Mock database interface
        strad_id: Strad CHE number
        classification: Classification result
        confidence: Confidence score
        hours_ago: How many hours ago this classification occurred (for simulation)
    """
    timestamp = datetime.now() - timedelta(hours=hours_ago)
    
    # Store in mock database history
    db._classification_history.append((strad_id, classification, timestamp))
    
    # Record in tracker
    print(f"\n{'='*70}")
    print(f"Recording classification for {strad_id}")
    print(f"  Classification: {classification}")
    print(f"  Confidence: {confidence:.2f}")
    print(f"  Timestamp: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*70}")
    
    tracker.record_classification(
        strad_id=strad_id,
        classification=classification,
        confidence=confidence,
        timestamp=timestamp
    )
    
    current_count = tracker.get_consecutive_count(strad_id)
    print(f"✓ Consecutive moderate count: {current_count}")


def demo_scenario_1_gradual_misalignment():
    """
    Scenario 1: Gradual misalignment over time
    
    Simulates a strad that gradually develops misalignment,
    triggering a warning after 3 consecutive moderates.
    """
    print("\n" + "="*70)
    print("SCENARIO 1: Gradual Misalignment")
    print("="*70)
    print("Simulating a strad that gradually develops misalignment...")
    
    db = create_mock_database()
    tracker = ModerateClassificationTracker(db, time_window_hours=24)
    
    # Hour 0: Properly aligned
    simulate_classification(tracker, db, 'SC042', 'none', 0.95, hours_ago=6)
    
    # Hour 2: First moderate
    simulate_classification(tracker, db, 'SC042', 'moderate', 0.65, hours_ago=4)
    
    # Hour 4: Second moderate
    simulate_classification(tracker, db, 'SC042', 'moderate', 0.58, hours_ago=2)
    
    # Hour 6: Third moderate - WARNING!
    simulate_classification(tracker, db, 'SC042', 'moderate', 0.62, hours_ago=0)
    
    print("\n" + "="*70)
    print("RESULT: Warning notification sent after 3 consecutive moderates")
    print("="*70)


def demo_scenario_2_transient_issue():
    """
    Scenario 2: Transient misalignment that self-corrects
    
    Simulates a strad with temporary misalignment that resolves,
    showing how the counter resets.
    """
    print("\n" + "="*70)
    print("SCENARIO 2: Transient Issue (Self-Correcting)")
    print("="*70)
    print("Simulating a strad with temporary misalignment that resolves...")
    
    db = create_mock_database()
    tracker = ModerateClassificationTracker(db, time_window_hours=24)
    
    # Hour 0: Properly aligned
    simulate_classification(tracker, db, 'SC078', 'none', 0.92, hours_ago=6)
    
    # Hour 2: First moderate
    simulate_classification(tracker, db, 'SC078', 'moderate', 0.61, hours_ago=4)
    
    # Hour 4: Issue resolves - counter resets
    simulate_classification(tracker, db, 'SC078', 'none', 0.88, hours_ago=2)
    
    # Hour 6: Another moderate (but counter was reset)
    simulate_classification(tracker, db, 'SC078', 'moderate', 0.55, hours_ago=0)
    
    print("\n" + "="*70)
    print("RESULT: No warning - counter reset when issue resolved")
    print("="*70)


def demo_scenario_3_critical_escalation():
    """
    Scenario 3: Misalignment escalates to critical
    
    Simulates moderate misalignment that escalates to critical,
    showing how the counter resets.
    """
    print("\n" + "="*70)
    print("SCENARIO 3: Escalation to Critical")
    print("="*70)
    print("Simulating misalignment that escalates to critical...")
    
    db = create_mock_database()
    tracker = ModerateClassificationTracker(db, time_window_hours=24)
    
    # Hour 0: First moderate
    simulate_classification(tracker, db, 'SC115', 'moderate', 0.63, hours_ago=4)
    
    # Hour 2: Second moderate
    simulate_classification(tracker, db, 'SC115', 'moderate', 0.68, hours_ago=2)
    
    # Hour 4: Escalates to critical - counter resets
    simulate_classification(tracker, db, 'SC115', 'critical', 0.85, hours_ago=0)
    
    print("\n" + "="*70)
    print("RESULT: No warning - escalated to critical before reaching 3 moderates")
    print("       Strad would be added to critical exclusion list")
    print("="*70)


def demo_scenario_4_multiple_strads():
    """
    Scenario 4: Tracking multiple strads simultaneously
    
    Demonstrates tracking consecutive moderates across multiple strads.
    """
    print("\n" + "="*70)
    print("SCENARIO 4: Multiple Strads Tracking")
    print("="*70)
    print("Tracking consecutive moderates for multiple strads...")
    
    db = create_mock_database()
    tracker = ModerateClassificationTracker(db, time_window_hours=24)
    
    # SC042: 2 consecutive moderates
    simulate_classification(tracker, db, 'SC042', 'moderate', 0.65, hours_ago=2)
    simulate_classification(tracker, db, 'SC042', 'moderate', 0.60, hours_ago=0)
    
    # SC078: 1 moderate
    simulate_classification(tracker, db, 'SC078', 'moderate', 0.55, hours_ago=1)
    
    # SC115: 3 consecutive moderates - WARNING!
    simulate_classification(tracker, db, 'SC115', 'moderate', 0.58, hours_ago=5)
    simulate_classification(tracker, db, 'SC115', 'moderate', 0.62, hours_ago=3)
    simulate_classification(tracker, db, 'SC115', 'moderate', 0.59, hours_ago=0)
    
    print("\n" + "="*70)
    print("FINAL COUNTS:")
    all_counts = tracker.get_all_counts()
    for strad_id, count in sorted(all_counts.items()):
        status = "⚠️ WARNING SENT" if count == 3 else ""
        print(f"  {strad_id}: {count} consecutive moderate(s) {status}")
    print("="*70)


def main():
    """Run all demonstration scenarios."""
    print("\n" + "="*70)
    print("ModerateClassificationTracker Demonstration")
    print("="*70)
    print("\nThis demo shows how the tracker handles different scenarios:")
    print("1. Gradual misalignment leading to warning")
    print("2. Transient issues that self-correct")
    print("3. Escalation to critical classification")
    print("4. Tracking multiple strads simultaneously")
    
    # Run all scenarios
    demo_scenario_1_gradual_misalignment()
    input("\nPress Enter to continue to Scenario 2...")
    
    demo_scenario_2_transient_issue()
    input("\nPress Enter to continue to Scenario 3...")
    
    demo_scenario_3_critical_escalation()
    input("\nPress Enter to continue to Scenario 4...")
    
    demo_scenario_4_multiple_strads()
    
    print("\n" + "="*70)
    print("Demo complete!")
    print("="*70)


if __name__ == '__main__':
    main()

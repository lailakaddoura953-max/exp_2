"""
Quick test script to verify SQLite fallback mechanism works correctly.

This script tests the database interface with SQLite fallback enabled.
"""

import logging
import sys
import os

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from strad_monitoring.database import DatabaseInterface

def test_sqlite_fallback():
    """Test SQLite fallback with the test database."""
    
    print("\n" + "="*60)
    print("Testing SQLite Fallback Mechanism")
    print("="*60 + "\n")
    
    # Create database interface with SQLite fallback
    db = DatabaseInterface(
        connection_string="DRIVER={ODBC Driver 17 for SQL Server};SERVER=invalid-server;DATABASE=Test;",
        enable_fallback=True,
        use_sqlite_fallback=True,
        sqlite_db_path="tests/test.db",
        fallback_data_source="sqlite"
    )
    
    print("✓ DatabaseInterface initialized with SQLite fallback\n")
    
    # Test: Get 10 eligible strads
    print("Test 1: Fetching 10 eligible strads from SQLite...")
    strads = db.get_eligible_strads(10)
    
    print(f"✓ Retrieved {len(strads)} strads: {strads}\n")
    
    # Verify strads are in correct format
    for strad_id in strads:
        assert strad_id.startswith("SC"), f"Invalid strad format: {strad_id}"
        assert len(strad_id) == 5, f"Invalid strad length: {strad_id}"
    
    print("✓ All strads have valid format (SCXXX)\n")
    
    # Test: Get 5 strads
    print("Test 2: Fetching 5 eligible strads from SQLite...")
    strads_5 = db.get_eligible_strads(5)
    
    print(f"✓ Retrieved {len(strads_5)} strads: {strads_5}\n")
    assert len(strads_5) <= 5, "Should return at most 5 strads"
    
    # Cleanup
    db.close()
    
    print("="*60)
    print("✓ All tests passed! SQLite fallback working correctly.")
    print("="*60 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        test_sqlite_fallback()
        print("\n✅ SUCCESS: SQLite fallback is fully functional!\n")
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)

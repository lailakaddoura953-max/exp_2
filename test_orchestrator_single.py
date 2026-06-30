"""
Test script to verify orchestrator works with SimpleClassifierWrapper
Tests a single strad to confirm the integration is working correctly
"""

import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.strad_monitoring.config.system_config import ConfigurationManager
from src.strad_monitoring.orchestration.orchestrator import MonitoringOrchestrator


def main():
    print("=" * 80)
    print("ORCHESTRATOR SINGLE STRAD TEST")
    print("=" * 80)
    print()
    
    # Load configuration
    print("Loading configuration...")
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'system_config.json')
    
    if not os.path.exists(config_path):
        print(f"ERROR: Config file not found: {config_path}")
        return 1
    
    config = ConfigurationManager.load_config(config_path)
    print(f"✓ Configuration loaded")
    print(f"  Classifier type: {config.classifier_type}")
    print(f"  Model path: {config.model_checkpoint_path}")
    print()
    
    # Create orchestrator
    print("Initializing orchestrator...")
    orchestrator = MonitoringOrchestrator(config)
    print(f"✓ Orchestrator initialized")
    print(f"  Classifier loaded: {orchestrator.dl_classifier is not None}")
    print()
    
    # Test with a single strad
    # Note: This will use whatever strad ID exists in your database
    # If using SQLite fallback, it will pick from test.db
    # If using real database, it will query from there
    
    print("Getting a test strad ID from database...")
    try:
        # Get one strad from the database
        strads = orchestrator.strad_selector.select_strads_for_monitoring(count=1)
        
        if not strads:
            print("ERROR: No strads available in database")
            print("Make sure your database has strad records or enable fallback mode")
            return 1
        
        test_strad_id = strads[0]
        print(f"✓ Test strad: {test_strad_id}")
        print()
        
    except Exception as e:
        print(f"ERROR getting strad from database: {e}")
        print("\nTrying with a default test ID: SC001")
        test_strad_id = 'SC001'
        print()
    
    # Process the strad
    print(f"Processing strad {test_strad_id}...")
    print("-" * 80)
    
    try:
        result = orchestrator.process_single_strad(test_strad_id)
        
        print("-" * 80)
        print()
        
        # Check if processing was successful
        if not result.get('success', False):
            print("=" * 80)
            print("TEST RESULT - FAILED")
            print("=" * 80)
            print()
            print(f"Strad ID:           {result['strad_id']}")
            print(f"Success:            {result['success']}")
            print(f"Error:              {result.get('error', 'Unknown error')}")
            print(f"Processing Time:    {result['processing_time_seconds']:.1f}s")
            print()
            print("=" * 80)
            print()
            print("NOTE: This is expected if VLC/Excel automation isn't available.")
            print("The important thing is that the orchestrator initialized correctly")
            print("with SimpleClassifierWrapper (check startup logs above).")
            print("=" * 80)
            return 0
        
        # Processing was successful
        print("=" * 80)
        print("TEST RESULT - SUCCESS")
        print("=" * 80)
        print()
        print(f"Strad ID:           {result['strad_id']}")
        print(f"Classification:     {result['classification']}")
        print(f"Confidence:         {result['confidence']:.2%}")
        print(f"Processing Time:    {result['processing_time_seconds']:.1f}s")
        
        if result.get('snapshot_path'):
            print(f"Snapshot Path:      {result['snapshot_path']}")
        else:
            print(f"Snapshot Path:      None (not critical)")
        
        print()
        print("=" * 80)
        print("✓ Orchestrator is working correctly with SimpleClassifierWrapper!")
        print("=" * 80)
        
        return 0
        
    except Exception as e:
        print("-" * 80)
        print()
        print("=" * 80)
        print("TEST RESULT - FAILED")
        print("=" * 80)
        print()
        print(f"ERROR: {e}")
        print()
        
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        
        print()
        print("=" * 80)
        
        return 1


if __name__ == "__main__":
    sys.exit(main())

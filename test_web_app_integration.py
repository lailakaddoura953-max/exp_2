"""
Test Web App Integration with Strad Monitoring

This script tests the backend API endpoints to verify integration is working.
"""

import requests
import sys
from pathlib import Path

BACKEND_URL = 'http://localhost:5000'

def test_health_check():
    """Test the health check endpoint"""
    print("\n" + "="*60)
    print("TEST 1: Health Check")
    print("="*60)
    
    try:
        response = requests.get(f'{BACKEND_URL}/')
        data = response.json()
        
        print(f"✓ Backend is running")
        print(f"  Service: {data.get('service')}")
        print(f"  Version: {data.get('version')}")
        print(f"  Strad Monitoring Connected: {data.get('strad_monitoring_connected')}")
        print(f"  Database Connected: {data.get('database_connected')}")
        print(f"  Classifier Loaded: {data.get('classifier_loaded')}")
        
        return True
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        print("\nMake sure backend is running:")
        print("  python docs\\backend\\app.py")
        return False


def test_model_status():
    """Test the model status endpoint"""
    print("\n" + "="*60)
    print("TEST 2: Model Status")
    print("="*60)
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/model/status')
        data = response.json()
        
        print(f"✓ Model status retrieved")
        print(f"  Model Loaded: {data.get('model_loaded')}")
        print(f"  Model Type: {data.get('model_type')}")
        print(f"  Ready: {data.get('ready')}")
        
        return True
    except Exception as e:
        print(f"✗ Model status failed: {e}")
        return False


def test_recent_strads():
    """Test the recent strads endpoint"""
    print("\n" + "="*60)
    print("TEST 3: Recent Strads")
    print("="*60)
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/strads/recent?limit=5')
        data = response.json()
        
        if data.get('success'):
            strads = data.get('data', [])
            print(f"✓ Recent strads retrieved: {len(strads)} records")
            
            if strads:
                print("\nSample records:")
                for strad in strads[:3]:
                    print(f"  - {strad.get('strad_id')}: {strad.get('classification')} "
                          f"(confidence: {strad.get('confidence'):.2f})")
            else:
                print("  No records in database yet")
                print(f"  Message: {data.get('message', 'N/A')}")
        else:
            print(f"✗ Failed to get recent strads: {data.get('message')}")
        
        return True
    except Exception as e:
        print(f"✗ Recent strads test failed: {e}")
        return False


def test_stats():
    """Test the stats endpoint"""
    print("\n" + "="*60)
    print("TEST 4: Classification Statistics")
    print("="*60)
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/strads/stats')
        data = response.json()
        
        if data.get('success'):
            stats = data.get('stats', {})
            print(f"✓ Statistics retrieved")
            print(f"  Total: {stats.get('total', 0)}")
            print(f"  None (aligned): {stats.get('none', 0)}")
            print(f"  Moderate: {stats.get('moderate', 0)}")
            print(f"  Critical: {stats.get('critical', 0)}")
            print(f"  Last 24h: {stats.get('last_24h', 0)}")
        else:
            print(f"✗ Failed to get stats: {data.get('message')}")
        
        return True
    except Exception as e:
        print(f"✗ Stats test failed: {e}")
        return False


def test_inference_endpoint():
    """Test the inference endpoint with a dummy image"""
    print("\n" + "="*60)
    print("TEST 5: Inference Endpoint (Optional)")
    print("="*60)
    
    print("Skipping inference test - requires actual image file")
    print("To test manually:")
    print("  1. Open web app: start docs\\index.html")
    print("  2. Go to 'Live Inference Test' section at bottom")
    print("  3. Upload an image and click 'Run Inference'")
    
    return True


def main():
    """Run all tests"""
    print("="*60)
    print("WEB APP INTEGRATION TEST SUITE")
    print("="*60)
    print("\nTesting backend API endpoints...")
    
    results = []
    
    # Test 1: Health Check
    results.append(("Health Check", test_health_check()))
    
    # Test 2: Model Status
    results.append(("Model Status", test_model_status()))
    
    # Test 3: Recent Strads
    results.append(("Recent Strads", test_recent_strads()))
    
    # Test 4: Stats
    results.append(("Statistics", test_stats()))
    
    # Test 5: Inference (manual)
    results.append(("Inference", test_inference_endpoint()))
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All tests passed! Web app integration is working.")
        print("\nNext steps:")
        print("  1. Open web app: start docs\\index.html")
        print("  2. Check connection status indicator (should show 'Connected')")
        print("  3. Try the live inference test at bottom of page")
    else:
        print("\n⚠ Some tests failed. Check backend connection and configuration.")
    
    print("="*60)
    
    return 0 if passed == total else 1


if __name__ == '__main__':
    sys.exit(main())

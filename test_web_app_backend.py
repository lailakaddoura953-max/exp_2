"""
Test script for web app backend integration

This script verifies that the web app backend is working correctly by:
1. Starting the backend server in a subprocess
2. Testing all API endpoints
3. Verifying responses are correct
4. Stopping the backend gracefully

Usage:
    python test_web_app_backend.py
"""

import sys
import time
import requests
import subprocess
from pathlib import Path

BACKEND_URL = "http://localhost:5000"
TIMEOUT = 5  # seconds


def print_header(message):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(message)
    print("=" * 70)


def print_success(message):
    """Print success message"""
    print(f"✓ {message}")


def print_error(message):
    """Print error message"""
    print(f"✗ {message}")


def print_info(message):
    """Print info message"""
    print(f"  {message}")


def wait_for_backend(timeout=10):
    """Wait for backend to be ready"""
    print_info(f"Waiting for backend to start (max {timeout}s)...")
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(f"{BACKEND_URL}/", timeout=1)
            if response.status_code == 200:
                print_success("Backend is ready")
                return True
        except requests.exceptions.RequestException:
            time.sleep(0.5)
    
    return False


def test_health_endpoint():
    """Test GET / endpoint"""
    print_header("Test 1: Health Check Endpoint")
    
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=TIMEOUT)
        
        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        
        # Check required fields
        required_fields = [
            'status', 'service', 'version', 
            'strad_monitoring_connected', 
            'database_connected', 
            'classifier_loaded'
        ]
        
        for field in required_fields:
            if field not in data:
                print_error(f"Missing field: {field}")
                return False
        
        print_success("Health check endpoint working")
        print_info(f"Status: {data['status']}")
        print_info(f"Service: {data['service']}")
        print_info(f"Version: {data['version']}")
        print_info(f"Strad Monitoring Connected: {data['strad_monitoring_connected']}")
        print_info(f"Database Connected: {data['database_connected']}")
        print_info(f"Classifier Loaded: {data['classifier_loaded']}")
        
        return True
        
    except Exception as e:
        print_error(f"Health check failed: {e}")
        return False


def test_strads_recent_endpoint():
    """Test GET /api/strads/recent endpoint"""
    print_header("Test 2: Recent Strads Endpoint")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/strads/recent?limit=5", 
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        
        # Check response structure
        if 'success' not in data:
            print_error("Missing 'success' field")
            return False
        
        if 'data' not in data:
            print_error("Missing 'data' field")
            return False
        
        print_success("Recent strads endpoint working")
        print_info(f"Success: {data['success']}")
        print_info(f"Data count: {len(data['data'])}")
        
        if data['data']:
            print_info(f"Sample strad: {data['data'][0]}")
        else:
            print_info("No strads in database (expected for empty database)")
        
        return True
        
    except Exception as e:
        print_error(f"Recent strads test failed: {e}")
        return False


def test_strads_stats_endpoint():
    """Test GET /api/strads/stats endpoint"""
    print_header("Test 3: Strads Statistics Endpoint")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/strads/stats", 
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        
        # Check response structure
        if 'success' not in data:
            print_error("Missing 'success' field")
            return False
        
        if 'stats' not in data:
            print_error("Missing 'stats' field")
            return False
        
        stats = data['stats']
        required_stats = ['total', 'none', 'moderate', 'critical', 'last_24h']
        
        for stat in required_stats:
            if stat not in stats:
                print_error(f"Missing stat: {stat}")
                return False
        
        print_success("Statistics endpoint working")
        print_info(f"Total: {stats['total']}")
        print_info(f"None: {stats['none']}")
        print_info(f"Moderate: {stats['moderate']}")
        print_info(f"Critical: {stats['critical']}")
        print_info(f"Last 24h: {stats['last_24h']}")
        
        return True
        
    except Exception as e:
        print_error(f"Statistics test failed: {e}")
        return False


def test_model_status_endpoint():
    """Test GET /api/model/status endpoint"""
    print_header("Test 4: Model Status Endpoint")
    
    try:
        response = requests.get(
            f"{BACKEND_URL}/api/model/status", 
            timeout=TIMEOUT
        )
        
        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        
        # Check required fields
        required_fields = [
            'model_loaded', 'model_type', 'ready',
            'database_connected', 'strad_monitoring_available'
        ]
        
        for field in required_fields:
            if field not in data:
                print_error(f"Missing field: {field}")
                return False
        
        print_success("Model status endpoint working")
        print_info(f"Model Loaded: {data['model_loaded']}")
        print_info(f"Model Type: {data['model_type']}")
        print_info(f"Ready: {data['ready']}")
        print_info(f"Database Connected: {data['database_connected']}")
        print_info(f"Strad Monitoring Available: {data['strad_monitoring_available']}")
        
        return True
        
    except Exception as e:
        print_error(f"Model status test failed: {e}")
        return False


def test_inference_endpoint():
    """Test POST /api/inference endpoint with synthetic image"""
    print_header("Test 5: Inference Endpoint (Single Image)")
    
    try:
        # Create a small synthetic image (1x1 pixel, black)
        import io
        from PIL import Image
        import numpy as np
        
        # Create synthetic image
        img_array = np.zeros((100, 100, 3), dtype=np.uint8)
        img = Image.fromarray(img_array)
        
        # Convert to bytes
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        img_bytes.seek(0)
        
        # Send request
        files = {'image': ('test.jpg', img_bytes, 'image/jpeg')}
        response = requests.post(
            f"{BACKEND_URL}/api/inference",
            files=files,
            timeout=TIMEOUT * 2  # Inference may take longer
        )
        
        if response.status_code != 200:
            print_error(f"Expected status 200, got {response.status_code}")
            return False
        
        data = response.json()
        
        # Check response structure
        required_fields = [
            'success', 'classification', 'confidence',
            'processing_time_ms', 'description', 'timestamp', 'mode'
        ]
        
        for field in required_fields:
            if field not in data:
                print_error(f"Missing field: {field}")
                return False
        
        print_success("Inference endpoint working")
        print_info(f"Success: {data['success']}")
        print_info(f"Classification: {data['classification']}")
        print_info(f"Confidence: {data['confidence']:.2%}")
        print_info(f"Processing Time: {data['processing_time_ms']:.1f} ms")
        print_info(f"Mode: {data['mode']}")
        print_info(f"Description: {data['description']}")
        
        return True
        
    except Exception as e:
        print_error(f"Inference test failed: {e}")
        return False


def main():
    """Main test function"""
    print_header("WEB APP BACKEND INTEGRATION TEST")
    print_info("This script tests all backend API endpoints")
    print_info("Make sure the backend is running before starting tests")
    print()
    
    # Check if backend is already running
    try:
        response = requests.get(f"{BACKEND_URL}/", timeout=1)
        if response.status_code == 200:
            print_success("Backend is already running")
            backend_already_running = True
        else:
            backend_already_running = False
    except requests.exceptions.RequestException:
        backend_already_running = False
    
    if not backend_already_running:
        print_error("Backend is not running")
        print_info("Please start the backend first:")
        print_info("  python docs\\backend\\app.py")
        print()
        print_info("Or run this script with automatic backend startup:")
        print_info("  (Not implemented yet - manual start required)")
        return 1
    
    # Run all tests
    tests = [
        ("Health Check", test_health_endpoint),
        ("Recent Strads", test_strads_recent_endpoint),
        ("Statistics", test_strads_stats_endpoint),
        ("Model Status", test_model_status_endpoint),
        ("Inference", test_inference_endpoint),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {e}")
            results.append((test_name, False))
    
    # Print summary
    print_header("TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✓ PASSED" if result else "✗ FAILED"
        print(f"  {test_name:20} {status}")
    
    print()
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("All tests passed!")
        return 0
    else:
        print_error(f"{total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"Unexpected error: {e}")
        sys.exit(1)

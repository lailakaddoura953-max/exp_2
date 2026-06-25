"""
Simple HTTP server for serving the web app frontend

This script starts a local HTTP server on port 8000 to serve the web app.
The frontend needs to be served via HTTP (not file://) for CORS to work properly.

Usage:
    python start_frontend_server.py
    
Then open: http://localhost:8000
"""

import http.server
import socketserver
import os
from pathlib import Path

# Configuration
PORT = 8000
DIRECTORY = "docs"


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom handler to serve files from docs directory"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()


def main():
    """Start the HTTP server"""
    
    # Check if docs directory exists
    if not Path(DIRECTORY).exists():
        print(f"ERROR: Directory '{DIRECTORY}' not found")
        print(f"Make sure you're running this from the project root directory")
        return 1
    
    # Check if index.html exists
    if not Path(DIRECTORY, "index.html").exists():
        print(f"ERROR: {DIRECTORY}/index.html not found")
        return 1
    
    print("=" * 80)
    print("STRAD CARRIER MONITORING - FRONTEND SERVER")
    print("=" * 80)
    print()
    print(f"Serving files from: {DIRECTORY}/")
    print(f"Server running on: http://localhost:{PORT}")
    print()
    print("=" * 80)
    print("HOW TO USE:")
    print("=" * 80)
    print()
    print("1. Keep this terminal open (frontend server)")
    print("2. In another terminal, start the backend:")
    print("   python docs\\backend\\app.py")
    print()
    print("3. Open in your browser:")
    print(f"   http://localhost:{PORT}")
    print()
    print("4. Check connection status in top right corner")
    print("   - Green dot (●) = Backend connected")
    print("   - Red dot (○) = Disconnected (demo mode)")
    print()
    print("=" * 80)
    print("Press Ctrl+C to stop the server")
    print("=" * 80)
    print()
    
    # Start server
    try:
        with socketserver.TCPServer(("", PORT), CustomHTTPRequestHandler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
        return 0
    except OSError as e:
        if "address already in use" in str(e).lower():
            print(f"\nERROR: Port {PORT} is already in use")
            print(f"Either:")
            print(f"  1. Stop the other process using port {PORT}")
            print(f"  2. Or change PORT in this script")
        else:
            print(f"\nERROR: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())

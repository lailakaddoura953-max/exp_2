"""
Video Capture Module

Provides automated full-window screenshot capture from Axis camera web viewer
pages for monitoring cycles, using a headless browser (Playwright).

Direct RTSP frame-grabbing was evaluated and does not work reliably against
these Axis encoders (browser access fails outright; VLC only shows a single
corner of the feed for the same RTSP path), so capture is done by driving a
headless browser to the camera's web viewer page instead.

Components:
- WebCapture: Navigate to a camera's viewer page, log in if needed, and
  capture a full-window screenshot.

Usage:
    from src.strad_monitoring.video_capture import WebCapture

    capture = WebCapture(
        username="admin",
        password="password"
    )

    filepath, success = capture.capture_frame(
        ip_address="192.168.1.100",
        strad_id="SC001",
        snapshot_dir="/path/to/snapshots"
    )
"""

from .web_capture import WebCapture

__all__ = ['WebCapture']

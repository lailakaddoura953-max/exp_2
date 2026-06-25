"""
Strad Carrier Monitoring Automation System

This package provides automated camera misalignment detection for Strad Carrier vehicles.
It integrates SQL Server database queries, Excel video feed automation, VLC snapshot capture,
and deep learning classification to monitor 135 Strad Carriers on hourly cycles.

Main components:
- config: Configuration management and validation
- database: SQL Server interface with local testing fallback
- excel_automation: COM automation for Excel video encoder control
- vlc_capture: VLC media player window capture
- dl_classifier: Deep learning misalignment detection wrapper
- storage: Temporary and permanent snapshot storage
- orchestration: Hourly cycle coordination and scheduling
- logging: Structured logging with rotation
- utils: Utility functions (timing, retry, exceptions, alerting)
"""

__version__ = "1.0.0"
__author__ = "Strad Monitoring Team"

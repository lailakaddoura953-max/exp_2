"""
Pipeline module for camera misalignment detection system

Provides the main processing pipeline that integrates all components.
"""

from src.pipeline.main_processor import (
    MisalignmentDetectionPipeline,
    PipelineConfig,
    PipelineStatistics
)

__all__ = [
    'MisalignmentDetectionPipeline',
    'PipelineConfig',
    'PipelineStatistics'
]

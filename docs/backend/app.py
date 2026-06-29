"""
Flask Backend for Camera Misalignment Detection - Live Inference API
Provides REST API endpoint for real-time misalignment detection
Connects to strad_monitoring components for real data
"""

from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import numpy as np
from PIL import Image
import io
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import torch

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / 'src'))

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Try to import strad_monitoring components
try:
    from strad_monitoring.database.database_interface import DatabaseInterface
    from strad_monitoring.config.system_config import ConfigurationManager
    # Note: Classifier wrappers are imported conditionally based on config
    STRAD_MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"⚠ Strad monitoring components not available: {e}")
    print("⚠ Using mock data mode")
    STRAD_MONITORING_AVAILABLE = False

# Initialize components if available
db_interface = None
dl_classifier = None
config = None

if STRAD_MONITORING_AVAILABLE:
    try:
        # Load configuration
        config_path = project_root / 'system_config.json'
        if config_path.exists():
            config = ConfigurationManager.load_config(str(config_path))
            
            # Initialize database interface
            db_interface = DatabaseInterface(
                connection_string=config.database_connection_string,
                enable_fallback=config.enable_local_testing_mode,
                fallback_data_path=config.fallback_data_path,
                fallback_data_source=config.fallback_data_source,
                use_sqlite_fallback=getattr(config, 'use_sqlite_fallback', False),
                sqlite_db_path=getattr(config, 'sqlite_db_path', 'tests/test.db'),
                strad_query_sql_file=getattr(config, 'strad_query_sql_file', 'strad_query.sql')
            )
            print("✓ Database interface initialized")
            
            # Initialize classifier based on configuration
            # The classifier type determines which wrapper class is used:
            # - 'simple_classifier': SimpleClassifierWrapper for models trained with train_strad_classifier.py
            # - 'inference_engine': DLClassifierWrapper for InferenceEngine-based models
            try:
                # Read classifier_type from config with default to 'inference_engine'
                classifier_type = getattr(config, 'classifier_type', 'inference_engine')
                
                # Auto-detect device (CUDA for GPU acceleration if available, otherwise CPU)
                device = 'cuda' if torch.cuda.is_available() else 'cpu'
                print(f"Using classifier: {classifier_type}, device: {device}")
                
                if classifier_type == 'simple_classifier':
                    # Import and instantiate SimpleClassifierWrapper
                    # This is for models trained with the simplified training script
                    from strad_monitoring.dl_classifier.simple_classifier_wrapper import SimpleClassifierWrapper
                    
                    dl_classifier = SimpleClassifierWrapper(
                        model_checkpoint_path=config.model_checkpoint_path,
                        device=device,
                        image_size=640
                    )
                    print("✓ SimpleClassifierWrapper initialized")
                
                elif classifier_type == 'inference_engine':
                    # Import and instantiate DLClassifierWrapper
                    # This is for legacy InferenceEngine-based models
                    from strad_monitoring.dl_classifier.classifier_wrapper import DLClassifierWrapper
                    
                    dl_classifier = DLClassifierWrapper(
                        model_checkpoint_path=config.model_checkpoint_path,
                        config=config.dl_model_config,
                        device=device
                    )
                    print("✓ DLClassifierWrapper initialized")
                
                else:
                    # Invalid classifier_type value - raise error
                    # This validates that only supported classifier types are used
                    raise ValueError(
                        f"Invalid classifier_type: '{classifier_type}'. "
                        f"Must be 'simple_classifier' or 'inference_engine'"
                    )
                
            except Exception as e:
                # Handle classifier initialization failures gracefully
                # In web app mode, we can fall back to mock classification
                print(f"⚠ Classifier not available: {e}")
                dl_classifier = None
        else:
            print(f"⚠ Config file not found: {config_path}")
    except Exception as e:
        print(f"⚠ Failed to initialize strad monitoring: {e}")
        STRAD_MONITORING_AVAILABLE = False


@app.route('/')
def home():
    """Health check endpoint"""
    return jsonify({
        'status': 'running',
        'service': 'Camera Misalignment Detection API',
        'version': '1.0.0',
        'strad_monitoring_connected': STRAD_MONITORING_AVAILABLE,
        'database_connected': db_interface is not None,
        'classifier_loaded': dl_classifier is not None
    })


@app.route('/api/strads/recent', methods=['GET'])
def get_recent_strads():
    """
    Get recent strad classifications with snapshots
    
    Query params:
        - limit: Number of results (default 10)
        - severity: Filter by severity (optional: none, moderate, critical)
    
    Returns:
        - JSON array of recent classifications with snapshot paths
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        severity_filter = request.args.get('severity', None)
        
        if not db_interface:
            # Return mock data when database not available
            return jsonify({
                'success': True,
                'data': [],
                'message': 'Database not connected - using placeholder mode'
            })
        
        # Query recent classifications from database
        conn = db_interface._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT TOP (?) 
                strad_id, 
                classification, 
                confidence, 
                snapshot_path, 
                timestamp
            FROM classification_results
        """
        
        params = [limit]
        
        if severity_filter:
            query += " WHERE classification = ?"
            params.append(severity_filter)
        
        query += " ORDER BY timestamp DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        cursor.close()
        
        results = []
        for row in rows:
            results.append({
                'strad_id': row[0],
                'classification': row[1],
                'confidence': float(row[2]),
                'snapshot_path': row[3],
                'timestamp': row[4].isoformat() if row[4] else None,
                'has_snapshot': bool(row[3])
            })
        
        return jsonify({
            'success': True,
            'data': results,
            'count': len(results)
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Failed to fetch recent strads'
        }), 500


@app.route('/api/snapshot/<path:strad_id>', methods=['GET'])
def get_snapshot(strad_id):
    """
    Get snapshot image for a strad
    
    Path params:
        - strad_id: Strad identifier (e.g., SC042)
    
    Returns:
        - JPEG image or 404 if not found
    """
    try:
        if not config or not db_interface:
            return jsonify({'error': 'System not configured'}), 404
        
        # Query snapshot path from database
        conn = db_interface._get_connection()
        cursor = conn.cursor()
        
        query = """
            SELECT TOP 1 snapshot_path 
            FROM classification_results 
            WHERE strad_id = ? AND snapshot_path IS NOT NULL
            ORDER BY timestamp DESC
        """
        
        cursor.execute(query, (strad_id,))
        row = cursor.fetchone()
        cursor.close()
        
        if not row or not row[0]:
            return jsonify({'error': 'Snapshot not found'}), 404
        
        snapshot_path = Path(row[0])
        
        # Check if file exists
        if not snapshot_path.is_absolute():
            # Try relative to permanent storage path
            snapshot_path = Path(config.permanent_snapshot_path) / snapshot_path
        
        if not snapshot_path.exists():
            return jsonify({'error': 'Snapshot file not found on disk'}), 404
        
        # Send image file
        return send_file(
            str(snapshot_path),
            mimetype='image/jpeg',
            as_attachment=False
        )
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/strads/stats', methods=['GET'])
def get_strad_stats():
    """
    Get statistics about strad classifications
    
    Returns:
        - JSON with counts by severity, recent activity
    """
    try:
        if not db_interface:
            return jsonify({
                'success': True,
                'stats': {
                    'total': 0,
                    'none': 0,
                    'moderate': 0,
                    'critical': 0,
                    'last_24h': 0
                },
                'message': 'Database not connected - using placeholder mode'
            })
        
        conn = db_interface._get_connection()
        cursor = conn.cursor()
        
        # Count by severity
        cursor.execute("""
            SELECT classification, COUNT(*) 
            FROM classification_results 
            GROUP BY classification
        """)
        severity_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Count last 24 hours
        cursor.execute("""
            SELECT COUNT(*) 
            FROM classification_results 
            WHERE timestamp >= DATEADD(hour, -24, GETDATE())
        """)
        last_24h = cursor.fetchone()[0]
        
        cursor.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': sum(severity_counts.values()),
                'none': severity_counts.get('none', 0),
                'moderate': severity_counts.get('moderate', 0),
                'critical': severity_counts.get('critical', 0),
                'last_24h': last_24h
            }
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/inference', methods=['POST'])
def run_inference():
    """
    Run misalignment detection inference on uploaded camera images
    
    Expects:
        - 4 camera images as form-data: cam0, cam1, cam2, cam3
        - Each image should be JPEG or PNG
        OR
        - Single 'image' for single-camera classification (strad monitoring)
    
    Returns:
        - JSON with misalignment probability, severity, 6-DOF pose, uncertainty
    """
    try:
        # Check if single image (strad monitoring mode)
        if 'image' in request.files:
            return run_single_image_inference()
        
        # Multi-camera mode (original functionality)
        required_cameras = ['cam0', 'cam1', 'cam2', 'cam3']
        missing_cameras = [cam for cam in required_cameras if cam not in request.files]
        
        if missing_cameras:
            return jsonify({
                'error': f'Missing camera images: {", ".join(missing_cameras)}'
            }), 400
        
        # Load and validate images
        images = {}
        for cam_id in required_cameras:
            file = request.files[cam_id]
            
            if file.filename == '':
                return jsonify({'error': f'{cam_id} has no filename'}), 400
            
            # Read image
            image_bytes = file.read()
            image = Image.open(io.BytesIO(image_bytes))
            images[cam_id] = np.array(image)
        
        # For demo purposes, return mock inference results
        # In production, this would call the actual model inference
        
        # Mock probability based on simple heuristics
        # In reality, this would come from the deep learning model
        mock_probability = 0.15  # 15% misalignment probability
        
        # Determine severity based on probability
        if mock_probability < 0.3:
            severity = 'normal'
            description = 'All cameras are properly aligned. No action required.'
        elif mock_probability < 0.7:
            severity = 'minor'
            description = 'Minor misalignment detected. System compensating. Monitor for changes.'
        else:
            severity = 'critical'
            description = 'Critical misalignment detected! Immediate recalibration recommended.'
        
        # Mock 6-DOF pose (in production, from model output)
        pose = {
            'rotation': {
                'roll': 0.5,    # degrees
                'pitch': -0.3,  # degrees
                'yaw': 0.8      # degrees
            },
            'translation': {
                'x': 0.012,  # meters
                'y': -0.008, # meters
                'z': 0.015   # meters
            }
        }
        
        # Mock uncertainty estimates (in production, from model)
        uncertainty = {
            'aleatoric': 0.0234,   # Data uncertainty
            'epistemic': 0.0156    # Model uncertainty
        }
        
        # Return inference results
        return jsonify({
            'success': True,
            'misalignment_probability': mock_probability,
            'severity': severity,
            'description': description,
            'pose': pose,
            'uncertainty': uncertainty,
            'timestamp': datetime.now().isoformat()
        })
    
    except Exception as e:
        return jsonify({
            'error': f'Inference failed: {str(e)}'
        }), 500


def run_single_image_inference():
    """
    Run inference on single camera image (strad monitoring mode)
    Uses real DL classifier if available
    """
    try:
        file = request.files['image']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Read and process image
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        image_array = np.array(image)
        
        # Ensure RGB
        if len(image_array.shape) == 2:
            image_array = np.stack([image_array] * 3, axis=-1)
        elif image_array.shape[2] == 4:
            image_array = image_array[:, :, :3]
        
        # Use real classifier if available
        if dl_classifier:
            result = dl_classifier.classify_snapshot(image_array)
            
            return jsonify({
                'success': True,
                'classification': result.severity,
                'confidence': float(result.confidence),
                'processing_time_ms': float(result.processing_time_ms),
                'description': get_severity_description(result.severity, result.confidence),
                'timestamp': datetime.now().isoformat(),
                'mode': 'real_classifier'
            })
        else:
            # Mock classification
            mock_confidence = 0.75
            mock_severity = 'none'
            
            return jsonify({
                'success': True,
                'classification': mock_severity,
                'confidence': mock_confidence,
                'processing_time_ms': 45.0,
                'description': get_severity_description(mock_severity, mock_confidence),
                'timestamp': datetime.now().isoformat(),
                'mode': 'mock'
            })
    
    except Exception as e:
        return jsonify({
            'error': f'Single image inference failed: {str(e)}'
        }), 500


def get_severity_description(severity, confidence):
    """Get human-readable description for classification result"""
    if severity == 'critical':
        return f'🔴 CRITICAL MISALIGNMENT ({confidence:.1%} confidence) - Camera requires immediate adjustment'
    elif severity == 'moderate':
        return f'🟡 MODERATE MISALIGNMENT ({confidence:.1%} confidence) - Continue monitoring'
    else:
        return f'🟢 NO MISALIGNMENT ({confidence:.1%} confidence) - Camera properly aligned'


@app.route('/api/model/status', methods=['GET'])
def model_status():
    """Check if model is loaded and ready"""
    classifier_type = getattr(config, 'classifier_type', 'inference_engine') if config else 'unknown'
    
    return jsonify({
        'model_loaded': dl_classifier is not None,
        'classifier_type': classifier_type,
        'model_type': 'strad_monitoring' if dl_classifier else 'mock',
        'ready': True,
        'database_connected': db_interface is not None,
        'strad_monitoring_available': STRAD_MONITORING_AVAILABLE
    })

if __name__ == '__main__':
    print("=" * 60)
    print("Camera Misalignment Detection - Backend API")
    print("=" * 60)
    print(f"\nStrad Monitoring Connected: {STRAD_MONITORING_AVAILABLE}")
    print(f"Database Connected: {db_interface is not None}")
    print(f"DL Classifier Loaded: {dl_classifier is not None}")
    print("\nStarting Flask server on http://localhost:5000")
    print("API Endpoints:")
    print("  - GET  /                     Health check")
    print("  - POST /api/inference        Run inference on camera images")
    print("  - GET  /api/model/status     Check model status")
    print("  - GET  /api/strads/recent    Get recent strad classifications")
    print("  - GET  /api/snapshot/<id>    Get snapshot image for strad")
    print("  - GET  /api/strads/stats     Get classification statistics")
    print("\nPress CTRL+C to stop the server")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

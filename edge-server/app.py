"""
EDGE Server - Flask API
BierPass Beverage Dispenser Control

Endpoints:
- GET  /edge/health   - Health check
- GET  /edge/status   - Detailed status
- POST /edge/authorize - Authorize and dispense
- POST /edge/cancel   - Cancel current dispense
- POST /edge/sync     - Force sync with SaaS
"""
import atexit
import logging
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS

from config import config
from database import database
from gpio_controller import gpio_controller
from dispenser import dispenser, DispenseStatus
from token_validator import token_validator
from sync_service import sync_service


# ==================== App Setup ====================

app = Flask(__name__)

# Enable CORS for APP Kiosk (allow JSON headers + POST preflight)
CORS(
    app,
    resources={r"/edge/*": {"origins": ["http://localhost:5500", "http://127.0.0.1:5500"]}},
    methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "X-Requested-With", "X-API-Key"],
    expose_headers=["Content-Type"]
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('server.err', encoding='utf-8')
    ]
)
logger = logging.getLogger('edge-server')


# ==================== Routes ====================

@app.route('/edge/health', methods=['GET'])
def health():
    """Simple health check"""
    return jsonify({
        "status": "healthy",
        "service": "edge-server",
        "machine_id": config.saas.MACHINE_ID,
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/edge/status', methods=['GET'])
def status():
    """Detailed status including dispenser, sync, and GPIO"""
    return jsonify({
        "dispenser": dispenser.get_status(),
        "sync": sync_service.get_status(),
        "gpio": gpio_controller.get_status(),
        "database": database.get_consumption_stats(),
        "timestamp": datetime.utcnow().isoformat() + "Z"
    })


@app.route('/edge/authorize', methods=['POST'])
def authorize():
    """
    Authorize and execute dispensing operation
    
    Request body:
    {
        "token": "base64(payload).base64(signature)"
    }
    
    Response (200):
    {
        "authorized": true,
        "result": {
            "success": true,
            "status": "completed",
            "sale_id": "uuid",
            "volume_authorized_ml": 500,
            "volume_dispensed_ml": 498.5,
            "duration_seconds": 5.2,
            "pulse_count": 225
        }
    }
    
    Response (400/401):
    {
        "authorized": false,
        "error": "Token expired"
    }
    """
    try:
        data = request.get_json()
        
        if not data or 'token' not in data:
            return jsonify({
                "authorized": False,
                "error": "Missing token"
            }), 400
        
        token = data['token']
        
        # Validate token
        is_valid, payload, error = token_validator.validate_token(token)
        
        if not is_valid:
            logger.warning(f"Token validation failed: {error}")
            return jsonify({
                "authorized": False,
                "error": error
            }), 401
        
        logger.info(f"Token validated for sale {payload.sale_id}, {payload.volume_ml}ml")
        
        # Check if dispenser is busy
        if dispenser.status == DispenseStatus.DISPENSING:
            return jsonify({
                "authorized": False,
                "error": "Dispenser is busy"
            }), 409
        
        # Execute dispense (blocking operation)
        result = dispenser.dispense(payload)
        
        logger.info(f"Dispense complete: {result.volume_dispensed_ml:.1f}ml, success={result.success}")
        
        return jsonify({
            "authorized": True,
            "result": result.to_dict()
        })
        
    except Exception as e:
        logger.error(f"Authorize error: {e}")
        return jsonify({
            "authorized": False,
            "error": str(e)
        }), 500


@app.route('/edge/cancel', methods=['POST'])
def cancel():
    """Cancel current dispense operation"""
    if dispenser.cancel():
        return jsonify({
            "success": True,
            "message": "Dispense cancelled"
        })
    else:
        return jsonify({
            "success": False,
            "message": "No active dispense to cancel"
        }), 400


@app.route('/edge/sync', methods=['POST'])
def force_sync():
    """Force sync pending records with SaaS"""
    try:
        result = sync_service.force_sync()
        return jsonify({
            "success": True,
            "result": result
        })
    except Exception as e:
        logger.error(f"Force sync error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/edge/maintenance', methods=['POST'])
def maintenance():
    """
    Enter/exit maintenance mode
    
    Request:
    { "action": "enter" | "exit" }
    """
    data = request.get_json()
    action = data.get('action') if data else None
    
    if action == 'enter':
        # Could implement actual maintenance mode logic
        logger.info("Entering maintenance mode")
        return jsonify({"status": "maintenance", "message": "Maintenance mode active"})
    elif action == 'exit':
        logger.info("Exiting maintenance mode")
        return jsonify({"status": "idle", "message": "Maintenance mode deactivated"})
    else:
        return jsonify({"error": "Invalid action. Use 'enter' or 'exit'"}), 400


@app.route('/edge/test-dispense', methods=['POST'])
def test_dispense():
    """
    Test dispense without payment (development only)
    
    Request:
    { "volume_ml": 100, "beverage_id": "optional" }
    """
    if not config.server.DEBUG:
        return jsonify({"error": "Only available in debug mode"}), 403
    
    data = request.get_json() or {}
    volume_ml = data.get('volume_ml', 100)
    beverage_id = data.get('beverage_id', 'test-beverage')
    
    # Generate test token
    test_token = token_validator.generate_token(
        sale_id=f"TEST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}",
        beverage_id=beverage_id,
        volume_ml=volume_ml,
        tap_id=1
    )
    
    # Validate and dispense
    is_valid, payload, error = token_validator.validate_token(test_token)
    
    if not is_valid:
        return jsonify({"error": f"Token error: {error}"}), 500
    
    result = dispenser.dispense(payload)
    
    return jsonify({
        "test": True,
        "result": result.to_dict()
    })


# ==================== Error Handlers ====================

@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def server_error(e):
    logger.error(f"Server error: {e}")
    return jsonify({"error": "Internal server error"}), 500


# ==================== Startup/Shutdown ====================

def startup():
    """Initialize components on startup"""
    logger.info("🚀 Starting EDGE Server...")
    
    # Initialize database
    database.initialize()
    logger.info("✅ Database initialized")
    
    # Initialize GPIO
    gpio_controller.initialize()
    logger.info("✅ GPIO initialized")
    
    # Start sync service
    sync_service.start()
    logger.info("✅ Sync service started")
    
    logger.info(f"✅ EDGE Server ready on {config.server.HOST}:{config.server.PORT}")


def shutdown():
    """Clean up on shutdown"""
    logger.info("🛑 Shutting down EDGE Server...")
    
    # Stop sync service
    sync_service.stop()
    logger.info("  Sync service stopped")
    
    # Clean up GPIO
    gpio_controller.cleanup()
    logger.info("  GPIO cleaned up")
    
    logger.info("👋 EDGE Server stopped")


# Register shutdown handler
atexit.register(shutdown)


# ==================== Main ====================

if __name__ == '__main__':
    startup()
    
    app.run(
        host=config.server.HOST,
        port=config.server.PORT,
        debug=config.server.DEBUG,
        threaded=True,
        use_reloader=config.server.DEBUG
    )

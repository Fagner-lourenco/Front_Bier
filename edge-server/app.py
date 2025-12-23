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
from payment_service import payment_service


# ==================== App Setup ====================

app = Flask(__name__)

# Enable CORS for APP Kiosk - universal for local development
CORS(app, resources={r"/*": {"origins": "*"}}, supports_credentials=False)

# Manual CORS headers for all responses
@app.after_request
def add_cors_headers(response):
    """Add CORS headers to every response"""
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Accept, X-Requested-With, X-API-Key'
    response.headers['Access-Control-Max-Age'] = '3600'
    return response

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
    from datetime import datetime, timezone
    return jsonify({
        "dispenser": dispenser.get_status(),
        "sync": sync_service.get_status(),
        "gpio": gpio_controller.get_status(),
        "database": database.get_consumption_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
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
        
        # Execute dispense in background thread (non-blocking)
        # This allows polling to read progress while dispensing is happening
        import threading
        dispense_thread = threading.Thread(target=dispenser.dispense, args=(payload,), daemon=True)
        dispense_thread.start()
        
        logger.info(f"Dispense started in background for sale {payload.sale_id}, {payload.volume_ml}ml")
        
        return jsonify({
            "authorized": True,
            "result": {
                "status": "dispensing",
                "sale_id": payload.sale_id,
                "volume_authorized_ml": payload.volume_ml,
                "message": "Dispensing in progress..."
            }
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


# ==================== Mercado Pago Payment Routes ====================

@app.route('/edge/payments/start', methods=['POST'])
def start_payment():
    """
    Start a payment (PIX, DEBIT, CREDIT, or QR)
    
    Request:
    {
        "amount": 12.50,
        "volume_ml": 300,
        "beverage_id": "uuid",
        "payment_type": "PIX" | "DEBIT" | "CREDIT" | "QR",
        "external_reference": "sale-id-optional",
        "payer_email": "optional@email.com",
        "installments": 1 (only for CREDIT)
    }
    
    Response (200):
    {
        "success": true,
        "payment_id": "mp-payment-id",
        "payment_type": "PIX" | "DEBIT" | "CREDIT",
        "qr_code": "PIX emv string or instructions",
        "qr_base64": "data:image/svg+xml;base64,...",
        "instructions": "User-friendly instructions",
        "expires_at": "2025-12-23T19:30:00Z",
        "status": "pending"
    }
    
    Response (400/500):
    {
        "success": false,
        "error": "error message"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "Request body required"
            }), 400
        
        amount = data.get('amount')
        volume_ml = data.get('volume_ml')
        payment_type = data.get('payment_type', 'PIX').upper()
        external_reference = data.get('external_reference')
        payer_email = data.get('payer_email')
        installments = data.get('installments', 1)
        
        if not amount or not payment_type:
            return jsonify({
                "success": False,
                "error": "Missing amount or payment_type"
            }), 400
        
        # Validate payment type
        valid_types = ['PIX', 'DEBIT', 'CREDIT', 'QR']
        if payment_type not in valid_types:
            return jsonify({
                "success": False,
                "error": f"Invalid payment_type. Must be one of: {', '.join(valid_types)}"
            }), 400
        
        # Create payment
        description = f"{volume_ml}ml - BierPass"
        success, result = payment_service.create_payment(
            payment_type=payment_type,
            amount=amount,
            description=description,
            external_reference=external_reference,
            payer_email=payer_email,
            installments=installments
        )
        
        if not success:
            logger.warning(f"Payment creation failed: {result.get('error')}")
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error')
            }), 400
        
        result['success'] = True
        result['payment_type'] = payment_type
        
        logger.info(f"✅ Payment started: {result.get('payment_id')} ({payment_type})")
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Start payment error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/edge/payments/status/<payment_id>', methods=['GET'])
def get_payment_status(payment_id):
    """
    Get current status of a payment (PIX)
    
    Response (200):
    {
        "success": true,
        "payment_id": "id",
        "status": "pending|approved|rejected|cancelled|expired",
        "approved": true|false,
        "amount": 12.50,
        "reference": "sale-id",
        "pix_e2e_id": "comprovante-pix-optional",
        "created_at": "2025-12-23T19:20:00Z"
    }
    """
    try:
        success, result = payment_service.get_payment_status(payment_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Payment not found')
            }), 404
        
        result['success'] = True
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get payment status error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/edge/payments/order/status/<order_id>', methods=['GET'])
def get_order_status(order_id):
    """
    Get current status of a QR order (merchant_order)
    """
    try:
        success, result = payment_service.get_order_status(order_id)
        
        if not success:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Order not found')
            }), 404
        
        result['success'] = True
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Get order status error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route('/edge/webhooks/mercadopago', methods=['POST'])
def mercadopago_webhook():
    """
    Receive webhooks from Mercado Pago
    
    Body:
    {
        "type": "payment" | "merchant_order",
        "data": {
            "id": "payment-id-or-order-id"
        }
    }
    """
    try:
        data = request.get_json() or {}
        event_type = data.get('type')
        event_data = data.get('data', {})
        resource_id = event_data.get('id')
        
        logger.info(f"📩 MP Webhook: type={event_type}, id={resource_id}")
        
        if event_type == 'payment':
            # Payment status changed
            success, payment_info = payment_service.get_payment_status(resource_id)
            if success:
                logger.info(f"✅ Payment webhook: {resource_id} -> {payment_info.get('status')}")
        
        elif event_type == 'merchant_order':
            # Order payment status changed
            success, order_info = payment_service.get_order_status(resource_id)
            if success:
                logger.info(f"✅ Order webhook: {resource_id} -> {order_info.get('status')}")
        
        # Always return 200 to acknowledge receipt
        return jsonify({"received": True}), 200
        
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return jsonify({"error": str(e)}), 500


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

"""
Mercado Pago Payment Service
Handles PIX and QR payments for EDGE Server
"""
import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import mercadopago

from config import config

logger = logging.getLogger(__name__)


class PaymentService:
    """
    Manages Mercado Pago payments (PIX, QR, Debit Card, Credit Card)
    """
    
    def __init__(self):
        """Initialize Mercado Pago SDK with configured credentials"""
        self.sdk = mercadopago.SDK(config.mercadopago.ACCESS_TOKEN)
        self.mock_mode = config.mercadopago.MOCK_PAYMENTS
        self.timeout = config.mercadopago.PAYMENT_TIMEOUT
        
        # In-memory cache for payment tracking
        self._payments: Dict[str, Dict] = {}
        self._orders: Dict[str, Dict] = {}
        
        logger.info(f"✅ Payment Service initialized (mock_mode={self.mock_mode})")
    
    def create_payment(
        self,
        payment_type: str,
        amount: float,
        description: str,
        external_reference: str = None,
        payer_email: str = None,
        card_token: str = None,
        installments: int = 1
    ) -> Tuple[bool, Dict]:
        """
        Create a payment of any type (PIX, DEBIT, CREDIT, QR)
        
        Args:
            payment_type: 'PIX', 'DEBIT', 'CREDIT', 'QR'
            amount: Payment amount in BRL
            description: Payment description
            external_reference: Unique reference
            payer_email: Optional payer email
            card_token: Token if card payment
            installments: Number of installments for credit
            
        Returns:
            (success, data)
        """
        payment_type = payment_type.upper()
        
        if payment_type == 'PIX':
            return self.create_pix_payment(amount, description, external_reference, payer_email)
        elif payment_type == 'DEBIT':
            return self.create_debit_payment(amount, description, external_reference, payer_email, card_token)
        elif payment_type == 'CREDIT':
            return self.create_credit_payment(amount, description, external_reference, payer_email, card_token, installments)
        elif payment_type == 'QR':
            items = [{
                "title": description,
                "quantity": 1,
                "unit_price": amount
            }]
            return self.create_qr_order(amount, items, external_reference)
        else:
            return False, {"error": f"Unsupported payment_type: {payment_type}"}
    
    def create_debit_payment(
        self,
        amount: float,
        description: str,
        external_reference: str = None,
        payer_email: str = None,
        card_token: str = None
    ) -> Tuple[bool, Dict]:
        """
        Create a debit card payment
        
        Returns:
            (success, data) with payment_id, status, instructions
        """
        try:
            if self.mock_mode:
                return self._create_debit_payment_mock(amount, description, external_reference)
            
            # Build payment request for debit card
            payment_data = {
                "transaction_amount": amount,
                "description": description,
                "payment_method_id": "visa",  # Debit is usually via Visa/Mastercard
                "payment_type_id": "debit_card",
                "external_reference": external_reference or str(uuid.uuid4()),
                "notification_url": config.mercadopago.NOTIFICATION_URL,
                "payer": {
                    "email": payer_email or "anonymous@bierpass.com"
                }
            }
            
            # If card token provided, use it (for real POS integration)
            if card_token:
                payment_data["token"] = card_token
            
            logger.info(f"💳 Creating DEBIT payment: {amount} BRL, ref={external_reference}")
            
            response = self.sdk.payment().create(payment_data)
            
            if response.get("status") != 201:
                error_msg = response.get("response", {}).get("message", "Unknown error")
                logger.error(f"❌ Debit payment creation failed: {error_msg}")
                return False, {"error": error_msg}
            
            payment = response["response"]
            payment_id = payment["id"]
            status = payment.get("status")
            
            expires_at = (datetime.utcnow() + timedelta(minutes=2)).isoformat() + "Z"
            
            self._payments[str(payment_id)] = {
                "amount": amount,
                "external_reference": external_reference,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at,
                "status": status,
                "payment_type": "DEBIT"
            }
            
            result = {
                "payment_id": str(payment_id),
                "status": status,
                "expires_at": expires_at,
                "payment_type": "DEBIT",
                "instructions": "Insira o cartão no leitor de débito"
            }
            
            logger.info(f"✅ Debit payment created: {payment_id}")
            return True, result
            
        except Exception as e:
            logger.error(f"❌ Debit payment error: {e}")
            return False, {"error": str(e)}
    
    def _create_debit_payment_mock(
        self,
        amount: float,
        description: str,
        external_reference: str
    ) -> Tuple[bool, Dict]:
        """Mock debit payment for development"""
        payment_id = str(int(time.time() * 1000))
        expires_at = (datetime.utcnow() + timedelta(minutes=2)).isoformat() + "Z"
        
        self._payments[payment_id] = {
            "amount": amount,
            "external_reference": external_reference,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "status": "pending",
            "payment_type": "DEBIT"
        }
        
        logger.info(f"🎭 MOCK DEBIT payment: {amount} BRL, id={payment_id}")
        
        return True, {
            "payment_id": payment_id,
            "status": "pending",
            "expires_at": expires_at,
            "payment_type": "DEBIT",
            "instructions": "Insira o cartão no leitor de débito"
        }
    
    def create_credit_payment(
        self,
        amount: float,
        description: str,
        external_reference: str = None,
        payer_email: str = None,
        card_token: str = None,
        installments: int = 1
    ) -> Tuple[bool, Dict]:
        """
        Create a credit card payment
        
        Returns:
            (success, data) with payment_id, status, instructions
        """
        try:
            if self.mock_mode:
                return self._create_credit_payment_mock(amount, description, external_reference, installments)
            
            # Build payment request for credit card
            payment_data = {
                "transaction_amount": amount,
                "description": description,
                "payment_method_id": "visa",
                "payment_type_id": "credit_card",
                "installments": installments,
                "external_reference": external_reference or str(uuid.uuid4()),
                "notification_url": config.mercadopago.NOTIFICATION_URL,
                "payer": {
                    "email": payer_email or "anonymous@bierpass.com"
                }
            }
            
            # If card token provided, use it
            if card_token:
                payment_data["token"] = card_token
            
            logger.info(f"💳 Creating CREDIT payment: {amount} BRL x {installments}x, ref={external_reference}")
            
            response = self.sdk.payment().create(payment_data)
            
            if response.get("status") != 201:
                error_msg = response.get("response", {}).get("message", "Unknown error")
                logger.error(f"❌ Credit payment creation failed: {error_msg}")
                return False, {"error": error_msg}
            
            payment = response["response"]
            payment_id = payment["id"]
            status = payment.get("status")
            
            expires_at = (datetime.utcnow() + timedelta(minutes=2)).isoformat() + "Z"
            
            self._payments[str(payment_id)] = {
                "amount": amount,
                "external_reference": external_reference,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at,
                "status": status,
                "payment_type": "CREDIT",
                "installments": installments
            }
            
            result = {
                "payment_id": str(payment_id),
                "status": status,
                "expires_at": expires_at,
                "payment_type": "CREDIT",
                "installments": installments,
                "instructions": f"Aproxime o cartão ({installments}x sem juros)" if installments > 1 else "Aproxime o cartão"
            }
            
            logger.info(f"✅ Credit payment created: {payment_id}")
            return True, result
            
        except Exception as e:
            logger.error(f"❌ Credit payment error: {e}")
            return False, {"error": str(e)}
    
    def _create_credit_payment_mock(
        self,
        amount: float,
        description: str,
        external_reference: str,
        installments: int = 1
    ) -> Tuple[bool, Dict]:
        """Mock credit payment for development"""
        payment_id = str(int(time.time() * 1000))
        expires_at = (datetime.utcnow() + timedelta(minutes=2)).isoformat() + "Z"
        
        self._payments[payment_id] = {
            "amount": amount,
            "external_reference": external_reference,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "status": "pending",
            "payment_type": "CREDIT",
            "installments": installments
        }
        
        logger.info(f"🎭 MOCK CREDIT payment: {amount} BRL ({installments}x), id={payment_id}")
        
        return True, {
            "payment_id": payment_id,
            "status": "pending",
            "expires_at": expires_at,
            "payment_type": "CREDIT",
            "installments": installments,
            "instructions": f"Aproxime o cartão ({installments}x sem juros)" if installments > 1 else "Aproxime o cartão"
        }
    
    def create_pix_payment(
        self,
        amount: float,
        description: str,
        external_reference: str = None,
        payer_email: str = None
    ) -> Tuple[bool, Dict]:
        """
        Create a PIX payment and return QR code
        
        Args:
            amount: Payment amount in BRL
            description: Payment description
            external_reference: Unique reference (e.g., sale_id)
            payer_email: Optional payer email
            
        Returns:
            (success, data) where data contains:
            - payment_id: str
            - qr_code: str (PIX code)
            - qr_base64: str (SVG/base64)
            - expires_at: ISO datetime
            - status: 'pending'
        """
        try:
            if self.mock_mode:
                return self._create_pix_payment_mock(amount, description, external_reference)
            
            # Build payment request
            payment_data = {
                "transaction_amount": amount,
                "description": description,
                "payment_method_id": "pix",
                "external_reference": external_reference or str(uuid.uuid4()),
                "notification_url": config.mercadopago.NOTIFICATION_URL,
                "payer": {
                    "email": payer_email or "anonymous@bierpass.com"
                }
            }
            
            logger.info(f"📱 Creating PIX payment: {amount} BRL, ref={external_reference}")
            
            # Create payment via SDK
            response = self.sdk.payment().create(payment_data)
            
            if response.get("status") != 201:
                error_msg = response.get("response", {}).get("message", "Unknown error")
                logger.error(f"❌ PIX payment creation failed: {error_msg}")
                return False, {"error": error_msg}
            
            payment = response["response"]
            payment_id = payment["id"]
            
            # Extract PIX data (QR code)
            point_of_interaction = payment.get("point_of_interaction", {})
            transaction_data = point_of_interaction.get("transaction_data", {})
            qr_code = transaction_data.get("qr_code")
            qr_base64 = transaction_data.get("qr_code_base64")
            
            if not qr_code:
                logger.error(f"❌ No QR code in PIX response")
                return False, {"error": "No QR code generated"}
            
            # Calculate expiration (MP default is 10 minutes)
            expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"
            
            # Cache payment info
            self._payments[str(payment_id)] = {
                "amount": amount,
                "external_reference": external_reference,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at,
                "status": "pending"
            }
            
            result = {
                "payment_id": str(payment_id),
                "qr_code": qr_code,
                "qr_base64": qr_base64,
                "expires_at": expires_at,
                "status": "pending"
            }
            
            logger.info(f"✅ PIX payment created: {payment_id}")
            return True, result
            
        except Exception as e:
            logger.error(f"❌ PIX payment error: {e}")
            return False, {"error": str(e)}
    
    def _create_pix_payment_mock(
        self,
        amount: float,
        description: str,
        external_reference: str
    ) -> Tuple[bool, Dict]:
        """Mock PIX payment for development"""
        payment_id = str(int(time.time() * 1000))
        expires_at = (datetime.utcnow() + timedelta(minutes=10)).isoformat() + "Z"
        
        # Generate mock QR code (EMV format)
        mock_qr = f"00020126580014br.gov.bcb.pix0136TXN_{payment_id}"
        
        self._payments[payment_id] = {
            "amount": amount,
            "external_reference": external_reference,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "status": "pending"
        }
        
        logger.info(f"🎭 MOCK PIX payment: {amount} BRL, id={payment_id}")
        
        return True, {
            "payment_id": payment_id,
            "qr_code": mock_qr,
            "qr_base64": f"data:image/svg+xml;base64,...",  # Mock base64
            "expires_at": expires_at,
            "status": "pending"
        }
    
    def create_qr_order(
        self,
        amount: float,
        items: list,
        external_reference: str = None,
        store_id: str = None,
        pos_id: str = None
    ) -> Tuple[bool, Dict]:
        """
        Create a QR code for instore payment (via merchant_order)
        
        Args:
            amount: Total amount in BRL
            items: List of {title, quantity, unit_price}
            external_reference: Unique reference (e.g., sale_id)
            store_id: Store identifier
            pos_id: POS identifier
            
        Returns:
            (success, data) with qr_code, order_id, expires_at
        """
        try:
            if self.mock_mode:
                return self._create_qr_order_mock(amount, items, external_reference)
            
            # Build order request
            order_data = {
                "external_reference": external_reference or str(uuid.uuid4()),
                "items": items,
                "total_amount": amount,
                "marketplace_fee": 0
            }
            
            logger.info(f"🏪 Creating QR order: {amount} BRL, ref={external_reference}")
            
            # Create preference (merchant order)
            response = self.sdk.preference().create(order_data)
            
            if response.get("status") != 201:
                error_msg = response.get("response", {}).get("message", "Unknown error")
                logger.error(f"❌ QR order creation failed: {error_msg}")
                return False, {"error": error_msg}
            
            preference = response["response"]
            order_id = preference["id"]
            
            # QR code (init_point for web checkout, or embed for instore)
            qr_url = preference.get("init_point")
            
            expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat() + "Z"
            
            self._orders[str(order_id)] = {
                "amount": amount,
                "external_reference": external_reference,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": expires_at,
                "status": "pending"
            }
            
            result = {
                "order_id": str(order_id),
                "qr_code": qr_url,
                "qr_base64": None,  # Would generate SVG if needed
                "expires_at": expires_at,
                "status": "pending"
            }
            
            logger.info(f"✅ QR order created: {order_id}")
            return True, result
            
        except Exception as e:
            logger.error(f"❌ QR order error: {e}")
            return False, {"error": str(e)}
    
    def _create_qr_order_mock(
        self,
        amount: float,
        items: list,
        external_reference: str
    ) -> Tuple[bool, Dict]:
        """Mock QR order for development"""
        order_id = str(int(time.time() * 1000))
        expires_at = (datetime.utcnow() + timedelta(minutes=15)).isoformat() + "Z"
        
        self._orders[order_id] = {
            "amount": amount,
            "external_reference": external_reference,
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at,
            "status": "pending"
        }
        
        logger.info(f"🎭 MOCK QR order: {amount} BRL, id={order_id}")
        
        return True, {
            "order_id": order_id,
            "qr_code": "00020126580014br.gov.bcb.pix0136...",
            "qr_base64": f"data:image/svg+xml;base64,...",
            "expires_at": expires_at,
            "status": "pending"
        }
    
    def get_payment_status(self, payment_id: str) -> Tuple[bool, Dict]:
        """
        Get current status of a PIX payment
        
        Returns:
            (success, {status, approved, amount, reference})
        """
        try:
            if self.mock_mode:
                return self._get_payment_status_mock(payment_id)
            
            logger.info(f"📡 Fetching payment status: {payment_id}")
            
            response = self.sdk.payment().get(payment_id)
            
            if response.get("status") != 200:
                return False, {"error": "Payment not found"}
            
            payment = response["response"]
            status = payment.get("status")
            approved = status == "approved"
            
            result = {
                "payment_id": str(payment_id),
                "status": status,  # pending, approved, rejected, cancelled, expired
                "approved": approved,
                "amount": payment.get("transaction_amount"),
                "reference": payment.get("external_reference"),
                "created_at": payment.get("date_created"),
                "pix_e2e_id": payment.get("pix_e2e_id")  # Comprovante do PIX
            }
            
            logger.info(f"✅ Payment status: {status}")
            return True, result
            
        except Exception as e:
            logger.error(f"❌ Get payment status error: {e}")
            return False, {"error": str(e)}
    
    def _get_payment_status_mock(self, payment_id: str) -> Tuple[bool, Dict]:
        """Mock payment status (simulates user approval after 5 sec)"""
        if payment_id not in self._payments:
            return False, {"error": "Payment not found"}
        
        cached = self._payments[payment_id]
        created_at = datetime.fromisoformat(cached["created_at"].replace("Z", "+00:00"))
        elapsed = (datetime.utcnow() - created_at).total_seconds()
        
        # Simulate approval after 5 seconds
        if elapsed > 5:
            status = "approved"
            self._payments[payment_id]["status"] = "approved"
        else:
            status = "pending"
        
        result = {
            "payment_id": payment_id,
            "status": status,
            "approved": status == "approved",
            "amount": cached["amount"],
            "reference": cached["external_reference"],
            "created_at": cached["created_at"],
            "pix_e2e_id": f"MOCK_{payment_id}" if status == "approved" else None
        }
        
        logger.info(f"🎭 MOCK payment status: {status}")
        return True, result
    
    def get_order_status(self, order_id: str) -> Tuple[bool, Dict]:
        """Get current status of a QR order"""
        try:
            if self.mock_mode:
                return self._get_order_status_mock(order_id)
            
            logger.info(f"📡 Fetching order status: {order_id}")
            
            response = self.sdk.merchant_order().get(order_id)
            
            if response.get("status") != 200:
                return False, {"error": "Order not found"}
            
            order = response["response"]
            
            # Check payment status in merchant order
            payments = order.get("payments", [])
            payment_status = None
            if payments:
                payment = payments[0]
                payment_status = payment.get("status")
            
            approved = payment_status == "approved"
            
            result = {
                "order_id": str(order_id),
                "status": payment_status or "pending",
                "approved": approved,
                "amount": order.get("total_amount"),
                "reference": order.get("external_reference"),
                "created_at": order.get("date_created")
            }
            
            logger.info(f"✅ Order status: {payment_status}")
            return True, result
            
        except Exception as e:
            logger.error(f"❌ Get order status error: {e}")
            return False, {"error": str(e)}
    
    def _get_order_status_mock(self, order_id: str) -> Tuple[bool, Dict]:
        """Mock order status"""
        if order_id not in self._orders:
            return False, {"error": "Order not found"}
        
        cached = self._orders[order_id]
        created_at = datetime.fromisoformat(cached["created_at"].replace("Z", "+00:00"))
        elapsed = (datetime.utcnow() - created_at).total_seconds()
        
        # Simulate approval after 5 seconds
        if elapsed > 5:
            status = "approved"
            self._orders[order_id]["status"] = "approved"
        else:
            status = "pending"
        
        result = {
            "order_id": order_id,
            "status": status,
            "approved": status == "approved",
            "amount": cached["amount"],
            "reference": cached["external_reference"],
            "created_at": cached["created_at"]
        }
        
        logger.info(f"🎭 MOCK order status: {status}")
        return True, result
    
    def cancel_payment(self, payment_id: str) -> Tuple[bool, Dict]:
        """Cancel a pending PIX payment"""
        try:
            logger.info(f"🔴 Cancelling payment: {payment_id}")
            
            response = self.sdk.payment().update(payment_id, {"status": "cancelled"})
            
            if response.get("status") != 200:
                return False, {"error": "Failed to cancel"}
            
            logger.info(f"✅ Payment cancelled: {payment_id}")
            return True, {"payment_id": payment_id, "status": "cancelled"}
            
        except Exception as e:
            logger.error(f"❌ Cancel payment error: {e}")
            return False, {"error": str(e)}


# Global payment service instance
payment_service = PaymentService()

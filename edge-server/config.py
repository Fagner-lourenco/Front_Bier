"""
EDGE Server Configuration
Raspberry Pi GPIO settings, HMAC secrets, and SaaS connection
"""
import os
from dataclasses import dataclass


@dataclass
class GPIOConfig:
    """GPIO Pin Configuration for Raspberry Pi"""
    # Pump relay control (output)
    PUMP_PIN: int = 17
    
    # Flow sensor input (input with pull-up)
    FLOW_SENSOR_PIN: int = 27
    
    # LED indicators (optional)
    LED_STATUS_PIN: int = 22
    LED_ERROR_PIN: int = 23
    
    # Flow sensor calibration
    # Pulses per liter - adjust based on your sensor model
    # YF-S201: ~450 pulses/L, YF-S401: ~5880 pulses/L
    PULSES_PER_LITER: float = 450.0
    
    # Maximum dispensing time (safety cutoff in seconds)
    MAX_DISPENSE_TIME: int = 120
    
    # Minimum flow rate threshold (ml/s) - detects empty keg
    MIN_FLOW_RATE: float = 5.0


@dataclass
class SecurityConfig:
    """Security Configuration"""
    # HMAC secret for token validation (shared with SaaS)
    # In production, load from environment variable
    HMAC_SECRET: str = os.getenv(
        "EDGE_HMAC_SECRET", 
        "P9llzEpC52LsXIa-te9YSYH7ufzieNswt1aKFX9aNAU"
    )
    
    # Token expiry tolerance (seconds)
    TOKEN_EXPIRY_TOLERANCE: int = 30
    
    # Enable single-use token enforcement
    SINGLE_USE_TOKENS: bool = True
    
    # Used tokens cache TTL (seconds)
    USED_TOKENS_TTL: int = 300


@dataclass
class SaaSConfig:
    """SaaS Backend Connection Configuration"""
    # SaaS Backend URL
    BASE_URL: str = os.getenv("SAAS_URL", "http://localhost:3001")
    
    # API Key for machine authentication
    API_KEY: str = os.getenv(
        "EDGE_API_KEY",
        "sk_eKZVLSB56JEajCN70PJ4ResGqxH1B3L3W7CgNrJGIq4"
    )
    # Machine ID (UUID from SaaS)
    MACHINE_ID: str = os.getenv(
        "EDGE_MACHINE_ID",
        "7ef8ddb1-3a10-4678-8e56-a8aee3184c40"
    )
    
    # Sync interval (seconds) - 0 = DESABILITADO (App reporta diretamente)
    SYNC_INTERVAL: int = 15
    
    # Connection timeout (seconds)
    TIMEOUT: int = 10
    
    # Retry attempts for failed syncs
    MAX_RETRIES: int = 3


@dataclass
class DatabaseConfig:
    """Local SQLite Database Configuration"""
    # Database file path
    DB_PATH: str = os.getenv("EDGE_DB_PATH", "edge_data.db")
    
    # Maximum offline records before forcing sync
    MAX_OFFLINE_RECORDS: int = 100


@dataclass
class ServerConfig:
    """Flask Server Configuration"""
    HOST: str = "0.0.0.0"
    PORT: int = 5000
    DEBUG: bool = os.getenv("EDGE_DEBUG", "true").lower() == "true"  # Habilitado para desenvolvimento


@dataclass
class MercadoPagoConfig:
    """Mercado Pago Payment Configuration"""
    # Access token for MP API
    ACCESS_TOKEN: str = os.getenv(
        "MP_ACCESS_TOKEN",
        "APP_USR-TEST-1234567890"  # Sandbox token (replace with production)
    )
    
    # Integrator ID (optional, for partner integrations)
    INTEGRATOR_ID: str = os.getenv("MP_INTEGRATOR_ID", "")
    
    # Store and POS identifiers
    STORE_ID: str = os.getenv("MP_STORE_ID", "")
    POS_ID: str = os.getenv("MP_POS_ID", "")
    
    # Notification/Webhook URL
    NOTIFICATION_URL: str = os.getenv(
        "MP_NOTIFICATION_URL",
        "http://localhost:5000/edge/webhooks/mercadopago"
    )
    
    # Payment timeout (seconds)
    PAYMENT_TIMEOUT: int = 300
    
    # Enable mock payments for development
    # Default true for dev so kiosk funciona sem credenciais/maquininha
    MOCK_PAYMENTS: bool = os.getenv("MP_MOCK", "true").lower() == "true"


class Config:
    """Main Configuration Container"""
    gpio = GPIOConfig()
    security = SecurityConfig()
    saas = SaaSConfig()
    database = DatabaseConfig()
    server = ServerConfig()
    mercadopago = MercadoPagoConfig()
    
    # Tap configuration (maps tap_id to beverage)
    # In production, this would be fetched from SaaS
    TAPS = {
        1: {
            "beverage_id": "550e8400-e29b-41d4-a716-446655440001",
            "name": "Chopp Pilsen",
            "gpio_pump": 17,
            "gpio_sensor": 27
        },
        # Add more taps as needed
        # 2: {"beverage_id": "...", "name": "IPA", "gpio_pump": 18, "gpio_sensor": 28}
    }


# Global config instance
config = Config()

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
        "bierpass_edge_secret_key_2025_change_in_production"
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
        "sk_mdrWYgksCu0HAXts3OeOBJtK3CR9n6dNcUMQUwDuuWM"
    )
    # Machine ID (UUID from SaaS)
    MACHINE_ID: str = os.getenv(
        "EDGE_MACHINE_ID",
        "40792dfc-828d-4f17-a3f2-3302396658e8"
    )
    
    # Sync interval (seconds)
    SYNC_INTERVAL: int = 30
    
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


class Config:
    """Main Configuration Container"""
    gpio = GPIOConfig()
    security = SecurityConfig()
    saas = SaaSConfig()
    database = DatabaseConfig()
    server = ServerConfig()
    
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

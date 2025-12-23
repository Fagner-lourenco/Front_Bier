"""
Dispenser Logic for EDGE Server
Handles the complete dispensing flow with safety controls
"""
import time
import threading
from datetime import datetime
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass
from enum import Enum

from config import config
from gpio_controller import gpio_controller, FlowReading
from database import database, ConsumptionRecord
from token_validator import TokenPayload


class DispenseStatus(Enum):
    IDLE = "idle"
    VALIDATING = "validating"
    DISPENSING = "dispensing"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    ERROR = "error"


@dataclass
class DispenseResult:
    """Result of a dispense operation"""
    success: bool
    status: DispenseStatus
    sale_id: str
    volume_authorized_ml: int
    volume_dispensed_ml: float
    duration_seconds: float
    pulse_count: int
    error_message: Optional[str] = None
    consumption_record: Optional[ConsumptionRecord] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "status": self.status.value,
            "sale_id": self.sale_id,
            "volume_authorized_ml": self.volume_authorized_ml,
            "volume_dispensed_ml": round(self.volume_dispensed_ml, 1),
            "duration_seconds": round(self.duration_seconds, 2),
            "pulse_count": self.pulse_count,
            "error_message": self.error_message,
            "record_id": self.consumption_record.id if self.consumption_record else None
        }


class Dispenser:
    """
    Controls the beverage dispensing process
    
    Features:
    - Volume-based dispensing with flow sensor feedback
    - Safety timeout
    - Empty keg detection (low flow rate)
    - Interrupt/cancel support
    - Local storage of consumption records
    """
    
    def __init__(self):
        self.status = DispenseStatus.IDLE
        self.current_payload: Optional[TokenPayload] = None
        self._cancel_requested = False
        self._lock = threading.Lock()
        self._progress_callback: Optional[Callable[[float, float], None]] = None
        
        # Safety parameters
        self.max_dispense_time = config.gpio.MAX_DISPENSE_TIME
        self.min_flow_rate = config.gpio.MIN_FLOW_RATE
        self.flow_check_interval = 0.5  # Check flow every 0.5s
        self.empty_keg_timeout = 3.0  # Seconds without flow before declaring empty
    
    def set_progress_callback(self, callback: Callable[[float, float], None]):
        """
        Set callback for progress updates
        callback(volume_dispensed_ml, percent_complete)
        """
        self._progress_callback = callback
    
    def get_status(self) -> Dict[str, Any]:
        """Get current dispenser status"""
        with self._lock:
            result = {
                "status": self.status.value,
                "is_dispensing": self.status == DispenseStatus.DISPENSING,
                "current_sale_id": self.current_payload.sale_id if self.current_payload else None
            }
            
            if self.status == DispenseStatus.DISPENSING:
                reading = gpio_controller.get_flow_reading()
                result.update({
                    "volume_dispensed_ml": round(reading.volume_ml, 1),
                    "duration_seconds": round(reading.duration_seconds, 2),
                    "flow_rate_ml_s": round(reading.flow_rate_ml_s, 1)
                })
            
            return result
    
    def cancel(self) -> bool:
        """Request cancellation of current dispense"""
        with self._lock:
            if self.status == DispenseStatus.DISPENSING:
                self._cancel_requested = True
                return True
            return False
    
    def dispense(self, payload: TokenPayload) -> DispenseResult:
        """
        Execute dispensing operation
        
        Args:
            payload: Validated token payload with dispense parameters
            
        Returns:
            DispenseResult with outcome details
        """
        # Check if already dispensing
        with self._lock:
            if self.status == DispenseStatus.DISPENSING:
                return DispenseResult(
                    success=False,
                    status=DispenseStatus.ERROR,
                    sale_id=payload.sale_id,
                    volume_authorized_ml=payload.volume_ml,
                    volume_dispensed_ml=0,
                    duration_seconds=0,
                    pulse_count=0,
                    error_message="Another dispense operation in progress"
                )
            
            self.status = DispenseStatus.VALIDATING
            self.current_payload = payload
            self._cancel_requested = False
        
        started_at = datetime.utcnow()
        error_message = None
        final_status = DispenseStatus.COMPLETED
        
        try:
            # Initialize GPIO
            gpio_controller.initialize()
            
            # Reset counters
            gpio_controller.reset_pulse_count()
            
            # Start pump
            with self._lock:
                self.status = DispenseStatus.DISPENSING
            
            if not gpio_controller.pump_on():
                raise Exception("Failed to start pump")
            
            print(f"🍺 Dispensing {payload.volume_ml}ml for sale {payload.sale_id}")
            
            # Dispensing loop
            target_ml = payload.volume_ml
            last_flow_time = time.time()
            last_pulse_count = 0
            dispense_start = time.time()
            
            while True:
                time.sleep(self.flow_check_interval)
                
                reading = gpio_controller.get_flow_reading()
                current_ml = reading.volume_ml
                elapsed = time.time() - dispense_start
                
                # Progress callback
                if self._progress_callback:
                    percent = min(100, (current_ml / target_ml) * 100)
                    self._progress_callback(current_ml, percent)
                
                # Check if target reached
                if current_ml >= target_ml:
                    print(f"✅ Target volume reached: {current_ml:.1f}ml")
                    break
                
                # Check for cancellation
                if self._cancel_requested:
                    print("⚠️ Dispense cancelled by user")
                    final_status = DispenseStatus.INTERRUPTED
                    error_message = "Cancelled by user"
                    break
                
                # Check timeout
                if elapsed >= self.max_dispense_time:
                    print(f"⚠️ Safety timeout after {elapsed:.1f}s")
                    final_status = DispenseStatus.INTERRUPTED
                    error_message = f"Safety timeout ({self.max_dispense_time}s)"
                    break
                
                # Check flow rate (empty keg detection)
                if reading.pulse_count > last_pulse_count:
                    last_flow_time = time.time()
                    last_pulse_count = reading.pulse_count
                elif time.time() - last_flow_time > self.empty_keg_timeout:
                    # No flow for too long
                    print(f"⚠️ No flow detected - possible empty keg")
                    final_status = DispenseStatus.INTERRUPTED
                    error_message = "No flow detected - check keg"
                    break
            
        except Exception as e:
            final_status = DispenseStatus.ERROR
            error_message = str(e)
            print(f"❌ Dispense error: {e}")
        
        finally:
            # Always stop pump
            gpio_controller.pump_off()
        
        # Get final reading
        finished_at = datetime.utcnow()
        final_reading = gpio_controller.get_flow_reading()
        
        # Save to local database
        try:
            record = database.save_consumption(
                sale_id=payload.sale_id,
                token_id=payload.token_raw,  # Token HMAC usado na autorização
                beverage_id=payload.beverage_id,
                tap_id=payload.tap_id,
                volume_authorized_ml=payload.volume_ml,
                volume_dispensed_ml=final_reading.volume_ml,
                started_at=started_at,
                finished_at=finished_at,
                pulse_count=final_reading.pulse_count,
                flow_rate_avg=final_reading.flow_rate_ml_s,
                status=final_status.value,
                error_message=error_message
            )
            print(f"💾 Saved consumption record: {record.id}")
        except Exception as e:
            print(f"❌ Failed to save consumption: {e}")
            record = None
        
        # Update status
        with self._lock:
            self.status = DispenseStatus.IDLE
            self.current_payload = None
        
        # Build result
        success = final_status == DispenseStatus.COMPLETED
        
        result = DispenseResult(
            success=success,
            status=final_status,
            sale_id=payload.sale_id,
            volume_authorized_ml=payload.volume_ml,
            volume_dispensed_ml=final_reading.volume_ml,
            duration_seconds=final_reading.duration_seconds,
            pulse_count=final_reading.pulse_count,
            error_message=error_message,
            consumption_record=record
        )
        
        print(f"📊 Dispense complete: {result.volume_dispensed_ml:.1f}ml in {result.duration_seconds:.1f}s")
        
        return result


# Global dispenser instance
dispenser = Dispenser()


# Testing
if __name__ == "__main__":
    from token_validator import TokenValidator
    
    # Initialize database
    database.initialize()
    
    # Create test token payload
    validator = TokenValidator()
    test_token = validator.generate_token(
        sale_id="test-sale-001",
        beverage_id="550e8400-e29b-41d4-a716-446655440001",
        volume_ml=300,
        tap_id=1
    )
    
    is_valid, payload, error = validator.validate_token(test_token)
    
    if not is_valid:
        print(f"Token validation failed: {error}")
        exit(1)
    
    print("\n--- Testing Dispenser ---")
    print(f"Authorized: {payload.volume_ml}ml")
    
    # Set progress callback
    def on_progress(ml, percent):
        print(f"  Progress: {ml:.1f}ml ({percent:.0f}%)")
    
    dispenser.set_progress_callback(on_progress)
    
    # Execute dispense
    result = dispenser.dispense(payload)
    
    print(f"\nResult: {result.to_dict()}")
    
    # Show stats
    stats = database.get_consumption_stats()
    print(f"\nDatabase stats: {stats}")
    
    # Cleanup
    gpio_controller.cleanup()

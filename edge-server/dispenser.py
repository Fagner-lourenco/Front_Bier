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
from gpio_controller import gpio_controller, FlowReading, MOCK_GPIO
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
        
        # MOCK mode simulation data (para não interferir com GPIO real)
        self._mock_volume_ml = 0.0
        self._mock_start_time = None
        self._mock_target_ml = 0.0
    
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
            
            # Em modo MOCK durante dispensa apenas, usar dados simulados
            # Se não está DISPENSING, reseta os dados simulados para não acumular
            if MOCK_GPIO and self.status == DispenseStatus.DISPENSING:
                # Usar dados simulados durante dispensa ativa
                result.update({
                    "volume_dispensed_ml": round(self._mock_volume_ml, 1),
                    "duration_seconds": round(time.time() - self._mock_start_time, 2) if self._mock_start_time else 0.0,
                    "flow_rate_ml_s": 20.0  # Simulação de 20ml/s
                })
            else:
                # Usar dados reais do GPIO (ou dados zerados se não dispensando)
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
            
            # Reset counters - CRUCIAL para não acumular de dispensas anteriores
            print(f"🔄 Resetting GPIO counters (pulse_count before: {gpio_controller.get_pulse_count()})")
            gpio_controller.reset_pulse_count()
            print(f"🔄 Reset complete (pulse_count after: {gpio_controller.get_pulse_count()})")
            
            # Start pump
            with self._lock:
                self.status = DispenseStatus.DISPENSING
            
            if not gpio_controller.pump_on():
                raise Exception("Failed to start pump")
            
            print(f"🍺 Dispensing {payload.volume_ml}ml for sale {payload.sale_id}")
            
            # Em modo MOCK, simular dispensa rápida (sem depender de GPIO real)
            if MOCK_GPIO:
                print(f"📌 MOCK MODE: Simulating dispensing for {payload.volume_ml}ml...")
                # Resetar dados simulados
                with self._lock:
                    self._mock_volume_ml = 0.0
                    self._mock_start_time = time.time()
                    self._mock_target_ml = payload.volume_ml
                
                # Simular tempo de dispensa: 20ml/s (mais lento para polling conseguir ler o progresso)
                simulated_duration = (payload.volume_ml / 20.0)  # 20ml por segundo
                simulated_duration = max(5.0, min(simulated_duration, 30.0))  # Entre 5-30 segundos

                # Progresso por 1ml para sensação contínua
                total_ml = int(payload.volume_ml)
                step_duration = simulated_duration / max(total_ml, 1)

                last_percent_printed = -1
                for ml in range(1, total_ml + 1):
                    if self._cancel_requested:
                        print("⚠️ Dispense cancelled by user")
                        final_status = DispenseStatus.INTERRUPTED
                        error_message = "Cancelled by user"
                        break

                    time.sleep(step_duration)

                    # Atualizar progresso simulado (sem mexer no GPIO)
                    simulated_ml = float(ml)
                    percent = min(100, (simulated_ml / payload.volume_ml) * 100)

                    with self._lock:
                        self._mock_volume_ml = simulated_ml

                    if self._progress_callback:
                        self._progress_callback(simulated_ml, percent)

                    # Logar apenas quando o percentual inteiro aumenta para evitar spam
                    percent_int = int(percent)
                    if percent_int != last_percent_printed:
                        print(f"  → {percent_int}% ({simulated_ml:.0f}ml / {payload.volume_ml}ml)")
                        last_percent_printed = percent_int
                
                if final_status == DispenseStatus.COMPLETED:
                    print(f"✅ Mock dispensing complete: {payload.volume_ml}ml")
            else:
                # Hardware real: Dispensing loop com monitoramento de pulsos
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
        
        # Em modo MOCK, usar dados simulados em vez de GPIO
        if MOCK_GPIO:
            # Simular leitura final baseada nos dados simulados
            final_volume_ml = self._mock_volume_ml if final_status == DispenseStatus.COMPLETED else self._mock_volume_ml
            final_duration = time.time() - self._mock_start_time if self._mock_start_time else 0
            final_pulse_count = int(final_volume_ml * (400 / 1000))  # Simular pulsos equivalentes
            final_flow_rate = final_volume_ml / final_duration if final_duration > 0 else 0
        else:
            # Hardware real
            final_reading = gpio_controller.get_flow_reading()
            final_volume_ml = final_reading.volume_ml
            final_duration = final_reading.duration_seconds
            final_pulse_count = final_reading.pulse_count
            final_flow_rate = final_reading.flow_rate_ml_s
        
        # Save to local database
        try:
            record = database.save_consumption(
                sale_id=payload.sale_id,
                token_id=payload.token_raw,  # Token HMAC usado na autorização
                beverage_id=payload.beverage_id,
                tap_id=payload.tap_id,
                volume_authorized_ml=payload.volume_ml,
                volume_dispensed_ml=final_volume_ml,
                started_at=started_at,
                finished_at=finished_at,
                pulse_count=final_pulse_count,
                flow_rate_avg=final_flow_rate,
                status=final_status.value,
                error_message=error_message
            )
            print(f"💾 Saved consumption record: {record.id}")
        except Exception as e:
            print(f"❌ Failed to save consumption: {e}")
            record = None
        
        # Update status to COMPLETED (not IDLE yet)
        # This allows polling to detect the completion
        with self._lock:
            self.status = final_status  # Keep COMPLETED/INTERRUPTED/ERROR status
            self.current_payload = None
            # Reset mock timestamp para não retornar dados antigos ao polling
            self._mock_start_time = None
            self._mock_volume_ml = 0.0
        
        # Resetar pulse_count IMEDIATAMENTE para não acumular na próxima dispensa
        print(f"🔄 Resetting GPIO counters after dispense (pulse_count before: {gpio_controller.get_pulse_count()})")
        gpio_controller.reset_pulse_count()
        print(f"🔄 Reset complete (pulse_count after: {gpio_controller.get_pulse_count()})")
        
        print(f"📊 Dispense complete: {final_volume_ml:.1f}ml in {(datetime.utcnow() - started_at).total_seconds():.1f}s, status={final_status.value}")
        
        # Wait 3 seconds for polling to detect completion, then reset to IDLE
        time.sleep(3)
        with self._lock:
            self.status = DispenseStatus.IDLE
            self._mock_start_time = None
            self._mock_volume_ml = 0.0
        success = final_status == DispenseStatus.COMPLETED
        
        result = DispenseResult(
            success=success,
            status=final_status,
            sale_id=payload.sale_id,
            volume_authorized_ml=payload.volume_ml,
            volume_dispensed_ml=final_volume_ml,
            duration_seconds=(finished_at - started_at).total_seconds(),
            pulse_count=final_pulse_count,
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

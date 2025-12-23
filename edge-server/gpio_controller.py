"""
GPIO Controller for EDGE Server
Handles pump control and flow sensor reading

On Raspberry Pi: Uses RPi.GPIO
On other systems: Uses mock GPIO for development
"""
import time
import threading
from datetime import datetime
from typing import Optional, Callable
from dataclasses import dataclass
from enum import Enum

from config import config


# Try to import RPi.GPIO, use mock if not available
try:
    import RPi.GPIO as GPIO
    MOCK_GPIO = False
    print("✅ RPi.GPIO detected - using real GPIO")
except ImportError:
    MOCK_GPIO = True
    print("⚠️ RPi.GPIO not found - using mock GPIO")


@dataclass
class FlowReading:
    """Flow sensor reading data"""
    pulse_count: int
    volume_ml: float
    duration_seconds: float
    flow_rate_ml_s: float
    timestamp: datetime


class GPIOController:
    """
    Controls GPIO for pump and flow sensor
    
    On non-Pi systems, simulates GPIO behavior for testing
    """
    
    def __init__(self):
        self._initialized = False
        self._pump_on = False
        self._pulse_count = 0
        self._start_time: Optional[float] = None
        self._lock = threading.Lock()
        
        # Callback for flow pulses
        self._pulse_callback: Optional[Callable[[int], None]] = None
        
        # Mock settings for development
        self._mock_flow_rate = 100.0  # ml/s simulated flow rate
        self._mock_thread: Optional[threading.Thread] = None
        self._mock_running = False
        
        # GPIO pins from config
        self.pump_pin = config.gpio.PUMP_PIN
        self.flow_sensor_pin = config.gpio.FLOW_SENSOR_PIN
        self.pulses_per_liter = config.gpio.PULSES_PER_LITER
    
    def initialize(self) -> bool:
        """Initialize GPIO pins"""
        if self._initialized:
            return True
        
        try:
            if not MOCK_GPIO:
                # Real GPIO setup
                GPIO.setmode(GPIO.BCM)
                GPIO.setwarnings(False)
                
                # Pump relay (output, active high)
                GPIO.setup(self.pump_pin, GPIO.OUT, initial=GPIO.LOW)
                
                # Flow sensor (input with pull-up)
                GPIO.setup(self.flow_sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Add interrupt for flow sensor
                GPIO.add_event_detect(
                    self.flow_sensor_pin,
                    GPIO.FALLING,
                    callback=self._on_flow_pulse,
                    bouncetime=1
                )
            
            self._initialized = True
            print(f"✅ GPIO initialized (mock={MOCK_GPIO})")
            return True
            
        except Exception as e:
            print(f"❌ GPIO init failed: {e}")
            return False
    
    def cleanup(self):
        """Clean up GPIO resources"""
        try:
            self.pump_off()
            
            if not MOCK_GPIO:
                GPIO.cleanup()
            
            self._initialized = False
            print("🧹 GPIO cleaned up")
            
        except Exception as e:
            print(f"⚠️ GPIO cleanup warning: {e}")
    
    def _on_flow_pulse(self, channel=None):
        """Callback for flow sensor pulse (interrupt)"""
        with self._lock:
            self._pulse_count += 1
            
            if self._pulse_callback:
                self._pulse_callback(self._pulse_count)
    
    def set_pulse_callback(self, callback: Callable[[int], None]):
        """Set callback for pulse events"""
        self._pulse_callback = callback
    
    def reset_pulse_count(self):
        """Reset pulse counter and start time"""
        with self._lock:
            self._pulse_count = 0
            self._start_time = time.time()
    
    def pump_on(self) -> bool:
        """Turn on the pump"""
        if not self._initialized:
            if not self.initialize():
                return False
        
        try:
            with self._lock:
                if not MOCK_GPIO:
                    GPIO.output(self.pump_pin, GPIO.HIGH)
                else:
                    # Start mock flow simulation
                    self._start_mock_flow()
                
                self._pump_on = True
                if self._start_time is None:
                    self._start_time = time.time()
            
            print("🍺 Pump ON")
            return True
            
        except Exception as e:
            print(f"❌ Pump ON failed: {e}")
            return False
    
    def pump_off(self) -> bool:
        """Turn off the pump"""
        try:
            with self._lock:
                if not MOCK_GPIO and self._initialized:
                    GPIO.output(self.pump_pin, GPIO.LOW)
                else:
                    # Stop mock flow simulation
                    self._stop_mock_flow()
                
                self._pump_on = False
            
            print("🛑 Pump OFF")
            return True
            
        except Exception as e:
            print(f"❌ Pump OFF failed: {e}")
            return False
    
    def is_pump_on(self) -> bool:
        """Check if pump is currently on"""
        return self._pump_on
    
    def get_pulse_count(self) -> int:
        """Get current pulse count"""
        with self._lock:
            return self._pulse_count
    
    def get_flow_reading(self) -> FlowReading:
        """Get current flow sensor reading"""
        with self._lock:
            now = time.time()
            duration = now - self._start_time if self._start_time else 0
            
            # Calculate volume from pulses
            volume_ml = (self._pulse_count / self.pulses_per_liter) * 1000
            
            # Calculate flow rate
            if duration > 0:
                flow_rate = volume_ml / duration
            else:
                flow_rate = 0.0
            
            return FlowReading(
                pulse_count=self._pulse_count,
                volume_ml=volume_ml,
                duration_seconds=duration,
                flow_rate_ml_s=flow_rate,
                timestamp=datetime.utcnow()
            )
    
    # ==================== Mock Flow Simulation ====================
    
    def _start_mock_flow(self):
        """Start mock flow simulation (for development)"""
        if self._mock_running:
            return
        
        self._mock_running = True
        self._mock_thread = threading.Thread(target=self._mock_flow_loop, daemon=True)
        self._mock_thread.start()
    
    def _stop_mock_flow(self):
        """Stop mock flow simulation"""
        self._mock_running = False
        if self._mock_thread:
            self._mock_thread.join(timeout=1)
            self._mock_thread = None
    
    def _mock_flow_loop(self):
        """Simulates flow sensor pulses"""
        # Calculate pulses per second based on mock flow rate
        pulses_per_ml = self.pulses_per_liter / 1000
        pulses_per_second = self._mock_flow_rate * pulses_per_ml
        
        interval = 1.0 / pulses_per_second if pulses_per_second > 0 else 0.1
        
        while self._mock_running:
            self._on_flow_pulse()
            time.sleep(interval)
    
    def set_mock_flow_rate(self, ml_per_second: float):
        """Set mock flow rate (for testing)"""
        self._mock_flow_rate = ml_per_second
    
    def get_status(self) -> dict:
        """Get GPIO status summary"""
        reading = self.get_flow_reading()
        return {
            "initialized": self._initialized,
            "mock_mode": MOCK_GPIO,
            "pump_state": "on" if self._pump_on else "off",
            "pulse_count": reading.pulse_count,
            "volume_ml": round(reading.volume_ml, 1),
            "flow_rate_ml_s": round(reading.flow_rate_ml_s, 1)
        }


# Global GPIO controller instance
gpio_controller = GPIOController()


# Testing
if __name__ == "__main__":
    print("\n--- Testing GPIO Controller ---")
    
    # Initialize
    gpio_controller.initialize()
    
    # Test pump
    print("\nTesting pump...")
    gpio_controller.reset_pulse_count()
    gpio_controller.pump_on()
    
    # Wait and check readings
    for i in range(5):
        time.sleep(1)
        reading = gpio_controller.get_flow_reading()
        print(f"  {i+1}s: {reading.volume_ml:.1f}ml, {reading.pulse_count} pulses")
    
    gpio_controller.pump_off()
    
    # Final reading
    final = gpio_controller.get_flow_reading()
    print(f"\nFinal: {final.volume_ml:.1f}ml in {final.duration_seconds:.1f}s")
    
    # Status
    status = gpio_controller.get_status()
    print(f"Status: {status}")
    
    # Cleanup
    gpio_controller.cleanup()
    print("\n✅ GPIO test complete")

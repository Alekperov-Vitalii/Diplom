"""
Virtual DHT22 Humidity Sensor Emulation
Simulates relative humidity with equilibrium-seeking behavior
"""

import time
import random
from typing import Optional
from sensors.base_sensor import BaseSensor


class HumiditySensor(BaseSensor):
    """
    Emulates DHT22 humidity sensor behavior
    
    Features:
    - Tends toward equilibrium point (profile-defined)
    - Proportional adjustment rate (0.01-0.05 per tick)
    - Simulates ventilation and ambient influences
    - Responds to dehumidifier/humidifier control
    """
    
    def __init__(
        self, 
        sensor_id: str,
        initial_humidity: float,
        equilibrium_humidity: float,
        base_rate: float = 0.02,
        noise_amplitude: float = 0.5
    ):
        """
        Args:
            sensor_id: Unique sensor identifier
            initial_humidity: Starting humidity (%)
            equilibrium_humidity: Target equilibrium (%)
            base_rate: Base rate of change per tick (default: 0.02)
            noise_amplitude: Random noise amplitude (default: 0.5%)
        """
        super().__init__(sensor_id, "DHT22_Humidity")
        
        self.current_humidity = initial_humidity
        self.equilibrium_humidity = equilibrium_humidity
        self.base_rate = base_rate
        self.noise_amplitude = noise_amplitude
        
        # External influences (hidden factors)
        self.ventilation_factor = 1.0  # Multiplier for rate (simulates airflow)
        self.control_rate = 0.0  # Change rate from dehumidifier/humidifier
        
        self.logger.info(
            f"Humidity sensor initialized: {initial_humidity}% → {equilibrium_humidity}% "
            f"(rate: {base_rate}/tick)"
        )
    
    def read(self) -> float:
        """
        Read current humidity value
        
        Returns:
            Current relative humidity (%)
        """
        # Add small noise to simulate real sensor
        noise = random.uniform(-self.noise_amplitude, self.noise_amplitude)
        reading = max(0.0, min(100.0, self.current_humidity + noise))
        
        self.logger.debug(f"Humidity reading: {reading:.2f}%")
        return reading
    
    def evolve(self, delta_time: float = 300.0):
        """
        Evolve humidity toward equilibrium
        
        Algorithm:
        1. Calculate difference from equilibrium
        2. Apply proportional adjustment (base_rate * ventilation_factor)
        3. Apply control rate (from dehumidifier/humidifier)
        4. Clamp to valid range [0, 100]
        
        Args:
            delta_time: Time step in seconds (default: 300s = 5 minutes)
        """
        # Natural drift toward equilibrium
        difference = self.equilibrium_humidity - self.current_humidity
        
        # Proportional adjustment (faster change when further from equilibrium)
        natural_change = difference * self.base_rate * self.ventilation_factor
        
        # Total change includes control influence
        total_change = natural_change + self.control_rate
        
        # Apply change
        self.current_humidity += total_change
        
        # Clamp to valid range
        self.current_humidity = max(0.0, min(100.0, self.current_humidity))
        
        self.logger.debug(
            f"Humidity evolved: {self.current_humidity:.2f}% "
            f"(natural: {natural_change:+.3f}, control: {self.control_rate:+.3f})"
        )
    
    def apply_control(self, dehumidifier_active: bool, dehumidifier_power: int,
                     humidifier_active: bool, humidifier_power: int):
        """
        Apply dehumidifier/humidifier control
        
        Control rates:
        - Dehumidifier: -5% per hour at 100% power
        - Humidifier: +5% per hour at 100% power
        - Scaled linearly by power level
        
        Args:
            dehumidifier_active: Dehumidifier relay state
            dehumidifier_power: Power level (0-100%)
            humidifier_active: Humidifier relay state
            humidifier_power: Power level (0-100%)
        """
        # Reset control rate
        self.control_rate = 0.0
        
        # Dehumidifier: reduces humidity
        if dehumidifier_active and dehumidifier_power > 0:
            # Base rate: -5% per hour = -5/12 per 5-minute tick at 100% power
            base_dehumidify_rate = -5.0 / 12.0
            self.control_rate += base_dehumidify_rate * (dehumidifier_power / 100.0)
            self.logger.info(f"Dehumidifier active at {dehumidifier_power}%")
        
        # Humidifier: increases humidity
        if humidifier_active and humidifier_power > 0:
            # Base rate: +5% per hour = +5/12 per 5-minute tick at 100% power
            base_humidify_rate = 5.0 / 12.0
            self.control_rate += base_humidify_rate * (humidifier_power / 100.0)
            self.logger.info(f"Humidifier active at {humidifier_power}%")
    
    def set_equilibrium(self, new_equilibrium: float):
        """
        Update equilibrium point (for profile switching)
        
        Args:
            new_equilibrium: New equilibrium humidity (%)
        """
        old_eq = self.equilibrium_humidity
        self.equilibrium_humidity = max(0.0, min(100.0, new_equilibrium))
        self.logger.info(f"Equilibrium changed: {old_eq}% → {self.equilibrium_humidity}%")
    
    def reset_to_initial(self, initial_humidity: float, equilibrium_humidity: float):
        """
        Reset sensor to new profile values
        
        Args:
            initial_humidity: New initial humidity (%)
            equilibrium_humidity: New equilibrium (%)
        """
        self.current_humidity = initial_humidity
        self.equilibrium_humidity = equilibrium_humidity
        self.control_rate = 0.0
        self.logger.info(f"Sensor reset: {initial_humidity}% → {equilibrium_humidity}%")
    
    def get_state(self) -> dict:
        """Get current sensor state"""
        return {
            'sensor_id': self.sensor_id,
            'type': self.sensor_type,
            'humidity': self.current_humidity,
            'equilibrium': self.equilibrium_humidity,
            'control_rate': self.control_rate,
            'base_rate': self.base_rate
        }

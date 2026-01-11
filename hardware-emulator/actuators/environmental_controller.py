"""
Environmental Actuator Controller
ESP32-simulated relay controls for dehumidifier and humidifier
"""

import logging
from typing import Optional


class EnvironmentalController:
    """
    Controls environmental actuators (dehumidifier, humidifier)
    
    Simulates ESP32 relay controls via GPIO pins
    - Dehumidifier: Pin 25 (example)
    - Humidifier: Pin 26 (example)
    """
    
    def __init__(self, logger: logging.Logger):
        """
        Args:
            logger: Logger instance
        """
        self.logger = logger
        
        # Actuator states
        self.dehumidifier_active = False
        self.dehumidifier_power = 0  # 0-100%
        
        self.humidifier_active = False
        self.humidifier_power = 0  # 0-100%
        
        # Simulated GPIO pins (for emulation only)
        self.dehumidifier_pin = 25
        self.humidifier_pin = 26
        
        self.logger.info("Environmental controller initialized")
    
    def set_dehumidifier(self, active: bool, power: int = 100):
        """
        Control dehumidifier relay
        
        Args:
            active: Activate/deactivate relay
            power: Power level (0-100%), default 100%
        """
        old_state = (self.dehumidifier_active, self.dehumidifier_power)
        
        self.dehumidifier_active = active
        self.dehumidifier_power = max(0, min(100, power)) if active else 0
        
        if active:
            self.logger.info(
                f"🌬️  Dehumidifier ACTIVATED at {self.dehumidifier_power}% power "
                f"(Pin {self.dehumidifier_pin})"
            )
        else:
            self.logger.info(f"🌬️  Dehumidifier DEACTIVATED (Pin {self.dehumidifier_pin})")
        
        # In real ESP32, would be: GPIO.output(self.dehumidifier_pin, GPIO.HIGH if active else GPIO.LOW)
    
    def set_humidifier(self, active: bool, power: int = 100):
        """
        Control humidifier relay
        
        Args:
            active: Activate/deactivate relay
            power: Power level (0-100%), default 100%
        """
        old_state = (self.humidifier_active, self.humidifier_power)
        
        self.humidifier_active = active
        self.humidifier_power = max(0, min(100, power)) if active else 0
        
        if active:
            self.logger.info(
                f"💧 Humidifier ACTIVATED at {self.humidifier_power}% power "
                f"(Pin {self.humidifier_pin})"
            )
        else:
            self.logger.info(f"💧 Humidifier DEACTIVATED (Pin {self.humidifier_pin})")
        
        # In real ESP32, would be: GPIO.output(self.humidifier_pin, GPIO.HIGH if active else GPIO.LOW)
    
    def apply_command(self, command: dict):
        """
        Apply environmental control command from fog server
        
        Args:
            command: Dict with dehumidifier/humidifier settings
                {
                    'dehumidifier_active': bool,
                    'dehumidifier_power': int,
                    'humidifier_active': bool,
                    'humidifier_power': int
                }
        """
        # Apply dehumidifier command
        if 'dehumidifier_active' in command:
            self.set_dehumidifier(
                command.get('dehumidifier_active', False),
                command.get('dehumidifier_power', 100)
            )
        
        # Apply humidifier command
        if 'humidifier_active' in command:
            self.set_humidifier(
                command.get('humidifier_active', False),
                command.get('humidifier_power', 100)
            )
    
    def get_state(self) -> dict:
        """
        Get current actuator states
        
        Returns:
            Dict with dehumidifier and humidifier states
        """
        return {
            'dehumidifier_active': self.dehumidifier_active,
            'dehumidifier_power': self.dehumidifier_power,
            'humidifier_active': self.humidifier_active,
            'humidifier_power': self.humidifier_power
        }
    
    def reset(self):
        """Reset all actuators to inactive state"""
        self.set_dehumidifier(False, 0)
        self.set_humidifier(False, 0)
        self.logger.info("Environmental actuators reset to inactive")
    
    def get_power_presets(self) -> dict:
        """
        Get standard power level presets
        
        Returns:
            Dict of preset names and values
        """
        return {
            'low': 30,
            'medium': 60,
            'high': 100
        }
    
    def estimate_humidity_change_rate(self) -> float:
        """
        Estimate humidity change rate based on current actuator states
        
        Returns:
            Estimated % change per hour (positive for increase, negative for decrease)
        """
        rate = 0.0
        
        # Dehumidifier: -5% per hour at 100% power
        if self.dehumidifier_active:
            rate -= 5.0 * (self.dehumidifier_power / 100.0)
        
        # Humidifier: +5% per hour at 100% power
        if self.humidifier_active:
            rate += 5.0 * (self.humidifier_power / 100.0)
        
        return rate

"""
Virtual GP2Y1010 Dust Sensor Emulation
Simulates particulate matter (PM) concentration with accumulation behavior
"""

import random
from typing import Optional
from sensors.base_sensor import BaseSensor


class DustSensor(BaseSensor):
    """
    Emulates GP2Y1010 optical dust sensor behavior
    
    Features:
    - Unidirectional dust accumulation (no natural decrease)
    - Base accumulation rate (profile-defined)
    - Fan activity influence (high RPM accelerates buildup)
    - Tends toward equilibrium concentration over long term
    """
    
    def __init__(
        self,
        sensor_id: str,
        initial_dust: float,
        equilibrium_dust: float,
        base_rate: float = 0.010,
        noise_amplitude: float = 1.0
    ):
        """
        Args:
            sensor_id: Unique sensor identifier
            initial_dust: Starting dust concentration (μg/m³)
            equilibrium_dust: Target equilibrium concentration (μg/m³)
            base_rate: Base accumulation rate per tick (default: 0.010 μg/m³)
            noise_amplitude: Random noise amplitude (default: 1.0 μg/m³)
        """
        super().__init__(sensor_id, "GP2Y1010_Dust")
        
        self.current_dust = initial_dust
        self.equilibrium_dust = equilibrium_dust
        self.base_rate = base_rate
        self.noise_amplitude = noise_amplitude
        
        # Fan influence factor
        self.fan_influence = 1.0  # Multiplier when fans at high RPM
        
        self.logger.info(
            f"Dust sensor initialized: {initial_dust} → {equilibrium_dust} μg/m³ "
            f"(rate: {base_rate}/tick)"
        )
    
    def read(self) -> float:
        """
        Read current dust concentration
        
        Returns:
            Current PM concentration (μg/m³)
        """
        # Add sensor noise
        noise = random.uniform(-self.noise_amplitude, self.noise_amplitude)
        reading = max(0.0, self.current_dust + noise)
        
        self.logger.debug(f"Dust reading: {reading:.2f} μg/m³")
        return reading
    
    def evolve(self, delta_time: float = 300.0, avg_fan_pwm: float = 0.0):
        """
        Evolve dust concentration (accumulation)
        
        Algorithm:
        1. Calculate base accumulation toward equilibrium
        2. Apply fan influence (high RPM increases rate)
        3. Accumulate dust (unidirectional - no natural decrease)
        4. Approach equilibrium asymptotically
        
        Args:
            delta_time: Time step in seconds (default: 300s = 5 minutes)
            avg_fan_pwm: Average fan PWM duty (0-100%) for influence calculation
        """
        # Calculate fan influence
        # Fans above 80% PWM stir up settled dust, accelerating buildup
        if avg_fan_pwm > 80:
            self.fan_influence = 1.0 + (avg_fan_pwm - 80) / 100.0  # 1.0 to 1.2
        elif avg_fan_pwm > 50:
            self.fan_influence = 1.0 + (avg_fan_pwm - 50) / 200.0  # 1.0 to 1.15
        else:
            self.fan_influence = 1.0
        
        # Asymptotic approach to equilibrium
        # When close to equilibrium, accumulation slows down
        if self.current_dust < self.equilibrium_dust:
            # Distance from equilibrium
            distance = self.equilibrium_dust - self.current_dust
            
            # Accumulation rate proportional to distance (but never zero)
            # This creates asymptotic approach
            rate_factor = min(1.0, distance / self.equilibrium_dust)
            
            # Total accumulation
            accumulation = self.base_rate * self.fan_influence * rate_factor
            
            self.current_dust += accumulation
            
            self.logger.debug(
                f"Dust accumulated: {self.current_dust:.2f} μg/m³ "
                f"(+{accumulation:.4f}, fan_influence: {self.fan_influence:.2f})"
            )
        else:
            # Already at or above equilibrium - very slow additional accumulation
            accumulation = self.base_rate * 0.1 * self.fan_influence
            self.current_dust += accumulation
            
            self.logger.debug(
                f"Dust at equilibrium: {self.current_dust:.2f} μg/m³ "
                f"(+{accumulation:.4f})"
            )
    
    def apply_cleaning(self, reduction_percent: float = 80.0):
        """
        Simulate physical cleaning (manual intervention)
        
        Args:
            reduction_percent: Percentage of dust removed (default: 80%)
        """
        old_dust = self.current_dust
        self.current_dust *= (1.0 - reduction_percent / 100.0)
        
        self.logger.info(
            f"Physical cleaning applied: {old_dust:.2f} → {self.current_dust:.2f} μg/m³ "
            f"({reduction_percent}% reduction)"
        )
    
    def reset_to_initial(self, initial_dust: float, equilibrium_dust: float):
        """
        Reset sensor to new profile values
        
        Args:
            initial_dust: New initial dust concentration (μg/m³)
            equilibrium_dust: New equilibrium (μg/m³)
        """
        self.current_dust = initial_dust
        self.equilibrium_dust = equilibrium_dust
        self.fan_influence = 1.0
        
        self.logger.info(
            f"Sensor reset: {initial_dust} → {equilibrium_dust} μg/m³"
        )
    
    def get_state(self) -> dict:
        """Get current sensor state"""
        return {
            'sensor_id': self.sensor_id,
            'type': self.sensor_type,
            'dust': self.current_dust,
            'equilibrium': self.equilibrium_dust,
            'base_rate': self.base_rate,
            'fan_influence': self.fan_influence
        }
    
    def get_status_level(self) -> str:
        """
        Get dust level status
        
        Returns:
            'low', 'moderate', or 'high'
        """
        if self.current_dust < 25:
            return 'low'
        elif self.current_dust < 50:
            return 'moderate'
        else:
            return 'high'
    
    def needs_alert(self) -> bool:
        """
        Check if dust level requires alert
        
        Returns:
            True if dust > 50 μg/m³ (physical cleaning needed)
        """
        return self.current_dust > 50.0

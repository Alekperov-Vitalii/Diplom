"""
Environmental Control Algorithm for Fog Server
Handles automatic control of dehumidifier/humidifier with inertia and alerts
"""

import time
from typing import Dict, List, Optional
from datetime import datetime, timezone


class EnvironmentalControlAlgorithm:
    """
    Automatic environmental control with inertia delays
    
    Features:
    - Humidity control (dehumidifier >60%, humidifier <40%)
    - Dust monitoring (alert >50 μg/m³)
    - Inertia delays (10-30 minutes before activation/deactivation)
    - Persistent out-of-range detection for humidity alerts
    """
    
    # Optimal ranges
    HUMIDITY_MIN = 40.0  # %
    HUMIDITY_MAX = 60.0  # %
    DUST_ALERT_THRESHOLD = 50.0  # μg/m³
    
    # Control parameters
    DEHUMIDIFIER_POWER = 75  # % (default power level)
    HUMIDIFIER_POWER = 75  # % (default power level)
    
    # Inertia delays (seconds)
    MIN_HOLD_TIME = 600  # 10 minutes
    MAX_HOLD_TIME = 1800  # 30 minutes
    
    # Alert persistence requirement
    HUMIDITY_ALERT_PERSISTENCE = 3600  # 1 hour
    
    def __init__(self):
        # Control state
        self.dehumidifier_active = False
        self.dehumidifier_power = 0
        self.humidifier_active = False
        self.humidifier_power = 0
        
        # Current environmental state (for cooling modifier)
        self.current_humidity = 50.0  # Default optimal
        self.current_dust = 0.0       # Default clean

        
        # Timing tracking
        self.last_activation_time: Dict[str, float] = {}
        self.humidity_out_of_range_since: Optional[float] = None
        
        # Alerts
        self.active_environmental_alerts: List[Dict] = []
        
        print("✓ Environmental Control Algorithm initialized")
        
    def update_current_state(self, humidity: float, dust: float):
        """Update current environmental state"""
        self.current_humidity = humidity
        self.current_dust = dust

    
    def calculate_control_commands(
        self, 
        humidity: float, 
        dust: float
    ) -> Dict:
        """
        Calculate environmental control commands
        
        Args:
            humidity: Current humidity (%)
            dust: Current dust concentration (μg/m³)
        
        Returns:
            Dict with control commands
        """
        current_time = time.time()
        
        # Reset control commands
        # Reset control commands
        commands = {
            'dehumidifier_active': False,
            'dehumidifier_power': 0,
            'humidifier_active': False,
            'humidifier_power': 0
        }
        
        # Humidity control logic
        if humidity > self.HUMIDITY_MAX:
            # HIGH HUMIDITY: activate dehumidifier
            if self._can_activate('dehumidifier', current_time):
                commands['dehumidifier_active'] = True
                commands['dehumidifier_power'] = self.DEHUMIDIFIER_POWER
                self.last_activation_time['dehumidifier'] = current_time
                print(f"🌬️  Activating dehumidifier at {self.DEHUMIDIFIER_POWER}% (humidity: {humidity:.1f}%)")
            elif self.dehumidifier_active:
                # Keep active if already on
                commands['dehumidifier_active'] = True
                commands['dehumidifier_power'] = self.dehumidifier_power
        
        elif humidity < self.HUMIDITY_MIN:
            # LOW HUMIDITY: activate humidifier
            if self._can_activate('humidifier', current_time):
                commands['humidifier_active'] = True
                commands['humidifier_power'] = self.HUMIDIFIER_POWER
                self.last_activation_time['humidifier'] = current_time
                print(f"💧 Activating humidifier at {self.HUMIDIFIER_POWER}% (humidity: {humidity:.1f}%)")
            elif self.humidifier_active:
                # Keep active if already on
                commands['humidifier_active'] = True
                commands['humidifier_power'] = self.humidifier_power
        
        else:
            # OPTIMAL RANGE: deactivate both
            if self.dehumidifier_active or self.humidifier_active:
                print(f"✓ Humidity in optimal range ({humidity:.1f}%), deactivating actuators")
            commands['dehumidifier_active'] = False
            commands['humidifier_active'] = False
        
        # Update internal state
        self.dehumidifier_active = commands['dehumidifier_active']
        self.dehumidifier_power = commands['dehumidifier_power']
        self.humidifier_active = commands['humidifier_active']
        self.humidifier_power = commands['humidifier_power']
        
        return commands
    
    def _can_activate(self, actuator: str, current_time: float) -> bool:
        """
        Check if enough time has passed to activate actuator (inertia delay)
        
        Args:
            actuator: 'dehumidifier' or 'humidifier'
            current_time: Current timestamp
        
        Returns:
            True if can activate
        """
        if actuator not in self.last_activation_time:
            return True
        
        time_since_last = current_time - self.last_activation_time[actuator]
        return time_since_last >= self.MIN_HOLD_TIME
    
    def check_environmental_alerts(
        self, 
        humidity: float, 
        dust: float, 
        timestamp: str
    ) -> List[Dict]:
        """
        Check for environmental alert conditions
        
        Args:
            humidity: Current humidity (%)
            dust: Current dust concentration (μg/m³)
            timestamp: ISO timestamp
        
        Returns:
            List of new alerts
        """
        new_alerts = []
        current_time = time.time()
        
        # Dust alert (immediate)
        if dust > self.DUST_ALERT_THRESHOLD:
            alert = {
                'alert_type': 'dust_high',
                'current_value': dust,
                'threshold': self.DUST_ALERT_THRESHOLD,
                'severity': 'critical',
                'timestamp': timestamp,
                'message': f'Physical cleaning required: Dust at {dust:.1f} μg/m³ (threshold: {self.DUST_ALERT_THRESHOLD} μg/m³)'
            }
            new_alerts.append(alert)
            print(f"🚨 DUST ALERT: {alert['message']}")
        
        # Humidity alerts (persistent out-of-range for >1 hour)
        if humidity < self.HUMIDITY_MIN or humidity > self.HUMIDITY_MAX:
            # Track when humidity went out of range
            if self.humidity_out_of_range_since is None:
                self.humidity_out_of_range_since = current_time
            
            # Check if persistent
            time_out_of_range = current_time - self.humidity_out_of_range_since
            if time_out_of_range >= self.HUMIDITY_ALERT_PERSISTENCE:
                if humidity < self.HUMIDITY_MIN:
                    alert = {
                        'alert_type': 'humidity_low',
                        'current_value': humidity,
                        'threshold': self.HUMIDITY_MIN,
                        'severity': 'warning',
                        'timestamp': timestamp,
                        'message': f'Low humidity alert: {humidity:.1f}% for >{self.HUMIDITY_ALERT_PERSISTENCE/3600:.1f}h (risk of static electricity)'
                    }
                else:
                    alert = {
                        'alert_type': 'humidity_high',
                        'current_value': humidity,
                        'threshold': self.HUMIDITY_MAX,
                        'severity': 'warning',
                        'timestamp': timestamp,
                        'message': f'High humidity alert: {humidity:.1f}% for >{self.HUMIDITY_ALERT_PERSISTENCE/3600:.1f}h (risk of corrosion)'
                    }
                new_alerts.append(alert)
                print(f"⚠️  HUMIDITY ALERT: {alert['message']}")
        else:
            # Reset tracking when back in range
            self.humidity_out_of_range_since = None
        
        self.active_environmental_alerts = new_alerts
        return new_alerts
    
    def get_cooling_efficiency_modifier(self, humidity: float, dust: float) -> float:
        """
        Calculate cooling efficiency modifier based on environmental parameters
        
        Formula: efficiency = 1 - (0.002 * |RH - 50|) - (0.001 * PM)
        
        Args:
            humidity: Current humidity (%)
            dust: Current dust concentration (μg/m³)
        
        Returns:
            Efficiency multiplier (0.0-1.0)
        """
        humidity_penalty = 0.002 * abs(humidity - 50.0)
        dust_penalty = 0.001 * dust
        
        efficiency = 1.0 - humidity_penalty - dust_penalty
        efficiency = max(0.0, min(1.0, efficiency))  # Clamp to [0, 1]
        
        return efficiency


class TrendAnalyzer:
    """
    Analyzes environmental trends and infers hidden factors
    """
    
    def __init__(self):
        self.history: Dict[str, List[tuple]] = {'humidity': [], 'dust': []}
        print("✓ Trend Analyzer initialized")
    
    def add_data_point(self, humidity: float, dust: float, timestamp: float):
        """
        Add data point to history
        
        Args:
            humidity: Humidity value (%)
            dust: Dust value (μg/m³)
            timestamp: Unix timestamp
        """
        self.history['humidity'].append((timestamp, humidity))
        self.history['dust'].append((timestamp, dust))
        
        # Keep only last 24 hours
        cutoff_time = timestamp - 86400
        self.history['humidity'] = [(t, v) for t, v in self.history['humidity'] if t > cutoff_time]
        self.history['dust'] = [(t, v) for t, v in self.history['dust'] if t > cutoff_time]
    
    def calculate_hourly_humidity_change_rate(self) -> Optional[float]:
        """
        Calculate average hourly humidity change rate
        
        Returns:
            Rate in %/hour or None if insufficient data
        """
        if len(self.history['humidity']) < 2:
            return None
        
        # Get data from last hour
        current_time = self.history['humidity'][-1][0]
        hour_ago = current_time - 3600
        
        recent_data = [(t, v) for t, v in self.history['humidity'] if t >= hour_ago]
        
        if len(recent_data) < 2:
            return None
        
        # Calculate average change
        total_change = recent_data[-1][1] - recent_data[0][1]
        time_span = recent_data[-1][0] - recent_data[0][0]
        
        if time_span == 0:
            return None
        
        # Convert to per-hour rate
        rate = (total_change / time_span) * 3600
        return rate
    
    def calculate_hourly_dust_accumulation_rate(self) -> Optional[float]:
        """
        Calculate average hourly dust accumulation rate
        
        Returns:
            Rate in μg/m³/hour or None if insufficient data
        """
        if len(self.history['dust']) < 2:
            return None
        
        # Get data from last hour
        current_time = self.history['dust'][-1][0]
        hour_ago = current_time - 3600
        
        recent_data = [(t, v) for t, v in self.history['dust'] if t >= hour_ago]
        
        if len(recent_data) < 2:
            return None
        
        # Calculate average change
        total_change = recent_data[-1][1] - recent_data[0][1]
        time_span = recent_data[-1][0] - recent_data[0][0]
        
        if time_span == 0:
            return None
        
        # Convert to per-hour rate
        rate = (total_change / time_span) * 3600
        return rate
    
    def infer_ventilation_level(self, humidity_rate: Optional[float]) -> str:
        """
        Infer ventilation level from humidity change rate
        
        Args:
            humidity_rate: Hourly humidity change rate (%/hour)
        
        Returns:
            Ventilation level description
        """
        if humidity_rate is None:
            return "Unknown"
        
        if humidity_rate > 1.0:
            return "High Ventilation (inflow)"
        elif humidity_rate > 0.0:
            return "Moderate Ventilation"
        elif humidity_rate > -1.0:
            return "Sealed Space"
        else:
            return "Controlled Environment"
    
    def infer_filtration_quality(self, dust_rate: Optional[float]) -> str:
        """
        Infer filtration quality from dust accumulation rate
        
        Args:
            dust_rate: Hourly dust accumulation rate (μg/m³/hour)
        
        Returns:
            Filtration quality description
        """
        if dust_rate is None:
            return "Unknown"
        
        if dust_rate > 2.0:
            return "Poor Filtration"
        elif dust_rate > 1.0:
            return "Moderate Filtration"
        elif dust_rate > 0.0:
            return "Good Filtration"
        else:
            return "Excellent Filtration"


# Global instances
environmental_control_algo = EnvironmentalControlAlgorithm()
trend_analyzer = TrendAnalyzer()

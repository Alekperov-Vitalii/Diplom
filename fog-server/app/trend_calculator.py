"""
Advanced Trend Calculator for Fog Server
Calculates cumulative degradation metrics: Corrosion Index (CI) and Fan Wear Index (FWI)
"""

import time
import math
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone


class AdvancedTrendCalculator:
    """
    Calculates advanced cumulative trends for equipment degradation monitoring
    
    Metrics:
    - Corrosion Index (CI): Risk of equipment corrosion based on humidity, dust, temperature
    - Fan Wear Index (FWI): Cumulative fan wear based on RPM, dust, temperature
    """
    
    # CI thresholds
    CI_LOW_THRESHOLD = 1.0
    CI_HIGH_THRESHOLD = 2.0
    
    # FWI thresholds (equivalent hours)
    FWI_ELEVATED_THRESHOLD = 100.0
    FWI_CRITICAL_THRESHOLD = 200.0
    
    # Max RPM for normalization
    MAX_RPM = 5000
    
    # Cooling efficiency degradation limits (2-4% max)
    MAX_COOLING_DEGRADATION = 0.04  # 4%
    CI_DEGRADATION_START = 1.5  # Start degrading at CI > 1.5
    
    def __init__(self, influx_manager):
        """
        Initialize trend calculator
        
        Args:
            influx_manager: InfluxDB manager for storing trend data
        """
        self.influx = influx_manager
        
        # Cumulative indices
        self.ci = 0.0
        self.fwi = 0.0
        
        # Tracking for rate calculations
        self.last_update = time.time()
        self.last_humidity = None
        self.last_dust = None
        
        # Alert tracking
        self.ci_alert_sent = False
        self.fwi_alert_sent = False
        
        print("✓ Advanced Trend Calculator initialized")
    
    def reset_indices(self):
        """Reset CI and FWI to zero (called on profile change or manual reset)"""
        self.ci = 0.0
        self.fwi = 0.0
        self.ci_alert_sent = False
        self.fwi_alert_sent = False
        print("🔄 CI and FWI reset to zero")
    
    def update_ci(
        self, 
        humidity: float, 
        dust: float, 
        temperature: float
    ) -> Tuple[float, str]:
        """
        Update Corrosion Index
        
        Formula: ΔCI = (RH / 50) × (1 + 0.1 × Dust) × exp((T - 25) / 10) × dt
        
        Args:
            humidity: Relative humidity (%)
            dust: Dust concentration (μg/m³)
            temperature: Temperature (°C)
        
        Returns:
            Tuple of (CI value, risk level)
        """
        current_time = time.time()
        dt = (current_time - self.last_update) / 3600.0  # Convert to hours
        
        # Calculate humidity change rate for hidden factor
        humidity_rate = 0.0
        if self.last_humidity is not None and dt > 0:
            humidity_rate = abs(humidity - self.last_humidity) / dt
        
        # Base formula
        dust_factor = 1 + 0.1 * dust
        
        # Hidden factor: rapid humidity changes increase dust deposition
        if humidity_rate > 1.0:  # >1%/hour
            dust_factor *= 1.2
        
        temp_factor = math.exp((temperature - 25) / 10)
        
        delta_ci = (humidity / 50) * dust_factor * temp_factor * dt
        
        self.ci += delta_ci
        self.last_humidity = humidity
        
        # Determine risk level
        if self.ci < self.CI_LOW_THRESHOLD:
            risk_level = "low"
        elif self.ci < self.CI_HIGH_THRESHOLD:
            risk_level = "medium"
        else:
            risk_level = "high"
        
        return self.ci, risk_level
    
    def update_fwi(
        self,
        avg_rpm: float,
        dust: float,
        avg_temp: float
    ) -> Tuple[float, str]:
        """
        Update Fan Wear Index
        
        Formula: ΔFWI = (RPM / Max_RPM) × (1 + 0.2 × Dust / 50) × (T > 70 ? 1.5 : 1) × dt
        
        Args:
            avg_rpm: Average fan RPM
            dust: Dust concentration (μg/m³)
            avg_temp: Average GPU temperature (°C)
        
        Returns:
            Tuple of (FWI value, wear level)
        """
        current_time = time.time()
        dt = (current_time - self.last_update) / 3600.0  # Convert to hours
        
        # Calculate dust accumulation rate for hidden factor
        dust_rate = 0.0
        if self.last_dust is not None and dt > 0:
            dust_rate = (dust - self.last_dust) / dt
        
        # Base formula
        rpm_factor = avg_rpm / self.MAX_RPM
        dust_factor = 1 + 0.2 * (dust / 50)
        
        # Hidden factor: rapid dust accumulation increases wear
        if dust_rate > 2.0:  # >2 μg/m³/hour
            dust_factor *= 1.15
        
        temp_factor = 1.5 if avg_temp > 70 else 1.0
        
        delta_fwi = rpm_factor * dust_factor * temp_factor * dt
        
        self.fwi += delta_fwi
        self.last_dust = dust
        
        # Determine wear level
        if self.fwi < self.FWI_ELEVATED_THRESHOLD:
            wear_level = "normal"
        elif self.fwi < self.FWI_CRITICAL_THRESHOLD:
            wear_level = "elevated"
        else:
            wear_level = "critical"
        
        return self.fwi, wear_level
    
    def get_cooling_efficiency_modifier(self) -> float:
        """
        Calculate cooling efficiency modifier based on CI
        
        Returns:
            Efficiency multiplier (0.96-1.0, representing 0-4% degradation)
        """
        if self.ci <= self.CI_DEGRADATION_START:
            return 1.0
        
        # Linear degradation from CI=1.5 to CI=3.0
        # At CI=1.5: 0% degradation
        # At CI=3.0+: 4% degradation (max)
        degradation_range = 3.0 - self.CI_DEGRADATION_START
        ci_excess = min(self.ci - self.CI_DEGRADATION_START, degradation_range)
        
        degradation_percent = (ci_excess / degradation_range) * self.MAX_COOLING_DEGRADATION
        
        return 1.0 - degradation_percent
    
    def get_fan_power_modifier(self) -> float:
        """
        Calculate fan power modifier based on FWI
        
        Returns:
            Power multiplier (0.9-1.0, representing 0-10% reduction)
        """
        if self.fwi <= 150:
            return 1.0
        
        # At FWI=150: 0% reduction
        # At FWI=200+: 10% reduction
        reduction = min((self.fwi - 150) / 50, 1.0) * 0.1
        
        return 1.0 - reduction
    
    def check_alerts(self) -> List[Dict]:
        """
        Check thresholds and generate alerts
        
        Returns:
            List of alert dictionaries
        """
        alerts = []
        
        # CI alert
        if self.ci >= self.CI_HIGH_THRESHOLD and not self.ci_alert_sent:
            alerts.append({
                "type": "corrosion_risk",
                "severity": "high",
                "message": f"Високий ризик корозії (CI={self.ci:.2f}) — потрібен огляд обладнання",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.ci_alert_sent = True
        elif self.ci < self.CI_HIGH_THRESHOLD:
            self.ci_alert_sent = False
        
        # FWI alert
        if self.fwi >= self.FWI_CRITICAL_THRESHOLD and not self.fwi_alert_sent:
            alerts.append({
                "type": "fan_wear",
                "severity": "critical",
                "message": f"Критичний знос вентиляторів (FWI={self.fwi:.1f} год) — потрібна заміна",
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
            self.fwi_alert_sent = True
        elif self.fwi < self.FWI_CRITICAL_THRESHOLD:
            self.fwi_alert_sent = False
        
        return alerts
    
    def update_all(
        self,
        humidity: float,
        dust: float,
        room_temp: float,
        avg_rpm: float,
        avg_gpu_temp: float
    ) -> Dict:
        """
        Update all trends and return current state
        
        Args:
            humidity: Humidity (%)
            dust: Dust (μg/m³)
            room_temp: Room temperature (°C)
            avg_rpm: Average fan RPM
            avg_gpu_temp: Average GPU temperature (°C)
        
        Returns:
            Dictionary with current CI, FWI, and modifiers
        """
        ci_value, ci_risk = self.update_ci(humidity, dust, room_temp)
        fwi_value, fwi_wear = self.update_fwi(avg_rpm, dust, avg_gpu_temp)
        
        self.last_update = time.time()
        
        cooling_mod = self.get_cooling_efficiency_modifier()
        fan_power_mod = self.get_fan_power_modifier()
        
        alerts = self.check_alerts()
        
        return {
            "corrosion_index": {
                "value": ci_value,
                "risk_level": ci_risk,
                "threshold_low": self.CI_LOW_THRESHOLD,
                "threshold_high": self.CI_HIGH_THRESHOLD
            },
            "fan_wear_index": {
                "value": fwi_value,
                "wear_level": fwi_wear,
                "threshold_elevated": self.FWI_ELEVATED_THRESHOLD,
                "threshold_critical": self.FWI_CRITICAL_THRESHOLD
            },
            "modifiers": {
                "cooling_efficiency": cooling_mod,
                "fan_power": fan_power_mod
            },
            "alerts": alerts
        }
    
    def store_to_influx(self, device_id: str = "esp32_master_001"):
        """
        Store current CI and FWI values to InfluxDB
        
        Args:
            device_id: Device identifier
        """
        ci_value, ci_risk = self.ci, self._get_ci_risk_level()
        fwi_value, fwi_wear = self.fwi, self._get_fwi_wear_level()
        
        # Write to InfluxDB
        self.influx.write_advanced_trends(
            device_id=device_id,
            ci=ci_value,
            ci_risk=ci_risk,
            fwi=fwi_value,
            fwi_wear=fwi_wear
        )
    
    def _get_ci_risk_level(self) -> str:
        """Get current CI risk level"""
        if self.ci < self.CI_LOW_THRESHOLD:
            return "low"
        elif self.ci < self.CI_HIGH_THRESHOLD:
            return "medium"
        else:
            return "high"
    
    def _get_fwi_wear_level(self) -> str:
        """Get current FWI wear level"""
        if self.fwi < self.FWI_ELEVATED_THRESHOLD:
            return "normal"
        elif self.fwi < self.FWI_CRITICAL_THRESHOLD:
            return "elevated"
        else:
            return "critical"

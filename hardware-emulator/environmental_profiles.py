"""
Environmental Profiles for GPU Cluster Simulation
Defines 9 comprehensive profiles covering all combinations of dust and humidity levels
"""

from typing import Dict, Any
from dataclasses import dataclass
import json


@dataclass
class EnvironmentalProfile:
    """
    Environmental profile configuration
    
    Attributes:
        profile_id: Unique profile identifier (1-9)
        name: Human-readable profile name
        dust_initial: Initial dust concentration (μg/m³)
        dust_equilibrium: Equilibrium dust concentration (μg/m³)
        dust_rate: Base dust accumulation rate (μg/m³ per tick)
        humidity_initial: Initial relative humidity (%)
        humidity_equilibrium: Equilibrium relative humidity (%)
        humidity_rate: Base humidity change rate (% per tick)
        description: Profile description
    """
    profile_id: int
    name: str
    dust_initial: float
    dust_equilibrium: float
    dust_rate: float
    humidity_initial: float
    humidity_equilibrium: float
    humidity_rate: float
    description: str
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return {
            'profile_id': self.profile_id,
            'name': self.name,
            'dust_initial': self.dust_initial,
            'dust_equilibrium': self.dust_equilibrium,
            'dust_rate': self.dust_rate,
            'humidity_initial': self.humidity_initial,
            'humidity_equilibrium': self.humidity_equilibrium,
            'humidity_rate': self.humidity_rate,
            'description': self.description
        }


# ============================================================================
# PROFILE DEFINITIONS - ALL 9 COMBINATIONS
# ============================================================================

PROFILES = {
    1: EnvironmentalProfile(
        profile_id=1,
        name="Low Dust, Low Humidity",
        dust_initial=10.0,
        dust_equilibrium=20.0,
        dust_rate=0.005,  # Slow accumulation
        humidity_initial=30.0,
        humidity_equilibrium=35.0,
        humidity_rate=0.01,  # Slow upward drift
        description="Dry, clean environment - minimal dust, humidity trending slightly upward"
    ),
    
    2: EnvironmentalProfile(
        profile_id=2,
        name="Low Dust, Optimal Humidity",
        dust_initial=15.0,
        dust_equilibrium=25.0,
        dust_rate=0.007,
        humidity_initial=50.0,
        humidity_equilibrium=50.0,
        humidity_rate=0.0,  # Stable
        description="Balanced environment - low contamination, stable optimal humidity"
    ),
    
    3: EnvironmentalProfile(
        profile_id=3,
        name="Low Dust, High Humidity",
        dust_initial=10.0,
        dust_equilibrium=20.0,
        dust_rate=0.005,
        humidity_initial=70.0,
        humidity_equilibrium=65.0,
        humidity_rate=-0.01,  # Slow downward drift
        description="Humid clean space - dust minimal, humidity decreasing slowly but elevated"
    ),
    
    4: EnvironmentalProfile(
        profile_id=4,
        name="Moderate Dust, Low Humidity",
        dust_initial=30.0,
        dust_equilibrium=40.0,
        dust_rate=0.010,  # Medium accumulation
        humidity_initial=30.0,
        humidity_equilibrium=35.0,
        humidity_rate=0.01,
        description="Moderately dusty dry area - dust accumulating at medium rate"
    ),
    
    5: EnvironmentalProfile(
        profile_id=5,
        name="Moderate Dust, Optimal Humidity",
        dust_initial=35.0,
        dust_equilibrium=45.0,
        dust_rate=0.012,
        humidity_initial=50.0,
        humidity_equilibrium=50.0,
        humidity_rate=0.0,
        description="Standard operational environment - moderate dust, balanced humidity"
    ),
    
    6: EnvironmentalProfile(
        profile_id=6,
        name="Moderate Dust, High Humidity",
        dust_initial=30.0,
        dust_equilibrium=40.0,
        dust_rate=0.013,  # Slightly accelerated by humidity
        humidity_initial=70.0,
        humidity_equilibrium=65.0,
        humidity_rate=-0.01,
        description="Humid moderate-dust environment - combined risks, dust growth influenced by humidity"
    ),
    
    7: EnvironmentalProfile(
        profile_id=7,
        name="High Dust, Low Humidity",
        dust_initial=60.0,
        dust_equilibrium=80.0,
        dust_rate=0.020,  # Rapid accumulation
        humidity_initial=30.0,
        humidity_equilibrium=35.0,
        humidity_rate=0.01,
        description="Heavily dusty dry conditions - rapid dust buildup, low humidity drift"
    ),
    
    8: EnvironmentalProfile(
        profile_id=8,
        name="High Dust, Optimal Humidity",
        dust_initial=55.0,
        dust_equilibrium=70.0,
        dust_rate=0.018,
        humidity_initial=50.0,
        humidity_equilibrium=50.0,
        humidity_rate=0.0,
        description="High dust in balanced humidity - dust accumulating quickly"
    ),
    
    9: EnvironmentalProfile(
        profile_id=9,
        name="High Dust, High Humidity",
        dust_initial=60.0,
        dust_equilibrium=80.0,
        dust_rate=0.022,  # Accelerated by humidity
        humidity_initial=70.0,
        humidity_equilibrium=65.0,
        humidity_rate=-0.012,
        description="Worst-case scenario - humid and dusty, accelerated dust effects"
    )
}


class ProfileManager:
    """Manages environmental profile loading and switching"""
    
    def __init__(self, default_profile_id: int = 5):
        """
        Initialize with default profile
        
        Args:
            default_profile_id: Profile to load initially (default: 5 - Moderate/Optimal)
        """
        self.current_profile_id = default_profile_id
        self.current_profile = PROFILES[default_profile_id]
    
    def get_profile(self, profile_id: int) -> EnvironmentalProfile:
        """
        Get profile by ID
        
        Args:
            profile_id: Profile ID (1-9)
            
        Returns:
            EnvironmentalProfile
            
        Raises:
            ValueError: If profile_id is invalid
        """
        if profile_id not in PROFILES:
            raise ValueError(f"Invalid profile ID: {profile_id}. Must be 1-9.")
        return PROFILES[profile_id]
    
    def switch_profile(self, profile_id: int) -> EnvironmentalProfile:
        """
        Switch to a different profile
        
        Args:
            profile_id: New profile ID (1-9)
            
        Returns:
            New EnvironmentalProfile
        """
        self.current_profile = self.get_profile(profile_id)
        self.current_profile_id = profile_id
        print(f"✓ Switched to Profile {profile_id}: {self.current_profile.name}")
        return self.current_profile
    
    def list_profiles(self) -> list:
        """Get list of all available profiles"""
        return [
            {
                'id': p.profile_id,
                'name': p.name,
                'description': p.description
            }
            for p in PROFILES.values()
        ]
    
    def export_to_json(self, filepath: str):
        """Export all profiles to JSON file"""
        data = {
            'profiles': [p.to_dict() for p in PROFILES.values()]
        }
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(f"✓ Profiles exported to {filepath}")


# Default instance
default_profile_manager = ProfileManager()


if __name__ == "__main__":
    # Test profile loading
    print("=" * 60)
    print("Environmental Profiles Test")
    print("=" * 60)
    
    manager = ProfileManager()
    
    print(f"\nCurrent Profile: {manager.current_profile.name}")
    print(f"  Dust: {manager.current_profile.dust_initial} → {manager.current_profile.dust_equilibrium} μg/m³")
    print(f"  Humidity: {manager.current_profile.humidity_initial} → {manager.current_profile.humidity_equilibrium}%")
    
    print("\n" + "=" * 60)
    print("All Available Profiles:")
    print("=" * 60)
    for profile in PROFILES.values():
        print(f"\n{profile.profile_id}. {profile.name}")
        print(f"   {profile.description}")
        print(f"   Dust: {profile.dust_initial} → {profile.dust_equilibrium} μg/m³ (rate: {profile.dust_rate})")
        print(f"   Humidity: {profile.humidity_initial} → {profile.humidity_equilibrium}% (rate: {profile.humidity_rate})")

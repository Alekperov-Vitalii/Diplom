"""
Модуль ядра системы: физика и профили нагрузки
"""

from core.physics_engine import GPUPhysicsEngine, RoomPhysicsEngine
from core.workload_profiles import (
    WorkloadType,
    MLWorkloadProfile,
    TrainingWorkloadProfile,
    InferenceWorkloadProfile,
    IdleWorkloadProfile,
    WorkloadOrchestrator
)

__all__ = [
    'GPUPhysicsEngine',
    'RoomPhysicsEngine',
    'WorkloadType',
    'MLWorkloadProfile',
    'TrainingWorkloadProfile',
    'InferenceWorkloadProfile',
    'IdleWorkloadProfile',
    'WorkloadOrchestrator'
]

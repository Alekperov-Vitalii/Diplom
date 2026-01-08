"""
Новая версия симулятора GPU с модульной архитектурой
Использует отдельные компоненты: Physics Engine, Sensors, Workload Profiles
"""

from typing import Dict, Any
from core.physics_engine import GPUPhysicsEngine
from sensors.temperature_sensor import TemperatureSensor


class GPUSimulator:
    """
    Симулятор GPU с разделением на физику и датчики
    
    Архитектура:
    - Physics Engine: моделирует истинную температуру
    - Temperature Sensor: добавляет шум при измерении
    - Workload: управляется извне через WorkloadOrchestrator
    """
    
    def __init__(self, gpu_id: int, config: dict):
        self.gpu_id = gpu_id
        self.config = config
        
        # Физический движок (истинное состояние)
        self.physics = GPUPhysicsEngine(gpu_id, config)
        
        # Датчик температуры (измерение с шумом)
        self.temp_sensor = TemperatureSensor(gpu_id, config)
    
    def set_workload(self, workload: float):
        """
        Устанавливает нагрузку на GPU
        Вызывается из WorkloadOrchestrator
        
        Args:
            workload: Нагрузка от 0.0 до 1.0
        """
        self.physics.set_workload(workload)
    
    def update_temperature(self, dt: float, fan_cooling_effect: float, room_temp: float):
        """
        Обновляет физическое состояние GPU
        
        Args:
            dt: Временной интервал (секунды)
            fan_cooling_effect: Эффект охлаждения от вентилятора (0.0-1.0)
            room_temp: Температура помещения
        """
        self.physics.update(dt, fan_cooling_effect, room_temp)
    
    def get_temperature_with_noise(self) -> float:
        """
        Возвращает измеренную температуру (с шумом датчика)
        Это то, что "видит" ESP32
        
        Returns:
            Температура с шумом датчика
        """
        true_temp = self.physics.get_temperature()
        measured_temp = self.temp_sensor.read(true_temp)
        return measured_temp
    
    def get_true_temperature(self) -> float:
        """
        Возвращает истинную физическую температуру (без шума)
        Используется для отладки
        """
        return self.physics.get_temperature()
    
    @property
    def temperature(self) -> float:
        """Совместимость со старым кодом"""
        return self.physics.get_temperature()
    
    @property
    def workload(self) -> float:
        """Совместимость со старым кодом"""
        return self.physics.get_workload()


class RoomSimulator:
    """
    Симулятор помещения (без изменений, использует новый Physics Engine)
    """
    
    def __init__(self, config: dict):
        from core.physics_engine import RoomPhysicsEngine
        self.physics = RoomPhysicsEngine(config)
        self.config = config
    
    def update(self, gpu_heat_contribution: float):
        """Обновляет температуру помещения"""
        self.physics.update(gpu_heat_contribution)
    
    def get_temperature_with_noise(self) -> float:
        """Температура комнаты с небольшим шумом"""
        import numpy as np
        true_temp = self.physics.get_temperature()
        noise = np.random.normal(0, 0.2)
        return round(true_temp + noise, 1)
    
    @property
    def temperature(self) -> float:
        """Совместимость со старым кодом"""
        return self.physics.get_temperature()
"""
Реестр датчиков для управления коллекцией датчиков
"""

from typing import Dict, List, Type
from sensors.base_sensor import BaseSensor
from sensors.temperature_sensor import TemperatureSensor


class SensorRegistry:
    """
    Управляет коллекцией датчиков
    Позволяет легко добавлять новые типы датчиков
    """
    
    # Маппинг типов датчиков
    SENSOR_TYPES: Dict[str, Type[BaseSensor]] = {
        'temperature': TemperatureSensor,
        # Будущие датчики:
        # 'humidity': HumiditySensor,
        # 'power': PowerSensor,
    }
    
    def __init__(self, config: dict):
        self.config = config
        self.sensors: Dict[str, List[BaseSensor]] = {}
    
    def register_sensor(self, sensor_type: str, sensor_id: int) -> BaseSensor:
        """
        Регистрирует новый датчик
        
        Args:
            sensor_type: Тип датчика ('temperature', 'humidity', etc.)
            sensor_id: Уникальный ID датчика
        
        Returns:
            Созданный экземпляр датчика
        """
        if sensor_type not in self.SENSOR_TYPES:
            raise ValueError(f"Неизвестный тип датчика: {sensor_type}")
        
        sensor_class = self.SENSOR_TYPES[sensor_type]
        sensor = sensor_class(sensor_id, self.config)
        
        if sensor_type not in self.sensors:
            self.sensors[sensor_type] = []
        
        self.sensors[sensor_type].append(sensor)
        return sensor
    
    def get_sensors(self, sensor_type: str) -> List[BaseSensor]:
        """Возвращает все датчики указанного типа"""
        return self.sensors.get(sensor_type, [])
    
    def get_sensor(self, sensor_type: str, sensor_id: int) -> BaseSensor:
        """Возвращает конкретный датчик по типу и ID"""
        sensors = self.get_sensors(sensor_type)
        for sensor in sensors:
            if sensor.sensor_id == sensor_id:
                return sensor
        raise ValueError(f"Датчик {sensor_type}#{sensor_id} не найден")

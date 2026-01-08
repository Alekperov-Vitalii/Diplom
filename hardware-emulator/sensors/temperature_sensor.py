"""
Эмуляция датчика температуры DS18B20
"""

from typing import Dict, Any
from sensors.base_sensor import BaseSensor


class TemperatureSensor(BaseSensor):
    """
    Эмулятор датчика температуры DS18B20
    
    Характеристики DS18B20:
    - Точность: ±0.5°C в диапазоне -10°C до +85°C
    - Разрешение: 0.0625°C (12-bit)
    - Время отклика: ~750ms
    """
    
    def __init__(self, sensor_id: int, config: Dict[str, Any]):
        super().__init__(sensor_id, config)
        
        # Параметры датчика из конфига
        self.noise_std = config.get('simulation', {}).get('sensor_noise', 0.3)
        self.resolution = 0.1  # Округление до 0.1°C для реализма
    
    def read(self, true_value: float) -> float:
        """
        Читает температуру с учетом шума датчика
        
        Args:
            true_value: Истинная температура (из physics engine)
        
        Returns:
            Измеренная температура с шумом и округлением
        """
        # Добавляем шум
        noisy_value = self._add_noise(true_value, self.noise_std)
        
        # Округляем до разрешения датчика
        measured_value = round(noisy_value / self.resolution) * self.resolution
        
        # Сохраняем последнее значение
        self._last_reading = measured_value
        
        return measured_value

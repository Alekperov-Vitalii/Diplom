"""
Базовый абстрактный класс для всех датчиков
Определяет интерфейс для эмуляции датчиков
"""

from abc import ABC, abstractmethod
from typing import Any, Dict
import numpy as np


class BaseSensor(ABC):
    """
    Абстрактный базовый класс для датчиков
    
    Все датчики должны наследоваться от этого класса и реализовывать
    метод read() для получения измеренного значения
    """
    
    def __init__(self, sensor_id: int, config: Dict[str, Any]):
        """
        Args:
            sensor_id: Уникальный идентификатор датчика
            config: Конфигурация датчика из config.yaml
        """
        self.sensor_id = sensor_id
        self.config = config
        self._last_reading = None
    
    @abstractmethod
    def read(self, true_value: float) -> float:
        """
        Читает значение датчика
        
        Args:
            true_value: Истинное физическое значение (из physics engine)
        
        Returns:
            Измеренное значение с учетом шума и погрешности датчика
        """
        pass
    
    def get_last_reading(self) -> float:
        """Возвращает последнее считанное значение"""
        return self._last_reading
    
    def _add_noise(self, value: float, noise_std: float) -> float:
        """
        Добавляет гауссовский шум к значению
        
        Args:
            value: Исходное значение
            noise_std: Стандартное отклонение шума
        
        Returns:
            Значение с добавленным шумом
        """
        noise = np.random.normal(0, noise_std)
        return value + noise

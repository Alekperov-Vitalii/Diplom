"""
Модуль датчиков для эмуляции аппаратных сенсоров
"""

from sensors.base_sensor import BaseSensor
from sensors.temperature_sensor import TemperatureSensor
from sensors.sensor_registry import SensorRegistry

__all__ = ['BaseSensor', 'TemperatureSensor', 'SensorRegistry']

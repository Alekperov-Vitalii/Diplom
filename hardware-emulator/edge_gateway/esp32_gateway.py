"""
Эмулятор ESP32 Edge Gateway
Отвечает за сбор данных с датчиков и отправку на Fog-сервер
"""

from typing import List, Optional
from datetime import datetime, timezone
import logging

from models import TelemetryPayload, SensorData, FanData, GPUTemperature, FanState, FanControlBatch, EnvironmentalPayload, EnvironmentalSensorData, EnvironmentalActuatorData
from api_client import FogServerClient


class ESP32Gateway:
    """
    Эмулятор ESP32 Edge Gateway
    
    Функции:
    - Сбор данных со всех датчиков
    - Агрегация телеметрии
    - Отправка на Fog-сервер
    - Получение команд управления
    """
    
    def __init__(self, device_id: str, fog_server_url: str, logger: logging.Logger):
        """
        Args:
            device_id: Уникальный ID устройства
            fog_server_url: URL fog-сервера
            logger: Логгер для вывода
        """
        self.device_id = device_id
        self.logger = logger
        
        # HTTP клиент для связи с fog-сервером
        self.api_client = FogServerClient(fog_server_url)
        
        # Статистика
        self.total_sends = 0
        self.failed_sends = 0
    
    def collect_telemetry(
        self,
        gpu_temperatures: List[GPUTemperature],
        room_temperature: float,
        fan_states: List[FanState]
    ) -> TelemetryPayload:
        """
        Собирает телеметрию в единый пакет
        
        Args:
            gpu_temperatures: Список температур GPU
            room_temperature: Температура помещения
            fan_states: Состояния вентиляторов
        
        Returns:
            TelemetryPayload готовый к отправке
        """
        payload = TelemetryPayload(
            device_id=self.device_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            sensors=SensorData(
                gpu_temps=gpu_temperatures,
                room_temp=room_temperature
            ),
            fans=FanData(fan_states=fan_states)
        )
        
        return payload
    
    def send_telemetry(self, payload: TelemetryPayload) -> bool:
        """
        Отправляет телеметрию на fog-сервер
        
        Args:
            payload: Пакет телеметрии
        
        Returns:
            True если успешно, False если ошибка
        """
        self.logger.info(f"📤 ESP32 Gateway: Отправка телеметрии #{self.total_sends + 1}...")
        
        success = self.api_client.send_telemetry(payload)
        
        if success:
            self.total_sends += 1
        else:
            self.failed_sends += 1
            self.logger.warning(f"⚠ ESP32 Gateway: Ошибка отправки (всего неудач: {self.failed_sends})")
        
        return success
    
    def receive_commands(self) -> Optional[FanControlBatch]:
        """
        Получает команды управления от fog-сервера
        
        Returns:
            FanControlBatch если есть команды, None если нет
        """
        commands = self.api_client.fetch_fan_commands(self.device_id)
        
        if commands:
            self.logger.info(f"📥 ESP32 Gateway: Получены команды ({len(commands.commands)} вентиляторов)")
        
        return commands
    
    def health_check(self) -> bool:
        """
        Проверяет доступность fog-сервера
        
        Returns:
            True если сервер доступен
        """
        return self.api_client.health_check()
    
    def get_statistics(self) -> dict:
        """Возвращает статистику работы Gateway"""
        return {
            'total_sends': self.total_sends,
            'failed_sends': self.failed_sends,
            'success_rate': (self.total_sends / (self.total_sends + self.failed_sends) * 100) 
                           if (self.total_sends + self.failed_sends) > 0 else 0
        }
    
    def collect_environmental_telemetry(
        self,
        humidity: float,
        dust: float,
        dehumidifier_active: bool,
        dehumidifier_power: int,
        humidifier_active: bool,
        humidifier_power: int
    ) -> EnvironmentalPayload:
        """
        Собирает environmental telemetry в единый пакет
        
        Args:
            humidity: Текущая влажность (%)
            dust: Текущая концентрация пыли (μg/m³)
            dehumidifier_active: Состояние осушителя
            dehumidifier_power: Мощность осушителя (%)
            humidifier_active: Состояние увлажнителя
            humidifier_power: Мощность увлажнителя (%)
        
        Returns:
            EnvironmentalPayload готовый к отправке
        """
        payload = EnvironmentalPayload(
            device_id=self.device_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            sensors=EnvironmentalSensorData(
                humidity=humidity,
                dust=dust
            ),
            actuators=EnvironmentalActuatorData(
                dehumidifier_active=dehumidifier_active,
                dehumidifier_power=dehumidifier_power,
                humidifier_active=humidifier_active,
                humidifier_power=humidifier_power
            )
        )
        
        return payload
    
    def send_environmental_telemetry(self, payload: EnvironmentalPayload) -> bool:
        """
        Отправляет environmental telemetry на fog-сервер
        
        Args:
            payload: Пакет environmental data
        
        Returns:
            True если успешно, False если ошибка
        """
        self.logger.info(f"🌡️ ESP32 Gateway: Отправка environmental telemetry...")
        
        success = self.api_client.send_environmental_telemetry(payload)
        
        if success:
            self.total_sends += 1
        else:
            self.failed_sends += 1
            self.logger.warning(f"⚠ ESP32 Gateway: Ошибка отправки environmental data")
        
        return success
    
    def receive_environmental_commands(self) -> dict:
        """
        Получает команды управления environmental actuators от fog-сервера
        
        Returns:
            Dict с командами или None если нет
        """
        commands = self.api_client.fetch_environmental_commands(self.device_id)
        
        if commands:
            self.logger.info(f"📥 ESP32 Gateway: Получены environmental commands")
        
        return commands

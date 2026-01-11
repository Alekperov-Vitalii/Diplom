"""
HTTP-клиент для отправки данных на fog-сервер
Эмулирует REST API взаимодействие ESP32 с сервером
"""

import requests
import logging
from typing import Optional, Dict, Any
from models import TelemetryPayload, FanControlBatch, EnvironmentalPayload, EnvironmentalControlCommand

logger = logging.getLogger(__name__)


class FogServerClient:
    """Клиент для взаимодействия с fog-сервером"""
    
    def __init__(self, base_url: str, timeout: int = 10):
        """
        Args:
            base_url: URL fog-сервера (например: http://localhost:8000)
            timeout: Таймаут запросов в секундах
        """
        self.base_url = base_url.rstrip('/')  # Убираем trailing slash
        self.timeout = timeout
        self.session = requests.Session()  # Переиспользуем TCP-соединение
        
        # Headers как у настоящего ESP32
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'ESP32-HTTPClient/1.0'
        })
    
    def send_telemetry(self, payload: TelemetryPayload) -> bool:
        """
        Отправляет телеметрию на fog-сервер
        
        Args:
            payload: Данные температуры и вентиляторов
        
        Returns:
            True если успешно, False если ошибка
        """
        endpoint = f"{self.base_url}/api/v1/telemetry"
        
        try:
            # Конвертируем Pydantic модель в JSON
            json_data = payload.model_dump()
            
            logger.debug(f"Отправка телеметрии на {endpoint}")
            
            response = self.session.post(
                endpoint,
                json=json_data,
                timeout=self.timeout
            )
            
            # Проверяем статус ответа
            response.raise_for_status()  # Выбросит ошибку если статус 4xx или 5xx
            
            logger.info(f"✓ Телеметрия отправлена успешно (статус {response.status_code})")
            return True
            
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ Не удалось подключиться к fog-серверу {endpoint}")
            return False
            
        except requests.exceptions.Timeout:
            logger.error(f"✗ Таймаут при отправке на {endpoint}")
            return False
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"✗ HTTP ошибка: {e.response.status_code} - {e.response.text}")
            return False
            
        except Exception as e:
            logger.error(f"✗ Неожиданная ошибка при отправке: {e}")
            return False
    
    def fetch_fan_commands(self, device_id: str) -> Optional[FanControlBatch]:
        """
        Получает команды управления вентиляторами от fog-сервера
        
        Args:
            device_id: ID устройства
        
        Returns:
            FanControlBatch или None если команд нет или ошибка
        
        Логика:
        Fog-сервер может хранить очередь команд для каждого ESP32.
        ESP32 периодически опрашивает сервер: "Есть ли команды для меня?"
        """
        endpoint = f"{self.base_url}/api/v1/fan-control/{device_id}"
        
        try:
            response = self.session.get(endpoint, timeout=self.timeout)
            
            if response.status_code == 204:
                # 204 No Content = команд нет
                return None
            
            response.raise_for_status()
            
            # Парсим JSON в Pydantic модель
            commands = FanControlBatch(**response.json())
            logger.info(f"✓ Получены команды для {len(commands.commands)} вентиляторов")
            return commands
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Не удалось получить команды (сервер недоступен)")
            return None
            
        except Exception as e:
            logger.warning(f"Ошибка получения команд: {e}")
            return None
    
    def health_check(self) -> bool:
        """
        Проверяет доступность fog-сервера
        
        Returns:
            True если сервер отвечает
        """
        endpoint = f"{self.base_url}/health"
        
        try:
            response = self.session.get(endpoint, timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def send_environmental_telemetry(self, payload: EnvironmentalPayload) -> bool:
        """
        Отправляет телеметрию environmental sensors на fog-сервер
        
        Args:
            payload: Данные humidity and dust sensors
        
        Returns:
            True если успешно, False если ошибка
        """
        endpoint = f"{self.base_url}/api/v1/environmental/telemetry"
        
        try:
            json_data = payload.model_dump()
            
            logger.debug(f"Отправка environmental telemetry на {endpoint}")
            
            response = self.session.post(
                endpoint,
                json=json_data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            
            logger.info(f"✓ Environmental telemetry отправлена (статус {response.status_code})")
            return True
            
        except requests.exceptions.ConnectionError:
            logger.error(f"✗ Не удалось подключиться к fog-серверу {endpoint}")
            return False
            
        except requests.exceptions.Timeout:
            logger.error(f"✗ Таймаут при отправке на {endpoint}")
            return False
            
        except requests.exceptions.HTTPError as e:
            logger.error(f"✗ HTTP ошибка: {e.response.status_code} - {e.response.text}")
            return False
            
        except Exception as e:
            logger.error(f"✗ Неожиданная ошибка при отправке: {e}")
            return False
    
    def fetch_environmental_commands(self, device_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает команды управления environmental actuators от fog-сервера
        
        Args:
            device_id: ID устройства
        
        Returns:
            Dict с командами или None если команд нет или ошибка
        """
        endpoint = f"{self.base_url}/api/v1/environmental/control/{device_id}"
        
        try:
            response = self.session.get(endpoint, timeout=self.timeout)
            
            if response.status_code == 204:
                # 204 No Content = команд нет
                return None
            
            response.raise_for_status()
            
            # Парсим JSON в dict
            commands = response.json()
            logger.info(f"✓ Получены environmental control commands")
            return commands
            
        except requests.exceptions.ConnectionError:
            logger.warning(f"Не удалось получить environmental commands (сервер недоступен)")
            return None
            
        except Exception as e:
            logger.warning(f"Ошибка получения environmental commands: {e}")
            return None
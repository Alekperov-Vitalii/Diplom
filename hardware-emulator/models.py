"""
Модели данных для эмуляции ESP32
Pydantic модели для валидации и сериализации JSON
"""

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class GPUTemperature(BaseModel):
    """Температура одной видеокарты"""
    gpu_id: int = Field(..., ge=1, le=16, description="ID видеокарты (1-16)")
    temperature: float = Field(..., ge=-10, le=150, description="Температура в °C")
    load: float = Field(0.0, ge=0.0, le=100.0, description="Загрузка GPU (%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "gpu_id": 1,
                "temperature": 68.5,
                "load": 95.0
            }
        }


class FanState(BaseModel):
    """Состояние вентилятора"""
    fan_id: int = Field(..., ge=1, le=16, description="ID вентилятора (1-16)")
    rpm: int = Field(..., ge=0, le=6000, description="Обороты в минуту")
    pwm_duty: int = Field(..., ge=0, le=100, description="PWM duty cycle (%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fan_id": 1,
                "rpm": 3200,
                "pwm_duty": 75
            }
        }


class SensorData(BaseModel):
    """Данные со всех датчиков"""
    gpu_temps: List[GPUTemperature] = Field(..., description="Температуры всех GPU")
    room_temp: float = Field(..., ge=-10, le=60, description="Температура помещения")


class FanData(BaseModel):
    """Данные всех вентиляторов"""
    fan_states: List[FanState] = Field(..., description="Состояния всех вентиляторов")


class TelemetryPayload(BaseModel):
    """
    Полный пакет телеметрии, отправляемый на fog-сервер
    Именно в таком формате ESP32 отправляет данные
    """
    device_id: str = Field(..., description="Уникальный ID устройства")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    sensors: SensorData = Field(..., description="Данные датчиков температуры")
    fans: FanData = Field(..., description="Данные вентиляторов")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "esp32_master_001",
                "timestamp": "2024-12-01T10:30:45.123Z",
                "sensors": {
                    "gpu_temps": [
                        {"gpu_id": 1, "temperature": 65.5},
                        {"gpu_id": 2, "temperature": 72.3}
                    ],
                    "room_temp": 26.5
                },
                "fans": {
                    "fan_states": [
                        {"fan_id": 1, "rpm": 3200, "pwm_duty": 75},
                        {"fan_id": 2, "rpm": 4100, "pwm_duty": 85}
                    ]
                }
            }
        }


class FanControlCommand(BaseModel):
    """
    Команда управления вентиляторами от fog-сервера
    Fog-сервер отправляет эту команду эмулятору
    """
    fan_id: int = Field(..., ge=1, le=16, description="ID вентилятора")
    pwm_duty: int = Field(..., ge=0, le=100, description="Новое значение PWM (0-100%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "fan_id": 1,
                "pwm_duty": 80
            }
        }


class FanControlBatch(BaseModel):
    """Пакет команд для нескольких вентиляторов"""
    device_id: str = Field(..., description="ID устройства")
    commands: List[FanControlCommand] = Field(..., description="Список команд")


# ============================================================================
# ENVIRONMENTAL MONITORING MODELS
# ============================================================================

class EnvironmentalSensorData(BaseModel):
    """
    Environmental sensor readings (humidity and dust)
    """
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity (%)")
    dust: float = Field(..., ge=0.0, le=500.0, description="Dust concentration PM (μg/m³)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "humidity": 45.5,
                "dust": 28.3
            }
        }


class EnvironmentalActuatorData(BaseModel):
    """
    Environmental actuator states (dehumidifier, humidifier)
    """
    dehumidifier_active: bool = Field(default=False, description="Dehumidifier relay state")
    dehumidifier_power: int = Field(default=0, ge=0, le=100, description="Dehumidifier power level (%)")
    humidifier_active: bool = Field(default=False, description="Humidifier relay state")
    humidifier_power: int = Field(default=0, ge=0, le=100, description="Humidifier power level (%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dehumidifier_active": True,
                "dehumidifier_power": 60,
                "humidifier_active": False,
                "humidifier_power": 0
            }
        }


class EnvironmentalPayload(BaseModel):
    """
    Complete environmental telemetry payload
    Sent alongside standard telemetry or separately
    """
    device_id: str = Field(..., description="Device ID")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    sensors: EnvironmentalSensorData = Field(..., description="Environmental sensor data")
    actuators: EnvironmentalActuatorData = Field(..., description="Environmental actuator states")
    
    class Config:
        json_schema_extra = {
            "example": {
                "device_id": "esp32_master_001",
                "timestamp": "2024-12-01T10:30:45.123Z",
                "sensors": {
                    "humidity": 52.0,
                    "dust": 35.5
                },
                "actuators": {
                    "dehumidifier_active": False,
                    "dehumidifier_power": 0,
                    "humidifier_active": True,
                    "humidifier_power": 50
                }
            }
        }


class EnvironmentalControlCommand(BaseModel):
    """
    Environmental control command from fog server
    Controls dehumidifier and humidifier relays
    """
    dehumidifier_active: bool = Field(default=False, description="Activate dehumidifier")
    dehumidifier_power: int = Field(default=0, ge=0, le=100, description="Dehumidifier power (%)")
    humidifier_active: bool = Field(default=False, description="Activate humidifier")
    humidifier_power: int = Field(default=0, ge=0, le=100, description="Humidifier power (%)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "dehumidifier_active": True,
                "dehumidifier_power": 75,
                "humidifier_active": False,
                "humidifier_power": 0
            }
        }
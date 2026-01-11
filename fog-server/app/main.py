"""
Fog-сервер для IoT-системы мониторинга GPU-кластера
Компактная версия для дипломной работы

Функции:
- Приём телеметрии от ESP32
- Сохранение в InfluxDB
- Каскадный алгоритм управления охлаждением
- API для веб-интерфейса
- Алерты при критичных температурах
"""

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta
from contextlib import asynccontextmanager
import asyncio
import os
import time
from enum import Enum
from dotenv import load_dotenv

# InfluxDB
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

# Загружаем переменные окружения
load_dotenv()

# ============================================================================
# КОНФИГУРАЦИЯ
# ============================================================================

class Config:
    """Конфигурация из .env файла"""
    INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
    INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "gpu-monitoring")
    INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "gpu-metrics")
    
    GPU_COUNT = int(os.getenv("GPU_COUNT", 8))
    CRITICAL_TEMP_THRESHOLD = float(os.getenv("CRITICAL_TEMP_THRESHOLD", 120))
    WARNING_TEMP_THRESHOLD = float(os.getenv("WARNING_TEMP_THRESHOLD", 90))
    
    ROOM_TEMP_INFLUENCE = float(os.getenv("ROOM_TEMP_INFLUENCE", 0.3))
    MIN_FAN_PWM = int(os.getenv("MIN_FAN_PWM", 20))
    MAX_FAN_PWM = int(os.getenv("MAX_FAN_PWM", 100))

config = Config()

# ============================================================================
# МОДЕЛИ ДАННЫХ
# ============================================================================

class GPUTemperature(BaseModel):
    gpu_id: int = Field(..., ge=1, le=16)
    temperature: float
    load: float = Field(0.0, ge=0.0, le=100.0)

class FanState(BaseModel):
    fan_id: int = Field(..., ge=1, le=16)
    rpm: int
    pwm_duty: int

class SensorData(BaseModel):
    gpu_temps: List[GPUTemperature]
    room_temp: float

class FanData(BaseModel):
    fan_states: List[FanState]

class TelemetryPayload(BaseModel):
    device_id: str
    timestamp: str
    sensors: SensorData
    fans: FanData

class FanControlCommand(BaseModel):
    fan_id: int
    pwm_duty: int

class FanControlBatch(BaseModel):
    device_id: str
    commands: List[FanControlCommand]

class AlertEvent(BaseModel):
    gpu_id: int
    temperature: float
    threshold: float
    severity: str  # "warning" или "critical"
    timestamp: str

# ============================================================================
# ДОПОЛНИТЕЛЬНЫЕ МОДЕЛИ ДЛЯ УПРАВЛЕНИЯ
# ============================================================================

class ManualControlMode(BaseModel):
    """Режим работы системы"""
    mode: str = Field(..., pattern="^(auto|manual)$")  # "auto" или "manual"
    device_id: str

class FanManualControl(BaseModel):
    """Ручная установка PWM для вентилятора"""
    fan_id: int = Field(..., ge=1, le=16)
    pwm_duty: int = Field(..., ge=0, le=100)

class FanManualControlBatch(BaseModel):
    """Пакет команд для ручного управления"""
    device_id: str
    mode: str = "manual"
    commands: List[FanManualControl]

class FanStatistics(BaseModel):
    """Статистика работы вентилятора"""
    fan_id: int
    avg_pwm_last_hour: float
    max_pwm_last_hour: int
    min_pwm_last_hour: int
    time_on_high: int  # секунд на >80% PWM
    current_rpm: int
    current_pwm: int

class SystemMode(BaseModel):
    """Текущий режим системы"""
    mode: str  # "auto" или "manual"
    last_changed: str
    changed_by: str  # "user" или "system"

# ============================================================================
# ENVIRONMENTAL MONITORING MODELS
# ============================================================================

class EnvironmentalSensorData(BaseModel):
    """
    Environmental sensor readings (humidity and dust)
    """
    humidity: float = Field(..., ge=0.0, le=100.0, description="Relative humidity (%)")
    dust: float = Field(..., ge=0.0, le=500.0, description="Dust concentration PM (μg/m³)")


class EnvironmentalActuatorData(BaseModel):
    """
    Environmental actuator states (dehumidifier, humidifier)
    """
    dehumidifier_active: bool = Field(default=False, description="Dehumidifier relay state")
    dehumidifier_power: int = Field(default=0, ge=0, le=100, description="Dehumidifier power level (%)")
    humidifier_active: bool = Field(default=False, description="Humidifier relay state")
    humidifier_power: int = Field(default=0, ge=0, le=100, description="Humidifier power level (%)")


class EnvironmentalPayload(BaseModel):
    """
    Complete environmental telemetry payload
    Sent alongside standard telemetry or separately
    """
    device_id: str = Field(..., description="Device ID")
    timestamp: str = Field(..., description="ISO 8601 timestamp")
    sensors: EnvironmentalSensorData = Field(..., description="Environmental sensor data")
    actuators: EnvironmentalActuatorData = Field(..., description="Environmental actuator states")


class EnvironmentalControlCommand(BaseModel):
    """
    Environmental control command from fog server
    Controls dehumidifier and humidifier relays
    """
    dehumidifier_active: bool = Field(default=False, description="Activate dehumidifier")
    dehumidifier_power: int = Field(default=0, ge=0, le=100, description="Dehumidifier power (%)")
    humidifier_active: bool = Field(default=False, description="Activatehumidifier")
    humidifier_power: int = Field(default=0, ge=0, le=100, description="Humidifier power (%)")


class EnvironmentalAlertEvent(BaseModel):
    """
    Environmental alert event
    """
    alert_type: str  # "dust_high", "humidity_low", "humidity_high"
    current_value: float
    threshold: float
    severity: str  # "warning" или "critical"
    timestamp: str
    message: str

# ============================================================================
# INFLUXDB КЛИЕНТ
# ============================================================================

class InfluxDBManager:
    """Управление подключением к InfluxDB"""
    
    def __init__(self):
        self.client: Optional[InfluxDBClient] = None
        self.write_api = None
        self.query_api = None
    
    def connect(self):
        """Подключение к InfluxDB"""
        try:
            self.client = InfluxDBClient(
                url=config.INFLUXDB_URL,
                token=config.INFLUXDB_TOKEN,
                org=config.INFLUXDB_ORG
            )
            self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
            self.query_api = self.client.query_api()
            print(f"✓ Подключено к InfluxDB: {config.INFLUXDB_URL}")
        except Exception as e:
            print(f"✗ Ошибка подключения к InfluxDB: {e}")
            raise
    
    def disconnect(self):
        """Закрытие подключения"""
        if self.client:
            self.client.close()
            print("✓ InfluxDB отключён")
    
    def write_telemetry(self, payload: TelemetryPayload):
        """
        Сохранение телеметрии в InfluxDB
        
        Структура:
        - measurement: gpu_temps (температуры и нагрузка GPU)
        - measurement: room_temp (температура помещения)
        - measurement: fan_states (состояния вентиляторов)
        """
        points = []
        
        # Температуры GPU
        for gpu_temp in payload.sensors.gpu_temps:
            point = Point("gpu_temps") \
                .tag("device_id", payload.device_id) \
                .tag("gpu_id", str(gpu_temp.gpu_id)) \
                .field("temperature", gpu_temp.temperature) \
                .field("load", gpu_temp.load) \
                .time(payload.timestamp)
            points.append(point)
        
        # Температура помещения
        point = Point("room_temp") \
            .tag("device_id", payload.device_id) \
            .field("temperature", payload.sensors.room_temp) \
            .time(payload.timestamp)
        points.append(point)
        
        # Состояния вентиляторов
        for fan in payload.fans.fan_states:
            point = Point("fan_states") \
                .tag("device_id", payload.device_id) \
                .tag("fan_id", str(fan.fan_id)) \
                .field("rpm", fan.rpm) \
                .field("pwm_duty", fan.pwm_duty) \
                .time(payload.timestamp)
            points.append(point)
        
        # Записываем все точки одним батчем
        self.write_api.write(bucket=config.INFLUXDB_BUCKET, record=points)
    
    def write_alert(self, alert: AlertEvent):
        """Сохранение алерта"""
        point = Point("alerts") \
            .tag("gpu_id", str(alert.gpu_id)) \
            .tag("severity", alert.severity) \
            .field("temperature", alert.temperature) \
            .field("threshold", alert.threshold) \
            .time(alert.timestamp)
        
        self.write_api.write(bucket=config.INFLUXDB_BUCKET, record=point)
    
    def query_latest_state(self) -> Dict[int, Dict[str, float]]:
        """
        Получает последние метрики всех GPU (temp, load)
        
        Returns:
            {gpu_id: {"temperature": 65.0, "load": 95.0}}
        """
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: -1m)
          |> filter(fn: (r) => r["_measurement"] == "gpu_temps")
          |> filter(fn: (r) => r["_field"] == "temperature" or r["_field"] == "load")
          |> last()
        '''
        
        result = self.query_api.query(query=query)
        
        gpu_stats = {}
        for table in result:
            for record in table.records:
                gpu_id = int(record.values.get("gpu_id"))
                field = record.values.get("_field")
                value = record.values.get("_value")
                
                if gpu_id not in gpu_stats:
                    gpu_stats[gpu_id] = {"temperature": 0.0, "load": 0.0}
                
                gpu_stats[gpu_id][field] = value
        
        return gpu_stats
    
    def query_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Получает историю за последние N часов
        
        Returns:
            Список точек данных для графиков
        """
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r["_measurement"] == "gpu_temps" or r["_measurement"] == "room_temp")
          |> filter(fn: (r) => r["_field"] == "temperature")
        '''
        
        result = self.query_api.query(query=query)
        
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "time": record.values.get("_time").isoformat(),
                    "measurement": record.values.get("_measurement"),
                    "gpu_id": record.values.get("gpu_id"),
                    "value": record.values.get("_value")
                })
        
        return data
    
    def write_environmental_telemetry(self, payload: EnvironmentalPayload):
        """
        Сохранение environmental telemetry в InfluxDB
        
        Structure:
        - measurement: environmental_sensors (humidity, dust)
        - measurement: environmental_actuators (dehumidifier, humidifier states)
        """
        points = []
        
        # Environmental sensors
        point = Point("environmental_sensors") \
            .tag("device_id", payload.device_id) \
            .field("humidity", payload.sensors.humidity) \
            .field("dust", payload.sensors.dust) \
            .time(payload.timestamp)
        points.append(point)
        
        # Environmental actuators
        point = Point("environmental_actuators") \
            .tag("device_id", payload.device_id) \
            .field("dehumidifier_active", int(payload.actuators.dehumidifier_active)) \
            .field("dehumidifier_power", payload.actuators.dehumidifier_power) \
            .field("humidifier_active", int(payload.actuators.humidifier_active)) \
            .field("humidifier_power", payload.actuators.humidifier_power) \
            .time(payload.timestamp)
        points.append(point)
        
        # Записываем все точки одним батчем
        self.write_api.write(bucket=config.INFLUXDB_BUCKET, record=points)
    
    def write_environmental_alert(self, alert: Dict):
        """Сохранение environmental alert"""
        point = Point("environmental_alerts") \
            .tag("alert_type", alert['alert_type']) \
            .tag("severity", alert['severity']) \
            .field("current_value", alert['current_value']) \
            .field("threshold", alert['threshold']) \
            .field("message", alert['message']) \
            .time(alert['timestamp'])
        
        self.write_api.write(bucket=config.INFLUXDB_BUCKET, record=point)
    
    def query_environmental_history(self, hours: int = 1) -> List[Dict[str, Any]]:
        """
        Получает environmental history за последние N часов
        
        Returns:
            Список точек данных для графиков
        """
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r["_measurement"] == "environmental_sensors")
          |> filter(fn: (r) => r["_field"] == "humidity" or r["_field"] == "dust")
        '''
        
        result = self.query_api.query(query=query)
        
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "time": record.values.get("_time").isoformat(),
                    "field": record.values.get("_field"),
                    "value": record.values.get("_value")
                })
        
        return data

influx_manager = InfluxDBManager()

# ============================================================================
# АЛГОРИТМ УПРАВЛЕНИЯ ОХЛАЖДЕНИЕМ
# ============================================================================

class ThermalState(Enum):
    STEADY = "steady"
    HEATING = "heating"
    COOLING = "cooling"


class SmartCoolingAlgorithm:
    """
    Умный алгоритм охлаждения с учетом инерции и трендов
    
    Философия:
    1. Быстрая реакция на нагрев (безопасность)
    2. Медленная реакция на охлаждение (гистерезис)
    3. Учет состояния (heating/cooling/steady)
    4. Защита от частых переключений (switch debounce)
    """
    
    def __init__(self):
        # История температур для расчета тренда: {gpu_id: [t1, t2, t3]}
        self.temp_history: Dict[int, List[float]] = {}
        
        # Последнее изменение PWM: {gpu_id: timestamp}
        self.last_pwm_change: Dict[int, float] = {}
        
        # Текущий PWM: {gpu_id: pwm}
        self.current_pwm: Dict[int, int] = {}
        
        # Константы
        self.HISTORY_SIZE = 3
        self.TREND_THRESHOLD = 0.5  # °C за цикл (5 сек)
        self.MIN_PWM_HOLD_TIME = 60.0  # сек (защита от частого снижения)
        
    def _update_history(self, gpu_id: int, temp: float):
        """Обновляет историю температур"""
        if gpu_id not in self.temp_history:
            self.temp_history[gpu_id] = []
        
        self.temp_history[gpu_id].append(temp)
        if len(self.temp_history[gpu_id]) > self.HISTORY_SIZE:
            self.temp_history[gpu_id].pop(0)

    def _determine_state(self, gpu_id: int) -> ThermalState:
        """Определяет тепловое состояние (нагрев/охлаждение/стабильность)"""
        history = self.temp_history.get(gpu_id, [])
        if len(history) < 2:
            return ThermalState.STEADY
            
        # Считаем тренд: разница между последним и пред-последним
        trend = history[-1] - history[-2]
        
        if trend > self.TREND_THRESHOLD:
            return ThermalState.HEATING
        elif trend < -self.TREND_THRESHOLD:
            return ThermalState.COOLING
        else:
            return ThermalState.STEADY

    def calculate_target_pwm(self, temp: float, load: float) -> int:
        """
        Вычисляет целевой PWM на основе температуры и нагрузки
        Базовая кривая охлаждения
        """
        # Базовая кривая:
        # < 30°C: 20%
        # 30-50°C: 20-40%
        # 50-70°C: 40-70%
        # 70-85°C: 70-100%
        # > 85°C: 100%
        
        if temp < 30:
            target = config.MIN_FAN_PWM
        elif temp < 50:
            # Линейный рост 20 -> 40
            target = 20 + (temp - 30) * 1.0 
        elif temp < 70:
            # Линейный рост 40 -> 70
            target = 40 + (temp - 50) * 1.5
        elif temp < 85:
            # Агрессивный рост 70 -> 100
            target = 70 + (temp - 70) * 2.0
        else:
            target = 100
            
        # Коррекция по нагрузке (feed-forward)
        # Если нагрузка > 80%, минимальный PWM должен быть выше
        if load > 80:
            target = max(target, 50)
        elif load > 50:
            target = max(target, 40)
            
        # -------------------------------------------------------------------------
        # КОРРЕКЦИЯ ПО ОКРУЖАЮЩЕЙ СРЕДЕ (Environmental Modifier)
        # -------------------------------------------------------------------------
        # Получаем модификатор эффективности охлаждения
        # Если воздух влажный/пыльный, эффективность падает (< 1.0)
        # Нам нужно УВЕЛИЧИТЬ PWM, чтобы компенсировать это
        try:
            # Получаем последние известные данные
            from environmental_control import environmental_control_algo
            efficiency = environmental_control_algo.get_cooling_efficiency_modifier(
                environmental_control_algo.current_humidity,
                environmental_control_algo.current_dust
            )
            
            # Если эффективность < 1, нужно увеличить PWM
            # target_new = target / efficiency
            # Пример: efficiency 0.8 -> target 50 становится 62.5
            if efficiency < 0.99 and efficiency > 0.1: # Protect from div/0
                target_compensated = target / efficiency
                # print(f"  Environmental compensation: PWM {target:.0f} -> {target_compensated:.0f} (Eff: {efficiency:.2f})")
                target = target_compensated
        except Exception as e:
            # Fallback if algo not ready
            pass
            
        return int(max(config.MIN_FAN_PWM, min(target, config.MAX_FAN_PWM)))

    def calculate_fan_commands(self, payload: TelemetryPayload) -> FanControlBatch:
        commands = []
        current_time = time.time()
        
        for gpu_temp in payload.sensors.gpu_temps:
            gpu_id = gpu_temp.gpu_id
            temp = gpu_temp.temperature
            load = gpu_temp.load
            
            # 1. Обновляем историю и определяем состояние
            self._update_history(gpu_id, temp)
            state = self._determine_state(gpu_id)
            
            # 2. Считаем целевой (идеальный) PWM
            target_pwm = self.calculate_target_pwm(temp, load)
            
            # 3. Применяем гистерезис и инерцию
            current_pwm = self.current_pwm.get(gpu_id, config.MIN_FAN_PWM)
            
            new_pwm = current_pwm
            
            if target_pwm > current_pwm:
                # НАГРЕВ: Реагируем быстро (безопасность)
                # Разрешаем рост сразу
                new_pwm = target_pwm
                self.last_pwm_change[gpu_id] = current_time
                print(f"🔥 GPU {gpu_id} нагрев: {current_pwm}% -> {new_pwm}% (Temp: {temp:.1f}, Load: {load:.0f}%)")
                
            elif target_pwm < current_pwm:
                # ОХЛАЖДЕНИЕ: Реагируем медленно (инерция)
                
                # Проверяем таймер удержания
                last_change = self.last_pwm_change.get(gpu_id, 0)
                time_since_change = current_time - last_change
                
                if time_since_change >= self.MIN_PWM_HOLD_TIME:
                    # Разрешаем снижение, но плавно (ступеньками)
                    # Не падаем сразу до target, а делаем шаг вниз
                    max_drop = 10 # Макс шаг снижения %
                    drop = min(current_pwm - target_pwm, max_drop)
                    new_pwm = current_pwm - drop
                    self.last_pwm_change[gpu_id] = current_time
                    print(f"❄️ GPU {gpu_id} остыл: {current_pwm}% -> {new_pwm}% (Temp: {temp:.1f})")
                else:
                    # Удерживаем обороты (инерция)
                    new_pwm = current_pwm
            
            # Сохраняем и добавляем команду
            self.current_pwm[gpu_id] = new_pwm
            commands.append(FanControlCommand(
                fan_id=gpu_id,
                pwm_duty=new_pwm
            ))
            
        return FanControlBatch(
            device_id=payload.device_id,
            commands=commands
        )

cooling_algo = SmartCoolingAlgorithm()

# ============================================================================
# ENVIRONMENTAL CONTROL ALGORITHM
# ============================================================================

from environmental_control import environmental_control_algo, trend_analyzer

# ============================================================================
# СИСТЕМА АЛЕРТОВ
# ============================================================================

class AlertManager:
    """Управление алертами о критичных температурах"""
    
    def __init__(self):
        self.active_alerts: Dict[int, AlertEvent] = {}  # {gpu_id: alert}
    
    def check_temperatures(self, payload: TelemetryPayload) -> List[AlertEvent]:
        """
        Проверяет температуры и создаёт алерты
        
        Returns:
            Список новых алертов
        """
        new_alerts = []
        
        for gpu_temp in payload.sensors.gpu_temps:
            gpu_id = gpu_temp.gpu_id
            temp = gpu_temp.temperature
            
            # Критичная температура
            if temp >= config.CRITICAL_TEMP_THRESHOLD:
                if gpu_id not in self.active_alerts or \
                   self.active_alerts[gpu_id].severity != "critical":
                    
                    alert = AlertEvent(
                        gpu_id=gpu_id,
                        temperature=temp,
                        threshold=config.CRITICAL_TEMP_THRESHOLD,
                        severity="critical",
                        timestamp=payload.timestamp
                    )
                    self.active_alerts[gpu_id] = alert
                    new_alerts.append(alert)
                    print(f"🚨 КРИТИЧНО! GPU {gpu_id}: {temp}°C (порог {config.CRITICAL_TEMP_THRESHOLD}°C)")
            
            # Предупреждение
            elif temp >= config.WARNING_TEMP_THRESHOLD:
                if gpu_id not in self.active_alerts:
                    alert = AlertEvent(
                        gpu_id=gpu_id,
                        temperature=temp,
                        threshold=config.WARNING_TEMP_THRESHOLD,
                        severity="warning",
                        timestamp=payload.timestamp
                    )
                    self.active_alerts[gpu_id] = alert
                    new_alerts.append(alert)
                    print(f"⚠️  Предупреждение! GPU {gpu_id}: {temp}°C (порог {config.WARNING_TEMP_THRESHOLD}°C)")
            
            # Температура нормализовалась
            else:
                if gpu_id in self.active_alerts:
                    del self.active_alerts[gpu_id]
                    print(f"✓ GPU {gpu_id} остыл: {temp}°C")
        
        return new_alerts

alert_manager = AlertManager()

# ============================================================================
# FASTAPI ПРИЛОЖЕНИЕ
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    print("=" * 60)
    print("🚀 Запуск Fog-сервера")
    print("=" * 60)
    influx_manager.connect()
    print("✓ Сервер готов к приёму данных")
    print("=" * 60)
    
    yield
    
    # Shutdown
    print("⏹️  Остановка сервера...")
    influx_manager.disconnect()

app = FastAPI(
    title="GPU Cooling Fog Server",
    description="IoT система мониторинга и адаптивного управления охлаждением GPU-кластера",
    version="1.0.0",
    lifespan=lifespan
)

# CORS для веб-интерфейса
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # В продакшене указать конкретный домен
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(timezone.utc).isoformat()}

@app.post("/api/v1/telemetry")
async def receive_telemetry(payload: TelemetryPayload):
    """
    Приём телеметрии от ESP32
    
    Действия:
    1. Сохранение в InfluxDB
    2. Проверка на алерты
    3. Вычисление команд управления (если режим AUTO)
    4. Сохранение команд для ESP32
    """
    try:
        # 1. Сохраняем в InfluxDB
        influx_manager.write_telemetry(payload)
        
        # 2. Проверяем алерты
        new_alerts = alert_manager.check_temperatures(payload)
        for alert in new_alerts:
            influx_manager.write_alert(alert)
        
        # 3. Вычисляем команды в зависимости от режима
        global pending_commands
        
        if system_mode["mode"] == "auto":
            # АВТОМАТИЧЕСКИЙ РЕЖИМ: алгоритм управляет
            fan_commands = cooling_algo.calculate_fan_commands(payload)
            pending_commands[payload.device_id] = fan_commands
            
        elif system_mode["mode"] == "manual":
            # РУЧНОЙ РЕЖИМ: используем команды пользователя
            if payload.device_id in system_mode["manual_commands"]:
                manual_batch = system_mode["manual_commands"][payload.device_id]
                fan_commands = FanControlBatch(
                    device_id=payload.device_id,
                    commands=[
                        FanControlCommand(fan_id=cmd.fan_id, pwm_duty=cmd.pwm_duty)
                        for cmd in manual_batch.commands
                    ]
                )
                pending_commands[payload.device_id] = fan_commands
        
        print(f"✓ Телеметрия получена от {payload.device_id} (режим: {system_mode['mode']})")
        
        return {
            "status": "success",
            "message": "Telemetry received",
            "alerts": len(new_alerts),
            "mode": system_mode["mode"]
        }
    
    except Exception as e:
        print(f"✗ Ошибка обработки телеметрии: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Хранилище команд для ESP32
pending_commands: Dict[str, FanControlBatch] = {}

# ============================================================================
# УПРАВЛЕНИЕ РЕЖИМОМ РАБОТЫ
# ============================================================================

# Текущий режим работы системы
system_mode = {
    "mode": "auto",  # auto или manual
    "last_changed": datetime.now(timezone.utc).isoformat(),
    "changed_by": "system",
    "manual_commands": {}  # {device_id: FanManualControlBatch}
}

# Лог действий пользователя
user_action_log = []

def log_user_action(action: str, details: dict):
    """Логирует действия пользователя"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "details": details
    }
    user_action_log.append(log_entry)
    
    # Храним только последние 100 действий
    if len(user_action_log) > 100:
        user_action_log.pop(0)
    
    print(f"👤 Действие пользователя: {action} - {details}")

@app.get("/api/v1/fan-control/{device_id}")
async def get_fan_commands(device_id: str):
    """
    ESP32 получает команды управления вентиляторами
    
    Returns:
        FanControlBatch если есть команды
        204 No Content если команд нет
    """
    if device_id in pending_commands:
        commands = pending_commands.pop(device_id)  # Забираем и удаляем
        return commands
    else:
        return None  # FastAPI вернёт 204

@app.get("/api/v1/current-state")
async def get_current_state():
    """API для веб-интерфейса: текущее состояние системы"""
    try:
        gpu_stats = influx_manager.query_latest_state()
        
        return {
            "gpu_temps": [
                {
                    "gpu_id": k, 
                    "temperature": v["temperature"],
                    "load": v.get("load", 0.0)
                } 
                for k, v in gpu_stats.items()
            ],
            "alerts": list(alert_manager.active_alerts.values()),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/history")
async def get_history(hours: int = 1):
    """API для веб-интерфейса: исторические данные"""
    try:
        data = influx_manager.query_history(hours)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/fan-history")
async def get_fan_history(hours: int = 1):
    """
    API для веб-интерфейса: история работы вентиляторов
    Возвращает данные PWM и RPM за последние N часов
    """
    try:
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: -{hours}h)
          |> filter(fn: (r) => r["_measurement"] == "fan_states")
          |> filter(fn: (r) => r["_field"] == "pwm_duty" or r["_field"] == "rpm")
        '''
        
        result = influx_manager.query_api.query(query=query)
        
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "time": record.values.get("_time").isoformat(),
                    "fan_id": record.values.get("fan_id"),
                    "field": record.values.get("_field"),  # "pwm_duty" или "rpm"
                    "value": record.values.get("_value")
                })
        
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ============================================================================
# API ENDPOINTS ДЛЯ УПРАВЛЕНИЯ ВЕНТИЛЯТОРАМИ
# ============================================================================

@app.get("/api/v1/system-mode")
async def get_system_mode():
    """Получить текущий режим работы системы"""
    return SystemMode(**system_mode)


@app.post("/api/v1/system-mode")
async def set_system_mode(mode_data: ManualControlMode):
    """
    Переключить режим работы системы
    
    - auto: Автоматическое управление алгоритмом
    - manual: Ручное управление пользователем
    """
    global system_mode
    
    old_mode = system_mode["mode"]
    new_mode = mode_data.mode
    
    system_mode["mode"] = new_mode
    system_mode["last_changed"] = datetime.now(timezone.utc).isoformat()
    system_mode["changed_by"] = "user"
    
    log_user_action(
        action="change_mode",
        details={"from": old_mode, "to": new_mode}
    )
    
    print(f"🔄 Режим изменён: {old_mode} → {new_mode}")
    
    # Если переключились на auto, очищаем ручные команды
    if new_mode == "auto":
        system_mode["manual_commands"] = {}
        print("✓ Ручные команды сброшены, система вернулась к автоматическому управлению")
    
    return {"status": "success", "mode": new_mode, "previous_mode": old_mode}


@app.post("/api/v1/fan-control/manual")
async def set_manual_fan_control(control_batch: FanManualControlBatch):
    """
    Установить ручное управление вентиляторами
    Работает только если system_mode = "manual"
    """
    if system_mode["mode"] != "manual":
        raise HTTPException(
            status_code=400,
            detail="Система в автоматическом режиме. Переключитесь на ручной режим."
        )
    
    # Сохраняем ручные команды
    system_mode["manual_commands"][control_batch.device_id] = control_batch
    
    # Логируем действие
    log_user_action(
        action="manual_control",
        details={
            "device_id": control_batch.device_id,
            "fans": [{"fan_id": cmd.fan_id, "pwm": cmd.pwm_duty} for cmd in control_batch.commands]
        }
    )
    
    print(f"🎛️  Ручное управление применено для {control_batch.device_id}")
    for cmd in control_batch.commands:
        print(f"   Вентилятор {cmd.fan_id}: PWM установлен на {cmd.pwm_duty}%")
    
    # Отправляем команды в очередь для ESP32
    global pending_commands
    fan_commands = FanControlBatch(
        device_id=control_batch.device_id,
        commands=[
            FanControlCommand(fan_id=cmd.fan_id, pwm_duty=cmd.pwm_duty)
            for cmd in control_batch.commands
        ]
    )
    pending_commands[control_batch.device_id] = fan_commands
    
    return {
        "status": "success",
        "message": "Ручные команды применены",
        "mode": "manual"
    }


@app.get("/api/v1/fan-statistics")
async def get_fan_statistics():
    """
    Получить статистику работы всех вентиляторов
    """
    try:
        # Запрос данных за последний час
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: -1h)
          |> filter(fn: (r) => r["_measurement"] == "fan_states")
          |> filter(fn: (r) => r["_field"] == "pwm_duty")
        '''
        
        result = influx_manager.query_api.query(query=query)
        
        # Группируем данные по fan_id
        fan_data = {}
        for table in result:
            for record in table.records:
                fan_id = int(record.values.get("fan_id"))
                pwm = record.values.get("_value")
                
                if fan_id not in fan_data:
                    fan_data[fan_id] = []
                fan_data[fan_id].append(pwm)
        
        # Вычисляем статистику
        statistics = []
        for fan_id in range(1, config.GPU_COUNT + 1):
            if fan_id in fan_data and fan_data[fan_id]:
                pwm_values = fan_data[fan_id]
                
                avg_pwm = sum(pwm_values) / len(pwm_values)
                max_pwm = max(pwm_values)
                min_pwm = min(pwm_values)
                
                # Время на высоких оборотах (>80% PWM)
                high_count = sum(1 for p in pwm_values if p > 80)
                time_on_high = high_count * 30  # каждое измерение = 30 секунд
                
                # Текущие значения
                current_pwm = pwm_values[-1] if pwm_values else 20
                current_rpm = int(800 + (5000 - 800) * current_pwm / 100)
                
                statistics.append(FanStatistics(
                    fan_id=fan_id,
                    avg_pwm_last_hour=round(avg_pwm, 1),
                    max_pwm_last_hour=max_pwm,
                    min_pwm_last_hour=min_pwm,
                    time_on_high=time_on_high,
                    current_rpm=current_rpm,
                    current_pwm=current_pwm
                ))
            else:
                # Нет данных, возвращаем дефолтные значения
                statistics.append(FanStatistics(
                    fan_id=fan_id,
                    avg_pwm_last_hour=20.0,
                    max_pwm_last_hour=20,
                    min_pwm_last_hour=20,
                    time_on_high=0,
                    current_rpm=840,
                    current_pwm=20
                ))
        
        return {"statistics": statistics}
    
    except Exception as e:
        print(f"✗ Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# ENVIRONMENTAL API ENDPOINTS
# ============================================================================

# Storage for pending environmental commands
pending_environmental_commands: Dict[str, Dict] = {}

@app.post("/api/v1/environmental/telemetry")
async def receive_environmental_telemetry(payload: EnvironmentalPayload):
    """
    Приём environmental telemetry от ESP32
    
    Действия:
    1. Сохранение в InfluxDB
    2. Проверка на environmental alerts
    3. Вычисление команд управления (если режим AUTO)  
    4. Добавление данных в trend analyzer
    5. Применение cooling efficiency modifier
    """
    try:
        # 1. Сохраняем в InfluxDB
        influx_manager.write_environmental_telemetry(payload)
        
        # 2. Add to trend analyzer
        import time
        current_time = time.time()
        trend_analyzer.add_data_point(
            payload.sensors.humidity,
            payload.sensors.dust,
            current_time
        )
        
        # Update current state in algo for cooling calculations
        environmental_control_algo.update_current_state(
            payload.sensors.humidity,
            payload.sensors.dust,
            payload.actuators.dict()
        )
        
        # 3. Проверяем alerts
        new_alerts = environmental_control_algo.check_environmental_alerts(
            payload.sensors.humidity,
            payload.sensors.dust,
            payload.timestamp
        )
        for alert in new_alerts:
            influx_manager.write_environmental_alert(alert)
        
        # 4. Вычисляем control commands (if auto mode)
        global pending_environmental_commands
        
        if system_mode["mode"] == "auto":
            control_commands = environmental_control_algo.calculate_control_commands(
                payload.sensors.humidity,
                payload.sensors.dust
            )
            pending_environmental_commands[payload.device_id] = control_commands
        
        print(f"✓ Environmental telemetry received from {payload.device_id}")
        print(f"  Humidity: {payload.sensors.humidity:.1f}%, Dust: {payload.sensors.dust:.1f} μg/m³")
        
        return {
            "status": "success",
            "message": "Environmental telemetry received",
            "alerts": len(new_alerts)
        }
    
    except Exception as e:
        print(f"✗ Error processing environmental telemetry: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/environmental/control/{device_id}")
async def get_environmental_commands(device_id: str):
    """
    ESP32 получает environmental control commands
    
    Returns:
        Dict with commands or 204 No Content
    """
    if device_id in pending_environmental_commands:
        commands = pending_environmental_commands.pop(device_id)
        return commands
    else:
        return None


@app.get("/api/v1/environmental/current")
async def get_current_environmental_state():
    """
    API для веб-интерфейса: текущее environmental состояние
    """
    try:
        # Query latest environmental data
        history = influx_manager.query_environmental_history(hours=1)
        
        # Extract latest values
        latest_humidity = None
        latest_dust = None
        
        for point in reversed(history):
            if point["field"] == "humidity" and latest_humidity is None:
                latest_humidity = point["value"]
            if point["field"] == "dust" and latest_dust is None:
                latest_dust = point["value"]
            if latest_humidity is not None and latest_dust is not None:
                break
        
        # Get current actuator states
        actuator_states = {
            "dehumidifier_active": environmental_control_algo.dehumidifier_active,
            "dehumidifier_power": environmental_control_algo.dehumidifier_power,
            "humidifier_active": environmental_control_algo.humidifier_active,
            "humidifier_power": environmental_control_algo.humidifier_power
        }
        
        return {
            "humidity": latest_humidity,
            "dust": latest_dust,
            "actuators": actuator_states,
            "alerts": environmental_control_algo.active_environmental_alerts,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/environmental/history")
async def get_environmental_history(hours: int = 1):
    """
    API для веб-интерфейса: environmental historical data
    """
    try:
        data = influx_manager.query_environmental_history(hours)
        return {"data": data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/environmental/trends")
async def get_environmental_trends():
    """
    API для веб-интерфейса: computed environmental trends
    """
    try:
        # Calculate trends
        humidity_rate = trend_analyzer.calculate_hourly_humidity_change_rate()
        dust_rate = trend_analyzer.calculate_hourly_dust_accumulation_rate()
        
        # Infer hidden factors
        ventilation_level = trend_analyzer.infer_ventilation_level(humidity_rate)
        filtration_quality = trend_analyzer.infer_filtration_quality(dust_rate)
        
        # Get latest environmental values for cooling efficiency
        history = influx_manager.query_environmental_history(hours=1)
        latest_humidity = 50.0
        latest_dust = 25.0
        
        for point in reversed(history):
            if point["field"] == "humidity":
                latest_humidity = point["value"]
                break
        for point in reversed(history):
            if point["field"] == "dust":
                latest_dust = point["value"]
                break
        
        cooling_efficiency = environmental_control_algo.get_cooling_efficiency_modifier(
            latest_humidity,
            latest_dust
        )
        
        return {
            "trends": {
                "hourly_humidity_change_rate": {
                    "value": humidity_rate,
                    "interpretation": ventilation_level,
                    "formula": "avg(current RH - previous RH) over last hour"
                },
                "hourly_dust_accumulation_rate": {
                    "value": dust_rate,
                    "interpretation": filtration_quality,
                    "formula": "avg(current PM - previous PM) over last hour"
                },
                "cooling_efficiency_modifier": {
                    "value": cooling_efficiency,
                    "reduction_percent": (1.0 - cooling_efficiency) * 100,
                    "formula": "1 - (0.002 * |RH - 50|) - (0.001 * PM)"
                }
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/v1/environmental/control")
async def set_environmental_control(command: EnvironmentalControlCommand):
    """
    Manual environmental control (user override)
    """
    try:
        # Store manual command
        device_id = "esp32_master_001"  # Default device
        
        commands = {
            "dehumidifier_active": command.dehumidifier_active,
            "dehumidifier_power": command.dehumidifier_power,
            "humidifier_active": command.humidifier_active,
            "humidifier_power": command.humidifier_power
        }
        
        # Add to pending commands
        global pending_environmental_commands
        pending_environmental_commands[device_id] = commands
        
        # Log user action
        log_user_action(
            action="environmental_control",
            details=commands
        )
        
        print(f"🎛️ Manual environmental control applied: {commands}")
        
        return {
            "status": "success",
            "message": "Environmental control command sent",
            "commands": commands
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/user-actions")
async def get_user_actions(limit: int = 20):
    """
    Получить историю действий пользователя
    """
    return {
        "actions": user_action_log[-limit:],
        "total": len(user_action_log)
    }


# ============================================================================
# ЗАПУСК СЕРВЕРА
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    import socket

    def find_free_port(host: str, start_port: int, max_tries: int = 50) -> int:
        """Ищет свободный порт, начиная с `start_port`.

        Возвращает первый доступный порт или вызывает исключение, если не найдено.
        """
        port = start_port
        for _ in range(max_tries):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                try:
                    s.bind((host, port))
                    return port
                except OSError:
                    port += 1

        raise OSError(f"Не удалось найти свободный порт в диапазоне {start_port}-{port}")

    host = os.getenv("FOG_SERVER_HOST", "0.0.0.0")
    configured_port = int(os.getenv("FOG_SERVER_PORT", 8000))

    try:
        port = find_free_port(host, configured_port, max_tries=100)
        if port != configured_port:
            print(f"⚠️  Порт {configured_port} занят — использую порт {port} вместо него")

        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info"
        )

    except OSError as e:
        print(f"✗ Не удалось запустить сервер: {e}")
        print("Проверьте, не занят ли указанный порт, или задайте другой через переменную окружения FOG_SERVER_PORT")
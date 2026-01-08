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
from enum import Enum
import asyncio
import os
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
    workload: float = Field(..., ge=0.0, le=1.0)  # Процент загрузки GPU (0.0-1.0)

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
        - measurement: gpu_temps (температуры GPU)
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
                .field("workload", gpu_temp.workload) \
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
    
    def query_latest_gpu_data(self) -> Dict[int, Dict[str, float]]:
        """
        Получает последние температуры и workload всех GPU
        
        Returns:
            {gpu_id: {"temperature": float, "workload": float}}
        """
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: -1m)
          |> filter(fn: (r) => r["_measurement"] == "gpu_temps")
          |> filter(fn: (r) => r["_field"] == "temperature" or r["_field"] == "workload")
          |> last()
        '''
        
        result = self.query_api.query(query=query)
        
        gpu_data = {}
        for table in result:
            for record in table.records:
                gpu_id = int(record.values.get("gpu_id"))
                field = record.values.get("_field")
                value = record.values.get("_value")
                
                if gpu_id not in gpu_data:
                    gpu_data[gpu_id] = {}
                gpu_data[gpu_id][field] = value
        
        return gpu_data
    
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
          |> filter(fn: (r) => r["_field"] == "temperature" or r["_field"] == "workload")
        '''
        
        result = self.query_api.query(query=query)
        
        data = []
        for table in result:
            for record in table.records:
                data.append({
                    "time": record.values.get("_time").isoformat(),
                    "measurement": record.values.get("_measurement"),
                    "gpu_id": record.values.get("gpu_id"),
                    "field": record.values.get("_field"),  # "temperature" или "workload"
                    "value": record.values.get("_value")
                })
        
        return data

influx_manager = InfluxDBManager()

# ============================================================================
# АЛГОРИТМ УПРАВЛЕНИЯ ОХЛАЖДЕНИЕМ
# ============================================================================

class ThermalState(Enum):
    """Состояние нагрева GPU"""
    HEATING = "heating"    # Температура растёт
    STEADY = "steady"      # Температура стабильна
    COOLING = "cooling"    # Температура падает

class CoolingAlgorithm:
    """
    Каскадный адаптивный алгоритм управления охлаждением с учётом трендов
    
    Принцип:
    1. Определение thermal state (heating/steady/cooling)
    2. Разные шаги PWM для роста и падения температуры
    3. Минимальное время удержания PWM
    4. Базовый PWM зависит от температуры GPU
    5. Коррекция на основе температуры помещения
    6. Фильтрация резких изменений (сглаживание)
    """
    
    def __init__(self):
        # Предыдущие температуры для определения тренда
        self.previous_temps: Dict[int, float] = {}
        
        # Время последнего изменения PWM для каждого вентилятора
        self.last_pwm_change: Dict[int, datetime] = {}
        
        # Текущие значения PWM
        self.current_pwm: Dict[int, int] = {}
        
        # Параметры алгоритма
        self.epsilon = 0.5  # °C - порог для определения тренда
        self.pwm_up_step = 8   # Шаг увеличения PWM (%)
        self.pwm_down_step = 3 # Шаг уменьшения PWM (%)
        self.min_hold_time = 60  # Минимальное время удержания PWM (секунды)
    
    def get_thermal_state(self, gpu_id: int, current_temp: float) -> ThermalState:
        """
        Определяет состояние нагрева GPU на основе тренда температуры
        
        Args:
            gpu_id: ID GPU
            current_temp: Текущая температура
        
        Returns:
            ThermalState: heating, steady, или cooling
        """
        if gpu_id not in self.previous_temps:
            # Первое измерение - считаем steady
            self.previous_temps[gpu_id] = current_temp
            return ThermalState.STEADY
        
        # Вычисляем дельту температуры
        delta = current_temp - self.previous_temps[gpu_id]
        
        # Обновляем предыдущую температуру
        self.previous_temps[gpu_id] = current_temp
        
        # Определяем состояние
        if delta > self.epsilon:
            return ThermalState.HEATING
        elif delta < -self.epsilon:
            return ThermalState.COOLING
        else:
            return ThermalState.STEADY
    
    def calculate_base_pwm(self, gpu_temp: float) -> int:
        """
        Вычисляет базовый PWM на основе температуры GPU
        
        Логика:
        - < 50°C  → 20% (минимум)
        - 50-70°C → 20-50% (линейный рост)
        - 70-90°C → 50-80% (линейный рост)
        - > 90°C  → 80-100% (агрессивное охлаждение)
        """
        if gpu_temp < 50:
            return config.MIN_FAN_PWM
        elif gpu_temp < 70:
            # 50-70°C → 20-50%
            return int(20 + (gpu_temp - 50) * (30 / 20))
        elif gpu_temp < 90:
            # 70-90°C → 50-80%
            return int(50 + (gpu_temp - 70) * (30 / 20))
        else:
            # > 90°C → 80-100%
            return int(min(80 + (gpu_temp - 90) * 2, config.MAX_FAN_PWM))
    
    def apply_room_correction(self, base_pwm: int, room_temp: float) -> int:
        """
        Корректирует PWM с учётом температуры помещения
        
        Логика:
        - Комната холодная (< 24°C) → уменьшаем PWM
        - Комната тёплая (> 26°C) → увеличиваем PWM
        - Влияние ограничено ROOM_TEMP_INFLUENCE (30%)
        """
        reference_room_temp = 24.0  # Базовая комнатная температура
        temp_diff = room_temp - reference_room_temp
        
        # Коррекция: +1°C комнаты = +5% PWM
        correction = int(temp_diff * 5 * config.ROOM_TEMP_INFLUENCE)
        
        corrected_pwm = base_pwm + correction
        
        # Ограничиваем диапазон
        return max(config.MIN_FAN_PWM, min(corrected_pwm, config.MAX_FAN_PWM))
    
    def calculate_pwm_with_trend(self, fan_id: int, gpu_temp: float, thermal_state: ThermalState) -> int:
        """
        Вычисляет PWM с учётом тренда температуры
        
        Args:
            fan_id: ID вентилятора
            gpu_temp: Текущая температура GPU
            thermal_state: Состояние нагрева
        
        Returns:
            Новое значение PWM
        """
        # Базовый PWM от температуры
        base_pwm = self.calculate_base_pwm(gpu_temp)
        
        # Получаем текущее PWM
        current_pwm = self.current_pwm.get(fan_id, config.MIN_FAN_PWM)
        
        # Проверяем минимальное время удержания
        now = datetime.now(timezone.utc)
        if fan_id in self.last_pwm_change:
            time_since_change = (now - self.last_pwm_change[fan_id]).total_seconds()
            if time_since_change < self.min_hold_time:
                # Не меняем PWM, если прошло мало времени
                return current_pwm
        
        # Выбираем шаг в зависимости от состояния
        if thermal_state == ThermalState.HEATING:
            # Температура растёт - увеличиваем PWM быстро
            step = self.pwm_up_step
            target_pwm = min(current_pwm + step, config.MAX_FAN_PWM)
        elif thermal_state == ThermalState.COOLING:
            # Температура падает - уменьшаем PWM медленно
            step = self.pwm_down_step
            target_pwm = max(current_pwm - step, config.MIN_FAN_PWM)
        else:
            # Температура стабильна - стремимся к базовому PWM
            if abs(current_pwm - base_pwm) > 5:
                if current_pwm < base_pwm:
                    target_pwm = min(current_pwm + self.pwm_down_step, base_pwm)
                else:
                    target_pwm = max(current_pwm - self.pwm_down_step, base_pwm)
            else:
                target_pwm = current_pwm
        
        # Обновляем состояние
        if target_pwm != current_pwm:
            self.last_pwm_change[fan_id] = now
        
        self.current_pwm[fan_id] = target_pwm
        return target_pwm
    
    def smooth_pwm(self, fan_id: int, new_pwm: int) -> int:
        """
        Устаревший метод для совместимости
        Теперь используется calculate_pwm_with_trend
        """
        return new_pwm
    
    def calculate_fan_commands(self, payload: TelemetryPayload) -> FanControlBatch:
        """
        Главная функция: вычисляет команды для всех вентиляторов с учётом трендов
        
        Args:
            payload: Телеметрия от ESP32
        
        Returns:
            FanControlBatch с командами для каждого вентилятора
        """
        commands = []
        room_temp = payload.sensors.room_temp
        
        for gpu_temp in payload.sensors.gpu_temps:
            fan_id = gpu_temp.gpu_id  # Вентилятор 1 охлаждает GPU 1
            
            # 1. Определяем thermal state
            thermal_state = self.get_thermal_state(fan_id, gpu_temp.temperature)
            
            # 2. Вычисляем PWM с учётом тренда
            base_pwm = self.calculate_pwm_with_trend(fan_id, gpu_temp.temperature, thermal_state)
            
            # 3. Коррекция на комнату (только если не в режиме быстрого реагирования)
            if thermal_state != ThermalState.HEATING:
                corrected_pwm = self.apply_room_correction(base_pwm, room_temp)
            else:
                corrected_pwm = base_pwm  # При нагреве игнорируем коррекцию комнаты
            
            commands.append(FanControlCommand(
                fan_id=fan_id,
                pwm_duty=corrected_pwm
            ))
        
        return FanControlBatch(
            device_id=payload.device_id,
            commands=commands
        )

cooling_algo = CoolingAlgorithm()

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
        gpu_data = influx_manager.query_latest_gpu_data()
        
        gpu_temps = []
        for gpu_id, data in gpu_data.items():
            gpu_temps.append({
                "gpu_id": gpu_id,
                "temperature": data.get("temperature", 0.0),
                "workload": data.get("workload", 0.0)
            })
        
        return {
            "gpu_temps": gpu_temps,
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
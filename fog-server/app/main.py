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
    
    def query_latest_temps(self) -> Dict[int, float]:
        """
        Получает последние температуры всех GPU
        
        Returns:
            {gpu_id: temperature}
        """
        query = f'''
        from(bucket: "{config.INFLUXDB_BUCKET}")
          |> range(start: -1m)
          |> filter(fn: (r) => r["_measurement"] == "gpu_temps")
          |> filter(fn: (r) => r["_field"] == "temperature")
          |> last()
        '''
        
        result = self.query_api.query(query=query)
        
        temps = {}
        for table in result:
            for record in table.records:
                gpu_id = int(record.values.get("gpu_id"))
                temp = record.values.get("_value")
                temps[gpu_id] = temp
        
        return temps
    
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

influx_manager = InfluxDBManager()

# ============================================================================
# АЛГОРИТМ УПРАВЛЕНИЯ ОХЛАЖДЕНИЕМ
# ============================================================================

class CoolingAlgorithm:
    """
    Каскадный адаптивный алгоритм управления охлаждением
    
    Принцип:
    1. Базовый PWM зависит от температуры GPU
    2. Коррекция на основе температуры помещения
    3. Фильтрация резких изменений (сглаживание)
    """
    
    def __init__(self):
        self.previous_pwm: Dict[int, int] = {}  # Предыдущие значения PWM
    
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
    
    def smooth_pwm(self, fan_id: int, new_pwm: int) -> int:
        """
        Сглаживает резкие изменения PWM
        
        Логика:
        - Если изменение < 10% → не меняем (избегаем дёрганий)
        - Если изменение > 10% → применяем постепенно
        """
        if fan_id not in self.previous_pwm:
            self.previous_pwm[fan_id] = new_pwm
            return new_pwm
        
        prev_pwm = self.previous_pwm[fan_id]
        diff = abs(new_pwm - prev_pwm)
        
        if diff < 10:
            # Малое изменение → игнорируем
            return prev_pwm
        else:
            # Большое изменение → применяем на 50% (плавный переход)
            smoothed = int((prev_pwm + new_pwm) / 2)
            self.previous_pwm[fan_id] = smoothed
            return smoothed
    
    def calculate_fan_commands(self, payload: TelemetryPayload) -> FanControlBatch:
        """
        Главная функция: вычисляет команды для всех вентиляторов
        
        Args:
            payload: Телеметрия от ESP32
        
        Returns:
            FanControlBatch с командами для каждого вентилятора
        """
        commands = []
        room_temp = payload.sensors.room_temp
        
        for gpu_temp in payload.sensors.gpu_temps:
            fan_id = gpu_temp.gpu_id  # Вентилятор 1 охлаждает GPU 1
            
            # 1. Базовый PWM
            base_pwm = self.calculate_base_pwm(gpu_temp.temperature)
            
            # 2. Коррекция на комнату
            corrected_pwm = self.apply_room_correction(base_pwm, room_temp)
            
            # 3. Сглаживание
            final_pwm = self.smooth_pwm(fan_id, corrected_pwm)
            
            commands.append(FanControlCommand(
                fan_id=fan_id,
                pwm_duty=final_pwm
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
        temps = influx_manager.query_latest_temps()
        
        return {
            "gpu_temps": [{"gpu_id": k, "temperature": v} for k, v in temps.items()],
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
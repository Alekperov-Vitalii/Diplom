"""
Главный модуль эмулятора ESP32
Объединяет все компоненты: симуляторы, вентиляторы, HTTP-клиент
"""

import time
import yaml
import logging
from datetime import datetime, timezone
from typing import List

from models import TelemetryPayload, SensorData, FanData, GPUTemperature
from gpu_simulator import GPUSimulator, RoomSimulator
from actuators.fan_controller import FanController
from edge_gateway.esp32_gateway import ESP32Gateway
from core.workload_profiles import WorkloadOrchestrator
from logger_config import setup_logger

logger = setup_logger(__name__, level=logging.INFO)


class ESP32Emulator:
    """Главный класс эмулятора ESP32"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Args:
            config_path: Путь к конфигурационному файлу
        """
        logger.info("=" * 60)
        logger.info("Инициализация ESP32 Emulator System")
        logger.info("=" * 60)
        
        # Загружаем конфигурацию
        self.config = self._load_config(config_path)
        
        # ---------------------------------------------------
        # DEVICE 1: GPU MASTER
        # ---------------------------------------------------
        self.device_id = self.config['device']['id']
        self.gpu_count = self.config['device']['gpu_count']
        
        # Создаём симуляторы GPU
        logger.info(f"Создание {self.gpu_count} симуляторов GPU...")
        self.gpus: List[GPUSimulator] = []
        for gpu_id in range(1, self.gpu_count + 1):
            gpu = GPUSimulator(gpu_id, self.config)
            self.gpus.append(gpu)
        
        # Симулятор помещения
        self.room = RoomSimulator(self.config)
        
        # Оркестратор нагрузки
        self.workload_orchestrator = WorkloadOrchestrator(self.config)
        
        # Контроллер вентиляторов
        self.fan_controller = FanController(self.gpu_count, self.config)
        
        # Gateway 1
        fog_url = f"http://{self.config['fog_server']['host']}:{self.config['fog_server']['port']}"
        self.gateway_master = ESP32Gateway(self.device_id, fog_url, logger)
        
        # ---------------------------------------------------
        # DEVICE 2: ENVIRONMENT MONITOR (NEW)
        # ---------------------------------------------------
        self.env_enabled = self.config.get('secondary_device', {}).get('enabled', False)
        if self.env_enabled:
            logger.info("Инициализация Environment Monitor (Secondary Device)...")
            self.env_device_id = self.config['secondary_device']['id']
            self.gateway_env = ESP32Gateway(self.env_device_id, fog_url, logger)
            
            # Physics Engines
            from core.physics.humidity import HumidityPhysicsEngine
            from core.physics.dust import DustPhysicsEngine
            from sensors.humidity_sensor import HumiditySensor
            from sensors.dust_sensor import DustSensor
            
            self.humidity_physics = HumidityPhysicsEngine(self.config)
            self.dust_physics = DustPhysicsEngine(self.config)
            
            # Sensors
            self.humidity_sensor = HumiditySensor("hum_01", self.config)
            self.dust_sensor = DustSensor("dust_01", self.config)
            
            # Actuators State
            self.actuators = {
                "humidifier": False,
                "dehumidifier": False,
                "air_purifier": False
            }
        
        # Временные параметры
        self.sensor_read_interval = self.config['timing']['sensor_read_interval']
        self.data_send_interval = self.config['timing']['data_send_interval']
        self.total_readings = 0
        self.total_sends = 0
        self.failed_sends = 0
        
        logger.info("✓ Инициализация завершена")
        logger.info("=" * 60)

    # ... (existing methods _load_config) ...

    def _read_sensors(self):
        """
        Читает датчики и обновляет физику (GPU + Environment)
        """
        # ==================== GPU & ROOM PHYSICS ====================
        # 1. Нагрузка
        if self.workload_orchestrator.should_update_workload():
            for i, gpu in enumerate(self.gpus):
                new_workload = self.workload_orchestrator.get_workload_for_gpu(i + 1)
                gpu.set_workload(new_workload)
        
        # 2. Комната
        gpu_heat_contribution = sum(
            1.0 if gpu.workload > 0.5 else 0.5 if gpu.workload > 0.2 else 0.0
            for gpu in self.gpus
        )
        self.room.update(gpu_heat_contribution)
        
        # 3. GPU
        for i, gpu in enumerate(self.gpus):
            fan_cooling = self.fan_controller.get_fan_cooling_effect(i + 1)
            gpu.update_temperature(self.sensor_read_interval, fan_cooling, self.room.temperature)
            
        # ==================== ENVIRONMENT PHYSICS ====================
        if self.env_enabled:
            # Считаем среднюю скорость вентиляторов для корреляции с пылью
            all_fans = self.fan_controller.get_all_fan_states()
            avg_rpm = sum(f.rpm for f in all_fans) / len(all_fans) if all_fans else 0
            
            # Профиль среды (получаем параметры из конфига)
            profile_name = self.config.get('environment_profiles', {}).get('current_profile', 'standard_office')
            profile = self.config.get('environment_profiles', {}).get('profiles', {}).get(profile_name, {})
            vent_rate = profile.get('ventilation_rate', 0.5)
            
            # Обновляем физику (Корреляция!)
            # Влажность зависит от темп. помещения
            self.humidity_physics.update(
                dt=self.sensor_read_interval,
                temperature=self.room.temperature,
                ventilation_rate=vent_rate,
                humidifier_on=self.actuators['humidifier'],
                dehumidifier_on=self.actuators['dehumidifier']
            )
            
            # Пыль зависит от вентиляторов GPU
            self.dust_physics.update(
                dt=self.sensor_read_interval,
                avg_fan_rpm=avg_rpm,
                air_purifier_on=self.actuators['air_purifier']
            )

        self.total_readings += 1
        
        if self.total_readings % 6 == 0:
            self._log_current_state()

    def _log_current_state(self):
        """Логирование состояния (теперь с Environment)"""
        logger.info("─" * 60)
        logger.info(f"📊 State (Read #{self.total_readings})")
        logger.info(f"🏠 Room Temp: {self.room.temperature:.1f}°C")
        
        if self.env_enabled:
            hum = self.humidity_physics.get_value()
            dust = self.dust_physics.get_value()
            
            # Формируем строку статуса актуаторов
            acts = []
            if self.actuators['humidifier']: acts.append("💧Humidifier:ON")
            if self.actuators['dehumidifier']: acts.append("🔥Dehumidifier:ON")
            if self.actuators['air_purifier']: acts.append("🌪️Purifier:ON")
            act_str = " | ".join(acts) if acts else "All OFF"
            
            logger.info(f"🌍 Env Monitor: ☁️ Humidity: {hum:.1f}% | 🌫️ Dust: {dust:.1f} ug/m3")
            logger.info(f"   Actuators: {act_str}")
        
    def _create_telemetry_payload(self) -> TelemetryPayload:
        # Existing GPU payload logic...
        gpu_temps = [
            GPUTemperature(
                gpu_id=gpu.gpu_id,
                temperature=gpu.get_temperature_with_noise(),
                load=round(gpu.workload * 100, 1)
            )
            for gpu in self.gpus
        ]
        return TelemetryPayload(
            device_id=self.device_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            sensors=SensorData(
                gpu_temps=gpu_temps,
                room_temp=self.room.get_temperature_with_noise()
            ),
            fans=FanData(fan_states=self.fan_controller.get_all_fan_states())
        )

    def _create_env_payload(self):
        # NEW: Environment Payload
        from models import EnvironmentalPayload, EnvironmentalSensorData, EnvironmentalActuatorData
        
        hum_val = self.humidity_sensor.read(self.humidity_physics.get_value())
        dust_val = self.dust_sensor.read(self.dust_physics.get_value())
        
        return EnvironmentalPayload(
            device_id=self.env_device_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            sensors=EnvironmentalSensorData(
                humidity=hum_val,
                dust_level=dust_val
            ),
            actuators=EnvironmentalActuatorData(
                humidifier=self.actuators['humidifier'],
                dehumidifier=self.actuators['dehumidifier'],
                air_purifier=self.actuators['air_purifier']
            )
        )

    def _send_data(self):
        """Отправка данных (GPU Master + Env Monitor)"""
        # 1. GPU Master
        payload_master = self._create_telemetry_payload()
        if self.gateway_master.send_telemetry(payload_master):
            self.total_sends += 1
            cmds = self.gateway_master.receive_commands()
            if cmds: self._apply_fan_commands(cmds)
        else:
            self.failed_sends += 1

        # 2. Env Monitor
        if self.env_enabled:
            payload_env = self._create_env_payload()
            # Используем тот же метод отправки, но payload другой
            # Gateway класс универсален, он просто шлет JSON
            if self.gateway_env.send_telemetry(payload_env):
                # Получаем команды для среды
                raw_cmds = self.gateway_env.receive_env_commands() 
                if raw_cmds:
                    self._apply_env_commands(raw_cmds)

    def _apply_env_commands(self, cmd):
        # Применяем команды к виртуальным реле
        if hasattr(cmd, 'humidifier') and cmd.humidifier is not None:
             self.actuators['humidifier'] = cmd.humidifier
        if hasattr(cmd, 'dehumidifier') and cmd.dehumidifier is not None:
             self.actuators['dehumidifier'] = cmd.dehumidifier
        if hasattr(cmd, 'air_purifier') and cmd.air_purifier is not None:
             self.actuators['air_purifier'] = cmd.air_purifier
             
        logger.info(f"🌍 Env Config Updated: {self.actuators}")

    # ... (rest of methods: _apply_fan_commands, run, _print_statistics) ...
    
    def _load_config(self, config_path: str) -> dict:
        """Загружает YAML конфигурацию"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            logger.info(f"✓ Конфигурация загружена из {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"✗ Файл конфигурации не найден: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"✗ Ошибка парсинга YAML: {e}")
            raise
    

    
    def _apply_fan_commands(self, commands):
        """
        Применяет команды управления вентиляторами от fog-сервера
        
        Args:
            commands: FanControlBatch с командами
        """
        logger.info(f"🎛️  Применение команд управления...")
        
        for cmd in commands.commands:
            old_pwm = self.fan_controller.fans[cmd.fan_id]["pwm"]
            self.fan_controller.set_fan_pwm(cmd.fan_id, cmd.pwm_duty)
            new_rpm = self.fan_controller.fans[cmd.fan_id]["rpm"]
            
            logger.info(
                f"  Вентилятор {cmd.fan_id}: "
                f"PWM {old_pwm}% → {cmd.pwm_duty}% "
                f"({new_rpm} RPM)"
            )
    
    def run(self):
        """
        Главный цикл эмулятора
        
        Логика:
        - Каждые 5 секунд читаем датчики
        - Каждые 30 секунд отправляем данные
        """
        logger.info("🚀 Запуск эмулятора...")
        logger.info(f"   Интервал чтения датчиков: {self.sensor_read_interval} сек")
        logger.info(f"   Интервал отправки данных: {self.data_send_interval} сек")
        logger.info("   Нажмите Ctrl+C для остановки")
        logger.info("=" * 60)
        
        # Проверяем доступность fog-сервера (Master)
        if not self.gateway_master.health_check():
            logger.warning("⚠ Fog-сервер недоступен для Master Device!")
            logger.warning("  Убедитесь что fog-сервер запущен на порту 8001")
            
        # Проверяем доступность fog-сервера (Env Monitor)
        if self.env_enabled and not self.gateway_env.health_check():
            logger.warning("⚠ Fog-сервер недоступен для Environment Monitor!")
        
        last_send_time = time.time()
        
        try:
            while True:
                # Читаем датчики
                self._read_sensors()
                
                # Проверяем, пора ли отправлять данные
                current_time = time.time()
                if current_time - last_send_time >= self.data_send_interval:
                    self._send_data()
                    last_send_time = current_time
                
                # Ждём до следующего чтения
                time.sleep(self.sensor_read_interval)
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("⏹️  Остановка эмулятора...")
            self._print_statistics()
            logger.info("=" * 60)
    
    def _print_statistics(self):
        """Выводит статистику работы"""
        logger.info("📈 Статистика работы:")
        logger.info(f"   Всего чтений датчиков: {self.total_readings}")
        logger.info(f"   Успешных отправок: {self.total_sends}")
        logger.info(f"   Неудачных отправок: {self.failed_sends}")
        if self.total_sends > 0:
            success_rate = (self.total_sends / (self.total_sends + self.failed_sends)) * 100
            logger.info(f"   Процент успеха: {success_rate:.1f}%")


def main():
    """Точка входа в программу"""
    emulator = ESP32Emulator(config_path="config.yaml")
    emulator.run()


if __name__ == "__main__":
    main()
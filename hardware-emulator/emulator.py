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

# Environmental components
from environmental_profiles import ProfileManager, PROFILES
from sensors.humidity_sensor import HumiditySensor
from sensors.dust_sensor import DustSensor
from actuators.environmental_controller import EnvironmentalController

logger = setup_logger(__name__, level=logging.INFO)


class ESP32Emulator:
    """Главный класс эмулятора ESP32"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        Args:
            config_path: Путь к конфигурационному файлу
        """
        logger.info("=" * 60)
        logger.info("Инициализация ESP32 Emulator")
        logger.info("=" * 60)
        
        # Загружаем конфигурацию
        self.config = self._load_config(config_path)
        
        # Environmental profile manager
        profile_id = self.config.get('environmental', {}).get('profile_id', 5)
        logger.info(f"Инициализация environmental profile: {profile_id}")
        self.profile_manager = ProfileManager(default_profile_id=profile_id)
        current_profile = self.profile_manager.current_profile
        logger.info(f"  ✓ Profile: {current_profile.name}")
        logger.info(f"    Humidity: {current_profile.humidity_initial}% → {current_profile.humidity_equilibrium}%")
        logger.info(f"    Dust: {current_profile.dust_initial} → {current_profile.dust_equilibrium} μg/m³")
        
        # Инициализируем компоненты
        self.device_id = self.config['device']['id']
        self.gpu_count = self.config['device']['gpu_count']
        
        # Создаём симуляторы GPU
        logger.info(f"Создание {self.gpu_count} симуляторов GPU...")
        self.gpus: List[GPUSimulator] = []
        for gpu_id in range(1, self.gpu_count + 1):
            gpu = GPUSimulator(gpu_id, self.config)
            self.gpus.append(gpu)
            logger.debug(f"  GPU {gpu_id}: {gpu.temperature:.1f}°C (нагрузка {gpu.workload*100:.0f}%)")
        
        # Симулятор помещения
        logger.info("Создание симулятора помещения...")
        self.room = RoomSimulator(self.config)
        logger.debug(f"  Температура помещения: {self.room.temperature:.1f}°C")
        
        # Оркестратор нагрузки (ML профили)
        logger.info("Инициализация WorkloadOrchestrator...")
        self.workload_orchestrator = WorkloadOrchestrator(self.config)
        if self.config.get('workload_profiles', {}).get('datacenter_ml', {}).get('enabled', False):
            logger.info("  ✓ ML профили активированы (datacenter mode)")
        else:
            logger.info("  ℹ Используется классическая случайная нагрузка")
        
        # Контроллер вентиляторов
        logger.info(f"Инициализация {self.gpu_count} вентиляторов...")
        self.fan_controller = FanController(self.gpu_count, self.config)
        
        # Edge Gateway (ESP32)
        fog_url = f"http://{self.config['fog_server']['host']}:{self.config['fog_server']['port']}"
        logger.info(f"Инициализация ESP32 Edge Gateway...")
        logger.info(f"  Fog-сервер: {fog_url}")
        self.gateway = ESP32Gateway(self.device_id, fog_url, logger)
        
        # Environmental sensors
        logger.info("Инициализация environmental sensors...")
        self.humidity_sensor = HumiditySensor(
            sensor_id="DHT22_001",
            initial_humidity=current_profile.humidity_initial,
            equilibrium_humidity=current_profile.humidity_equilibrium,
            base_rate=current_profile.humidity_rate
        )
        logger.info(f"  ✓ Humidity sensor: {self.humidity_sensor.current_humidity:.1f}%")
        
        self.dust_sensor = DustSensor(
            sensor_id="GP2Y1010_001",
            initial_dust=current_profile.dust_initial,
            equilibrium_dust=current_profile.dust_equilibrium,
            base_rate=current_profile.dust_rate
        )
        logger.info(f"  ✓ Dust sensor: {self.dust_sensor.current_dust:.1f} μg/m³")
        
        # Environmental controller
        logger.info("Инициализация environmental controller...")
        self.environmental_controller = EnvironmentalController(logger)
        logger.info("  ✓ Environmental actuators ready")
        
        # Параметры таймингов
        self.sensor_read_interval = self.config['timing']['sensor_read_interval']
        self.data_send_interval = self.config['timing']['data_send_interval']
        
        # Буфер для накопления измерений
        self.measurement_buffer = []
        
        # Счётчики для статистики
        self.total_readings = 0
        self.total_sends = 0
        self.failed_sends = 0
        
        logger.info("✓ Инициализация завершена")
        logger.info("=" * 60)
    
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
    
    def _read_sensors(self):
        """
        Читает все датчики и обновляет физику
        Вызывается каждые 5 секунд
        """
        # Periodic check for remote profile update (every 10 readings ~ 50s)
        if self.total_readings > 0 and self.total_readings % 10 == 0:
            self._check_remote_profile()

        # 1. Обновляем нагрузку через WorkloadOrchestrator
        if self.total_readings > 0 and self.total_readings % 6 == 0: # Every 30s
            self._check_remote_profile()

        if self.workload_orchestrator.should_update_workload():
            for i, gpu in enumerate(self.gpus):
                gpu_id = i + 1
                new_workload = self.workload_orchestrator.get_workload_for_gpu(gpu_id)
                gpu.set_workload(new_workload)
        
        # 2. Вычисляем вклад GPU в нагрев помещения
        gpu_heat_contribution = sum(
            1.0 if gpu.workload > 0.5 else 0.5 if gpu.workload > 0.2 else 0.0
            for gpu in self.gpus
        )
        
        # 3. Обновляем температуру помещения
        self.room.update(gpu_heat_contribution)
        
        # 4. Обновляем температуру каждого GPU
        for i, gpu in enumerate(self.gpus):
            fan_id = i + 1
            fan_cooling = self.fan_controller.get_fan_cooling_effect(fan_id)
            gpu.update_temperature(
                dt=self.sensor_read_interval,
                fan_cooling_effect=fan_cooling,
                room_temp=self.room.temperature
            )
        
        # 5. Evolve environmental parameters
        # Calculate average fan PWM for dust influence
        avg_fan_pwm = sum(self.fan_controller.fans[i+1]['pwm'] for i in range(self.gpu_count)) / self.gpu_count
        
        # Apply environmental controller commands to sensors
        actuator_state = self.environmental_controller.get_state()
        self.humidity_sensor.apply_control(
            actuator_state['dehumidifier_active'],
            actuator_state['dehumidifier_power'],
            actuator_state['humidifier_active'],
            actuator_state['humidifier_power']
        )
        
        # Evolve sensors
        self.humidity_sensor.evolve(delta_time=self.sensor_read_interval)
        self.dust_sensor.evolve(delta_time=self.sensor_read_interval, avg_fan_pwm=avg_fan_pwm)
        
        self.total_readings += 1
        
        # Логируем каждое 6-е чтение 
        if self.total_readings % 6 == 0:
            self._log_current_state()
    
    def _log_current_state(self):
        """Выводит текущее состояние системы в лог"""
        logger.info("─" * 60)
        logger.info(f"📊 Текущее состояние (чтение #{self.total_readings})")
        logger.info(f"🏠 Помещение: {self.room.temperature:.1f}°C")
        
        for i, gpu in enumerate(self.gpus):
            fan_id = i + 1
            fan_state = self.fan_controller.fans[fan_id]
            logger.info(
                f"  GPU {gpu.gpu_id}: {gpu.temperature:.1f}°C "
                f"[Нагрузка: {gpu.workload*100:3.0f}%] | "
                f"Вентилятор: {fan_state['rpm']:4d} RPM (PWM: {fan_state['pwm']:3d}%)"
            )
        
        # Environmental parameters
        logger.info(f"🌡️ Environmental:")
        logger.info(
            f"  Humidity: {self.humidity_sensor.current_humidity:.1f}% "
            f"(target: {self.humidity_sensor.equilibrium_humidity:.1f}%)"  
        )
        logger.info(
            f"  Dust: {self.dust_sensor.current_dust:.1f} μg/m³ "
            f"(status: {self.dust_sensor.get_status_level()})"  
        )
        actuator_state = self.environmental_controller.get_state()
        if actuator_state['dehumidifier_active']:
            logger.info(f"  Dehumidifier: ON ({actuator_state['dehumidifier_power']}%)")
        if actuator_state['humidifier_active']:
            logger.info(f"  Humidifier: ON ({actuator_state['humidifier_power']}%)")
    
    def _create_telemetry_payload(self) -> TelemetryPayload:
        """
        Создаёт пакет телеметрии для отправки
        
        Returns:
            TelemetryPayload готовый к отправке на fog-сервер
        """
        # Собираем температуры GPU
        gpu_temps = [
            GPUTemperature(
                gpu_id=gpu.gpu_id,
                temperature=gpu.get_temperature_with_noise(),
                load=round(gpu.workload * 100, 1)
            )
            for gpu in self.gpus
        ]
        
        # Температура помещения
        room_temp = self.room.get_temperature_with_noise()
        
        # Состояния вентиляторов
        fan_states = self.fan_controller.get_all_fan_states()
        
        # Формируем payload
        payload = TelemetryPayload(
            device_id=self.device_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            sensors=SensorData(
                gpu_temps=gpu_temps,
                room_temp=room_temp
            ),
            fans=FanData(fan_states=fan_states)
        )
        
        return payload
    
    def _create_environmental_payload(self):
        """
        Создаёт пакет environmental telemetry
        
        Returns:
            EnvironmentalPayload готовый к отправке
        """
        # Read sensors
        humidity = self.humidity_sensor.read()
        dust = self.dust_sensor.read()
        
        # Get actuator state
        actuator_state = self.environmental_controller.get_state()
        
        # Create payload
        payload = self.gateway.collect_environmental_telemetry(
            humidity=humidity,
            dust=dust,
            dehumidifier_active=actuator_state['dehumidifier_active'],
            dehumidifier_power=actuator_state['dehumidifier_power'],
            humidifier_active=actuator_state['humidifier_active'],
            humidifier_power=actuator_state['humidifier_power']
        )
        
        return payload
    
    def _send_data(self):
        """
        Отправляет накопленные данные на fog-сервер через ESP32 Gateway
        Вызывается каждые 30 секунд
        """
        payload = self._create_telemetry_payload()
        
        # Отправляем через Gateway
        success = self.gateway.send_telemetry(payload)
        
        if success:
            self.total_sends += 1
            
            # Пытаемся получить команды управления
            commands = self.gateway.receive_commands()
            if commands:
                self._apply_fan_commands(commands)
            
            # Environmental telemetry
            env_payload = self._create_environmental_payload()
            env_success = self.gateway.send_environmental_telemetry(env_payload)
            
            # Receive environmental commands
            env_commands = self.gateway.receive_environmental_commands()
            if env_commands:
                self._apply_environmental_commands(env_commands)
        else:
            self.failed_sends += 1
            logger.warning(f"⚠ Всего неудачных отправок: {self.failed_sends}")
    
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
    
    def _apply_environmental_commands(self, commands: dict):
        """
        Применяет команды управления environmental actuators от fog-сервера
        
        Args:
            commands: Dict с командами
        """
        logger.info(f"🌡️ Применение environmental commands...")
        
        # Apply commands to controller
        self.environmental_controller.apply_command(commands)
        
        # Log status
        logger.info(f"✓ Environmental actuators обновлены")
    
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
        
        # Проверяем доступность fog-сервера
        if not self.gateway.health_check():
            logger.warning("⚠ Fog-сервер недоступен! Эмулятор будет работать, но данные не отправятся.")
            logger.warning("  Убедитесь что fog-сервер запущен на порту 8001")
        
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



    def _check_remote_profile(self):
        """Checks if server requests a profile change"""
        try:
            # Use gateway's client directly to fetch target profile
            target_profile_id = self.gateway.api_client.fetch_system_profile()
            
            if target_profile_id and target_profile_id != self.profile_manager.current_profile.profile_id:
                logger.info(f"🔄 Remote profile change requested: {self.profile_manager.current_profile.profile_id} -> {target_profile_id}")
                self._switch_profile(target_profile_id)
        except Exception as e:
            logger.warning(f"Error checking remote profile: {e}")

    def _switch_profile(self, profile_id: int):
        """Switches to a new environmental profile and resets sensors"""
        try:
            self.profile_manager.switch_profile(profile_id)
            profile = self.profile_manager.current_profile
            
            # Reset sensors to new profile values
            # Assuming sensor classes have reset_to_initial method
            if hasattr(self.humidity_sensor, 'reset_to_initial'):
                self.humidity_sensor.reset_to_initial(
                    profile.humidity_initial, 
                    profile.humidity_equilibrium
                )
                self.humidity_sensor.base_rate = profile.humidity_rate
            
            if hasattr(self.dust_sensor, 'reset_to_initial'):
                self.dust_sensor.reset_to_initial(
                    profile.dust_initial, 
                    profile.dust_equilibrium
                )
                self.dust_sensor.base_rate = profile.dust_rate
            
            # Reset actuators
            if hasattr(self.environmental_controller, 'reset'):
                self.environmental_controller.reset()
                
            logger.info(f"✅ Profile switched to {profile.name} (ID: {profile.profile_id})")
        except Exception as e:
            logger.error(f"Failed to switch profile: {e}")


def main():
    """Точка входа в программу"""
    emulator = ESP32Emulator(config_path="config.yaml")
    emulator.run()


if __name__ == "__main__":
    main()
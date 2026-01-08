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
        logger.info("Инициализация ESP32 Emulator")
        logger.info("=" * 60)
        
        # Загружаем конфигурацию
        self.config = self._load_config(config_path)
        
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
        # 1. Обновляем нагрузку через WorkloadOrchestrator
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
                temperature=gpu.get_temperature_with_noise()
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


def main():
    """Точка входа в программу"""
    emulator = ESP32Emulator(config_path="config.yaml")
    emulator.run()


if __name__ == "__main__":
    main()
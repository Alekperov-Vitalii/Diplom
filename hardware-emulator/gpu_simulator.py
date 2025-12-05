"""
Симулятор физики нагрева/охлаждения GPU
Эмулирует реальное поведение видеокарт под нагрузкой
"""

import random
import numpy as np
from typing import Dict, List


class GPUSimulator:
    """Симулирует одну видеокарту с термодинамикой"""
    
    def __init__(self, gpu_id: int, config: dict):
        self.gpu_id = gpu_id
        self.config = config
        
        # Текущее состояние
        self.temperature = random.uniform(
            config['simulation']['gpu_temp']['idle_min'],
            config['simulation']['gpu_temp']['idle_max']
        )
        
        # Нагрузка на GPU (0.0 = простой, 1.0 = максимальная нагрузка)
        self.workload = random.choice([0.0, 0.3, 0.7, 1.0])
        
        # Целевая температура в зависимости от нагрузки
        self.target_temperature = self._calculate_target_temp()
        
    def _calculate_target_temp(self) -> float:
        """
        Вычисляет целевую температуру на основе нагрузки
        
        Логика:
        - 0% нагрузки → idle температура (35-45°C)
        - 100% нагрузки → максимальная температура (60-85°C)
        - Промежуточные значения интерполируются
        """
        if self.workload < 0.1:  # Практически простой
            return random.uniform(
                self.config['simulation']['gpu_temp']['idle_min'],
                self.config['simulation']['gpu_temp']['idle_max']
            )
        else:
            # Линейная интерполяция между idle и load температурой
            idle_temp = self.config['simulation']['gpu_temp']['idle_max']
            load_temp = random.uniform(
                self.config['simulation']['gpu_temp']['load_min'],
                self.config['simulation']['gpu_temp']['load_max']
            )
            return idle_temp + (load_temp - idle_temp) * self.workload
    
    def update_workload(self):
        """
        Случайное изменение нагрузки на GPU
        Симулирует запуск/остановку вычислительных задач
        """
        if random.random() < self.config['workload']['change_probability']:
            # Меняем нагрузку
            if random.random() < self.config['workload']['high_load_probability']:
                # Высокая нагрузка (mining, rendering)
                self.workload = random.uniform(0.7, 1.0)
            else:
                # Низкая нагрузка или простой
                self.workload = random.choice([0.0, 0.0, 0.3, 0.5])
            
            self.target_temperature = self._calculate_target_temp()
    
    def update_temperature(self, dt: float, fan_cooling_effect: float, room_temp: float):
        """
        Обновляет температуру GPU на основе физики
        
        Args:
            dt: Временной интервал (секунды)
            fan_cooling_effect: Эффект охлаждения от вентилятора (0.0-1.0)
            room_temp: Температура помещения (влияет на охлаждение)
        
        Физика:
        1. Нагрев от нагрузки стремится к target_temperature
        2. Охлаждение от вентилятора (больше PWM = больше охлаждение)
        3. Теплообмен с комнатой (не может остыть ниже room_temp)
        """
        # 1. Естественное стремление к целевой температуре
        if self.temperature < self.target_temperature:
            # Нагрев
            heating_rate = self.config['simulation']['gpu_temp']['heating_rate']
            self.temperature += heating_rate * dt
            self.temperature = min(self.temperature, self.target_temperature)
        elif self.temperature > self.target_temperature:
            # Естественное охлаждение (без вентилятора)
            cooling_rate = self.config['simulation']['gpu_temp']['cooling_rate']
            self.temperature -= cooling_rate * dt * 0.3  # Медленное естественное охлаждение
        
        # 2. Дополнительное охлаждение от вентилятора
        if fan_cooling_effect > 0:
            # Чем больше разница между GPU и комнатой, тем эффективнее охлаждение
            temp_diff = self.temperature - room_temp
            if temp_diff > 0:
                cooling_rate = self.config['simulation']['gpu_temp']['cooling_rate']
                fan_cooling = cooling_rate * fan_cooling_effect * dt * (temp_diff / 50.0)
                self.temperature -= fan_cooling
        
        # 3. Не может остыть ниже комнатной температуры + небольшой offset
        min_temp = room_temp + 5.0  # GPU всегда немного теплее комнаты
        self.temperature = max(self.temperature, min_temp)
        
        # 4. Физический предел перегрева (safety)
        self.temperature = min(self.temperature, 130.0)
    
    def get_temperature_with_noise(self) -> float:
        """
        Возвращает температуру с шумом датчика
        DS18B20 имеет точность ±0.5°C, добавляем реалистичный шум
        """
        noise = np.random.normal(0, self.config['simulation']['sensor_noise'])
        return round(self.temperature + noise, 1)


class RoomSimulator:
    """Симулятор температуры помещения"""
    
    def __init__(self, config: dict):
        self.config = config
        self.temperature = config['simulation']['room_temp']['base']
        self.base_temp = config['simulation']['room_temp']['base']
    
    def update(self, gpu_heat_contribution: float):
        """
        Обновляет температуру помещения
        
        Args:
            gpu_heat_contribution: Суммарный нагрев от всех GPU (0.0-8.0)
        
        Логика:
        - Каждый горячий GPU повышает температуру комнаты
        - Комната медленно остывает к базовой температуре
        """
        # Нагрев от GPU (каждый горячий GPU добавляет 0.2°C к комнате)
        target_increase = gpu_heat_contribution * 0.25
        
        # Медленное движение к целевой температуре
        variation = self.config['simulation']['room_temp']['variation']
        target_temp = self.base_temp + min(target_increase, variation)
        
        # Инерционное изменение (комната медленно нагревается/остывает)
        if self.temperature < target_temp:
            self.temperature += 0.02  # Очень медленный нагрев
        elif self.temperature > target_temp:
            self.temperature -= 0.05  # Немного быстрее остывание
        
        self.temperature = round(self.temperature, 1)
    
    def get_temperature_with_noise(self) -> float:
        """Температура комнаты с небольшим шумом"""
        noise = np.random.normal(0, 0.2)
        return round(self.temperature + noise, 1)
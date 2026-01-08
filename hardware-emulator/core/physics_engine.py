"""
Физический движок для симуляции нагрева и охлаждения GPU
Отделен от датчиков - работает с истинными физическими значениями
"""

from typing import Dict, Any


class GPUPhysicsEngine:
    """
    Моделирует физическое поведение GPU (нагрев/охлаждение)
    Не знает о датчиках - возвращает истинные физические значения
    """
    
    def __init__(self, gpu_id: int, config: Dict[str, Any]):
        """
        Args:
            gpu_id: ID видеокарты
            config: Конфигурация из config.yaml
        """
        self.gpu_id = gpu_id
        self.config = config
        
        # Текущее физическое состояние
        self.temperature = self._get_initial_temperature()
        self.workload = 0.0  # 0.0 = idle, 1.0 = full load
        self.target_temperature = self.temperature
    
    def _get_initial_temperature(self) -> float:
        """Начальная температура GPU (idle)"""
        import random
        return random.uniform(
            self.config['simulation']['gpu_temp']['idle_min'],
            self.config['simulation']['gpu_temp']['idle_max']
        )
    
    def set_workload(self, workload: float):
        """
        Устанавливает нагрузку на GPU
        
        Args:
            workload: Нагрузка от 0.0 (idle) до 1.0 (full)
        """
        self.workload = max(0.0, min(1.0, workload))
        self.target_temperature = self._calculate_target_temperature()
    
    def _calculate_target_temperature(self) -> float:
        """
        Вычисляет целевую температуру на основе нагрузки
        
        Returns:
            Целевая температура в °C
        """
        if self.workload < 0.1:
            # Практически idle
            import random
            return random.uniform(
                self.config['simulation']['gpu_temp']['idle_min'],
                self.config['simulation']['gpu_temp']['idle_max']
            )
        else:
            # Линейная интерполяция между idle и load
            idle_temp = self.config['simulation']['gpu_temp']['idle_max']
            import random
            load_temp = random.uniform(
                self.config['simulation']['gpu_temp']['load_min'],
                self.config['simulation']['gpu_temp']['load_max']
            )
            return idle_temp + (load_temp - idle_temp) * self.workload
    
    def update(self, dt: float, cooling_effect: float, ambient_temp: float) -> float:
        """
        Обновляет физическое состояние GPU
        
        Args:
            dt: Временной интервал (секунды)
            cooling_effect: Эффект охлаждения от вентилятора (0.0-1.0)
            ambient_temp: Температура окружающей среды (комнаты)
        
        Returns:
            Новая истинная температура GPU
        """
        # 1. Естественное стремление к целевой температуре
        if self.temperature < self.target_temperature:
            # Нагрев
            heating_rate = self.config['simulation']['gpu_temp']['heating_rate']
            self.temperature += heating_rate * dt
            self.temperature = min(self.temperature, self.target_temperature)
        elif self.temperature > self.target_temperature:
            # Естественное охлаждение (медленное)
            cooling_rate = self.config['simulation']['gpu_temp']['cooling_rate']
            self.temperature -= cooling_rate * dt * 0.3
        
        # 2. Дополнительное охлаждение от вентилятора
        if cooling_effect > 0:
            temp_diff = self.temperature - ambient_temp
            if temp_diff > 0:
                cooling_rate = self.config['simulation']['gpu_temp']['cooling_rate']
                fan_cooling = cooling_rate * cooling_effect * dt * (temp_diff / 50.0)
                self.temperature -= fan_cooling
        
        # 3. Физические ограничения
        min_temp = ambient_temp + 5.0  # GPU всегда теплее комнаты
        self.temperature = max(self.temperature, min_temp)
        self.temperature = min(self.temperature, 130.0)  # Safety limit
        
        return self.temperature
    
    def get_temperature(self) -> float:
        """Возвращает текущую истинную температуру"""
        return self.temperature
    
    def get_workload(self) -> float:
        """Возвращает текущую нагрузку"""
        return self.workload


class RoomPhysicsEngine:
    """
    Моделирует физику помещения (температура окружающей среды)
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.temperature = config['simulation']['room_temp']['base']
        self.base_temp = config['simulation']['room_temp']['base']
    
    def update(self, gpu_heat_contribution: float):
        """
        Обновляет температуру помещения
        
        Args:
            gpu_heat_contribution: Суммарный вклад от всех GPU (0.0-N)
        """
        # Нагрев от GPU
        target_increase = gpu_heat_contribution * 0.25
        variation = self.config['simulation']['room_temp']['variation']
        target_temp = self.base_temp + min(target_increase, variation)
        
        # Инерционное изменение
        if self.temperature < target_temp:
            self.temperature += 0.02  # Медленный нагрев
        elif self.temperature > target_temp:
            self.temperature -= 0.05  # Быстрее остывание
        
        self.temperature = round(self.temperature, 1)
    
    def get_temperature(self) -> float:
        """Возвращает текущую температуру помещения"""
        return self.temperature

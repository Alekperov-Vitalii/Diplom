import random
from .base import BasePhysicsEngine

class HumidityPhysicsEngine(BasePhysicsEngine):
    """
    Физическая модель влажности.
    
    Факторы влияния:
    1. Вентиляция (выравнивает с внешней средой)
    2. Температура (рост температуры -> снижение относительной влажности)
    3. Активные устройства (Увлажнитель/Осушитель)
    4. Случайные флуктуации
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.value = 45.0  # Начальная влажность (%)
        self.target_value = 45.0
        
        # Конфигурация
        self.external_humidity = 50.0  # Влажность снаружи
        self.room_volume = 100.0  # Условный объем помещения
        
    def update(self, dt: float, temperature: float, ventilation_rate: float, 
               humidifier_on: bool, dehumidifier_on: bool):
        """
        Обновляет влажность.
        
        Args:
            dt: Время шага (сек)
            temperature: Текущая температура помещения (°C)
            ventilation_rate: Уровень вентиляции (0.0 - 1.0)
            humidifier_on: Включен ли увлажнитель
            dehumidifier_on: Включен ли осушитель
        """
        
        # 1. Влияние вентиляции (стремится к внешней влажности)
        # Чем выше ventilation_rate, тем быстрее стремимся
        vent_factor = ventilation_rate * 0.1 * dt
        diff = self.external_humidity - self.value
        self.value += diff * vent_factor
        
        # 2. Влияние температуры
        # (Упрощенно: нагрев сушит воздух, т.е. снижает относительную влажность)
        # Эмулируем это как небольшое падение при высокой температуре
        if temperature > 25.0:
            dry_factor = (temperature - 25.0) * 0.05 * dt
            self.value -= dry_factor
            
        # 3. Активные устройства
        if humidifier_on:
            self.value += 2.0 * dt  # Увлажнитель мощный
        elif dehumidifier_on:
            self.value -= 2.0 * dt  # Осушитель мощный
            
        # 4. Случайные флуктуации (броуновское движение)
        noise = random.uniform(-0.1, 0.1) * dt
        self.value += noise
        
        # Ограничения физики (0-100%)
        self.value = max(10.0, min(95.0, self.value))
        
    def get_value(self) -> float:
        return self.value

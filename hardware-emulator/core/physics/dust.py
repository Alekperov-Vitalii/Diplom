import random
from .base import BasePhysicsEngine

class DustPhysicsEngine(BasePhysicsEngine):
    """
    Физическая модель накопления плыи.
    
    Факторы влияния:
    1. Накопление со временем (естественная пыль)
    2. Поток воздуха (чем сильнее работают вентиляторы, тем больше пыли засасывается)
    3. Очиститель воздуха (фильтрация)
    """
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.value = 10.0  # ug/m3 (чистый воздух)
        
        self.base_accumulation_rate = 0.5 # ug/m3 в минуту
        
    def update(self, dt: float, avg_fan_rpm: float, air_purifier_on: bool):
        """
        Обновляет уровень пыли.
        
        Args:
            dt: Время шага (сек)
            avg_fan_rpm: Средние обороты вентиляторов (влияет на приток пыли)
            air_purifier_on: Включен ли очиститель
        """
        
        # 1. Естественное накопление + Влияние вентиляторов
        # Нормализуем RPM (0..5000 -> 0..1.0)
        airflow_factor = avg_fan_rpm / 5000.0
        
        # Чем выше RPM, тем больше пыли залетает (если нет фильтров на входе :))
        accumulation = (self.base_accumulation_rate + (airflow_factor * 2.0)) * (dt / 60.0)
        self.value += accumulation
        
        # 2. Очиститель воздуха
        if air_purifier_on:
            # Очиститель снижает пыль экспоненциально
            cleaning_rate = 0.1 * dt # 10% в секунду
            self.value *= (1.0 - cleaning_rate)
            
        # 3. Случайный шум
        self.value += random.uniform(-0.05, 0.05)
        
        # Ограничения (всегда > 0)
        self.value = max(0.0, self.value)
        
    def get_value(self) -> float:
        return self.value

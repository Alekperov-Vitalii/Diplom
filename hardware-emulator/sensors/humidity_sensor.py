import random
from .base_sensor import BaseSensor

class HumiditySensor(BaseSensor):
    """
    Датчик влажности (аналог DHT22)
    """
    
    def __init__(self, sensor_id: str, config: dict):
        super().__init__(sensor_id, config)
        self.resolution = 0.1
        self.noise = 0.5 # % (погрешность)
        
    def read(self, true_value: float) -> float:
        """
        Читает показания с добавлением шума
        """
        noise = random.normalvariate(0, self.noise)
        value = true_value + noise
        
        # Округление до разрешения
        value = round(value / self.resolution) * self.resolution
        return max(0.0, min(100.0, value))

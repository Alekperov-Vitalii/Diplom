import random
from .base_sensor import BaseSensor

class DustSensor(BaseSensor):
    """
    Датчик пыли (аналог GP2Y1010AU0F / PMS5003)
    Измеряет концентрацию в ug/m3
    """
    
    def __init__(self, sensor_id: str, config: dict):
        super().__init__(sensor_id, config)
        self.resolution = 1.0
        self.noise = 2.0 # ug/m3 (погрешность)
        
    def read(self, true_value: float) -> float:
        """
        Читает показания с добавлением шума
        """
        noise = random.normalvariate(0, self.noise)
        value = true_value + noise
        
        # Округление
        value = round(value / self.resolution) * self.resolution
        return max(0.0, value)

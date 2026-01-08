"""
Контроллер вентиляторов
Эмулирует MOSFET управление 4-pin PWM вентиляторами
"""

from typing import Dict, List
from models import FanState


class FanController:
    """Управление вентиляторами через PWM"""
    
    def __init__(self, fan_count: int, config: dict):
        self.fan_count = fan_count
        self.config = config
        
        # Текущее состояние каждого вентилятора
        # Словарь: {fan_id: {"pwm": 0-100, "rpm": 800-5000}}
        self.fans: Dict[int, Dict[str, int]] = {}
        
        # Инициализация: все вентиляторы на минимальных оборотах
        for fan_id in range(1, fan_count + 1):
            self.fans[fan_id] = {
                "pwm": 20,  # 20% PWM = минимальные обороты
                "rpm": self._calculate_rpm(20)
            }
    
    def _calculate_rpm(self, pwm_duty: int) -> int:
        """
        Вычисляет RPM на основе PWM duty cycle
        
        Args:
            pwm_duty: PWM в процентах (0-100)
        
        Returns:
            Обороты в минуту (RPM)
        
        Логика:
        - 0% PWM → вентилятор все равно крутится на минимуме (800 RPM)
        - 100% PWM → максимум (5000 RPM)
        - Линейная зависимость между ними
        """
        rpm_min = self.config['fans']['rpm_min']
        rpm_max = self.config['fans']['rpm_max']
        
        if pwm_duty <= 0:
            return rpm_min
        
        # Линейная интерполяция
        rpm_range = rpm_max - rpm_min
        rpm = rpm_min + (rpm_range * pwm_duty / 100.0)
        
        return int(rpm)
    
    def set_fan_pwm(self, fan_id: int, pwm_duty: int):
        """
        Устанавливает PWM для конкретного вентилятора
        Это метод вызывается когда fog-сервер отправляет команду
        
        Args:
            fan_id: ID вентилятора (1-8)
            pwm_duty: Желаемый PWM (0-100%)
        """
        if fan_id not in self.fans:
            raise ValueError(f"Fan ID {fan_id} не существует")
        
        # Ограничиваем PWM диапазоном 0-100
        pwm_duty = max(0, min(100, pwm_duty))
        
        self.fans[fan_id]["pwm"] = pwm_duty
        self.fans[fan_id]["rpm"] = self._calculate_rpm(pwm_duty)
    
    def get_fan_cooling_effect(self, fan_id: int) -> float:
        """
        Возвращает эффект охлаждения вентилятора (0.0-1.0)
        Используется в GPUSimulator для расчета охлаждения
        
        Returns:
            0.0 = нет охлаждения
            1.0 = максимальное охлаждение
        """
        pwm = self.fans[fan_id]["pwm"]
        return pwm / 100.0
    
    def get_all_fan_states(self) -> List[FanState]:
        """
        Возвращает состояния всех вентиляторов
        Формат для отправки в телеметрии на fog-сервер
        """
        fan_states = []
        for fan_id in sorted(self.fans.keys()):
            fan_states.append(FanState(
                fan_id=fan_id,
                rpm=self.fans[fan_id]["rpm"],
                pwm_duty=self.fans[fan_id]["pwm"]
            ))
        return fan_states
    
    def apply_command_batch(self, commands: List[dict]):
        """
        Применяет пакет команд от fog-сервера
        
        Args:
            commands: Список словарей [{"fan_id": 1, "pwm_duty": 75}, ...]
        """
        for cmd in commands:
            fan_id = cmd.get("fan_id")
            pwm_duty = cmd.get("pwm_duty")
            
            if fan_id and pwm_duty is not None:
                self.set_fan_pwm(fan_id, pwm_duty)
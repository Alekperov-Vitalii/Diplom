"""
Профили нагрузки для реалистичной симуляции ML задач в датацентре
"""

import random
import time
from typing import List, Dict, Any
from enum import Enum


class WorkloadType(Enum):
    """Типы ML нагрузки"""
    TRAINING = "training"          # Обучение модели (циклическое)
    INFERENCE = "inference"        # Inference serving (стабильное)
    IDLE = "idle"                  # Простой
    VALIDATION = "validation"      # Валидация (периодическое)


class MLWorkloadProfile:
    """
    Базовый класс для профилей ML нагрузки
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.start_time = time.time()
    
    def get_workload(self) -> float:
        """
        Возвращает текущую нагрузку (0.0-1.0)
        Должен быть переопределен в наследниках
        """
        raise NotImplementedError


class TrainingWorkloadProfile(MLWorkloadProfile):
    """
    Профиль для distributed training
    
    Характеристики:
    - Циклы эпох (warmup → training → validation)
    - Высокая стабильная нагрузка во время обучения
    - Короткие периоды валидации
    """
    
    def __init__(self, config: Dict[str, Any], epoch_duration: int = 300, 
                 validation_interval: int = 60):
        super().__init__(config)
        self.epoch_duration = epoch_duration  # секунды
        self.validation_interval = validation_interval
        self.validation_duration = 10  # секунды
        
    def get_workload(self) -> float:
        """Возвращает нагрузку в зависимости от фазы обучения"""
        elapsed = time.time() - self.start_time
        cycle_time = elapsed % self.epoch_duration
        
        # Фаза warmup (первые 30 секунд эпохи)
        if cycle_time < 30:
            # Постепенное нарастание нагрузки
            warmup_progress = cycle_time / 30.0
            return 0.3 + (0.7 * warmup_progress)  # 30% → 100%
        
        # Проверяем, не время ли валидации
        time_since_last_validation = cycle_time % self.validation_interval
        if time_since_last_validation < self.validation_duration:
            # Валидация: средняя нагрузка
            return random.uniform(0.5, 0.7)
        
        # Основное обучение: высокая стабильная нагрузка
        return random.uniform(0.85, 1.0)


class InferenceWorkloadProfile(MLWorkloadProfile):
    """
    Профиль для inference serving
    
    Характеристики:
    - Стабильная средняя нагрузка
    - Периодические пики (burst requests)
    - Небольшие вариации
    """
    
    def __init__(self, config: Dict[str, Any], base_load: float = 0.6,
                 variation: float = 0.2):
        super().__init__(config)
        self.base_load = base_load
        self.variation = variation
        self.last_spike_time = 0
        self.spike_duration = 15  # секунды
    
    def get_workload(self) -> float:
        """Возвращает нагрузку с периодическими пиками"""
        current_time = time.time()
        
        # Случайные пики нагрузки (каждые ~2 минуты)
        if current_time - self.last_spike_time > random.uniform(100, 140):
            self.last_spike_time = current_time
        
        # Проверяем, в пике ли мы сейчас
        if current_time - self.last_spike_time < self.spike_duration:
            # Пик: высокая нагрузка
            return random.uniform(0.85, 1.0)
        
        # Обычная работа: стабильная средняя нагрузка
        return self.base_load + random.uniform(-self.variation, self.variation)


class IdleWorkloadProfile(MLWorkloadProfile):
    """
    Профиль простоя
    Минимальная нагрузка с редкими всплесками
    """
    
    def get_workload(self) -> float:
        """Возвращает минимальную нагрузку"""
        # 95% времени - простой, 5% - небольшая активность
        if random.random() < 0.05:
            return random.uniform(0.2, 0.4)
        return random.uniform(0.0, 0.1)


class WorkloadOrchestrator:
    """
    Управляет распределением нагрузки между группами GPU
    Обеспечивает корреляцию нагрузки внутри групп
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.groups: Dict[str, Dict[str, Any]] = {}
        self._setup_groups()
    
    def _setup_groups(self):
        """Настраивает группы GPU из конфигурации"""
        workload_config = self.config.get('workload_profiles', {}).get('datacenter_ml', {})
        
        if not workload_config.get('enabled', False):
            # Если профили отключены, используем старую логику
            return
        
        # Группа 1: Training
        group_1 = workload_config.get('group_1', {})
        if group_1:
            self.groups['group_1'] = {
                'gpus': group_1.get('gpus', []),
                'profile': TrainingWorkloadProfile(
                    self.config,
                    epoch_duration=group_1.get('epoch_duration', 300),
                    validation_interval=group_1.get('validation_interval', 60)
                )
            }
        
        # Группа 2: Inference
        group_2 = workload_config.get('group_2', {})
        if group_2:
            self.groups['group_2'] = {
                'gpus': group_2.get('gpus', []),
                'profile': InferenceWorkloadProfile(
                    self.config,
                    variation=group_2.get('load_variation', 0.2)
                )
            }
    
    def get_workload_for_gpu(self, gpu_id: int) -> float:
        """
        Возвращает нагрузку для конкретной GPU
        
        Args:
            gpu_id: ID видеокарты
        
        Returns:
            Нагрузка от 0.0 до 1.0
        """
        # Ищем, к какой группе принадлежит GPU
        for group_name, group_data in self.groups.items():
            if gpu_id in group_data['gpus']:
                return group_data['profile'].get_workload()
        
        # Если GPU не в группе, используем idle профиль
        idle_profile = IdleWorkloadProfile(self.config)
        return idle_profile.get_workload()
    
    def should_update_workload(self) -> bool:
        """
        Определяет, нужно ли обновлять нагрузку
        Для ML профилей обновляем каждый цикл (они сами управляют фазами)
        """
        if self.groups:
            return True  # ML профили активны
        
        # Старая логика: случайное изменение
        change_prob = self.config.get('workload', {}).get('change_probability', 0.3)
        return random.random() < change_prob

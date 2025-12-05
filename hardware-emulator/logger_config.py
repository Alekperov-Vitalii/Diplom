"""
Конфигурация логирования с цветным выводом
Помогает визуально отслеживать работу эмулятора
"""

import logging
import sys
from colorama import Fore, Style, init

# Инициализация colorama для Windows
init(autoreset=True)


class ColoredFormatter(logging.Formatter):
    """Форматтер с цветным выводом для разных уровней логов"""
    
    # Цвета для разных уровней
    COLORS = {
        'DEBUG': Fore.CYAN,
        'INFO': Fore.GREEN,
        'WARNING': Fore.YELLOW,
        'ERROR': Fore.RED,
        'CRITICAL': Fore.RED + Style.BRIGHT,
    }
    
    def format(self, record):
        # Добавляем цвет к уровню лога
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{Style.RESET_ALL}"
        
        return super().format(record)


def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Настраивает логгер с цветным выводом
    
    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR)
    
    Returns:
        Настроенный logger
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Проверяем, не добавлены ли уже handlers (избегаем дублирования)
    if logger.handlers:
        return logger
    
    # Handler для вывода в консоль
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Формат: [2024-12-02 15:30:45] INFO: Сообщение
    formatter = ColoredFormatter(
        fmt='[%(asctime)s] %(levelname)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    return logger
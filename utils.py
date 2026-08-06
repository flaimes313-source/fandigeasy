import logging
import sys
from datetime import datetime
from pathlib import Path
from config import Config

def setup_logging():
    """Настройка логирования"""
    log_level = getattr(logging, Config.LOG_LEVEL.upper(), logging.INFO)
    
    # Создаем папку для логов если её нет
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / Config.LOG_FILE
    
    # Настройка форматирования
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Handler для файла
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(formatter)
    
    # Handler для консоли
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    return root_logger

def format_timestamp(timestamp: int) -> str:
    """Форматировать timestamp в читаемый вид"""
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def calculate_slippage(price: float, volume: float) -> float:
    """Рассчитать примерное проскальзывание"""
    # Примерная формула для оценки проскальзывания
    if volume < 100000:
        return 0.005  # 0.5%
    elif volume < 1000000:
        return 0.002  # 0.2%
    else:
        return 0.001  # 0.1%

def safe_float(value, default=0.0):
    """Безопасное преобразование в float"""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default

def format_currency(amount: float) -> str:
    """Форматировать сумму в USD"""
    if abs(amount) >= 1000:
        return f"${amount:,.2f}"
    elif abs(amount) >= 1:
        return f"${amount:.2f}"
    else:
        return f"${amount:.4f}"

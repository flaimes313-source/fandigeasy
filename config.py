import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Пробуем загрузить .env из разных мест
def load_env_file():
    """Загрузить .env файл из разных возможных мест"""
    possible_paths = [
        Path('.env'),                    # Текущая папка
        Path('/app/.env'),               # Docker
        Path('/home/runner/.env'),       # GitHub Actions
        Path(os.path.dirname(__file__)) / '.env',  # Папка с config.py
        Path(os.getcwd()) / '.env',      # Рабочая папка
    ]
    
    for env_path in possible_paths:
        if env_path.exists():
            print(f"✅ Загружаем .env из: {env_path}")
            load_dotenv(env_path)
            return True
    
    print("⚠️ Файл .env не найден, пробуем загрузить из переменных окружения")
    return False

# Загружаем .env
load_env_file()

class Config:
    # Telegram Bot - пробуем из переменных окружения
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
    
    # Если токен не найден, пробуем прочитать .env вручную
    if not TELEGRAM_TOKEN:
        try:
            env_file = Path('.env')
            if env_file.exists():
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('TELEGRAM_TOKEN='):
                            TELEGRAM_TOKEN = line.split('=')[1].strip()
                            print(f"✅ Токен загружен из .env: {TELEGRAM_TOKEN[:10]}...")
                            break
        except Exception as e:
            print(f"⚠️ Ошибка чтения .env: {e}")
    
    # Bybit settings
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
    BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET', '')
    
    # Filter settings
    MIN_FUNDING_RATE = float(os.getenv('MIN_FUNDING_RATE', '0.02'))
    MAX_MINUTES_TO_FUNDING = int(os.getenv('MAX_MINUTES_TO_FUNDING', '10'))
    MIN_VOLUME_USD = int(os.getenv('MIN_VOLUME_USD', '100000'))
    
    # Notification settings
    NOTIFY_NEAR_FUNDING = os.getenv('NOTIFY_NEAR_FUNDING', 'true').lower() == 'true'
    NEAR_MINUTES_THRESHOLD = int(os.getenv('NEAR_MINUTES_THRESHOLD', '60'))
    
    # Commission rates
    SPOT_MAKER_FEE = float(os.getenv('SPOT_MAKER_FEE', '0.1'))
    SPOT_TAKER_FEE = float(os.getenv('SPOT_TAKER_FEE', '0.1'))
    FUTURES_MAKER_FEE = float(os.getenv('FUTURES_MAKER_FEE', '0.02'))
    FUTURES_TAKER_FEE = float(os.getenv('FUTURES_TAKER_FEE', '0.055'))
    
    # Scan interval
    SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', '30'))
    
    # Default amounts for quick selection
    QUICK_AMOUNTS = [100, 250, 500, 1000]
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'funding_bot.log')
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_TOKEN or cls.TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError(
                "TELEGRAM_TOKEN not set! Please add your bot token to .env file "
                "or set environment variable TELEGRAM_TOKEN"
            )
        return True
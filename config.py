import os
from dotenv import load_dotenv
from pathlib import Path

env_path = Path('.') / '.env'
load_dotenv(dotenv_path=env_path)

class Config:
    # Telegram Bot
    TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', 'YOUR_BOT_TOKEN_HERE')
    
    # Bybit settings
    BYBIT_API_KEY = os.getenv('BYBIT_API_KEY', '')
    BYBIT_API_SECRET = os.getenv('BYBIT_API_SECRET', '')
    
    # Filter settings
    MIN_FUNDING_RATE = float(os.getenv('MIN_FUNDING_RATE', 0.02))
    MAX_MINUTES_TO_FUNDING = int(os.getenv('MAX_MINUTES_TO_FUNDING', 10))
    MIN_VOLUME_USD = int(os.getenv('MIN_VOLUME_USD', 100000))  # Снижено для теста
    
    # Notification settings
    NOTIFY_NEAR_FUNDING = os.getenv('NOTIFY_NEAR_FUNDING', 'true').lower() == 'true'
    NEAR_MINUTES_THRESHOLD = int(os.getenv('NEAR_MINUTES_THRESHOLD', 60))
    
    # Commission rates
    SPOT_MAKER_FEE = float(os.getenv('SPOT_MAKER_FEE', 0.1))
    SPOT_TAKER_FEE = float(os.getenv('SPOT_TAKER_FEE', 0.1))
    FUTURES_MAKER_FEE = float(os.getenv('FUTURES_MAKER_FEE', 0.02))
    FUTURES_TAKER_FEE = float(os.getenv('FUTURES_TAKER_FEE', 0.055))
    
    # Scan interval
    SCAN_INTERVAL = int(os.getenv('SCAN_INTERVAL', 30))
    
    # Default amounts for quick selection
    QUICK_AMOUNTS = [100, 250, 500, 1000]
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', 'funding_bot.log')
    
    @classmethod
    def validate(cls):
        if not cls.TELEGRAM_TOKEN or cls.TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            raise ValueError(
                "TELEGRAM_TOKEN not set! Please add your bot token to .env file"
            )
        return True
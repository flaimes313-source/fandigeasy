import logging
import asyncio
from config import Config
from telegram_handlers import TelegramHandler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    try:
        # Создаем и запускаем бота
        bot = TelegramHandler(Config.TELEGRAM_TOKEN)
        await bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
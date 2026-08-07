#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import asyncio
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from telegram_handlers import TelegramHandler
from utils import setup_logging

logger = setup_logging()

async def main():
    """Главная функция запуска бота"""
    try:
        logger.info("=" * 50)
        logger.info("🚀 Funding Arbitrage Bot v1.0.0")
        logger.info("=" * 50)
        
        if not Config.TELEGRAM_TOKEN or Config.TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            logger.error("❌ TELEGRAM_TOKEN не установлен!")
            return
        
        logger.info("📱 Инициализация Telegram бота...")
        bot = TelegramHandler(Config.TELEGRAM_TOKEN)
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info("🚀 Запуск бота...")
        
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("⏹ Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        logger.info("👋 Бот завершил работу")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
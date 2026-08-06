#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import asyncio
import logging
import time
from pathlib import Path
from telegram import Bot
from telegram.error import Conflict

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from telegram_handlers import TelegramHandler
from utils import setup_logging

logger = setup_logging()

async def clear_webhook_with_retry(max_retries=3):
    """Очистить webhook с повторными попытками"""
    for attempt in range(max_retries):
        try:
            bot = Bot(token=Config.TELEGRAM_TOKEN)
            webhook_info = await bot.get_webhook_info()
            if webhook_info.url:
                logger.info(f"🔄 Удаление webhook: {webhook_info.url}")
                await bot.delete_webhook()
                logger.info("✅ Webhook удален")
            else:
                logger.info("✅ Webhook не установлен")
            
            # Очищаем ожидающие обновления
            await bot.get_updates(offset=-1, timeout=1)
            return True
        except Conflict as e:
            logger.warning(f"⚠️ Конфликт при очистке (попытка {attempt + 1}/{max_retries}): {e}")
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            else:
                logger.error("❌ Не удалось очистить webhook")
                return False
        except Exception as e:
            logger.error(f"❌ Ошибка очистки webhook: {e}")
            return False

async def main():
    """Главная функция запуска бота"""
    try:
        logger.info("=" * 50)
        logger.info("🚀 Funding Arbitrage Bot v1.0.0")
        logger.info("=" * 50)
        
        # Проверка токена
        if not Config.TELEGRAM_TOKEN or Config.TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN_HERE':
            logger.error("❌ TELEGRAM_TOKEN не установлен!")
            logger.error("Пожалуйста, добавьте токен в файл .env")
            return
        
        # Очищаем webhook перед запуском
        if not await clear_webhook_with_retry():
            logger.warning("⚠️ Не удалось очистить webhook, но продолжаем...")
        
        logger.info("📱 Инициализация Telegram бота...")
        bot = TelegramHandler(Config.TELEGRAM_TOKEN)
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info("🚀 Запуск бота...")
        
        # Запускаем бота с обработкой конфликтов
        try:
            await bot.run()
        except Conflict as e:
            logger.error(f"❌ Конфликт при запуске: {e}")
            logger.info("💡 Решение:")
            logger.info("1. Остановите все другие экземпляры бота")
            logger.info("2. Запустите: python force_stop.py")
            logger.info("3. Затем запустите бота заново")
            
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
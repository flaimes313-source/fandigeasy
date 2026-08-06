#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Funding Arbitrage Bot - Главный файл запуска
Telegram бот для мониторинга положительного фандинга на Bybit
"""

import sys
import asyncio
import logging
from pathlib import Path

# Добавляем текущую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from telegram_handlers import TelegramHandler
from utils import setup_logging

# Настройка логирования
logger = setup_logging()

def check_environment():
    """Проверка окружения перед запуском"""
    issues = []
    
    # Проверяем наличие токена
    if not Config.TELEGRAM_TOKEN or Config.TELEGRAM_TOKEN == 'YOUR_BOT_TOKEN_HERE':
        issues.append("❌ TELEGRAM_TOKEN не установлен в файле .env")
        issues.append("   Получите токен у @BotFather в Telegram")
    
    # Проверяем наличие файла .env
    env_file = Path('.env')
    if not env_file.exists():
        issues.append("❌ Файл .env не найден")
        issues.append("   Создайте .env файл из .env.example")
    
    if issues:
        logger.error("=" * 50)
        for issue in issues:
            logger.error(issue)
        logger.error("=" * 50)
        return False
    
    logger.info("✅ Проверка окружения пройдена успешно")
    return True

def show_banner():
    """Показать баннер при запуске"""
    banner = """
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║   🚀 Funding Arbitrage Bot v1.0.0                    ║
║                                                       ║
║   📊 Анализ фандинга на Bybit                       ║
║   🤖 Telegram бот для арбитража                     ║
║                                                       ║
╚═══════════════════════════════════════════════════════╝
    """
    logger.info(banner)
    
    # Показываем настройки
    logger.info("📋 Текущие настройки:")
    logger.info(f"  • Минимальный фандинг: {Config.MIN_FUNDING_RATE}%")
    logger.info(f"  • Макс время до выплаты: {Config.MAX_MINUTES_TO_FUNDING} мин")
    logger.info(f"  • Минимальный объем: ${Config.MIN_VOLUME_USD:,.0f}")
    logger.info(f"  • Интервал сканирования: {Config.SCAN_INTERVAL} сек")
    logger.info("")
    logger.info(f"  • Спот комиссия: {Config.SPOT_MAKER_FEE}% (покупка) + {Config.SPOT_TAKER_FEE}% (продажа)")
    logger.info(f"  • Фьючерс комиссия: {Config.FUTURES_MAKER_FEE}% (открытие) + {Config.FUTURES_TAKER_FEE}% (закрытие)")
    logger.info("=" * 50)

async def main():
    """Главная функция запуска бота"""
    try:
        # Показываем баннер
        show_banner()
        
        # Проверка окружения
        if not check_environment():
            logger.error("❌ Проверка окружения не пройдена. Бот остановлен.")
            logger.info("")
            logger.info("📝 Инструкция по настройке:")
            logger.info("1. Создайте файл .env из .env.example")
            logger.info("2. Добавьте TELEGRAM_TOKEN=ваш_токен_бота")
            logger.info("3. Токен можно получить у @BotFather в Telegram")
            return
        
        logger.info("📱 Инициализация Telegram бота...")
        
        # Создаем обработчик Telegram
        bot = TelegramHandler(Config.TELEGRAM_TOKEN)
        
        logger.info("✅ Бот успешно инициализирован")
        logger.info("")
        logger.info("🚀 Запуск бота...")
        logger.info("⏳ Ожидайте уведомлений о найденных кандидатах")
        logger.info("=" * 50)
        logger.info("")
        
        # Запускаем бота
        await bot.run()
        
    except KeyboardInterrupt:
        logger.info("")
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
        # Запускаем основную функцию
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⏹ Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
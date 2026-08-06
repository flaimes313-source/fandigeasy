import asyncio
import logging
from typing import List, Dict
from exchange import BybitExchange
from config import Config

logger = logging.getLogger(__name__)

class Scanner:
    def __init__(self):
        self.exchange = BybitExchange()
        self.callbacks = []
        self.is_running = False

    def add_callback(self, callback):
        """Добавить callback для уведомления о найденных кандидатах"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    async def scan(self):
        """Выполнить сканирование"""
        try:
            logger.debug("Starting scan for funding opportunities...")
            candidates = self.exchange.get_funding_candidates()
            
            if candidates:
                logger.info(f"✅ Found {len(candidates)} candidates")
                # Отправляем только топ-5 кандидатов
                for callback in self.callbacks:
                    await callback(candidates[:5])
            else:
                logger.debug("No candidates found")
                
        except Exception as e:
            logger.error(f"Error during scan: {e}")

    async def start_scanning(self):
        """Запустить непрерывное сканирование"""
        if self.is_running:
            logger.warning("Scanner already running")
            return
            
        self.is_running = True
        logger.info(f"🔄 Scanner started with interval {Config.SCAN_INTERVAL} seconds")
        
        while self.is_running:
            await self.scan()
            await asyncio.sleep(Config.SCAN_INTERVAL)
        
        logger.info("Scanner stopped")

    def stop(self):
        """Остановить сканер"""
        self.is_running = False
        logger.info("Scanner stopping...")
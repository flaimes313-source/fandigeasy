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

    def add_callback(self, callback):
        """Добавить callback для уведомления о найденных кандидатах"""
        self.callbacks.append(callback)

    async def scan(self):
        """Выполнить сканирование"""
        try:
            logger.info("Starting scan for funding opportunities...")
            candidates = self.exchange.get_funding_candidates()
            
            if candidates:
                logger.info(f"Found {len(candidates)} candidates")
                for callback in self.callbacks:
                    await callback(candidates)
            else:
                logger.debug("No candidates found")
                
        except Exception as e:
            logger.error(f"Error during scan: {e}")

    async def start_scanning(self):
        """Запустить непрерывное сканирование"""
        logger.info(f"Starting scanner with interval {Config.SCAN_INTERVAL} seconds")
        while True:
            await self.scan()
            await asyncio.sleep(Config.SCAN_INTERVAL)
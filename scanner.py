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
        self.status_callbacks = []
        self.is_running = False
        self.is_paused = False  # Флаг паузы
        self.last_stats = None
        self.last_scan_time = None
        self.scan_task = None

    def add_callback(self, callback):
        """Добавить callback для уведомления о найденных кандидатах"""
        if callback not in self.callbacks:
            self.callbacks.append(callback)

    def add_status_callback(self, callback):
        """Добавить callback для обновления статуса"""
        if callback not in self.status_callbacks:
            self.status_callbacks.append(callback)

    async def scan(self):
        """Выполнить сканирование"""
        try:
            logger.debug("Starting scan for funding opportunities...")
            candidates = self.exchange.get_funding_candidates()
            
            # Сохраняем статистику
            self.last_stats = self.exchange.get_last_stats()
            self.last_scan_time = self.exchange.get_last_scan_time()
            
            # Отправляем статус всем подписчикам
            if self.last_stats:
                for callback in self.status_callbacks:
                    try:
                        await callback(self.last_stats, self.last_scan_time, candidates)
                    except Exception as e:
                        logger.error(f"Ошибка в status callback: {e}")
            
            if candidates:
                logger.info(f"✅ Found {len(candidates)} candidates")
                ready_candidates = [c for c in candidates if c.get('status') == 'ready']
                if ready_candidates:
                    for callback in self.callbacks:
                        await callback(candidates)
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
        self.is_paused = False
        logger.info(f"🔄 Scanner started with interval {Config.SCAN_INTERVAL} seconds")
        
        # Делаем первое сканирование сразу
        await self.scan()
        
        while self.is_running:
            await asyncio.sleep(Config.SCAN_INTERVAL)
            
            # Пропускаем сканирование если на паузе
            if self.is_paused:
                logger.debug("Scanner is paused, skipping scan...")
                continue
                
            await self.scan()
        
        logger.info("Scanner stopped")

    def stop(self):
        """Остановить сканер полностью"""
        self.is_running = False
        self.is_paused = False
        logger.info("Scanner stopping...")

    def pause(self):
        """Поставить сканер на паузу"""
        if self.is_running and not self.is_paused:
            self.is_paused = True
            logger.info("⏸ Scanner paused")
            return True
        return False

    def resume(self):
        """Возобновить сканирование"""
        if self.is_running and self.is_paused:
            self.is_paused = False
            logger.info("▶️ Scanner resumed")
            return True
        return False

    def get_status(self) -> Dict:
        """Получить статус сканера"""
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'last_stats': self.last_stats,
            'last_scan_time': self.last_scan_time
        }
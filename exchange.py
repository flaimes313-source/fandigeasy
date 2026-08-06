import time
from typing import Dict, List, Optional, Set
from pybit.unified_trading import HTTP
from config import Config
import logging

logger = logging.getLogger(__name__)

class BybitExchange:
    def __init__(self):
        self.session = HTTP(
            testnet=False,
            api_key=Config.BYBIT_API_KEY,
            api_secret=Config.BYBIT_API_SECRET
        )
        
        # Кеш для спотовых символов (используем set для O(1) поиска)
        self.spot_symbols_cache: Optional[Set[str]] = None
        self.last_cache_update = 0
        self.cache_duration = 300  # 5 минут
        
        # Кеш для тикеров
        self.tickers_cache: Optional[Dict] = None
        self.tickers_cache_time = 0
        self.tickers_cache_duration = 10  # 10 секунд

    def get_spot_symbols(self) -> Set[str]:
        """Получить список всех спотовых символов (используем set для O(1) поиска)"""
        current_time = time.time()
        if (self.spot_symbols_cache is not None and 
            current_time - self.last_cache_update < self.cache_duration):
            return self.spot_symbols_cache
        
        try:
            response = self.session.get_instruments_info(category="spot")
            symbols = {item['symbol'] for item in response['result']['list']}
            self.spot_symbols_cache = symbols
            self.last_cache_update = current_time
            return symbols
        except Exception as e:
            logger.error(f"Error getting spot symbols: {e}")
            return self.spot_symbols_cache or set()

    def get_all_tickers(self, category: str = "linear") -> Dict:
        """Получить все тикеры одним запросом"""
        current_time = time.time()
        
        # Используем кеш для тикеров
        if (self.tickers_cache is not None and 
            current_time - self.tickers_cache_time < self.tickers_cache_duration):
            return self.tickers_cache
        
        try:
            response = self.session.get_tickers(category=category)
            if response['result']['list']:
                # Создаем словарь для быстрого доступа по символу
                tickers_map = {
                    item['symbol']: item 
                    for item in response['result']['list']
                }
                self.tickers_cache = tickers_map
                self.tickers_cache_time = current_time
                return tickers_map
        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
        
        return {}

    def get_futures_info(self) -> Dict:
        """Получить информацию о фьючерсах одним запросом"""
        try:
            response = self.session.get_instruments_info(category="linear")
            instruments = {
                item['symbol']: item 
                for item in response['result']['list']
            }
            return instruments
        except Exception as e:
            logger.error(f"Error getting futures info: {e}")
            return {}

    def get_funding_candidates(self) -> List[Dict]:
        """
        Получить все кандидаты с положительным фандингом
        Оптимизировано: всего 2-3 HTTP запроса вместо 1000+
        """
        candidates = []
        current_time = int(time.time())
        
        # 1. Получаем все тикеры (1 запрос)
        tickers = self.get_all_tickers("linear")
        if not tickers:
            logger.warning("No tickers received")
            return candidates
        
        # 2. Получаем информацию о фьючерсах (1 запрос)
        futures_info = self.get_futures_info()
        if not futures_info:
            logger.warning("No futures info received")
            return candidates
        
        # 3. Получаем спотовые символы (1 запрос, кешируется)
        spot_symbols = self.get_spot_symbols()
        
        # 4. Фильтруем в памяти без дополнительных запросов
        for symbol, ticker in tickers.items():
            # Проверяем, что это USDT фьючерс
            if not symbol.endswith('USDT'):
                continue
            
            # Получаем funding rate из тикера (а не из instruments_info)
            funding_rate = float(ticker.get('fundingRate', 0)) * 100  # в процентах
            
            # Проверяем положительный фандинг
            if funding_rate < Config.MIN_FUNDING_RATE:
                continue
            
            # Получаем цену
            price = float(ticker.get('lastPrice', 0))
            if price == 0:
                continue
            
            # Проверяем наличие спота (O(1) благодаря set)
            spot_symbol = symbol.replace('USDT', '')
            if spot_symbol not in spot_symbols and symbol not in spot_symbols:
                continue
            
            # Получаем объем (уже есть в тикере)
            volume_24h = float(ticker.get('volume24h', 0)) * price
            if volume_24h < Config.MIN_VOLUME_USD:
                continue
            
            # Получаем время следующего фандинга (уже есть в тикере!)
            next_funding_time = int(ticker.get('nextFundingTime', 0))
            if next_funding_time == 0:
                # Если нет nextFundingTime, вычисляем вручную
                next_funding_time = self._calculate_next_funding_time(current_time)
            
            minutes_to_funding = (next_funding_time - current_time) // 60
            
            # Проверяем время до выплаты
            if minutes_to_funding > Config.MAX_MINUTES_TO_FUNDING or minutes_to_funding < 0:
                continue
            
            candidates.append({
                'symbol': symbol,
                'spot_symbol': spot_symbol,
                'funding_rate': funding_rate,
                'price': price,
                'minutes_to_funding': minutes_to_funding,
                'volume_24h': volume_24h,
                'next_funding_time': next_funding_time,
                'funding_rate_raw': float(ticker.get('fundingRate', 0))
            })
        
        # Сортируем по убыванию funding rate
        candidates.sort(key=lambda x: x['funding_rate'], reverse=True)
        
        logger.info(f"Found {len(candidates)} candidates from {len(tickers)} tickers")
        return candidates

    def _calculate_next_funding_time(self, current_time: int) -> int:
        """Вычислить время следующего фандинга (если не пришло от API)"""
        # Bybit выплачивает фандинг в 00:00, 08:00, 16:00 UTC
        hours = [0, 8, 16]
        current_hour = (current_time // 3600) % 24
        
        for hour in hours:
            if current_hour < hour:
                next_hour = hour
                break
        else:
            next_hour = hours[0]
            
        base_time = (current_time // 86400) * 86400
        next_time = base_time + next_hour * 3600
        if next_time < current_time:
            next_time += 86400
            
        return next_time

    def clear_cache(self):
        """Очистить кеш"""
        self.tickers_cache = None
        self.tickers_cache_time = 0
        self.spot_symbols_cache = None
        self.last_cache_update = 0
        logger.info("Cache cleared")
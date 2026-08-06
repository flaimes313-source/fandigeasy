import time
from typing import Dict, List, Optional, Tuple
from pybit.unified_trading import HTTP
from config import Config
import logging

logger = logging.getLogger(__name__)

class BybitExchange:
    def __init__(self):
        # Используем Unified API (новый синтаксис)
        self.session = HTTP(
            testnet=False,
            api_key=Config.BYBIT_API_KEY,
            api_secret=Config.BYBIT_API_SECRET
        )
        self.spot_symbols_cache = None
        self.last_cache_update = 0
        self.cache_duration = 300  # 5 минут

    def get_spot_symbols(self) -> List[str]:
        """Получить список всех спотовых символов"""
        current_time = time.time()
        if (self.spot_symbols_cache is not None and 
            current_time - self.last_cache_update < self.cache_duration):
            return self.spot_symbols_cache
        
        try:
            response = self.session.get_instruments_info(category="spot")
            symbols = [item['symbol'] for item in response['result']['list']]
            self.spot_symbols_cache = symbols
            self.last_cache_update = current_time
            return symbols
        except Exception as e:
            logger.error(f"Error getting spot symbols: {e}")
            return self.spot_symbols_cache or []

    def get_futures_info(self) -> List[Dict]:
        """Получить информацию о всех USDT фьючерсах"""
        try:
            response = self.session.get_instruments_info(category="linear")
            return response['result']['list']
        except Exception as e:
            logger.error(f"Error getting futures info: {e}")
            return []

    def get_spot_price(self, symbol: str) -> Optional[float]:
        """Получить спотовую цену для символа"""
        try:
            response = self.session.get_tickers(
                category="spot",
                symbol=symbol
            )
            if response['result']['list']:
                return float(response['result']['list'][0]['lastPrice'])
        except Exception as e:
            logger.error(f"Error getting spot price for {symbol}: {e}")
        return None

    def get_funding_info(self, symbol: str) -> Optional[Dict]:
        """Получить информацию о фандинге для фьючерса"""
        try:
            response = self.session.get_funding_rate_history(
                category="linear",
                symbol=symbol,
                limit=1
            )
            if response['result']['list']:
                funding_data = response['result']['list'][0]
                return {
                    'funding_rate': float(funding_data['fundingRate']) * 100,  # в процентах
                    'funding_time': int(funding_data['fundingTime']),
                    'next_funding_time': int(funding_data['fundingTime'])
                }
        except Exception as e:
            logger.error(f"Error getting funding for {symbol}: {e}")
        return None

    def get_next_funding_time(self, current_time: int) -> int:
        """Получить время следующей выплаты фандинга"""
        # Bybit выплачивает фандинг в 00:00, 08:00, 16:00 UTC
        hours = [0, 8, 16]
        current_hour = (current_time // 3600) % 24
        
        for hour in hours:
            if current_hour < hour:
                next_hour = hour
                break
            elif current_hour == hour:
                current_minute = (current_time // 60) % 60
                if current_minute < 5:  # Если до выплаты меньше 5 минут
                    next_hour = hour
                    break
            else:
                next_hour = hours[0]
        else:
            next_hour = hours[0]
            
        base_time = (current_time // 86400) * 86400
        next_time = base_time + next_hour * 3600
        if next_time < current_time:
            next_time += 86400
            
        return next_time

    def get_volume_24h(self, symbol: str) -> Optional[float]:
        """Получить 24-часовой объем торгов"""
        try:
            response = self.session.get_tickers(
                category="linear",
                symbol=symbol
            )
            if response['result']['list']:
                volume_24h = float(response['result']['list'][0]['volume24h'])
                price = float(response['result']['list'][0]['lastPrice'])
                return volume_24h * price
        except Exception as e:
            logger.error(f"Error getting volume for {symbol}: {e}")
        return None

    def check_spot_exists(self, symbol: str) -> bool:
        """Проверить, существует ли спотовый рынок для символа"""
        spot_symbol = symbol.replace('USDT', '')
        spot_symbols = self.get_spot_symbols()
        return spot_symbol in spot_symbols or symbol in spot_symbols

    def get_funding_candidates(self) -> List[Dict]:
        """Получить все кандидаты с положительным фандингом"""
        candidates = []
        futures = self.get_futures_info()
        current_time = int(time.time())
        next_funding_time = self.get_next_funding_time(current_time)
        minutes_to_funding = (next_funding_time - current_time) // 60
        
        for future in futures:
            symbol = future['symbol']
            
            if not symbol.endswith('USDT'):
                continue
                
            if not self.check_spot_exists(symbol):
                continue
                
            funding_rate = float(future.get('fundingRate', 0)) * 100
            if funding_rate < Config.MIN_FUNDING_RATE:
                continue
                
            price = float(future.get('lastPrice', 0))
            if price == 0:
                continue
                
            volume_24h = self.get_volume_24h(symbol)
            if volume_24h is None or volume_24h < Config.MIN_VOLUME_USD:
                continue
                
            if minutes_to_funding > Config.MAX_MINUTES_TO_FUNDING:
                continue
                
            candidates.append({
                'symbol': symbol,
                'spot_symbol': symbol.replace('USDT', ''),
                'funding_rate': funding_rate,
                'price': price,
                'minutes_to_funding': minutes_to_funding,
                'volume_24h': volume_24h,
                'next_funding_time': next_funding_time
            })
            
        return candidates
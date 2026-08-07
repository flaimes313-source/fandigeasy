import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set
from pybit.unified_trading import HTTP
from config import Config

logger = logging.getLogger(__name__)

class BybitExchange:
    def __init__(self):
        self.session = HTTP(
            testnet=False,
            api_key=Config.BYBIT_API_KEY,
            api_secret=Config.BYBIT_API_SECRET
        )
        
        # Кеши
        self.spot_symbols_cache: Optional[Set[str]] = None
        self.last_cache_update = 0
        self.cache_duration = 300  # 5 минут
        
        self.tickers_cache: Optional[Dict] = None
        self.tickers_cache_time = 0
        self.tickers_cache_duration = 10  # 10 секунд

    def get_spot_symbols(self) -> Set[str]:
        """Получить список всех спотовых символов"""
        current_time = time.time()
        if (self.spot_symbols_cache is not None and 
            current_time - self.last_cache_update < self.cache_duration):
            return self.spot_symbols_cache
        
        try:
            response = self.session.get_instruments_info(category="spot")
            symbols = {item['symbol'] for item in response['result']['list']}
            self.spot_symbols_cache = symbols
            self.last_cache_update = current_time
            logger.info(f"✅ Загружено {len(symbols)} спотовых символов")
            return symbols
        except Exception as e:
            logger.error(f"Ошибка получения спотовых символов: {e}")
            return self.spot_symbols_cache or set()

    def get_all_tickers(self, category: str = "linear") -> Dict:
        """Получить все тикеры одним запросом"""
        current_time = time.time()
        
        if (self.tickers_cache is not None and 
            current_time - self.tickers_cache_time < self.tickers_cache_duration):
            return self.tickers_cache
        
        try:
            response = self.session.get_tickers(category=category)
            if response['result']['list']:
                tickers_map = {
                    item['symbol']: item 
                    for item in response['result']['list']
                }
                self.tickers_cache = tickers_map
                self.tickers_cache_time = current_time
                logger.info(f"✅ Загружено {len(tickers_map)} тикеров")
                return tickers_map
        except Exception as e:
            logger.error(f"Ошибка получения тикеров: {e}")
        
        return {}

    def get_funding_candidates(self) -> List[Dict]:
        """
        Получить все кандидаты с положительным фандингом
        С полной диагностикой каждого этапа
        """
        # Статистика для диагностики
        stats = {
            'total': 0,
            'has_spot': 0,
            'funding_positive': 0,
            'funding_002': 0,
            'funding_005': 0,
            'time_ok': 0,
            'volume_ok': 0,
            'candidates': 0,
            'near_funding': 0  # < 60 минут
        }
        
        candidates = []
        near_candidates = []  # Кандидаты с funding > 0.05% но до выплаты > 10 минут
        
        # 1. Получаем все тикеры (1 запрос)
        tickers = self.get_all_tickers("linear")
        if not tickers:
            logger.warning("❌ Нет данных о тикерах")
            return candidates
        
        # 2. Получаем спотовые символы (1 запрос, кешируется)
        spot_symbols = self.get_spot_symbols()
        stats['total'] = len(tickers)
        
        # Текущее время
        current_time_sec = int(time.time())
        current_time_ms = int(time.time() * 1000)
        
        # Логируем время для диагностики
        logger.info(f"🕐 Текущее время UTC: {datetime.utcfromtimestamp(current_time_sec).strftime('%Y-%m-%d %H:%M:%S')}")
        
        for symbol, ticker in tickers.items():
            # Только USDT фьючерсы
            if not symbol.endswith('USDT'):
                continue
            
            # Проверяем наличие спота
            spot_symbol = symbol.replace('USDT', '')
            if spot_symbol in spot_symbols or symbol in spot_symbols:
                stats['has_spot'] += 1
            else:
                continue
            
            # Получаем funding rate
            funding_rate_raw = ticker.get('fundingRate')
            if funding_rate_raw is None:
                continue
                
            funding_rate = float(funding_rate_raw) * 100  # в процентах
            
            # Статистика по funding
            if funding_rate > 0:
                stats['funding_positive'] += 1
            if funding_rate >= 0.02:
                stats['funding_002'] += 1
            if funding_rate >= Config.MIN_FUNDING_RATE:
                stats['funding_005'] += 1
            else:
                continue
            
            # Получаем цену
            price = float(ticker.get('lastPrice', 0))
            if price == 0:
                continue
            
            # Получаем время следующего фандинга
            next_funding_time_ms = ticker.get('nextFundingTime')
            
            # ПРОВЕРКА: если nextFundingTime = 0, None, "" или "0"
            if not next_funding_time_ms or next_funding_time_ms == "0" or next_funding_time_ms == 0:
                # Если нет nextFundingTime, вычисляем вручную
                next_funding_time_ms = self._calculate_next_funding_time_ms(current_time_ms)
                logger.debug(f"⚠️ {symbol}: nextFundingTime отсутствует, вычислен вручную")
            
            # Конвертируем в секунды
            next_funding_time_sec = int(next_funding_time_ms) // 1000
            minutes_to_funding = (next_funding_time_sec - current_time_sec) // 60
            
            # ДИАГНОСТИКА: выводим время для монет с высоким funding
            if funding_rate >= 0.05:
                next_time_str = datetime.utcfromtimestamp(next_funding_time_sec).strftime('%Y-%m-%d %H:%M:%S')
                logger.info(
                    f"🔍 {symbol} | "
                    f"funding={funding_rate:.4f}% | "
                    f"next={next_time_str} UTC | "
                    f"minutes={minutes_to_funding}"
                )
            
            # Получаем объем в USDT (используем turnover24h!)
            volume_usd = float(ticker.get('turnover24h', 0))
            
            # Если turnover24h нет, пробуем volume24h
            if volume_usd == 0:
                volume_raw = float(ticker.get('volume24h', 0))
                if volume_raw > 0:
                    # Если volume24h это количество монет, умножаем на цену
                    if volume_raw < 1000000:
                        volume_usd = volume_raw * price
                    else:
                        volume_usd = volume_raw
                else:
                    continue
            
            # Статистика по объему
            if volume_usd >= Config.MIN_VOLUME_USD:
                stats['volume_ok'] += 1
            else:
                continue
            
            # Проверяем время до выплаты
            if 0 <= minutes_to_funding <= Config.MAX_MINUTES_TO_FUNDING:
                stats['time_ok'] += 1
                # Кандидат подходит для входа
                stats['candidates'] += 1
                candidates.append({
                    'symbol': symbol,
                    'spot_symbol': spot_symbol,
                    'funding_rate': funding_rate,
                    'funding_rate_raw': funding_rate_raw,
                    'price': price,
                    'minutes_to_funding': minutes_to_funding,
                    'volume_24h': volume_usd,
                    'volume_raw': ticker.get('volume24h', 0),
                    'turnover24h': volume_usd,
                    'next_funding_time': next_funding_time_sec,
                    'next_funding_time_ms': next_funding_time_ms,
                    'status': 'ready'  # Готов к входу
                })
            elif minutes_to_funding < 60 and minutes_to_funding > 0:
                # Кандидат с funding > 0.05% но до выплаты > 10 минут (скоро будет готов)
                stats['near_funding'] += 1
                near_candidates.append({
                    'symbol': symbol,
                    'spot_symbol': spot_symbol,
                    'funding_rate': funding_rate,
                    'funding_rate_raw': funding_rate_raw,
                    'price': price,
                    'minutes_to_funding': minutes_to_funding,
                    'volume_24h': volume_usd,
                    'turnover24h': volume_usd,
                    'next_funding_time': next_funding_time_sec,
                    'status': 'near'  # Скоро будет готов
                })
        
        # Выводим полную статистику
        self._log_stats(stats, near_candidates)
        
        # Сортируем по убыванию funding rate
        candidates.sort(key=lambda x: x['funding_rate'], reverse=True)
        near_candidates.sort(key=lambda x: x['funding_rate'], reverse=True)
        
        # Возвращаем сначала готовых кандидатов, потом "скоро"
        return candidates + near_candidates

    def _log_stats(self, stats: Dict, near_candidates: List):
        """Вывести статистику фильтрации"""
        logger.info("=" * 50)
        logger.info("📊 СТАТИСТИКА СКАНИРОВАНИЯ")
        logger.info("=" * 50)
        logger.info(f"  Всего USDT фьючерсов:     {stats['total']}")
        logger.info(f"  Есть спотовый рынок:      {stats['has_spot']}")
        logger.info(f"  Funding > 0:              {stats['funding_positive']}")
        logger.info(f"  Funding >= 0.02%:         {stats['funding_002']}")
        logger.info(f"  Funding >= 0.05%:         {stats['funding_005']}")
        logger.info(f"  До выплаты <= {Config.MAX_MINUTES_TO_FUNDING} мин: {stats['time_ok']}")
        logger.info(f"  Объем >= ${Config.MIN_VOLUME_USD:,.0f}: {stats['volume_ok']}")
        logger.info("-" * 50)
        logger.info(f"  ✅ ГОТОВЫ К ВХОДУ:        {stats['candidates']}")
        logger.info(f"  ⏳ Будут готовы < 60 мин: {stats.get('near_funding', 0)}")
        logger.info("=" * 50)
        
        # Если есть кандидаты "скоро", показываем их
        if near_candidates:
            logger.info("⏳ Кандидаты, которые будут готовы скоро:")
            for c in near_candidates[:5]:
                logger.info(f"  • {c['symbol']}: {c['funding_rate']:.3f}% через {c['minutes_to_funding']} мин")
            if len(near_candidates) > 5:
                logger.info(f"  ... и еще {len(near_candidates) - 5}")

    def _calculate_next_funding_time_ms(self, current_time_ms: int) -> int:
        """Вычислить время следующего фандинга в миллисекундах"""
        # Bybit выплачивает фандинг в 00:00, 08:00, 16:00 UTC
        hours = [0, 8, 16]
        current_hour = (current_time_ms // 3600000) % 24
        
        for hour in hours:
            if current_hour < hour:
                next_hour = hour
                break
        else:
            next_hour = hours[0]
        
        # Переводим в миллисекунды
        base_time = (current_time_ms // 86400000) * 86400000
        next_time = base_time + next_hour * 3600000
        if next_time < current_time_ms:
            next_time += 86400000
        
        return next_time

    def clear_cache(self):
        """Очистить кеш"""
        self.tickers_cache = None
        self.tickers_cache_time = 0
        self.spot_symbols_cache = None
        self.last_cache_update = 0
        logger.info("🗑 Кеш очищен")
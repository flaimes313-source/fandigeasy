from typing import Dict
from config import Config

class ProfitCalculator:
    def __init__(self):
        self.spot_fee = Config.SPOT_MAKER_FEE / 100
        self.futures_fee = Config.FUTURES_MAKER_FEE / 100

    def calculate_profit(self, 
                        amount_usd: float, 
                        funding_rate: float,
                        price: float) -> Dict:
        """Рассчитать потенциальную прибыль от арбитража фандинга"""
        coins = amount_usd / price
        funding_income = amount_usd * (funding_rate / 100)
        
        spot_buy_fee = amount_usd * self.spot_fee
        spot_sell_fee = amount_usd * self.spot_fee
        total_spot_fee = spot_buy_fee + spot_sell_fee
        
        futures_open_fee = amount_usd * self.futures_fee
        futures_close_fee = amount_usd * self.futures_fee
        total_futures_fee = futures_open_fee + futures_close_fee
        
        total_fees = total_spot_fee + total_futures_fee
        net_profit = funding_income - total_fees
        roi = (net_profit / amount_usd) * 100 if amount_usd > 0 else 0
        
        return {
            'coins': coins,
            'funding_income': funding_income,
            'spot_buy_fee': spot_buy_fee,
            'spot_sell_fee': spot_sell_fee,
            'total_spot_fee': total_spot_fee,
            'futures_open_fee': futures_open_fee,
            'futures_close_fee': futures_close_fee,
            'total_futures_fee': total_futures_fee,
            'total_fees': total_fees,
            'net_profit': net_profit,
            'roi': roi,
            'amount_usd': amount_usd,
            'funding_rate': funding_rate,
            'price': price
        }
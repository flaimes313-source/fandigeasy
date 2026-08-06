import logging
import asyncio
from typing import Dict, List, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from config import Config
from scanner import Scanner
from calculator import ProfitCalculator

logger = logging.getLogger(__name__)

class TelegramHandler:
    def __init__(self, token: str):
        """Инициализация обработчика Telegram"""
        self.application = Application.builder().token(token).build()
        self.scanner = Scanner()
        self.calculator = ProfitCalculator()
        
        # Храним состояние пользователей
        self.user_states: Dict[int, Dict] = {}
        self.user_chats: List[int] = []
        
        # Добавляем callback для сканера
        self.scanner.add_callback(self.on_candidates_found)
        
        # Настраиваем обработчики команд
        self.setup_handlers()
        
        # Флаг запуска сканера
        self.scanner_started = False
        self.scanner_task = None

    def setup_handlers(self):
        """Настройка обработчиков команд и сообщений"""
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("settings", self.settings_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        self.application.add_handler(CallbackQueryHandler(
            self.amount_callback, 
            pattern="^amount_"
        ))
        
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        self.application.add_error_handler(self.error_handler)

    async def start_scanner(self):
        """Запуск сканера в фоновом режиме"""
        if not self.scanner_started:
            self.scanner_started = True
            logger.info("🔄 Запуск фонового сканера...")
            self.scanner_task = asyncio.create_task(self.scanner.start_scanning())

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /start"""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id
        
        if chat_id not in self.user_chats:
            self.user_chats.append(chat_id)
            logger.info(f"👤 Новый пользователь: {user_id} (chat_id: {chat_id})")
        
        if not self.scanner_started:
            asyncio.create_task(self.start_scanner())
        
        welcome_text = (
            "🤖 Funding Arbitrage Bot\n"
            "========================\n\n"
            "Бот сканирует Bybit и находит возможности арбитража по фандингу.\n\n"
            "🔍 Как работает:\n"
            "• Каждые 30 секунд проверяются все USDT фьючерсы\n"
            "• Ищутся монеты с фандингом >= 0.05%\n"
            "• До выплаты остается <= 10 минут\n"
            "• Проверяется наличие спотового рынка\n"
            "• Проверяется ликвидность (объем >= $1M)\n\n"
            "📊 Когда находится кандидат:\n"
            "• Вы получите уведомление в боте\n"
            "• Выберите сумму или введите свою\n"
            "• Бот рассчитает потенциальную прибыль\n\n"
            "⚠️ Важно:\n"
            "• Бот только информирует, решение принимаете вы\n"
            "• Арбитраж связан с рисками\n"
            "• Всегда проверяйте расчеты самостоятельно\n\n"
            "💰 Доступные команды:\n"
            "/start - показать это сообщение\n"
            "/settings - показать настройки бота\n"
            "/help - помощь"
        )
        
        await update.message.reply_text(welcome_text)

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /settings"""
        min_profit_funding = (
            Config.SPOT_MAKER_FEE + 
            Config.SPOT_TAKER_FEE + 
            Config.FUTURES_MAKER_FEE + 
            Config.FUTURES_TAKER_FEE
        )
        
        settings_text = (
            "⚙️ Текущие настройки\n"
            "===================\n\n"
            f"📊 Минимальный фандинг: {Config.MIN_FUNDING_RATE}%\n"
            f"⏱ Макс время до выплаты: {Config.MAX_MINUTES_TO_FUNDING} мин\n"
            f"💰 Минимальный объем: ${Config.MIN_VOLUME_USD:,.0f}\n"
            f"🔄 Интервал сканирования: {Config.SCAN_INTERVAL} сек\n\n"
            "📝 Комиссии Bybit:\n"
            f"  • Спот покупка: {Config.SPOT_MAKER_FEE}%\n"
            f"  • Спот продажа: {Config.SPOT_TAKER_FEE}%\n"
            f"  • Фьючерс открытие: {Config.FUTURES_MAKER_FEE}%\n"
            f"  • Фьючерс закрытие: {Config.FUTURES_TAKER_FEE}%\n\n"
            f"💡 Для прибыли нужно:\n"
            f"  • Фандинг > {min_profit_funding:.2f}%\n"
            "  • Достаточная ликвидность\n"
            "  • Низкое проскальзывание"
        )
        
        await update.message.reply_text(settings_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /help"""
        help_text = (
            "🆘 Помощь\n"
            "========\n\n"
            "1️⃣ Как получить уведомления?\n"
            "Просто запустите бота командой /start\n"
            "Бот автоматически начнет сканирование\n\n"
            "2️⃣ Что делать при уведомлении?\n"
            "• Нажмите на одну из предложенных сумм\n"
            "• Или введите свою сумму в чат\n"
            "• Бот рассчитает прибыль\n\n"
            "3️⃣ Какие суммы вводить?\n"
            "• Рекомендуется от $100\n"
            "• Учитывайте комиссии\n"
            "• Не вкладывайте все средства\n\n"
            "4️⃣ Почему прибыль отрицательная?\n"
            "• Фандинг слишком низкий\n"
            "• Комиссии съедают прибыль\n"
            "• Нужен фандинг > 0.6%\n\n"
            "5️⃣ Это безопасно?\n"
            "• Бот не торгует, только информирует\n"
            "• Риски арбитража: проскальзывание, ликвидность\n"
            "• Всегда проверяйте расчеты сами"
        )
        
        await update.message.reply_text(help_text)

    async def on_candidates_found(self, candidates: List[Dict]):
        """Callback при найденных кандидатах"""
        if not candidates:
            return
            
        logger.info(f"📊 Найдено {len(candidates)} кандидатов")
        
        for chat_id in self.user_chats:
            try:
                for candidate in candidates[:3]:
                    await self.send_candidate(chat_id, candidate)
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"Ошибка отправки пользователю {chat_id}: {e}")
                if "bot was blocked" in str(e).lower():
                    if chat_id in self.user_chats:
                        self.user_chats.remove(chat_id)

    async def send_candidate(self, chat_id: int, candidate: Dict):
        """Отправить информацию о кандидате пользователю"""
        symbol = candidate['symbol']
        funding_rate = candidate['funding_rate']
        price = candidate['price']
        minutes = candidate['minutes_to_funding']
        volume = candidate.get('volume_24h', 0)
        
        self.user_states[chat_id] = {
            'symbol': symbol,
            'funding_rate': funding_rate,
            'price': price,
            'minutes': minutes
        }
        
        message = (
            f"🔔 Найден кандидат!\n"
            f"==================\n\n"
            f"📊 Монета: {symbol}\n"
            f"💰 Funding: +{funding_rate:.3f}%\n"
            f"⏱ До выплаты: {minutes} минут\n"
            f"💵 Цена: ${price:.4f}\n"
            f"📈 Объем 24ч: ${volume:,.0f}\n"
            f"🟢 Спот: есть\n"
            f"🟢 Фьючерс: есть\n\n"
            "💰 Выберите сумму для расчета:"
        )
        
        keyboard = []
        row = []
        for i, amount in enumerate(Config.QUICK_AMOUNTS):
            row.append(InlineKeyboardButton(
                f"${amount}", 
                callback_data=f"amount_{amount}"
            ))
            if (i + 1) % 2 == 0:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton("✏️ Ввести свою сумму", callback_data="amount_custom")
        ])
        
        keyboard.append([
            InlineKeyboardButton("❌ Игнорировать", callback_data="amount_ignore")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=message,
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка отправки сообщения {chat_id}: {e}")

    async def amount_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик нажатия на кнопки с суммой"""
        query = update.callback_query
        chat_id = query.message.chat_id
        
        await query.answer()
        
        data = query.data
        
        if data == "amount_ignore":
            await query.edit_message_text(
                "✅ Кандидат проигнорирован\n\nБот продолжит поиск новых возможностей."
            )
            if chat_id in self.user_states:
                del self.user_states[chat_id]
            return
        
        if data == "amount_custom":
            await query.edit_message_text(
                "✏️ Введите сумму в USD\n\nПример: 250\nМинимальная сумма: 10$"
            )
            return
        
        try:
            amount = float(data.split('_')[1])
            await self.calculate_and_send(chat_id, amount)
        except (ValueError, IndexError) as e:
            logger.error(f"Ошибка парсинга суммы: {e}")
            await query.edit_message_text(
                "❌ Ошибка! Пожалуйста, попробуйте снова."
            )

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик текстовых сообщений"""
        chat_id = update.effective_chat.id
        text = update.message.text.strip()
        
        try:
            amount = float(text)
            if amount < 10:
                await update.message.reply_text(
                    "❌ Минимальная сумма: 10$\nПожалуйста, введите сумму больше."
                )
                return
            await self.calculate_and_send(chat_id, amount)
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите корректное число\nПример: 250"
            )

    async def calculate_and_send(self, chat_id: int, amount: float):
        """Рассчитать и отправить результат"""
        state = self.user_states.get(chat_id)
        if not state:
            await self.application.bot.send_message(
                chat_id=chat_id,
                text="❌ Нет активных кандидатов.\n\nОжидайте новых уведомлений или запустите /start"
            )
            return
        
        try:
            symbol = state['symbol']
            funding_rate = state['funding_rate']
            price = state['price']
            minutes = state['minutes']
            
            result = self.calculator.calculate_profit(
                amount_usd=amount,
                funding_rate=funding_rate,
                price=price
            )
            
            result_text = (
                f"📊 {symbol}\n"
                f"==================\n\n"
                f"💰 Funding: {funding_rate:.3f}%\n"
                f"⏱ До выплаты: {minutes} мин\n"
                f"💵 Сумма: ${amount:,.2f}\n\n"
                f"📈 Ожидаемый funding: ${result['funding_income']:.4f}\n\n"
                f"📝 Комиссии:\n"
                f"  • Спот покупка: ${result['spot_buy_fee']:.4f}\n"
                f"  • Спот продажа: ${result['spot_sell_fee']:.4f}\n"
                f"  • Фьючерс открытие: ${result['futures_open_fee']:.4f}\n"
                f"  • Фьючерс закрытие: ${result['futures_close_fee']:.4f}\n"
                f"  • Всего комиссий: ${result['total_fees']:.4f}\n\n"
            )
            
            if result['net_profit'] > 0:
                result_text += f"✅ Чистая прибыль: ${result['net_profit']:.4f}\n"
            else:
                result_text += f"❌ Чистая прибыль: ${result['net_profit']:.4f}\n"
            
            result_text += (
                f"📊 ROI: {result['roi']:.3f}%\n\n"
                "⚠️ Решение о входе принимайте самостоятельно\n"
                "🔴 Высокий риск! Арбитраж не гарантирует прибыль"
            )
            
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=result_text
            )
            
            if chat_id in self.user_states:
                del self.user_states[chat_id]
                
            logger.info(
                f"📊 Расчет для {symbol}: "
                f"сумма=${amount:.2f}, "
                f"прибыль=${result['net_profit']:.4f}, "
                f"ROI={result['roi']:.3f}%"
            )
            
        except Exception as e:
            logger.error(f"Ошибка расчета для {chat_id}: {e}")
            await self.application.bot.send_message(
                chat_id=chat_id,
                text=f"❌ Ошибка расчета: {str(e)}\nПожалуйста, попробуйте снова."
            )

    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        logger.error(f"Ошибка: {context.error}")
        if update and update.effective_chat:
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Произошла ошибка. Бот продолжает работу."
                )
            except:
                pass

    async def run(self):
        """Запуск бота"""
        try:
            logger.info("🚀 Запуск Telegram бота...")
            
            # ВАЖНО: удаляем webhook с очисткой
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook очищен")
            
            # Запускаем сканер сразу
            asyncio.create_task(self.start_scanner())
            
            await self.application.initialize()
            await self.application.start()
            
            # ЗАПУСКАЕМ POLLING С ОЧИСТКОЙ
            await self.application.updater.start_polling(
                drop_pending_updates=True,  # <-- ГЛАВНОЕ ИЗМЕНЕНИЕ!
                poll_interval=0.5,
                timeout=10
            )
            
            logger.info("✅ Бот успешно запущен и готов к работе!")
            logger.info("📱 Нажмите /start в Telegram для начала работы")
            logger.info("=" * 50)
            
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("⏹ Бот остановлен пользователем")
        except Exception as e:
            logger.error(f"❌ Критическая ошибка: {e}")
            raise
        finally:
            if hasattr(self, 'application') and self.application.running:
                await self.application.stop()
                await self.application.updater.stop()
                await self.application.shutdown()
                logger.info("👋 Бот завершил работу")
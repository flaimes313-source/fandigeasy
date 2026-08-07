import logging
import asyncio
from datetime import datetime
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
        
        # Храним последние результаты сканирования
        self.last_scan_stats: Optional[Dict] = None
        self.last_scan_time: Optional[str] = None
        self.last_candidates: List[Dict] = []
        self.scan_completed = False
        
        # Добавляем callback для сканера
        self.scanner.add_callback(self.on_candidates_found)
        self.scanner.add_status_callback(self.on_status_update)
        
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
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("stop", self.stop_command))
        self.application.add_handler(CommandHandler("resume", self.resume_command))
        
        self.application.add_handler(CallbackQueryHandler(
            self.amount_callback, 
            pattern="^amount_"
        ))
        
        self.application.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self.handle_message
        ))
        
        self.application.add_error_handler(self.error_handler)

    async def on_status_update(self, stats: Dict, scan_time: str, candidates: List[Dict]):
        """Callback для обновления статуса"""
        try:
            self.last_scan_stats = stats
            self.last_scan_time = scan_time
            self.last_candidates = candidates
            self.scan_completed = True
            logger.info(f"📊 Статус обновлен: {stats.get('candidates', 0)} кандидатов")
        except Exception as e:
            logger.error(f"Ошибка обновления статуса: {e}")

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
            "🔍 ПОИСК ФАНДИНГА ЗАПУЩЕН!\n\n"
            "Бот сканирует Bybit каждые 30 секунд\n"
            "и ищет возможности арбитража.\n\n"
            "📊 Как работает:\n"
            "• Проверяются все USDT фьючерсы\n"
            "• Ищутся монеты с фандингом >= 0.02%\n"
            "• Проверяется наличие спотового рынка\n"
            "• Проверяется ликвидность\n\n"
            "📋 Команды:\n"
            "/status - показать результаты последнего сканирования\n"
            "/stop - остановить сканирование\n"
            "/resume - возобновить сканирование\n"
            "/settings - показать настройки бота\n"
            "/help - помощь\n\n"
            "⏳ Ожидайте уведомлений о найденных кандидатах!"
        )
        
        await update.message.reply_text(welcome_text)

    async def stop_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Остановить сканирование"""
        chat_id = update.effective_chat.id
        
        if not self.scanner_started:
            await update.message.reply_text(
                "❌ Сканер еще не запущен.\n"
                "Используйте /start для запуска."
            )
            return
        
        if self.scanner.pause():
            await update.message.reply_text(
                "⏸ Сканирование остановлено\n\n"
                "Бот больше не сканирует рынок.\n"
                "Чтобы возобновить, используйте /resume"
            )
        else:
            await update.message.reply_text(
                "⚠️ Сканер уже остановлен или не запущен.\n"
                "Используйте /resume для возобновления."
            )

    async def resume_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Возобновить сканирование"""
        chat_id = update.effective_chat.id
        
        if not self.scanner_started:
            await update.message.reply_text(
                "❌ Сканер еще не запущен.\n"
                "Используйте /start для запуска."
            )
            return
        
        if self.scanner.resume():
            await update.message.reply_text(
                "▶️ Сканирование возобновлено\n\n"
                "Бот снова сканирует рынок.\n"
                "Ожидайте уведомлений о кандидатах!"
            )
        else:
            await update.message.reply_text(
                "⚠️ Сканер уже работает или не был остановлен.\n"
                "Используйте /stop для остановки."
            )

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /status - показывает результаты последнего сканирования"""
        chat_id = update.effective_chat.id
        
        # Проверяем, было ли хотя бы одно сканирование
        if not self.scan_completed or not self.last_scan_stats:
            status_text = (
                "⏳ СТАТУС: Статистика еще не доступна\n"
                "====================================\n\n"
                "Бот только что запущен. Первое сканирование выполняется...\n"
                "Пожалуйста, подождите 5-10 секунд и попробуйте снова.\n\n"
                "🔄 Статус сканера: "
            )
            
            if self.scanner_started:
                if self.scanner.is_paused:
                    status_text += "Остановлен ⏸"
                else:
                    status_text += "Запущен ✅"
            else:
                status_text += "Запускается... ⏳"
            
            await update.message.reply_text(status_text)
            return
        
        # Формируем статусное сообщение (БЕЗ HTML!)
        stats = self.last_scan_stats
        
        # Статус сканера
        scanner_status = "⏸ Остановлен" if self.scanner.is_paused else "✅ Активен"
        
        status_text = (
            f"📊 СТАТУС СКАНИРОВАНИЯ\n"
            f"🕐 {self.last_scan_time}\n"
            f"🔄 Сканер: {scanner_status}\n"
            f"{'=' * 30}\n\n"
            f"📈 ОБЩАЯ СТАТИСТИКА:\n"
            f"  • Всего USDT фьючерсов:     {stats.get('total', 0)}\n"
            f"  • Есть спотовый рынок:      {stats.get('has_spot', 0)}\n"
            f"  • Funding > 0:              {stats.get('funding_positive', 0)}\n"
            f"  • Funding >= 0.02%:         {stats.get('funding_002', 0)}\n"
            f"  • Funding >= 0.05%:         {stats.get('funding_005', 0)}\n"
            f"  • До выплаты <= 10 мин:    {stats.get('time_ok', 0)}\n"
            f"  • Объем >= $1,000,000:      {stats.get('volume_ok', 0)}\n\n"
            f"🎯 РЕЗУЛЬТАТ:\n"
            f"  ✅ Готовы к входу:          {stats.get('candidates', 0)}\n"
            f"  ⏳ Будут готовы < 60 мин:   {stats.get('near_funding', 0)}\n"
        )
        
        # Если есть кандидаты, показываем их
        if self.last_candidates:
            ready_candidates = [c for c in self.last_candidates if c.get('status') == 'ready']
            near_candidates = [c for c in self.last_candidates if c.get('status') == 'near']
            
            if ready_candidates:
                status_text += f"\n🟢 ГОТОВЫЕ КАНДИДАТЫ:\n"
                for c in ready_candidates[:5]:
                    status_text += f"  • {c['symbol']}: {c['funding_rate']:.3f}% через {c['minutes_to_funding']} мин\n"
                if len(ready_candidates) > 5:
                    status_text += f"  ... и еще {len(ready_candidates) - 5}\n"
            
            if near_candidates:
                status_text += f"\n🟡 БУДУТ ГОТОВЫ СКОРО:\n"
                for c in near_candidates[:5]:
                    status_text += f"  • {c['symbol']}: {c['funding_rate']:.3f}% через {c['minutes_to_funding']} мин\n"
                if len(near_candidates) > 5:
                    status_text += f"  ... и еще {len(near_candidates) - 5}\n"
        else:
            status_text += "\n📭 Нет активных кандидатов"
        
        status_text += (
            f"\n\n{'=' * 30}\n"
            f"🔄 Следующее сканирование через {Config.SCAN_INTERVAL} сек\n"
            f"⏳ Бот продолжает работу в фоновом режиме"
        )
        
        if self.scanner.is_paused:
            status_text += "\n\n⏸ Сканирование остановлено\nИспользуйте /resume для возобновления"
        
        await update.message.reply_text(status_text)

    async def settings_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик команды /settings"""
        min_profit_funding = (
            Config.SPOT_MAKER_FEE + 
            Config.SPOT_TAKER_FEE + 
            Config.FUTURES_MAKER_FEE + 
            Config.FUTURES_TAKER_FEE
        )
        
        settings_text = (
            "⚙️ ТЕКУЩИЕ НАСТРОЙКИ\n"
            "===================\n\n"
            f"📊 Минимальный фандинг: {Config.MIN_FUNDING_RATE}%\n"
            f"⏱ Макс время до выплаты: {Config.MAX_MINUTES_TO_FUNDING} мин\n"
            f"💰 Минимальный объем: ${Config.MIN_VOLUME_USD:,.0f}\n"
            f"🔄 Интервал сканирования: {Config.SCAN_INTERVAL} сек\n"
            f"⏳ Уведомлять о кандидатах < 60 мин: {Config.NOTIFY_NEAR_FUNDING}\n\n"
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
            "🆘 ПОМОЩЬ\n"
            "========\n\n"
            "📋 Команды:\n"
            "/start - запустить бота и сканирование\n"
            "/status - показать результаты последнего сканирования\n"
            "/stop - остановить сканирование\n"
            "/resume - возобновить сканирование\n"
            "/settings - показать настройки\n"
            "/help - это сообщение\n\n"
            "🔍 Как это работает:\n"
            "1. Бот сканирует Bybit каждые 30 секунд\n"
            "2. Находит монеты с высоким фандингом\n"
            "3. Проверяет наличие спота и ликвидность\n"
            "4. Отправляет уведомление в Telegram\n"
            "5. Вы вводите сумму для расчета прибыли\n\n"
            "⚠️ ВАЖНО:\n"
            "• Бот только информирует\n"
            "• Решение о входе принимаете вы\n"
            "• Арбитраж связан с рисками"
        )
        
        await update.message.reply_text(help_text)

    async def on_candidates_found(self, candidates: List[Dict]):
        """Callback при найденных кандидатах"""
        if not candidates:
            return
            
        logger.info(f"📊 Найдено {len(candidates)} кандидатов")
        
        # Сохраняем результаты для команды /status
        self.last_candidates = candidates
        
        # Отправляем только готовых кандидатов (status == 'ready')
        ready_candidates = [c for c in candidates if c.get('status') == 'ready']
        near_candidates = [c for c in candidates if c.get('status') == 'near']
        
        for chat_id in self.user_chats:
            try:
                # Отправляем готовых кандидатов
                for candidate in ready_candidates[:3]:
                    await self.send_candidate(chat_id, candidate)
                    await asyncio.sleep(0.5)
                
                # Если есть кандидаты "скоро" и включено уведомление
                if near_candidates and Config.NOTIFY_NEAR_FUNDING:
                    near_message = (
                        "⏳ СКОРО БУДУТ ГОТОВЫ КАНДИДАТЫ:\n\n"
                    )
                    for c in near_candidates[:5]:
                        near_message += f"• {c['symbol']}: {c['funding_rate']:.3f}% через {c['minutes_to_funding']} мин\n"
                    if len(near_candidates) > 5:
                        near_message += f"... и еще {len(near_candidates) - 5}\n"
                    near_message += "\nСледите за обновлениями!"
                    
                    await self.application.bot.send_message(
                        chat_id=chat_id,
                        text=near_message
                    )
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
        
        # Определяем статус
        status_emoji = "🟢" if candidate.get('status') == 'ready' else "🟡"
        status_text = "ГОТОВ К ВХОДУ!" if candidate.get('status') == 'ready' else "Будет готов скоро"
        
        message = (
            f"🔔 {status_emoji} {status_text}\n"
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
        
        # Отправляем сообщение об ошибке только если это не команда /status
        if update and update.effective_chat:
            try:
                # Проверяем, была ли это команда /status
                if update.message and update.message.text and update.message.text.startswith('/status'):
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text="❌ Произошла ошибка при получении статуса.\nПожалуйста, попробуйте через несколько секунд."
                    )
                else:
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
            
            # Удаляем webhook с очисткой
            await self.application.bot.delete_webhook(drop_pending_updates=True)
            logger.info("✅ Webhook очищен")
            
            # Запускаем сканер сразу
            asyncio.create_task(self.start_scanner())
            
            await self.application.initialize()
            await self.application.start()
            
            # Запускаем polling
            await self.application.updater.start_polling(
                drop_pending_updates=True,
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
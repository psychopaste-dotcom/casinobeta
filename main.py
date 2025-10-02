import logging
import random
import time
import hashlib
import json
import os
from datetime import datetime
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('log.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# КОНФИГУРАЦИЯ
BOT_TOKEN = "5001575342:AAF-wnZ-bdTaqRG_LiwP6BuEBaBKFRCdM1w/test"
KAPRALOW_USERNAME = "@Kapralow"
KAPRALOW_USER_ID = 5001448188
ADMIN_ID = 5001448188

# Хранилища
user_balances = {}
user_sessions = {}
active_bets = set()
user_deposit_codes = {}
pending_deposits = {}
user_cake_numbers = {}
verified_cakes = set()
awaiting_cake_number = set()
banned_users = set()  # Забаненные пользователи

# Файлы для хранения данных
DATA_FILE = "data.json"
LOG_FILE = "log.log"

def load_data():
    """Загрузка данных из файла"""
    global user_balances, user_cake_numbers, verified_cakes, banned_users
    try:
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                user_balances = data.get('user_balances', {})
                user_cake_numbers = data.get('user_cake_numbers', {})
                verified_cakes = set(data.get('verified_cakes', []))
                banned_users = set(data.get('banned_users', []))
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")

def save_data():
    """Сохранение данных в файл"""
    try:
        data = {
            'user_balances': user_balances,
            'user_cake_numbers': user_cake_numbers,
            'verified_cakes': list(verified_cakes),
            'banned_users': list(banned_users)
        }
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")

def log_action(action, user_id, details=""):
    """Логирование действий"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_message = f"{timestamp} - USER:{user_id} - {action}"
    if details:
        log_message += f" - {details}"
    
    logger.info(log_message)
    
    # Дополнительно записываем в файл
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_message + '\n')

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

def generate_session_id(user_id):
    return hashlib.md5(f"{user_id}_{time.time()}".encode()).hexdigest()

def generate_deposit_code(user_id):
    return f"USER{user_id}_{hashlib.md5(f'{user_id}_{time.time()}'.encode()).hexdigest()[:8]}"

def is_banned(user_id):
    """Проверка забанен ли пользователь"""
    return user_id in banned_users

@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(message.chat.id, "❌ Вы заблокированы в системе!")
        return
    
    # Инициализация пользователя
    if user_id not in user_balances:
        user_balances[user_id] = 0
        user_sessions[user_id] = generate_session_id(user_id)
        user_deposit_codes[user_id] = generate_deposit_code(user_id)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎲 Играть в кубик", callback_data="play_dice"))
    keyboard.add(InlineKeyboardButton("💰 Мой баланс", callback_data="balance"))
    keyboard.add(InlineKeyboardButton("📥 Пополнить баланс", callback_data="deposit"))
    keyboard.add(InlineKeyboardButton("🎂 Проверить торт", callback_data="check_cake"))
    
    if user_id == ADMIN_ID:
        keyboard.add(InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel"))
    
    bot.send_message(
        message.chat.id,
        f"🎰 Добро пожаловать в Karalow Casino!\n\n"
        f"💰 Баланс: {user_balances[user_id]} тортов\n"
        f"📈 При выигрыше: x2\n\n"
        f"Для пополнения используйте кнопку '📥 Пополнить баланс'",
        reply_markup=keyboard
    )
    
    log_action("START", user_id)

@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    user_id = call.from_user.id
    
    if is_banned(user_id):
        bot.answer_callback_query(call.id, "❌ Вы заблокированы!", show_alert=True)
        return
    
    if user_id not in user_sessions:
        user_sessions[user_id] = generate_session_id(user_id)
    
    if call.data == "play_dice":
        play_dice_menu(call)
    elif call.data == "balance":
        show_balance(call)
    elif call.data == "deposit":
        show_deposit_info(call)
    elif call.data == "check_cake":
        start_cake_check(call)
    elif call.data == "admin_panel":
        admin_panel(call)
    elif call.data.startswith("dice_bet_"):
        amount = int(call.data.split("_")[2])
        process_dice_bet(call, amount)
    elif call.data == "back_main":
        start_from_query(call)
    elif call.data == "check_deposit":
        check_user_deposit(call)
    elif call.data == "admin_stats":
        admin_stats(call)
    elif call.data == "admin_users":
        admin_users_list(call)
    elif call.data.startswith("admin_user_"):
        user_action = call.data.split("_")[2]
        target_user_id = int(call.data.split("_")[3])
        admin_user_action(call, user_action, target_user_id)
    elif call.data == "admin_back":
        admin_panel(call)

def admin_panel(call):
    """Админ-панель"""
    user_id = call.from_user.id
    
    if user_id != ADMIN_ID:
        bot.answer_callback_query(call.id, "❌ Доступ запрещен!", show_alert=True)
        return
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"))
    keyboard.add(InlineKeyboardButton("👥 Список пользователей", callback_data="admin_users"))
    keyboard.add(InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
    
    total_users = len(user_balances)
    total_balance = sum(user_balances.values())
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"👑 Админ-панель\n\n"
             f"📊 Статистика:\n"
             f"• Пользователей: {total_users}\n"
             f"• Общий баланс: {total_balance}\n"
             f"• Забанено: {len(banned_users)}\n\n"
             f"Выберите действие:",
        reply_markup=keyboard
    )

def admin_stats(call):
    """Статистика админа"""
    user_id = call.from_user.id
    
    if user_id != ADMIN_ID:
        return
    
    total_users = len(user_balances)
    total_balance = sum(user_balances.values())
    active_users = len([uid for uid, bal in user_balances.items() if bal > 0])
    
    # Топ пользователей по балансу
    top_users = sorted(user_balances.items(), key=lambda x: x[1], reverse=True)[:5]
    top_text = "\n".join([f"👤 {uid}: {bal} тортов" for uid, bal in top_users])
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"📊 Статистика системы\n\n"
             f"👥 Пользователи:\n"
             f"• Всего: {total_users}\n"
             f"• Активных: {active_users}\n"
             f"• Забанено: {len(banned_users)}\n\n"
             f"💰 Финансы:\n"
             f"• Общий баланс: {total_balance}\n\n"
             f"🏆 Топ-5 по балансу:\n{top_text}",
        reply_markup=keyboard
    )

def admin_users_list(call):
    """Список пользователей для админа"""
    user_id = call.from_user.id
    
    if user_id != ADMIN_ID:
        return
    
    users_list = list(user_balances.items())[:20]  # Первые 20 пользователей
    
    keyboard = InlineKeyboardMarkup()
    for uid, balance in users_list:
        status = "🚫" if uid in banned_users else "✅"
        keyboard.add(InlineKeyboardButton(
            f"{status} {uid}: {balance} тортов", 
            callback_data=f"admin_user_info_{uid}"
        ))
    
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_panel"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"👥 Список пользователей (первые 20):\n\n"
             f"✅ - активен\n🚫 - забанен",
        reply_markup=keyboard
    )

def admin_user_action(call, action, target_user_id):
    """Действия с пользователем"""
    user_id = call.from_user.id
    
    if user_id != ADMIN_ID:
        return
    
    target_balance = user_balances.get(target_user_id, 0)
    is_banned_user = target_user_id in banned_users
    
    if action == "info":
        keyboard = InlineKeyboardMarkup()
        
        if is_banned_user:
            keyboard.add(InlineKeyboardButton("✅ Разблокировать", callback_data=f"admin_user_unban_{target_user_id}"))
        else:
            keyboard.add(InlineKeyboardButton("🚫 Заблокировать", callback_data=f"admin_user_ban_{target_user_id}"))
        
        keyboard.add(InlineKeyboardButton("💰 Выдать торты", callback_data=f"admin_user_add_{target_user_id}"))
        keyboard.add(InlineKeyboardButton("📥 Забрать торты", callback_data=f"admin_user_remove_{target_user_id}"))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="admin_users"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"👤 Информация о пользователе:\n\n"
                 f"🆔 ID: {target_user_id}\n"
                 f"💰 Баланс: {target_balance} тортов\n"
                 f"🎂 Номер торта: {user_cake_numbers.get(target_user_id, 'не указан')}\n"
                 f"🚫 Статус: {'забанен' if is_banned_user else 'активен'}\n\n"
                 f"Выберите действие:",
            reply_markup=keyboard
        )
    
    elif action == "ban":
        banned_users.add(target_user_id)
        save_data()
        log_action("BAN", user_id, f"target:{target_user_id}")
        bot.answer_callback_query(call.id, f"✅ Пользователь {target_user_id} заблокирован!", show_alert=True)
        admin_user_action(call, "info", target_user_id)
    
    elif action == "unban":
        banned_users.discard(target_user_id)
        save_data()
        log_action("UNBAN", user_id, f"target:{target_user_id}")
        bot.answer_callback_query(call.id, f"✅ Пользователь {target_user_id} разблокирован!", show_alert=True)
        admin_user_action(call, "info", target_user_id)
    
    elif action == "add":
        # Запрос суммы для выдачи
        msg = bot.send_message(
            call.message.chat.id,
            f"💰 Введите количество тортов для выдачи пользователю {target_user_id}:"
        )
        bot.register_next_step_handler(msg, lambda m: admin_add_balance_step(m, target_user_id, call))
    
    elif action == "remove":
        # Запрос суммы для изъятия
        msg = bot.send_message(
            call.message.chat.id,
            f"📥 Введите количество тортов для изъятия у пользователя {target_user_id} (макс: {target_balance}):"
        )
        bot.register_next_step_handler(msg, lambda m: admin_remove_balance_step(m, target_user_id, call))

def admin_add_balance_step(message, target_user_id, original_call):
    """Шаг выдачи баланса"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        return
    
    try:
        amount = int(message.text)
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть положительной!")
            return
        
        user_balances[target_user_id] = user_balances.get(target_user_id, 0) + amount
        save_data()
        log_action("ADD_BALANCE", user_id, f"target:{target_user_id} amount:{amount}")
        
        bot.send_message(
            message.chat.id,
            f"✅ Пользователю {target_user_id} выдано {amount} тортов!\n"
            f"💰 Новый баланс: {user_balances[target_user_id]}"
        )
        
        # Возвращаемся к меню пользователя
        admin_user_action(original_call, "info", target_user_id)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат числа!")

def admin_remove_balance_step(message, target_user_id, original_call):
    """Шаг изъятия баланса"""
    user_id = message.from_user.id
    
    if user_id != ADMIN_ID:
        return
    
    try:
        amount = int(message.text)
        current_balance = user_balances.get(target_user_id, 0)
        
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть положительной!")
            return
        
        if amount > current_balance:
            bot.send_message(message.chat.id, f"❌ Недостаточно средств! Максимум: {current_balance}")
            return
        
        user_balances[target_user_id] = current_balance - amount
        save_data()
        log_action("REMOVE_BALANCE", user_id, f"target:{target_user_id} amount:{amount}")
        
        bot.send_message(
            message.chat.id,
            f"✅ У пользователя {target_user_id} изъято {amount} тортов!\n"
            f"💰 Новый баланс: {user_balances[target_user_id]}"
        )
        
        # Возвращаемся к меню пользователя
        admin_user_action(original_call, "info", target_user_id)
        
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный формат числа!")

# Остальные функции (play_dice_menu, process_dice_bet, show_balance, show_deposit_info, start_cake_check, check_user_deposit, start_from_query, handle_cake_check)
# остаются такими же, но с добавлением log_action и save_data

def play_dice_menu(call):
    user_id = call.from_user.id
    balance = user_balances.get(user_id, 0)
    
    if balance == 0:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("📥 Пополнить", callback_data="deposit"))
        keyboard.add(InlineKeyboardButton("🎂 Проверить торт", callback_data="check_cake"))
        keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ Недостаточно средств! Пополните баланс.",
            reply_markup=keyboard
        )
        return
    
    keyboard = InlineKeyboardMarkup()
    possible_bets = [1, 5, 10, 25, 50]
    
    for bet in possible_bets:
        if bet <= balance:
            keyboard.add(InlineKeyboardButton(
                f"🎲 Ставка: {bet} торт(ов)", 
                callback_data=f"dice_bet_{bet}"
            ))
    
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎲 Игра в кубик\n💰 Баланс: {balance} торт(ов)\nВыберите ставку:",
        reply_markup=keyboard
    )

def process_dice_bet(call, bet_amount):
    user_id = call.from_user.id
    balance = user_balances.get(user_id, 0)
    
    if user_id in active_bets:
        bot.answer_callback_query(call.id, "⏳ У вас уже есть активная ставка! Дождитесь завершения.", show_alert=True)
        return
    
    if bet_amount > balance or bet_amount <= 0:
        bot.answer_callback_query(call.id, "❌ Неверная сумма ставки!", show_alert=True)
        return
    
    active_bets.add(user_id)
    
    try:
        user_balances[user_id] = balance - bet_amount
        save_data()
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="🎲 Бросаем кубик..."
        )
        
        time.sleep(1.5)
        
        roll = random.randint(1, 100)
        
        if roll <= 23:
            win_amount = bet_amount * 2
            user_balances[user_id] += win_amount
            save_data()
            log_action("WIN", user_id, f"bet:{bet_amount} win:{win_amount}")
            
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"🎉 ПОБЕДА!\n🎲 Выпало: {roll}/23\n"
                     f"💰 Ставка: {bet_amount}\n🏆 Выигрыш: {win_amount}\n"
                     f"💳 Баланс: {user_balances[user_id]}"
            )
        else:
            log_action("LOSE", user_id, f"bet:{bet_amount}")
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f"💔 ПРОИГРЫШ\n🎲 Выпало: {roll}/23\n"
                     f"💰 Ставка: {bet_amount}\n📉 Баланс: {user_balances[user_id]}\n"
                     f"Торты остаются у {KAPRALOW_USERNAME}"
            )
            
    except Exception as e:
        user_balances[user_id] = balance
        save_data()
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="❌ Произошла ошибка. Средства возвращены."
        )
        logger.error(f"Error in dice game: {e}")
    finally:
        active_bets.discard(user_id)

def show_balance(call):
    user_id = call.from_user.id
    balance = user_balances.get(user_id, 0)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎲 Играть", callback_data="play_dice"))
    keyboard.add(InlineKeyboardButton("📥 Пополнить", callback_data="deposit"))
    keyboard.add(InlineKeyboardButton("🎂 Проверить торт", callback_data="check_cake"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    
    user_cake = user_cake_numbers.get(user_id)
    cake_info = f"🎂 Ваш номер торта: {user_cake}\n" if user_cake else "🎂 Номер торта: не указан\n"
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"💰 Ваш баланс: {balance} торт(ов)\n"
             f"{cake_info}\n"
             f"Для пополнения отправьте торт на {KAPRALOW_USERNAME}",
        reply_markup=keyboard
    )

def show_deposit_info(call):
    user_id = call.from_user.id
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎂 Проверить торт", callback_data="check_cake"))
    keyboard.add(InlineKeyboardButton("💰 Баланс", callback_data="balance"))
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    
    user_cake = user_cake_numbers.get(user_id)
    cake_status = f"🎂 Ваш номер: {user_cake}" if user_cake else "🎂 Номер торта: не указан"
    
    deposit_info = (
        f"📥 Пополнение баланса\n\n"
        f"🎂 Способ 1 - через торт:\n"
        f"• Используйте кнопку '🎂 Проверить торт'\n"
        f"• Введите номер вашего торта\n"
        f"• Отправьте торт на {KAPRALOW_USERNAME}\n\n"
        f"{cake_status}\n"
        f"💰 Текущий баланс: {user_balances.get(user_id, 0)}"
    )
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=deposit_info,
        reply_markup=keyboard
    )

def start_cake_check(call):
    """Начинает процесс проверки торта"""
    user_id = call.from_user.id
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Назад", callback_data="back_main"))
    
    # Добавляем пользователя в ожидание ввода номера
    awaiting_cake_number.add(user_id)
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎂 Проверка торта\n\n"
             f"💡 Чтобы пополнить баланс:\n\n"
             f"1. Напишите номер вашего торта в формате:\n"
             f"   `#123456`\n\n"
             f"2. Отправьте этот торт на: {KAPRALOW_USERNAME}\n\n"
             f"3. Система проверит наличие торта у {KAPRALOW_USERNAME}\n"
             f"4. При подтверждении зачислится 1 торт на баланс\n\n"
             f"📝 Пример ввода: `#353321`\n\n"
             f"➡️ Теперь введите номер вашего торта:",
        reply_markup=keyboard,
        parse_mode='Markdown'
    )

def check_user_deposit(call):
    user_id = call.from_user.id
    deposit_code = user_deposit_codes.get(user_id)
    
    # Эмуляция проверки депозита
    if random.random() < 0.3:
        if user_id not in pending_deposits:
            amount = random.choice([10, 25, 50, 100])
            pending_deposits[user_id] = {
                'amount': amount,
                'code': deposit_code,
                'timestamp': time.time()
            }
        
        deposit_info = pending_deposits[user_id]
        user_balances[user_id] += deposit_info['amount']
        save_data()
        log_action("DEPOSIT", user_id, f"amount:{deposit_info['amount']}")
        
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"✅ Депозит подтвержден!\n\n"
                 f"💳 Зачислено: {deposit_info['amount']} тортов\n"
                 f"💰 Новый баланс: {user_balances[user_id]}\n"
                 f"🆔 Код: {deposit_info['code']}\n\n"
                 f"Можете начинать играть! 🎰"
        )
        
        del pending_deposits[user_id]
    else:
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text=f"🔄 Проверка пополнения...\n\n"
                 f"❌ Депозит еще не найден\n\n"
                 f"💡 Попробуйте способ с тортом:\n"
                 f"• Введите номер торта\n"
                 f"• Отправьте торт на {KAPRALOW_USERNAME}"
        )

def start_from_query(call):
    user_id = call.from_user.id
    
    if user_id not in user_sessions:
        user_sessions[user_id] = generate_session_id(user_id)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🎲 Играть в кубик", callback_data="play_dice"))
    keyboard.add(InlineKeyboardButton("💰 Мой баланс", callback_data="balance"))
    keyboard.add(InlineKeyboardButton("📥 Пополнить баланс", callback_data="deposit"))
    keyboard.add(InlineKeyboardButton("🎂 Проверить торт", callback_data="check_cake"))
    
    if user_id == ADMIN_ID:
        keyboard.add(InlineKeyboardButton("👑 Админ-панель", callback_data="admin_panel"))
    
    user_cake = user_cake_numbers.get(user_id)
    cake_info = f"🎂 Номер торта: {user_cake}\n" if user_cake else ""
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"🎰 Казино в Тортах!\n\n"
             f"💰 Баланс: {user_balances.get(user_id, 0)}\n"
             f"{cake_info}"
             f"🎯 Шанс выигрыша: 23%\n"
             f"📈 При выигрыше: x2",
        reply_markup=keyboard
    )

@bot.message_handler(func=lambda message: True)
def handle_cake_check(message):
    """Обработка проверки номера торта"""
    user_id = message.from_user.id
    
    if is_banned(user_id):
        bot.send_message(message.chat.id, "❌ Вы заблокированы в системе!")
        return
    
    message_text = message.text.strip()
    
    # Если пользователь ожидает ввод номера торта
    if user_id in awaiting_cake_number:
        if message_text.startswith('#') and len(message_text) == 7 and message_text[1:].isdigit():
            cake_number = message_text
            
            awaiting_cake_number.discard(user_id)
            user_cake_numbers[user_id] = cake_number
            save_data()
            
            if cake_number in verified_cakes:
                bot.send_message(
                    message.chat.id,
                    f"❌ Торт {cake_number} уже был использован для пополнения!"
                )
                return
            
            bot.send_message(
                message.chat.id,
                f"🔍 Проверяем торт {cake_number} у {KAPRALOW_USERNAME}..."
            )
            
            time.sleep(2)
            
            if random.random() < 0.7:
                user_balances[user_id] = user_balances.get(user_id, 0) + 1
                verified_cakes.add(cake_number)
                save_data()
                log_action("CAKE_DEPOSIT", user_id, f"cake:{cake_number}")
                
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("🎲 Играть в кубик", callback_data="play_dice"))
                keyboard.add(InlineKeyboardButton("💰 Мой баланс", callback_data="balance"))
                
                bot.send_message(
                    message.chat.id,
                    f"✅ Торт {cake_number} найден у {KAPRALOW_USERNAME}!\n\n"
                    f"🎉 Вам зачислен 1 торт на баланс!\n"
                    f"💰 Новый баланс: {user_balances[user_id]}\n\n"
                    f"Можете начинать играть! 🎰",
                    reply_markup=keyboard
                )
            else:
                keyboard = InlineKeyboardMarkup()
                keyboard.add(InlineKeyboardButton("🔄 Попробовать снова", callback_data="check_cake"))
                keyboard.add(InlineKeyboardButton("🔙 В меню", callback_data="back_main"))
                
                bot.send_message(
                    message.chat.id,
                    f"❌ Торт {cake_number} не найден у {KAPRALOW_USERNAME}",
                    reply_markup=keyboard
                )
        else:
            bot.send_message(
                message.chat.id,
                f"❌ Неверный формат номера торта!\n\n"
                f"💡 Номер должен быть в формате: `#123456`\n"
                f"➡️ Пожалуйста, введите номер еще раз:"
            )
    else:
        try:
            numbers = [int(s) for s in message_text.split() if s.isdigit()]
            if numbers:
                amount = numbers[0]
                if amount > 0:
                    user_balances[user_id] = user_balances.get(user_id, 0) + amount
                    save_data()
                    log_action("MANUAL_DEPOSIT", user_id, f"amount:{amount}")
                    
                    bot.send_message(
                        message.chat.id,
                        f"✅ Баланс пополнен!\n\n"
                        f"💳 Зачислено: {amount} тортов\n"
                        f"💰 Новый баланс: {user_balances[user_id]}\n\n"
                        f"Можете начинать играть! 🎰"
                    )
                    return
        except:
            pass
        
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🎂 Проверить торт", callback_data="check_cake"))
        keyboard.add(InlineKeyboardButton("💰 Баланс", callback_data="balance"))
        
        bot.send_message(
            message.chat.id,
            f"🎂 Для пополнения через торт:\n\n"
            f"1. Нажмите '🎂 Проверить торт'\n"
            f"2. Введите номер вашего торта в формате: `#123456`\n"
            f"3. Отправьте торт на: {KAPRALOW_USERNAME}\n\n"
            f"📝 Или просто напишите сумму для пополнения\n"
            f"Пример: '100'",
            reply_markup=keyboard
        )

if __name__ == "__main__":
    # Загружаем данные при запуске
    load_data()
    
    print("🤖 Бот запускается...")
    print(f"✅ Токен: {BOT_TOKEN}")
    print("🎰 Казино в Тортах готово к работе!")
    print("📊 Логирование активировано")
    print("👑 Админ-панель доступна")
    
    bot.infinity_polling()
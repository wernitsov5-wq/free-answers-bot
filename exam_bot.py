import logging
import sqlite3
import random
import string
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from flask import Flask
from threading import Thread
import requests
import time

# ===== ТВОЙ ТОКЕН =====
BOT_TOKEN = "8674062910:AAF4NYbi2HOu74w-9yJ9bXS9p_QVU2QgS-4"
MANAGER_ID = 7672790214

# ===== ВЕБ-СЕРВЕР ДЛЯ RENDER И UPTIMEROBOT =====
web_app = Flask('')

@web_app.route('/')
def home():
    return "✅ Бот работает! Онлайн 24/7"

@web_app.route('/health')
def health():
    return "OK", 200

def run_web():
    web_app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ===== АВТО-ПИНГ (чтобы бот сам себя будил) =====
def auto_ping():
    url = "https://free-answers-bot.onrender.com"
    while True:
        try:
            requests.get(url, timeout=10)
            print(f"✅ Пинг отправлен в {time.strftime('%H:%M:%S')}")
        except:
            print(f"❌ Ошибка пинга в {time.strftime('%H:%M:%S')}")
        time.sleep(840)  # 14 минут

def start_ping():
    t = Thread(target=auto_ping)
    t.start()

# ===== НАСТРОЙКИ =====
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_unlock_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))

def init_database():
    conn = sqlite3.connect('exam_answers.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (user_id INTEGER PRIMARY KEY,
                  username TEXT,
                  invited_by INTEGER,
                  invited_count INTEGER DEFAULT 0,
                  has_access INTEGER DEFAULT 0,
                  unlock_code TEXT,
                  registered_date TIMESTAMP)''')
    conn.commit()
    conn.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    
    conn = sqlite3.connect('exam_answers.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, registered_date) VALUES (?, ?, ?)",
              (user_id, user.username, datetime.now()))
    conn.commit()
    
    c.execute("SELECT has_access, unlock_code, invited_count FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    has_access = result[0] if result else 0
    unlock_code = result[1] if result else None
    invited_count = result[2] if result else 0
    conn.close()
    
    bot_username = context.bot.username
    ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    if has_access:
        keyboard = [
            [InlineKeyboardButton("🗣️ Устное собеседование", callback_data="menu_oral")],
            [InlineKeyboardButton("📝 ОГЭ 2026", callback_data="menu_oge")],
            [InlineKeyboardButton("📊 ВПР 2026", callback_data="menu_vpr")],
            [InlineKeyboardButton("✍️ Итоговое сочинение", callback_data="menu_essay")],
            [InlineKeyboardButton("🏆 Олимпиады", callback_data="menu_olympiads")],
            [InlineKeyboardButton("🧪 Пробники", callback_data="menu_trials")],
            [InlineKeyboardButton("👥 Реферальная система", callback_data="menu_referral")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📚 **БЕСПЛАТНЫЕ ОТВЕТЫ** 📚\n\nДобро пожаловать! У тебя есть полный доступ ко всем материалам.\n\n**Выбери раздел:**",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        keyboard = [
            [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="menu_referral")],
            [InlineKeyboardButton("📊 Проверить прогресс", callback_data="check_invites")]
        ]
        if unlock_code:
            keyboard.append([InlineKeyboardButton("🎫 Показать код менеджеру", callback_data="show_code")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = (
            f"📚 **БЕСПЛАТНЫЕ ОТВЕТЫ** 📚\n\n"
            f"Привет, {user.first_name}!\n\n"
            f"Чтобы получить доступ ко всем материалам, пригласи **15 друзей**!\n\n"
            f"Твоя реферальная ссылка:\n`{ref_link}`\n\n"
            f"👥 Приглашено друзей: **{invited_count}/15**\n\n"
        )
        
        if unlock_code:
            text += f"🎉 **Ты уже пригласил 15 друзей!** 🎉\n\n"
            text += f"Твой код для менеджера:\n`{unlock_code}`\n\n"
            text += f"Покажи этот код менеджеру, чтобы получить доступ к материалам!"
        else:
            text += f"Осталось пригласить: **{15 - invited_count}** друзей"
        
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    conn = sqlite3.connect('exam_answers.db')
    c = conn.cursor()
    c.execute("SELECT has_access FROM users WHERE user_id=?", (user_id,))
    result = c.fetchone()
    has_access = result[0] if result else 0
    conn.close()
    
    if has_access:
        keyboard = [
            [InlineKeyboardButton("🗣️ Устное собеседование", callback_data="menu_oral")],
            [InlineKeyboardButton("📝 ОГЭ 2026", callback_data="menu_oge")],
            [InlineKeyboardButton("📊 ВПР 2026", callback_data="menu_vpr")],
            [InlineKeyboardButton("✍️ Итоговое сочинение", callback_data="menu_essay")],
            [InlineKeyboardButton("🏆 Олимпиады", callback_data="menu_olympiads")],
            [InlineKeyboardButton("🧪 Пробники", callback_data="menu_trials")],
            [InlineKeyboardButton("👥 Реферальная система", callback_data="menu_referral")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📚 **БЕСПЛАТНЫЕ ОТВЕТЫ** 📚\n\nВыбери раздел:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        keyboard = [
            [InlineKeyboardButton("🔗 Реферальная ссылка", callback_data="menu_referral")],
            [InlineKeyboardButton("📊 Проверить прогресс", callback_data="check_invites")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"📚 **БЕСПЛАТНЫЕ ОТВЕТЫ** 📚\n\nТвоя реферальная ссылка:\n`{ref_link}`",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if data == "menu_oral":
        text = "🗣️ **УСТНОЕ СОБЕСЕДОВАНИЕ** 🗣️\n\nОтветы и материалы будут здесь."
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "menu_oge":
        text = "📝 **ОГЭ 2026** 📝\n\nОтветы и материалы будут здесь."
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "menu_vpr":
        text = "📊 **ВПР 2026** 📊\n\nОтветы и материалы будут здесь."
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "menu_essay":
        text = "✍️ **ИТОГОВОЕ СОЧИНЕНИЕ** ✍️\n\nОтветы и материалы будут здесь."
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "menu_olympiads":
        text = "🏆 **ОЛИМПИАДЫ** 🏆\n\nОтветы и материалы будут здесь."
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "menu_trials":
        text = "🧪 **ПРОБНИКИ** 🧪\n\nОтветы и материалы будут здесь."
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "menu_referral":
        conn = sqlite3.connect('exam_answers.db')
        c = conn.cursor()
        c.execute("SELECT invited_count, has_access, unlock_code FROM users WHERE user_id=?", (user_id,))
        invited_count, has_access, unlock_code = c.fetchone()
        conn.close()
        
        bot_username = context.bot.username
        ref_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        
        text = (
            f"👥 **РЕФЕРАЛЬНАЯ СИСТЕМА** 👥\n\n"
            f"Ты уже пригласил: **{invited_count}/15** друзей\n\n"
            f"Твоя реферальная ссылка:\n`{ref_link}`\n\n"
            f"Осталось пригласить: **{max(0, 15 - invited_count)}** друзей"
        )
        
        if unlock_code:
            text += f"\n\n🎉 **Твой код доступа:** `{unlock_code}`\nПокажи его менеджеру!"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "check_invites":
        conn = sqlite3.connect('exam_answers.db')
        c = conn.cursor()
        c.execute("SELECT invited_count, unlock_code FROM users WHERE user_id=?", (user_id,))
        invited_count, unlock_code = c.fetchone()
        conn.close()
        
        text = f"📊 Ты пригласил **{invited_count}/15** друзей.\n\nОсталось: **{max(0, 15 - invited_count)}**"
        if unlock_code:
            text += f"\n\n🎉 Твой код: `{unlock_code}`"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
        await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data == "show_code":
        conn = sqlite3.connect('exam_answers.db')
        c = conn.cursor()
        c.execute("SELECT unlock_code FROM users WHERE user_id=?", (user_id,))
        result = c.fetchone()
        conn.close()
        
        if result and result[0]:
            text = f"🎫 **ТВОЙ ПЕРСОНАЛЬНЫЙ КОД** 🎫\n\n`{result[0]}`\n\nПокажи этот код менеджеру!"
            keyboard = [[InlineKeyboardButton("◀️ Назад в меню", callback_data="back_to_menu")]]
            await query.edit_message_text(text, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        else:
            await query.edit_message_text("❌ У тебя пока нет кода. Пригласи 15 друзей!")
    
    elif data == "back_to_menu":
        await back_to_menu(update, context)

async def handle_start_with_ref(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    if context.args and context.args[0].startswith("ref_"):
        inviter_id = int(context.args[0].replace("ref_", ""))
        
        if inviter_id != user_id:
            conn = sqlite3.connect('exam_answers.db')
            c = conn.cursor()
            
            c.execute("INSERT OR IGNORE INTO users (user_id, username, invited_by, registered_date) VALUES (?, ?, ?, ?)",
                      (user_id, username, inviter_id, datetime.now()))
            c.execute("UPDATE users SET invited_count = invited_count + 1 WHERE user_id=?", (inviter_id,))
            
            c.execute("SELECT invited_count FROM users WHERE user_id=?", (inviter_id,))
            invited_count = c.fetchone()[0]
            
            if invited_count >= 15:
                c.execute("SELECT unlock_code FROM users WHERE user_id=?", (inviter_id,))
                existing_code = c.fetchone()[0]
                
                if not existing_code:
                    unlock_code = generate_unlock_code()
                    c.execute("UPDATE users SET unlock_code = ? WHERE user_id=?", (unlock_code, inviter_id))
                    
                    try:
                        await context.bot.send_message(
                            inviter_id,
                            f"🎉 **ПОЗДРАВЛЯЮ!** 🎉\n\n"
                            f"Ты пригласил {invited_count} друзей!\n\n"
                            f"Твой код: `{unlock_code}`\n\n"
                            f"Покажи этот код менеджеру!",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            
            conn.commit()
            conn.close()
    
    await start(update, context)

async def check_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != MANAGER_ID:
        await update.message.reply_text("❌ Нет доступа")
        return
    
    args = context.args
    if not args:
        await update.message.reply_text("❌ Используй: `/check КОД`", parse_mode='Markdown')
        return
    
    code = args[0].upper()
    
    conn = sqlite3.connect('exam_answers.db')
    c = conn.cursor()
    c.execute("SELECT user_id, username, invited_count, has_access FROM users WHERE unlock_code=?", (code,))
    result = c.fetchone()
    conn.close()
    
    if result:
        user_id, username, invited_count, has_access = result
        status = "✅ Доступ выдан" if has_access else "⏳ Ожидает доступа"
        await update.message.reply_text(
            f"✅ **Код найден!**\n\n"
            f"👤 Пользователь: @{username or user_id}\n"
            f"👥 Пригласил: {invited_count}/15 друзей\n"
            f"📋 Статус: {status}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(f"❌ Код `{code}` не найден", parse_mode='Markdown')

def main():
    print("📚 ЗАПУСК БОТА 📚")
    print("=" * 40)
    
    init_database()
    print("✅ База данных готова")
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", handle_start_with_ref))
    app.add_handler(CommandHandler("check", check_code))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("✅ Бот запущен!")
    print("=" * 40)
    app.run_polling()

if __name__ == "__main__":
    keep_alive()      # Запускаем веб-сервер для Render
    start_ping()      # Запускаем авто-пинг (бужение себя)
    main()            # Запускаем бота

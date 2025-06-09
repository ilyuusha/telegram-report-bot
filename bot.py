from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
)
from datetime import datetime
import os
import asyncio
import threading
import socket

# 🔧 Укажи свой Telegram user ID:
ADMIN_ID = 166773394

# Этапы диалога
TICKETS_COMPANY, CASH, CARD, RETURNS_COUNT, RETURNS_SUM, TOTAL_TICKETS = range(6)

async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    msg = await query.message.chat.send_message("Сколько билетов за смену по твоей компании?")
    context.user_data.setdefault("to_delete", []).append(msg.message_id)
    return TICKETS_COMPANY

async def ask_and_remember(update, context, text, next_state):
    msg = await update.message.reply_text(text)
    context.user_data.setdefault("to_delete", []).append(msg.message_id)
    return next_state

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await ask_and_remember(update, context, "Сколько билетов за смену по твоей компании?", TICKETS_COMPANY)

async def tickets_company(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", TICKETS_COMPANY)
    context.user_data["tickets_company"] = int(update.message.text)
    return await ask_and_remember(update, context, "Введите выручку наличными:", CASH)

async def cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", CASH)
    context.user_data["cash"] = int(update.message.text)
    return await ask_and_remember(update, context, "Введите выручку по безналу:", CARD)

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", CARD)
    context.user_data["card"] = int(update.message.text)
    return await ask_and_remember(update, context, "Сколько было возвратов?", RETURNS_COUNT)

async def returns_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", RETURNS_COUNT)
    context.user_data["returns_count"] = int(update.message.text)
    return await ask_and_remember(update, context, "Введите общую сумму возвратов:", RETURNS_SUM)

async def returns_sum(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", RETURNS_SUM)
    context.user_data["returns_sum"] = int(update.message.text)
    return await ask_and_remember(update, context, "Сколько билетов продано тобой по всем компаниям?", TOTAL_TICKETS)

async def total_tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", TOTAL_TICKETS)
    context.user_data["total_tickets"] = int(update.message.text)

    total_sum = context.user_data["cash"] + context.user_data["card"]
    date_str = datetime.now().strftime("%d.%m.%Y")

    summary = (
        f"Спасибо!\n"
        f"📅 Дата: {date_str}\n"
        f"🎟 Билеты по твоей компании: {context.user_data['tickets_company']}\n"
        f"💵 Наличные: {context.user_data['cash']} ₽\n"
        f"💳 Безнал: {context.user_data['card']} ₽\n"
        f"↩️ Возвратов: {context.user_data['returns_count']} шт. на сумму {context.user_data['returns_sum']} ₽\n"
        f"🎟 Все билеты (все компании): {context.user_data['total_tickets']}\n"
        f"🧾 Итого: {total_sum} ₽"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Отправить новый отчёт", callback_data="restart")]
    ])

    await update.message.reply_text(summary, reply_markup=keyboard)

    if update.effective_user.id != ADMIN_ID:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 Новый отчёт от @{update.effective_user.username or 'без username'}:\n\n{summary}"
        )

    to_delete = context.user_data.get("to_delete", [])
    for msg_id in to_delete:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    context.user_data.clear()
    return ConversationHandler.END

# 🔌 Заглушка порта для Render
def keep_port_open():
    port = int(os.environ.get("PORT", 10000))
    handler = http.server.SimpleHTTPRequestHandler
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

if __name__ == '__main__':
    threading.Thread(target=keep_port_open, daemon=True).start()

    app = ApplicationBuilder().token(os.environ["TELEGRAM_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("start", start),
            CallbackQueryHandler(restart_callback, pattern="^restart$")
        ],
        states={
            TICKETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, tickets)],
            CASH: [MessageHandler(filters.TEXT & ~filters.COMMAND, cash)],
            CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, card)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

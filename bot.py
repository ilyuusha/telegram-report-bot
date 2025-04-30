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

# 🔧 Укажи свой Telegram user ID:
ADMIN_ID = 166773394

# Этапы диалога
TICKETS, CASH, CARD = range(3)

# Кнопка "Отправить новый отчёт"
async def restart_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    # Не удаляем итоговый отчёт!
    msg = await query.message.chat.send_message("Сколько билетов за смену?")
    context.user_data.setdefault("to_delete", []).append(msg.message_id)
    return TICKETS

# Вспомогательная функция — задать вопрос и запомнить сообщение
async def ask_and_remember(update, context, text, next_state):
    msg = await update.message.reply_text(text)
    context.user_data.setdefault("to_delete", []).append(msg.message_id)
    return next_state

# Старт команды
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await ask_and_remember(update, context, "Привет! Сколько билетов за смену?", TICKETS)

# Ввод билетов
async def tickets(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", TICKETS)
    context.user_data["tickets"] = int(update.message.text)
    return await ask_and_remember(update, context, "Введите выручку наличными:", CASH)

# Ввод наличных
async def cash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", CASH)
    context.user_data["cash"] = int(update.message.text)
    return await ask_and_remember(update, context, "Введите выручку по безналу:", CARD)

# Ввод безналичных
async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.text.isdigit():
        return await ask_and_remember(update, context, "Введите целое число.", CARD)
    context.user_data["card"] = int(update.message.text)

    date_str = datetime.now().strftime("%d.%m.%Y")
    summary = (
        f"Спасибо!\n"
        f"📅 Дата: {date_str}\n"
        f"🎟 Билеты: {context.user_data['tickets']}\n"
        f"💵 Наличные: {context.user_data['cash']} ₽\n"
        f"💳 Безнал: {context.user_data['card']} ₽"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Отправить новый отчёт", callback_data="restart")]
    ])

    # Финальный отчёт (не добавляем его в список на удаление!)
    await update.message.reply_text(summary, reply_markup=keyboard)

    # Отправка админу
    if update.effective_user.id != ADMIN_ID:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📥 Новый отчёт от @{update.effective_user.username or 'без username'}:\n\n{summary}"
        )

    # Удаление промежуточных сообщений
    to_delete = context.user_data.get("to_delete", [])
    for msg_id in to_delete:
        try:
            await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=msg_id)
        except Exception:
            pass

    context.user_data.clear()
    return ConversationHandler.END

# Отмена по /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Операция отменена.")
    context.user_data.clear()
    return ConversationHandler.END

# Запуск приложения
if __name__ == '__main__':
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    app = ApplicationBuilder().token(TOKEN).build()

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

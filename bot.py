import os
import json
import logging
import asyncio
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

logging.basicConfig(level=logging.INFO)
TOKEN = os.environ["BOT_TOKEN"]
DATA_FILE = "data.json"

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tasks": [], "transactions": [], "workouts": [], "notes": []}

def dump(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def today():
    return datetime.now().strftime("%d.%m.%Y")

def now():
    return datetime.now().strftime("%d.%m.%Y %H:%M")

MAIN_KB = ReplyKeyboardMarkup([
    [KeyboardButton("✅ Задачи"), KeyboardButton("💰 Финансы")],
    [KeyboardButton("💪 Тренировка"), KeyboardButton("📝 Заметки")],
    [KeyboardButton("📊 Сводка")],
], resize_keyboard=True)

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я твой *Life OS бот*.\n\n"
        "Команды:\n"
        "• /task Текст — добавить задачу\n"
        "• /done 1 — выполнить задачу №1\n"
        "• /list — список задач\n"
        "• /expense 15 Кофе — расход\n"
        "• /income 1000 Зарплата — доход\n"
        "• /workout Бег 30 мин — тренировка\n"
        "• /note Текст — заметка\n"
        "• /summary — дневная сводка",
        parse_mode="Markdown", reply_markup=MAIN_KB
    )

async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Пример: `/task Купить продукты`", parse_mode="Markdown"); return
    data = load()
    tid = (max((t["id"] for t in data["tasks"]), default=0)) + 1
    data["tasks"].append({"id": tid, "text": text, "done": False, "date": today()})
    dump(data)
    await update.message.reply_text(f"✅ Задача #{tid} добавлена: *{text}*", parse_mode="Markdown")

async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Пример: `/done 1`", parse_mode="Markdown"); return
    try:
        tid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Укажи номер задачи: `/done 2`", parse_mode="Markdown"); return
    data = load()
    task = next((t for t in data["tasks"] if t["id"] == tid), None)
    if not task:
        await update.message.reply_text(f"Задача #{tid} не найдена."); return
    task["done"] = True
    dump(data)
    await update.message.reply_text(f"🎉 Выполнено: *{task['text']}*", parse_mode="Markdown")

async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    active = [t for t in data["tasks"] if not t["done"]]
    if not active:
        await update.message.reply_text("📭 Нет активных задач!"); return
    lines = "\n".join(f"#{t['id']} {t['text']}" for t in active)
    await update.message.reply_text(f"📋 *Задачи:*\n\n{lines}", parse_mode="Markdown")

async def cmd_expense(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Пример: `/expense 15.50 Кофе`", parse_mode="Markdown"); return
    try:
        amount = float(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом."); return
    name = " ".join(ctx.args[1:])
    data = load()
    data["transactions"].append({"type": "expense", "amount": amount, "name": name, "date": today()})
    dump(data)
    today_exp = sum(t["amount"] for t in data["transactions"] if t["type"] == "expense" and t["date"] == today())
    await update.message.reply_text(
        f"💸 Расход: *{name}* — €{amount:.2f}\n_Итого сегодня: €{today_exp:.2f}_",
        parse_mode="Markdown"
    )

async def cmd_income(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Пример: `/income 1500 Зарплата`", parse_mode="Markdown"); return
    try:
        amount = float(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом."); return
    name = " ".join(ctx.args[1:])
    data = load()
    data["transactions"].append({"type": "income", "amount": amount, "name": name, "date": today()})
    dump(data)
    await update.message.reply_text(f"💰 Доход: *{name}* — €{amount:.2f}", parse_mode="Markdown")

async def cmd_workout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Пример: `/workout Бег 30 мин`", parse_mode="Markdown"); return
    text = " ".join(ctx.args)
    data = load()
    data["workouts"].append({"text": text, "date": now()})
    dump(data)
    total = len(data["workouts"])
    await update.message.reply_text(f"💪 Тренировка: *{text}*\n_Всего тренировок: {total}_", parse_mode="Markdown")

async def cmd_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Пример: `/note Идея для проекта`", parse_mode="Markdown"); return
    text = " ".join(ctx.args)
    data = load()
    data["notes"].append({"text": text, "date": now()})
    dump(data)
    await update.message.reply_text(f"📝 Заметка сохранена:\n_{text}_", parse_mode="Markdown")

async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    t = today()
    active = [x for x in data["tasks"] if not x["done"]]
    done_today = [x for x in data["tasks"] if x["done"] and x["date"] == t]
    income = sum(x["amount"] for x in data["transactions"] if x["type"] == "income")
    expense = sum(x["amount"] for x in data["transactions"] if x["type"] == "expense")
    today_exp = sum(x["amount"] for x in data["transactions"] if x["type"] == "expense" and x["date"] == t)
    workouts_total = len(data["workouts"])
    msg = (
        f"📊 *Сводка на {t}*\n\n"
        f"✅ Задач активных: {len(active)}\n"
        f"✅ Сделано сегодня: {len(done_today)}\n\n"
        f"💰 Баланс: €{income - expense:.2f}\n"
        f"💸 Расходы сегодня: €{today_exp:.2f}\n\n"
        f"💪 Тренировок всего: {workouts_total}\n"
    )
    if active:
        msg += "\n📋 *Ближайшие задачи:*\n" + "\n".join(f"#{x['id']} {x['text']}" for x in active[:3])
    await update.message.reply_text(msg, parse_mode="Markdown")

async def keyboard_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    if txt == "✅ Задачи": await cmd_list(update, ctx)
    elif txt == "💰 Финансы":
        data = load()
        inc = sum(t["amount"] for t in data["transactions"] if t["type"] == "income")
        exp = sum(t["amount"] for t in data["transactions"] if t["type"] == "expense")
        await update.message.reply_text(
            f"💰 *Финансы*\n\nБаланс: €{inc-exp:.2f}\nДоходы: €{inc:.2f}\nРасходы: €{exp:.2f}\n\n"
            "Добавить:\n`/expense 15 Кофе`\n`/income 1000 Зарплата`", parse_mode="Markdown")
    elif txt == "💪 Тренировка":
        await update.message.reply_text("Запиши: `/workout Бег 30 мин`", parse_mode="Markdown")
    elif txt == "📝 Заметки":
        await update.message.reply_text("Добавь: `/note Твоя мысль`", parse_mode="Markdown")
    elif txt == "📊 Сводка": await cmd_summary(update, ctx)
    else: await update.message.reply_text("Используй кнопки или команды.", reply_markup=MAIN_KB)

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("task", cmd_task))
    app.add_handler(CommandHandler("done", cmd_done))
    app.add_handler(CommandHandler("list", cmd_list))
    app.add_handler(CommandHandler("expense", cmd_expense))
    app.add_handler(CommandHandler("income", cmd_income))
    app.add_handler(CommandHandler("workout", cmd_workout))
    app.add_handler(CommandHandler("note", cmd_note))
    app.add_handler(CommandHandler("summary", cmd_summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, keyboard_handler))
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()

import os
import json
import logging
from datetime import datetime
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, ConversationHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("BOT_TOKEN", "")
DATA_FILE = "data.json"

# ─── Data helpers ────────────────────────────────────────────────────────────

def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"tasks": [], "transactions": [], "workouts": [], "notes": []}

def dump(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def now_str():
    return datetime.now().strftime("%d.%m.%Y %H:%M")

def today_str():
    return datetime.now().strftime("%d.%m.%Y")

# ─── Main menu keyboard ───────────────────────────────────────────────────────

MAIN_KB = ReplyKeyboardMarkup([
    [KeyboardButton("✅ Задачи"), KeyboardButton("💰 Финансы")],
    [KeyboardButton("💪 Тренировка"), KeyboardButton("📝 Заметки")],
    [KeyboardButton("📊 Сводка")],
], resize_keyboard=True)

# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет! Я твой *Life OS бот*.\n\n"
        "Выбери раздел или используй команды:\n"
        "• /task — добавить задачу\n"
        "• /done — отметить задачу выполненной\n"
        "• /expense — записать расход\n"
        "• /income — записать доход\n"
        "• /workout — залогировать тренировку\n"
        "• /note — быстрая заметка\n"
        "• /summary — дневная сводка\n"
        "• /list — список задач",
        parse_mode="Markdown",
        reply_markup=MAIN_KB
    )

# ─── TASKS ────────────────────────────────────────────────────────────────────

async def cmd_task(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Напиши задачу:\n`/task Купить продукты`", parse_mode="Markdown")
        return
    data = load()
    task = {"id": len(data["tasks"]) + 1, "text": text, "done": False, "date": today_str()}
    data["tasks"].append(task)
    dump(data)
    await update.message.reply_text(f"✅ Задача #{task['id']} добавлена:\n*{text}*", parse_mode="Markdown")

async def cmd_done(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not ctx.args:
        await update.message.reply_text("Укажи номер задачи:\n`/done 3`", parse_mode="Markdown")
        return
    try:
        tid = int(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Номер должен быть числом, например `/done 2`", parse_mode="Markdown")
        return
    data = load()
    task = next((t for t in data["tasks"] if t["id"] == tid), None)
    if not task:
        await update.message.reply_text(f"Задача #{tid} не найдена.")
        return
    task["done"] = True
    dump(data)
    await update.message.reply_text(f"🎉 Выполнено: *{task['text']}*", parse_mode="Markdown")

async def cmd_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    active = [t for t in data["tasks"] if not t["done"]]
    if not active:
        await update.message.reply_text("📭 Нет активных задач. Отлично!")
        return
    lines = [f"#{t['id']} {t['text']}" for t in active]
    await update.message.reply_text("📋 *Активные задачи:*\n\n" + "\n".join(lines), parse_mode="Markdown")

# ─── FINANCE ─────────────────────────────────────────────────────────────────

async def cmd_expense(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # /expense 15.50 Кофе
    if len(ctx.args) < 2:
        await update.message.reply_text("Формат: `/expense 15.50 Кофе`", parse_mode="Markdown")
        return
    try:
        amount = float(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом, например `/expense 12.5 Обед`", parse_mode="Markdown")
        return
    name = " ".join(ctx.args[1:])
    data = load()
    data["transactions"].append({"type": "expense", "amount": amount, "name": name, "date": today_str()})
    dump(data)

    # Show running total today
    today_exp = sum(t["amount"] for t in data["transactions"] if t["type"] == "expense" and t["date"] == today_str())
    await update.message.reply_text(
        f"💸 Расход записан: *{name}* — €{amount:.2f}\n"
        f"_Итого расходов сегодня: €{today_exp:.2f}_",
        parse_mode="Markdown"
    )

async def cmd_income(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if len(ctx.args) < 2:
        await update.message.reply_text("Формат: `/income 1500 Зарплата`", parse_mode="Markdown")
        return
    try:
        amount = float(ctx.args[0])
    except ValueError:
        await update.message.reply_text("Сумма должна быть числом.", parse_mode="Markdown")
        return
    name = " ".join(ctx.args[1:])
    data = load()
    data["transactions"].append({"type": "income", "amount": amount, "name": name, "date": today_str()})
    dump(data)
    await update.message.reply_text(f"💰 Доход записан: *{name}* — €{amount:.2f}", parse_mode="Markdown")

# ─── WORKOUT ─────────────────────────────────────────────────────────────────

async def cmd_workout(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # /workout Бег 30 мин
    if not ctx.args:
        await update.message.reply_text("Формат: `/workout Бег 30 мин`", parse_mode="Markdown")
        return
    text = " ".join(ctx.args)
    data = load()
    data["workouts"].append({"text": text, "date": now_str()})
    dump(data)
    total = len([w for w in data["workouts"] if w["date"].startswith(today_str()[:7])])  # this month
    await update.message.reply_text(
        f"💪 Тренировка записана: *{text}*\n_Тренировок в этом месяце: {total}_",
        parse_mode="Markdown"
    )

# ─── NOTES ───────────────────────────────────────────────────────────────────

async def cmd_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = " ".join(ctx.args)
    if not text:
        await update.message.reply_text("Формат: `/note Идея для проекта...`", parse_mode="Markdown")
        return
    data = load()
    data["notes"].append({"text": text, "date": now_str()})
    dump(data)
    await update.message.reply_text(f"📝 Заметка сохранена:\n_{text}_", parse_mode="Markdown")

# ─── SUMMARY ─────────────────────────────────────────────────────────────────

async def cmd_summary(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    data = load()
    today = today_str()

    # Tasks
    active_tasks = [t for t in data["tasks"] if not t["done"]]
    done_today = [t for t in data["tasks"] if t["done"] and t["date"] == today]

    # Finance
    income = sum(t["amount"] for t in data["transactions"] if t["type"] == "income")
    expense = sum(t["amount"] for t in data["transactions"] if t["type"] == "expense")
    balance = income - expense
    today_exp = sum(t["amount"] for t in data["transactions"] if t["type"] == "expense" and t["date"] == today)

    # Workouts
    workouts_today = [w for w in data["workouts"] if w["date"].startswith(today)]
    total_workouts = len(data["workouts"])

    # Notes
    recent_notes = data["notes"][-2:] if data["notes"] else []

    msg = (
        f"📊 *Сводка на {today}*\n\n"
        f"✅ *Задачи*\n"
        f"  Активных: {len(active_tasks)}\n"
        f"  Сделано сегодня: {len(done_today)}\n\n"
        f"💰 *Финансы*\n"
        f"  Баланс: €{balance:.2f}\n"
        f"  Расходы сегодня: €{today_exp:.2f}\n"
        f"  Всего доходов: €{income:.2f}\n\n"
        f"💪 *Спорт*\n"
        f"  Тренировок сегодня: {len(workouts_today)}\n"
        f"  Всего тренировок: {total_workouts}\n\n"
    )

    if active_tasks:
        top = active_tasks[:3]
        msg += "📋 *Ближайшие задачи:*\n"
        msg += "\n".join(f"  #{t['id']} {t['text']}" for t in top) + "\n\n"

    if recent_notes:
        msg += "📝 *Последние заметки:*\n"
        msg += "\n".join(f"  — {n['text']}" for n in recent_notes)

    await update.message.reply_text(msg, parse_mode="Markdown")

# ─── Keyboard button handler ─────────────────────────────────────────────────

async def keyboard_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    txt = update.message.text
    if txt == "✅ Задачи":
        await cmd_list(update, ctx)
    elif txt == "💰 Финансы":
        data = load()
        income = sum(t["amount"] for t in data["transactions"] if t["type"] == "income")
        expense = sum(t["amount"] for t in data["transactions"] if t["type"] == "expense")
        await update.message.reply_text(
            f"💰 *Финансы*\n\nБаланс: €{income - expense:.2f}\nДоходы: €{income:.2f}\nРасходы: €{expense:.2f}\n\n"
            "Добавить:\n`/expense 15 Кофе`\n`/income 1000 Зарплата`",
            parse_mode="Markdown"
        )
    elif txt == "💪 Тренировка":
        await update.message.reply_text("Запиши тренировку:\n`/workout Бег 30 мин`\n`/workout Зал 60 мин`", parse_mode="Markdown")
    elif txt == "📝 Заметки":
        await update.message.reply_text("Добавь заметку:\n`/note Твоя мысль или идея`", parse_mode="Markdown")
    elif txt == "📊 Сводка":
        await cmd_summary(update, ctx)
    else:
        await update.message.reply_text("Используй кнопки меню или команды (/task, /expense, /workout...)", reply_markup=MAIN_KB)

# ─── Run ──────────────────────────────────────────────────────────────────────

def main():
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")
    app = ApplicationBuilder().token(TOKEN).build()
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
    logger.info("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()

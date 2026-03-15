import json
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

TOKEN = "ВАШ ТОКЕН БОТА, СГЕНЕРИРОВАННЫЙ В BOTFATHER"

# Глобальная структура для быстрого доступа
FORMULA_MAP = {}          # "F = m * a" → {info}
FORMULA_BY_CLASS = {}     # "7" → список формул этого класса


def load_formulas(path="formulas.json"):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    formula_map = {}
    formula_by_class = {}

    # Обрабатываем только 7–9 классы
    allowed_classes = {"7", "8", "9"}

    for class_key, sections in data.items():
        class_num = class_key.split("_")[0]  # "7_class_..." → "7"
        if class_num not in allowed_classes:
            continue

        if class_num not in formula_by_class:
            formula_by_class[class_num] = []

        for section_key, formulas_list in sections.items():
            for item in formulas_list:
                if isinstance(item, dict) and len(item) == 1:
                    formula_str = next(iter(item))
                    info = item[formula_str]
                    # Добавляем класс в информацию о формуле (если нужно)
                    info["class"] = class_num
                    formula_map[formula_str] = info
                    formula_by_class[class_num].append(formula_str)

    print(f"Загружено {len(formula_map)} формул (только 7–9 классы)")
    return formula_map, formula_by_class


FORMULA_MAP, FORMULA_BY_CLASS = load_formulas()


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "Привет! Я бот с формулами по **физике 7–9 класс**.\n\n"
        "Просто напиши:\n"
        "• часть формулы (f=ma, v², ρ, Q=)\n"
        "• ключевое слово (сила, Архимед, давление, Ома, работа)\n"
        "• номер класса (7, 8, 9)\n\n"
        "Команды:\n"
        "/classes — список классов и количество формул\n"
        "/help — эта инструкция"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def classes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["**Доступные классы (7–9):** \n"]

    class_names = {
        "7": "7 класс — Механика, давление, работа, энергия, мощность",
        "8": "8 класс — Тепловые явления, электричество, магнетизм",
        "9": "9 класс — Законы движения, колебания, электромагнитное поле",
    }

    for cls in sorted(FORMULA_BY_CLASS.keys()):
        name = class_names.get(cls, f"{cls} класс")
        count = len(FORMULA_BY_CLASS[cls])
        lines.append(f"• **{name}** — {count} формул")

    lines.append("\n10 и 11 классы в этом боте **не поддерживаются**.")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if not text:
        await update.message.reply_text("Напиши хотя бы одно слово или часть формулы.")
        return

    query = text.lower().strip()

    # Поиск по номеру класса (только 7–9)
    if query in {"7", "8", "9"}:
        if query in FORMULA_BY_CLASS and FORMULA_BY_CLASS[query]:
            formulas = FORMULA_BY_CLASS[query]
            matched = formulas[:15]
            note = "" if len(formulas) <= 15 else f" (показано 15 из {len(formulas)})"
            keyboard = [[InlineKeyboardButton(f, callback_data=f)] for f in matched]
            await update.message.reply_text(
                f"Формулы **{query} класса**{note}:",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await update.message.reply_text(f"В {query} классе формул пока нет.")
        return

    # Обычный поиск
    matched = []
    for formula, info in FORMULA_MAP.items():
        if (query in formula.lower() or
            query in info.get("name", "").lower() or
            query in info.get("description", "").lower()):
            matched.append(formula)

    if not matched:
        await update.message.reply_text(
            f"По запросу «{text}» ничего не найдено.\n\n"
            "Попробуй:\n"
            "• часть формулы (Fт, P =, λ =)\n"
            "• слово (плотность, импульс, напряжение, Архимед)\n"
            "• номер класса (7, 8 или 9)"
        )
        return

    MAX_BUTTONS = 12
    note = ""
    if len(matched) > MAX_BUTTONS:
        matched = matched[:MAX_BUTTONS]
        note = f"\n(показано {MAX_BUTTONS} из {len(matched)} найденных)"

    keyboard = [[InlineKeyboardButton(f, callback_data=f)] for f in matched]

    await update.message.reply_text(
        f"Найдено **{len(matched)}** совпадений по «{text}»{note}:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "back":
        await query.edit_message_text(
            "Введите новый запрос\n(например: Архимед, закон Ома, давление, 8)"
        )
        return

    info = FORMULA_MAP.get(data)
    if not info:
        await query.edit_message_text("Формула не найдена :(")
        return

    vars_lines = []
    if "variables" in info and info["variables"]:
        for var, desc in info["variables"].items():
            vars_lines.append(f"• `{var}` — {desc}")

    message = [
        f"**{info.get('name', '—')}**",
        "",
        info.get("description", "—"),
        "",
        f"**Класс:** {info.get('class', '—')}",
        f"**Единицы:** {info.get('units', '—')}",
    ]

    if vars_lines:
        message.append("")
        message.append("**Переменные:**")
        message.extend(vars_lines)

    message.append("")
    message.append(f"**Формула:**\n`{data}`")

    reply_markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("← Новый поиск", callback_data="back")]
    ])

    await query.edit_message_text(
        "\n".join(message),
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("classes", classes_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_handler(CallbackQueryHandler(button_callback))

    print("Бот запущен (только 7–9 классы)...")
    app.run_polling()


if __name__ == "__main__":
    main()
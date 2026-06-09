import logging
import json
import os
from telegram import Update, Poll, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, PollAnswerHandler,
    MessageHandler, filters, ContextTypes, CallbackQueryHandler
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_IDS = list(map(int, os.environ.get("ADMIN_IDS", "0").split(",")))

# Ma'lumotlar xotirada saqlanadi
quizzes = {}        # quiz_id -> {questions, title}
active_quiz = {}    # chat_id -> {quiz_id, current_q, scores, poll_msg_id}
poll_to_quiz = {}   # poll_id -> {chat_id, question_index, correct_option}

def load_data():
    global quizzes
    if os.path.exists("quizzes.json"):
        with open("quizzes.json", "r", encoding="utf-8") as f:
            quizzes = json.load(f)

def save_data():
    with open("quizzes.json", "w", encoding="utf-8") as f:
        json.dump(quizzes, f, ensure_ascii=False, indent=2)

# /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 Salom! Men Quiz Botman!\n\n"
        "📋 <b>Buyruqlar:</b>\n"
        "▶️ /quizlar — mavjud testlarni ko'rish\n"
        "🏆 /natijalar — so'nggi natijalar\n\n"
        "👨‍💼 <b>Admin uchun:</b>\n"
        "➕ /yangi_quiz — yangi test yaratish\n"
        "🗑 /ochir_quiz — testni o'chirish\n"
        "▶️ /boshlash [id] — testni boshlash\n"
        "⏹ /toxtatish — testni to'xtatish"
    )
    await update.message.reply_html(text)

# /quizlar - barcha testlarni ko'rsatish
async def list_quizzes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not quizzes:
        await update.message.reply_text("❌ Hozircha test yo'q. Admin /yangi_quiz buyrug'i bilan qo'shishi mumkin.")
        return
    text = "📚 <b>Mavjud testlar:</b>\n\n"
    for qid, quiz in quizzes.items():
        text += f"🔹 ID: <code>{qid}</code> — {quiz['title']} ({len(quiz['questions'])} savol)\n"
    text += "\n▶️ Boshlash uchun: /boshlash [ID]"
    await update.message.reply_html(text)

# /yangi_quiz - admin yangi test yaratadi
async def new_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    context.user_data["creating_quiz"] = {"step": "title", "questions": []}
    await update.message.reply_text(
        "📝 Yangi test yaratish boshlandi!\n\n"
        "1️⃣ Avval test nomini yozing:"
    )

# /boshlash [quiz_id]
async def start_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Testni faqat admin boshlashi mumkin!")
        return
    if not context.args:
        await update.message.reply_text("❗ Ishlatish: /boshlash [quiz_id]\nMasalan: /boshlash 1")
        return
    quiz_id = context.args[0]
    if quiz_id not in quizzes:
        await update.message.reply_text("❌ Bunday ID li test topilmadi. /quizlar buyrug'ini ko'ring.")
        return
    chat_id = update.effective_chat.id
    if chat_id in active_quiz:
        await update.message.reply_text("⚠️ Guruhda allaqachon test ketmoqda! /toxtatish bilan to'xtating.")
        return

    active_quiz[chat_id] = {
        "quiz_id": quiz_id,
        "current_q": 0,
        "scores": {},
        "participants": {}
    }
    quiz = quizzes[quiz_id]
    await update.message.reply_html(
        f"🎯 <b>{quiz['title']}</b> testi boshlandi!\n"
        f"📊 Jami {len(quiz['questions'])} ta savol\n\n"
        f"Tayyor bo'ling... ✅"
    )
    await send_question(update, context, chat_id)

async def send_question(update_or_context, context, chat_id):
    state = active_quiz.get(chat_id)
    if not state:
        return
    quiz = quizzes[state["quiz_id"]]
    q_index = state["current_q"]

    if q_index >= len(quiz["questions"]):
        await finish_quiz(update_or_context, context, chat_id)
        return

    q = quiz["questions"][q_index]
    msg = await context.bot.send_poll(
        chat_id=chat_id,
        question=f"❓ {q_index + 1}/{len(quiz['questions'])}: {q['question']}",
        options=q["options"],
        type=Poll.QUIZ,
        correct_option_id=q["correct"],
        explanation=q.get("explanation", ""),
        is_anonymous=False,
        open_period=30
    )
    poll_to_quiz[msg.poll.id] = {
        "chat_id": chat_id,
        "question_index": q_index,
        "correct_option": q["correct"]
    }
    state["current_poll_id"] = msg.poll.id

    # 35 soniyadan keyin keyingi savolga o'tish
    context.job_queue.run_once(
        next_question_job,
        35,
        data={"chat_id": chat_id, "poll_id": msg.poll.id},
        name=f"next_{chat_id}"
    )

async def next_question_job(context: ContextTypes.DEFAULT_TYPE):
    data = context.job.data
    chat_id = data["chat_id"]
    state = active_quiz.get(chat_id)
    if not state:
        return
    state["current_q"] += 1
    class FakeUpdate:
        effective_chat = type("C", (), {"id": chat_id})()
    await send_question(FakeUpdate(), context, chat_id)

async def poll_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.poll_answer
    poll_id = answer.poll_id
    if poll_id not in poll_to_quiz:
        return
    info = poll_to_quiz[poll_id]
    chat_id = info["chat_id"]
    state = active_quiz.get(chat_id)
    if not state:
        return

    user = answer.user
    user_name = user.full_name
    user_id = user.id

    if user_id not in state["scores"]:
        state["scores"][user_id] = 0
        state["participants"][user_id] = user_name

    selected = answer.option_ids
    if selected and selected[0] == info["correct_option"]:
        state["scores"][user_id] += 1

async def finish_quiz(update_or_context, context, chat_id):
    state = active_quiz.pop(chat_id, None)
    if not state:
        return

    quiz = quizzes[state["quiz_id"]]
    total = len(quiz["questions"])
    scores = state["scores"]
    participants = state["participants"]

    if not scores:
        await context.bot.send_message(chat_id, "⚠️ Hech kim javob bermadi.")
        return

    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    medals = ["🥇", "🥈", "🥉"]
    text = f"🏁 <b>{quiz['title']} — Natijalar!</b>\n\n"
    for i, (uid, score) in enumerate(sorted_scores):
        medal = medals[i] if i < 3 else f"{i+1}."
        name = participants.get(uid, "Noma'lum")
        percent = round(score / total * 100)
        text += f"{medal} <b>{name}</b>: {score}/{total} ({percent}%)\n"

    text += f"\n👥 Ishtirokchilar: {len(scores)} ta"
    await context.bot.send_message(chat_id, text, parse_mode="HTML")

# /toxtatish
async def stop_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    chat_id = update.effective_chat.id
    if chat_id not in active_quiz:
        await update.message.reply_text("⚠️ Hozir hech qanday test ketmayapti.")
        return
    await finish_quiz(update, context, chat_id)

# /ochir_quiz
async def delete_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Bu buyruq faqat adminlar uchun!")
        return
    if not context.args:
        await update.message.reply_text("❗ Ishlatish: /ochir_quiz [quiz_id]")
        return
    quiz_id = context.args[0]
    if quiz_id in quizzes:
        del quizzes[quiz_id]
        save_data()
        await update.message.reply_text(f"✅ {quiz_id} ID li test o'chirildi.")
    else:
        await update.message.reply_text("❌ Bunday test topilmadi.")

# Matnli xabarlarni qayta ishlash (quiz yaratish jarayoni)
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = context.user_data.get("creating_quiz")
    if not state:
        return

    text = update.message.text.strip()
    step = state["step"]

    if step == "title":
        state["title"] = text
        state["step"] = "question"
        state["current_q"] = {}
        await update.message.reply_text(
            f"✅ Test nomi: <b>{text}</b>\n\n"
            "2️⃣ Endi savolni yozing:\n"
            "<i>(Savolni kiritgan so'ng javob variantlarini so'rayman)</i>",
            parse_mode="HTML"
        )

    elif step == "question":
        state["current_q"]["question"] = text
        state["step"] = "options"
        state["current_q"]["options"] = []
        await update.message.reply_text(
            f"❓ Savol: <b>{text}</b>\n\n"
            "3️⃣ 1-variant javobini yozing:",
            parse_mode="HTML"
        )

    elif step == "options":
        opts = state["current_q"]["options"]
        opts.append(text)
        count = len(opts)
        if count < 4:
            await update.message.reply_text(f"✅ {count}-variant qabul qilindi.\n{count+1}-variant javobini yozing:")
        else:
            state["step"] = "correct"
            options_text = "\n".join([f"{i+1}. {o}" for i, o in enumerate(opts)])
            await update.message.reply_text(
                f"📋 Variantlar:\n{options_text}\n\n"
                "4️⃣ To'g'ri javob raqamini yozing (1-4):"
            )

    elif step == "correct":
        if text not in ["1", "2", "3", "4"]:
            await update.message.reply_text("❗ Faqat 1, 2, 3 yoki 4 raqamini yozing!")
            return
        state["current_q"]["correct"] = int(text) - 1
        state["step"] = "explanation"
        await update.message.reply_text(
            "5️⃣ Izoh yozing (ixtiyoriy, o'tkazish uchun '-' yozing):"
        )

    elif step == "explanation":
        state["current_q"]["explanation"] = "" if text == "-" else text
        state["questions"].append(state["current_q"])
        state["current_q"] = {}

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("➕ Yana savol qo'shish", callback_data="add_more")],
            [InlineKeyboardButton("✅ Testni saqlash", callback_data="save_quiz")]
        ])
        await update.message.reply_text(
            f"✅ Savol qo'shildi! Jami: {len(state['questions'])} ta savol.",
            reply_markup=keyboard
        )

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    state = context.user_data.get("creating_quiz")
    if not state:
        return

    if query.data == "add_more":
        state["step"] = "question"
        await query.message.reply_text("📝 Yangi savolni yozing:")

    elif query.data == "save_quiz":
        quiz_id = str(len(quizzes) + 1)
        quizzes[quiz_id] = {
            "title": state["title"],
            "questions": state["questions"]
        }
        save_data()
        context.user_data.pop("creating_quiz", None)
        await query.message.reply_text(
            f"🎉 Test saqlandi!\n\n"
            f"📌 ID: <code>{quiz_id}</code>\n"
            f"📝 Nom: <b>{state['title']}</b>\n"
            f"❓ Savollar: {len(state['questions'])} ta\n\n"
            f"▶️ Boshlash uchun: /boshlash {quiz_id}",
            parse_mode="HTML"
        )

def main():
    load_data()
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("quizlar", list_quizzes))
    app.add_handler(CommandHandler("yangi_quiz", new_quiz))
    app.add_handler(CommandHandler("boshlash", start_quiz))
    app.add_handler(CommandHandler("toxtatish", stop_quiz))
    app.add_handler(CommandHandler("ochir_quiz", delete_quiz))
    app.add_handler(PollAnswerHandler(poll_answer))
    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("✅ Bot ishga tushdi!")
    app.run_polling()

if __name__ == "__main__":
    main()

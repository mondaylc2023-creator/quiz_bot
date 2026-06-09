# 🤖 Telegram Quiz Bot — O'rnatish Yo'riqnomasi

## 1-qadam: Bot Token olish
1. Telegramda **@BotFather** ni oching
2. `/newbot` yozing
3. Bot nomini kiriting (masalan: `Mening Quiz Botim`)
4. Username kiriting (masalan: `mening_quiz_bot`)
5. BotFather sizga **TOKEN** beradi — uni saqlab qo'ying!

## 2-qadam: Telegram ID olish (Admin ID)
1. Telegramda **@userinfobot** ga `/start` yozing
2. U sizga Telegram ID ingizni ko'rsatadi
3. Uni saqlab qo'ying

## 3-qadam: Railway.app da joylash (BEPUL)

1. **https://railway.app** ga kiring
2. GitHub bilan ro'yxatdan o'ting (bepul)
3. **"New Project"** → **"Deploy from GitHub repo"** bosing
4. Bu fayllarni GitHub ga yuklang (yoki Railway template ishlating)
5. **Environment Variables** ga qo'shing:
   ```
   BOT_TOKEN = sizning_bot_tokeningiz
   ADMIN_IDS = sizning_telegram_id_ingiz
   ```
6. Deploy bosing — bot ishga tushadi! ✅

## Botni guruhga qo'shish
1. Botni guruhga qo'shing
2. Botni **Admin** qiling (poll yuborish uchun kerak)
3. `/start` bosing

## Buyruqlar

### Hammaga:
- `/start` — botni ishga tushirish
- `/quizlar` — testlar ro'yxatini ko'rish

### Faqat Admin:
- `/yangi_quiz` — yangi test yaratish
- `/boshlash [id]` — testni boshlash (masalan: `/boshlash 1`)
- `/toxtatish` — testni to'xtatish
- `/ochir_quiz [id]` — testni o'chirish

## Misol: Test yaratish
```
Admin: /yangi_quiz
Bot: Test nomini yozing
Admin: Matematika Testi
Bot: Savolni yozing
Admin: 2+2 nechaga teng?
Bot: 1-variant javobini yozing
Admin: 3
Bot: 2-variant...
Admin: 4
...
Bot: To'g'ri javob raqamini yozing (1-4)
Admin: 2
Bot: ✅ Saqlandi! ID: 1
Admin: /boshlash 1
```

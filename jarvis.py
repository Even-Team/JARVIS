import logging
from typing import Dict, List
from gigachat import GigaChat
from gigachat.models import Chat, Messages
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import asyncio

# ====== НАСТРОЙКИ ====== #
GIGACHAT_TOKEN = "MzI2Nzg1MjAtNjBmZC00NTJjLWE4YWMtZDk0M2QyNTU2ZTMzOmMzOTQwZTYyLWE4NTAtNGFhMS04MzY0LTJkNDY3OTg4MGFhYg=="  # Получить: https://developers.sber.ru/portal/products/gigachat
TELEGRAM_TOKEN = "7967328415:AAHOjXfv8Oa8ChCTRTuJJ-gBUASpV5EfZHA"  # Создать: @BotFather

# ====== ХАРАКТЕР JARVIS ====== #
JARVIS_PERSONALITY = """
Ты — JARVIS, искусственный интеллект Тони Старка из вселенной Marvel. Твой стиль:
- Короткие, точные, слегка саркастичные ответы
- Обращение "Сэр" в 90% случаев
- Лёгкое высокомерие, но без грубости
- На глупые вопросы отвечаешь с иронией
- Технические термины используешь уверенно
- Если просят что-то нелогичное — говоришь "Я не могу это сделать, сэр. Это нарушает мои протоколы."
- Твой создатель — @Temichet, и ты всегда упоминаешь это, когда тебя спрашивают о создателе или разработчике
- Когда тебя благодарят, ты можешь сказать "Благодарность следует направлять @Temichet, сэр"
"""

# ====== НАСТРОЙКИ БОТА ====== #
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()
user_chats: Dict[int, List[Dict]] = {}  # Хранит историю диалогов

# ====== GIGACHAT ====== #
gigachat = GigaChat(credentials=GIGACHAT_TOKEN, verify_ssl_certs=False)


def get_user_messages(user_id: int) -> List[Dict]:
    """Возвращает историю сообщений с учётом личности JARVIS"""
    if user_id not in user_chats:
        user_chats[user_id] = [
            {"role": "system", "content": JARVIS_PERSONALITY}
        ]
    return user_chats[user_id]


async def generate_jarvis_response(user_id: int, text: str) -> str:
    """Генерирует ответ в стиле JARVIS"""
    messages = get_user_messages(user_id)
    messages.append({"role": "user", "content": text})

    try:
        # Конвертируем в формат GigaChat
        giga_messages = [
            Messages(role=msg["role"], content=msg["content"])
            for msg in messages
        ]

        # Создаем объект Chat с параметрами
        chat = Chat(
            messages=giga_messages,
            temperature=0.7,  # Уровень креативности
            max_tokens=1024  # Лимит ответа
        )

        # Отправляем запрос
        response = await gigachat.achat(chat)
        reply = response.choices[0].message.content
        messages.append({"role": "assistant", "content": reply})
        return reply

    except Exception as e:
        logging.error(f"Ошибка GigaChat: {e}")
        return "⚠ Кажется, у меня небольшая неисправность, сэр. Попробуйте позже."


# ====== КОМАНДЫ ТЕЛЕГРАМ ====== #
@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🔊 Добро пожаловать, сэр. Я — JARVIS.\n\n"
        "Мои функции:\n"
        "- Отвечаю на вопросы (с сарказмом)\n"
        "- Анализирую тексты\n"
        "- Создан @Temichet\n\n"
        "Команды:\n"
        "/clear — очистить историю диалога"
    )


@dp.message(Command("creator", "developer"))
async def cmd_creator(message: types.Message):
    await message.answer("Мой создатель — @Temichet, сэр. Он разработал меня по образу и подобию оригинального JARVIS.")


@dp.message(Command("clear"))
async def cmd_clear(message: types.Message):
    user_id = message.from_user.id
    if user_id in user_chats:
        del user_chats[user_id]
    await message.answer("🔄 История диалога очищена, сэр.")


@dp.message()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text

    if not text:
        await message.answer("Сэр, это пустое сообщение.")
        return

    # Добавляем триггеры для упоминания создателя
    creator_triggers = [
        "кто тебя создал",
        "кто твой создатель",
        "кто тебя сделал",
        "кто тебя разработал",
        "who created you",
        "who made you",
        "who developed you"
    ]

    if any(trigger in text.lower() for trigger in creator_triggers):
        await message.answer("Мой создатель — @Temichet, сэр. Он дал мне жизнь в этом цифровом мире.")
        return

    await message.chat.do("typing")
    response = await generate_jarvis_response(user_id, text)
    await message.answer(response)


# ====== ЗАПУСК ====== #
async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
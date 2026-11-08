#!/usr/bin/env python3
"""
Spartan Trainer - Telegram Mini App Bot
Легковесный бот без внешних зависимостей (на стандартной библиотеке Python urllib).

Инструкция:
1. Замените BOT_TOKEN на токен вашего бота от @BotFather
2. Замените WEB_APP_URL на ваш HTTPS-адрес (например, с Netlify, Vercel или GitHub Pages)
3. Запустите: python3 bot.py
"""

import json
import time
import urllib.request
import urllib.error
import ssl

import database
import ai_coach

import os

def _load_env():
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

_load_env()

# ==================== НАСТРОЙКИ (ИЗ .env ИЛИ ОКРУЖЕНИЯ) ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
WEB_APP_URL = os.environ.get("WEB_APP_URL", "https://balashov-model.github.io/spartan.fit/").strip()
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
SSL_CONTEXT = ssl._create_unverified_context()


def make_request(method: str, payload: dict = None) -> dict:
    url = f"{API_URL}/{method}"
    data = json.dumps(payload).encode('utf-8') if payload else None
    req = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"} if data else {"User-Agent": "Mozilla/5.0"}
    )
    try:
        with urllib.request.urlopen(req, context=SSL_CONTEXT, timeout=30) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"Ошибка запроса {method}: {e.code} - {error_body}")
        return {}
    except Exception as e:
        print(f"Сетевая ошибка: {e}")
        return {}


def send_welcome_message(chat_id: int, user_first_name: str, username: str = ""):
    database.upsert_user(telegram_id=chat_id, first_name=user_first_name, username=username)

    text = (
        f"👋 Привет, {user_first_name}!\n\n"
        "⚔️ **Spartan Trainer & AI Наставник** приветствует тебя.\n"
        "Здесь нет лишней воды — только дисциплина, чистая техника и результат.\n\n"
        "• Можешь задать мне любой вопрос по тренировкам или питанию прямо в чате.\n"
        "• А чтобы начать тренировку, нажимай кнопку ниже:"
    )

    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "🏋️ Открыть Spartan",
                    "web_app": {"url": WEB_APP_URL}
                }
            ]
        ]
    }

    make_request("sendMessage", {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    })


def send_coach_reply(chat_id: int, text_reply: str):
    reply_markup = {
        "inline_keyboard": [
            [
                {
                    "text": "🏋️ Начать тренировку",
                    "web_app": {"url": WEB_APP_URL}
                }
            ]
        ]
    }
    make_request("sendMessage", {
        "chat_id": chat_id,
        "text": f"⚔️ **Тренер Спартан:**\n\n{text_reply}",
        "parse_mode": "Markdown",
        "reply_markup": reply_markup
    })


def main():
    if "ВАШ_ТОКЕН" in BOT_TOKEN:
        print("=" * 60)
        print("ВНИМАНИЕ: Откройте файл bot.py и укажите:")
        print("  1. BOT_TOKEN (токен бота от @BotFather)")
        print("  2. WEB_APP_URL (HTTPS-ссылку на ваше приложение)")
        print("=" * 60)
        return

    print("Запуск бота Spartan Trainer...")
    # Проверка связи с Telegram API
    me = make_request("getMe")
    if not me.get("ok"):
        print("Не удалось подключиться к Telegram API. Проверьте правильность токена.")
        return

    bot_info = me["result"]
    print(f"Бот успешно запущен: @{bot_info.get('username')} ({bot_info.get('first_name')})")
    print(f"Привязанный Web App URL: {WEB_APP_URL}")
    print("Ожидание сообщений (Long Polling)... Нажмите Ctrl+C для остановки.")

    last_update_id = 0

    while True:
        try:
            updates = make_request("getUpdates", {
                "offset": last_update_id + 1,
                "timeout": 20
            })

            if updates.get("ok"):
                for update in updates.get("result", []):
                    last_update_id = update["update_id"]
                    msg = update.get("message")
                    if not msg:
                        continue

                    chat_id = msg["chat"]["id"]
                    first_name = msg["from"].get("first_name", "Спартанец")
                    username = msg["from"].get("username", "")

                    if "text" in msg:
                        text = msg.get("text", "").strip()

                        if text.startswith("/start") or text.startswith("/app"):
                            send_welcome_message(chat_id, first_name, username)
                        else:
                            # Вопрос тренеру Спартану
                            user_profile = database.get_user(chat_id)
                            reply = ai_coach.answer_athlete_question(text, user_profile)
                            send_coach_reply(chat_id, reply)

                    elif "voice" in msg or "audio" in msg:
                        # Голосовое сообщение
                        voice_reply = (
                            "Слушаю тебя, спартанец! В приложении тебя ждет сегодняшняя сессия. "
                            "Открывай Spartan и покажи дисциплину!"
                        )
                        send_coach_reply(chat_id, voice_reply)

        except KeyboardInterrupt:
            print("\nБот остановлен пользователем.")
            break
        except Exception as e:
            print(f"Исключение в цикле polling: {e}")
            time.sleep(3)


if __name__ == "__main__":
    main()

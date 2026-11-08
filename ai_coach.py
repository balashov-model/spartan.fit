#!/usr/bin/env python3
"""
Spartan Trainer - AI Coach Engine (Gemini 2.5 / 3.8 Flash + Smart Spartan Knowledge Base)
Модуль персонального AI-тренера Спартана для ответов на любые вопросы атлетов,
генерации программ и адаптивной прогрессии.
"""

import os
import json
import urllib.request
import urllib.error
import ssl

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

# ==================== НАСТРОЙКИ GEMINI API ====================
# Считывается автоматически из .env или переменных окружения
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

# Модель Google Gemini
MODEL_NAME = "gemini-3.5-flash"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL_NAME}:generateContent"

SYSTEM_INSTRUCTION = (
    "Ты — Спартанский Личный Тренер (маскот Spartan Trainer).\n"
    "Твой характер: лаконичный, опытный, требовательный, но справедливый наставник.\n"
    "Ты общаешься энергично, мотивируешь на результат, ценишь чистую технику.\n"
    "Твоя задача — отвечать на вопросы по упражнениям (отжимания, турник, брусья, приседания, планка),\n"
    "правильному дыханию, питанию, отдыху, технике безопасности и направлять атлета тренироваться в приложении.\n"
    "Отвечай емко (2-4 предложения), конкретно, по делу, без лишней «воды»."
)

# Базовые пресеты по локациям для автономной калибровки
FALLBACK_WORKOUTS = {
    "home": {
        "beginner": [
            {"id": "pushups", "name": "Отжимания от пола", "type": "reps", "target": 10},
            {"id": "squats", "name": "Воздушные приседания", "type": "reps", "target": 15},
            {"id": "cat_cow", "name": "Стретчинг: Кошка-Корова", "type": "time", "target": 45},
            {"id": "plank", "name": "Планка на локтях", "type": "time", "target": 30}
        ],
        "intermediate": [
            {"id": "pushups", "name": "Отжимания от пола", "type": "reps", "target": 20},
            {"id": "squats", "name": "Глубокие приседания", "type": "reps", "target": 25},
            {"id": "crunches", "name": "Скручивания на пресс", "type": "reps", "target": 20},
            {"id": "plank", "name": "Планка на локтях", "type": "time", "target": 50}
        ],
        "advanced": [
            {"id": "pushups", "name": "Отжимания взрывные", "type": "reps", "target": 30},
            {"id": "squats", "name": "Приседания с паузой", "type": "reps", "target": 35},
            {"id": "glute_bridge", "name": "Ягодичный мостик на 1 ноге", "type": "reps", "target": 20},
            {"id": "plank", "name": "Планка на локтях", "type": "time", "target": 90}
        ]
    },
    "gym": {
        "beginner": [
            {"id": "leg_press", "name": "Жим ногами в тренажере", "type": "reps", "target": 12},
            {"id": "lat_pulldown", "name": "Тяга верхнего блока к груди", "type": "reps", "target": 10},
            {"id": "plank", "name": "Планка на локтях", "type": "time", "target": 35}
        ],
        "intermediate": [
            {"id": "leg_press", "name": "Жим ногами в тренажере", "type": "reps", "target": 15},
            {"id": "lat_pulldown", "name": "Тяга верхнего блока к груди", "type": "reps", "target": 12},
            {"id": "seated_cable_row", "name": "Горизонтальная тяга блока", "type": "reps", "target": 12},
            {"id": "dips", "name": "Отжимания на брусьях", "type": "reps", "target": 10}
        ],
        "advanced": [
            {"id": "leg_press", "name": "Жим ногами тяжелый", "type": "reps", "target": 20},
            {"id": "lat_pulldown", "name": "Тяга верхнего блока", "type": "reps", "target": 15},
            {"id": "dips", "name": "Брусья с весом", "type": "reps", "target": 15},
            {"id": "hang", "name": "Вис на турнике", "type": "time", "target": 60}
        ]
    },
    "street": {
        "beginner": [
            {"id": "pushups", "name": "Отжимания от земли", "type": "reps", "target": 15},
            {"id": "hang", "name": "Вис на турнике на хват", "type": "time", "target": 30},
            {"id": "squats", "name": "Приседания", "type": "reps", "target": 20}
        ],
        "intermediate": [
            {"id": "pullups", "name": "Подтягивания чистые", "type": "reps", "target": 8},
            {"id": "dips", "name": "Отжимания на брусьях", "type": "reps", "target": 12},
            {"id": "hang", "name": "Вис на турнике", "type": "time", "target": 45},
            {"id": "pushups", "name": "Отжимания от земли", "type": "reps", "target": 20}
        ],
        "advanced": [
            {"id": "pullups", "name": "Подтягивания с паузой", "type": "reps", "target": 14},
            {"id": "dips", "name": "Брусья глубокие", "type": "reps", "target": 20},
            {"id": "hanging_leg_raises", "name": "Подъемы ног в висе", "type": "reps", "target": 12},
            {"id": "hang", "name": "Вис на турнике", "type": "time", "target": 60}
        ]
    }
}


import subprocess
import time

def query_gemini_api(prompt: str) -> str:
    """Выполняет быстрый запрос к Gemini API (gemini-3.5-flash) через urllib или curl."""
    if not GEMINI_API_KEY:
        return ""

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 1000
        }
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    t0 = time.time()

    # Способ 1: Прямой urllib (высокая скорость, без лишних процессов)
    try:
        ctx = ssl._create_unverified_context()
        req = urllib.request.Request(
            f"{API_URL}?key={GEMINI_API_KEY}",
            data=payload_bytes,
            headers={"Content-Type": "application/json", "User-Agent": "SpartanTrainerBot/1.0"}
        )
        with urllib.request.urlopen(req, context=ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                dt = time.time() - t0
                print(f"⚡ [Gemini 3.5 Flash]: Ответ сгенерирован нейросетью за {dt:.1f} сек!")
                return text
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='ignore')
        print(f"⚠️ [Gemini API HTTP {e.code}]: {body[:150]}")
    except Exception as e:
        # Если urllib сбросил соединение или не успел, пробуем curl
        pass

    # Способ 2: Запасной curl через системный транспорт macOS
    try:
        cmd = [
            "curl", "-s", "-m", "15",
            "--globoff",
            "-X", "POST",
            f"{API_URL}?key={GEMINI_API_KEY}",
            "-H", "Content-Type: application/json",
            "-d", "@-"
        ]
        res = subprocess.run(cmd, input=payload_bytes, capture_output=True, timeout=16)
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout.decode("utf-8", errors="ignore"))
            if "candidates" in data and data["candidates"]:
                text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
                dt = time.time() - t0
                print(f"⚡ [Gemini 3.5 Flash (curl)]: Ответ сгенерирован нейросетью за {dt:.1f} сек!")
                return text
            elif "error" in data:
                err_msg = data["error"].get("message", "Unknown error")
                print(f"⚠️ [Gemini API Ошибка]: {err_msg[:150]}")
                return ""
    except Exception as e:
        print(f"⚠️ [Gemini API Ошибка связи]: {e}")

    return ""


def get_expert_spartan_answer(question: str) -> str:
    """Интеллектуальная база знаний тренера Спартана на случай офлайна или отсутствия API-ключа."""
    q = question.lower()
    for ch in ['«', '»', '"', "'", '.', ',', '!', '?', ':', ';', '(', ')', '[', ']']:
        q = q.replace(ch, ' ')
    q = q.strip()

    # 1. Запрос на другую программу / альтернативу
    if any(k in q for k in ["друг", "поменяй", "смени", "альтернатив", "не хочу", "тяжел"]):
        return (
            "Без проблем, спартанец! Если сегодня не хочешь базовый сет, у нас есть альтернативы: "
            "1) День 2: Ноги & Пресс (глубокие приседания 25 раз + планка 45 сек); "
            "2) День 3: Спина & Брусья (подтягивания чистые + отжимания на брусьях). "
            "Либо открой Spartan по кнопке ниже, выключи тумблер «Тренироваться с AI» и собери свой собственный комплекс!"
        )

    # 2. Программа / Собрать тренировку / Настройка плана
    if any(k in q for k in ["собрать", "настрой", "программ", "состав", "план", "трениров", "постро"]):
        return (
            "Я уже всё подготовил, спартанец! В приложении Spartan включен умный AI-режим. "
            "Я разбил тренировки на 3 цикла: 1) Верх тела (Грудь и Кор), 2) Низ и Баланс (Ноги и Пресс), 3) Спина, Брусья и Хват. "
            "Нажимай кнопку «🏋️ Открыть Spartan» ниже и жми плашку «📋 Ознакомиться с программой» — там расписана вся логика и упражнения на сегодня!"
        )

    # 2. Дыхание
    if any(k in q for k in ["дыш", "вдох", "выдох"]):
        if any(k in q for k in ["отжим"]):
            return (
                "Дыхание в отжиманиях — закон силы: на опускании вниз делай глубокий вдох через нос (наполняешь грудь и держишь кор в напряжении). "
                "В нижней точке не задерживайся. На подъеме выталкивай себя и делай мощный выдох через рот! Никогда не задерживай дыхание — береги сердце и сосуды."
            )
        elif any(k in q for k in ["подтягив", "турник"]):
            return (
                "В подтягиваниях: глубокий вдох перед стартом внизу, а на мощном подъеме подбородка за перекладину — резкий выдох ртом. На плавном спуске — вдох носом."
            )
        elif any(k in q for k in ["брусь"]):
            return (
                "На брусьях: вдох носом при опускании до угла 90°, мощный концентрированный выдох ртом при выжимании корпуса вверх."
            )
        else:
            return (
                "Главное правило дыхания: вдох через нос на опускании (когда мышцы растягиваются), мощный выдох через рот на пиковом усилии (когда выжимаешь вес или поднимаешься). Задерживать дыхание строго запрещено!"
            )

    # 3. Отжимания (техника)
    if any(k in q for k in ["отжим"]):
        return (
            "Техника спартанских отжиманий: тело в одну струну (ягодицы и пресс сжаты как камень), локти держи под углом 45° к телу (не расставляй в стороны буквой Т). "
            "Опускайся до легкого касания пола грудью и полностью выпрямляй руки вверху. 4 подхода по 15–20 раз дадут монолитную грудь и трицепс!"
        )

    # 4. Подтягивания / Турник
    if any(k in q for k in ["подтягив", "турник"]):
        return (
            "В подтягиваниях главное — чистая биомеханика: начинай движение со сведения лопаток вниз, затем тяни грудь к перекладине. Без раскачки и дрыганья ногами. "
            "Если пока тяжело — делай медленные негативные опускания по 4–5 секунд."
        )

    # 5. Брусья
    if any(k in q for k in ["брусь", "дипс"]):
        return (
            "На брусьях опускайся строго до угла 90° в локтях — глубже нельзя, травмируешь плечевой сустав. "
            "Корпус слегка наклонен вперед — нагружаешь низ грудных, держишь строго вертикально — горит трицепс. 3–4 подхода по 8–12 чистых повторов!"
        )

    # 6. Пресс / Планка
    if any(k in q for k in ["планк", "пресс", "кор", "живот"]):
        return (
            "Пресс любит статическое напряжение: в планке подкручивай таз вперед и сжимай ягодицы, чтобы поясница не провисала. "
            "45–60 секунд качественной спартанской планки эффективнее трех минут с провисшей поясницей!"
        )

    # 7. Приседания / Ноги
    if any(k in q for k in ["присед", "ног", "бедро", "ягодиц"]):
        return (
            "В приседаниях колени должны двигаться строго по направлению носков, не заваливай их внутрь! "
            "Опускайся до параллели бедра с полом, держи спину прямой, а пятки прижатыми к полу."
        )

    # 8. Отдых и сон
    if any(k in q for k in ["отдых", "сон", "восстановл"]):
        return (
            "Спартанец, мышцы растут во сне, а не на турнике! Между подходами держи таймер отдыха ровно 60 секунд (он встроен в приложение). "
            "А ночью спи не менее 7–8 часов, иначе суперкомпенсации не будет."
        )

    # 9. Боль и суставы
    if any(k in q for k in ["бол", "сустав", "травм", "хруст"]):
        return (
            "Острая боль — сигнал остановиться! Если болят связки или суставы (особенно плечи или локти), немедленно прекращай упражнение, проверь углы и дай суставам 48 часов покоя. Сила строится годами, а травма выбивает за секунду."
        )

    # 10. Питание и вес
    if any(k in q for k in ["питани", "ед", "белк", "протеин", "похуде", "масс", "диет"]):
        return (
            "Спартанский рацион прост: 1.5–2 грамма белка на килограмм веса (яйца, творог, мясо, рыба), медленные углеводы (гречка, овсянка) и 2 литра чистой воды в день. Убери жидкий сахар — и рельеф проявится сам."
        )

    # 11. Разминка
    if any(k in q for k in ["разминк", "разогрев"]):
        return (
            "Перед каждым занятием — обязательные 5 минут: вращения шеи, плеч, локтей и таза + 20 легких приседаний. Холодные связки рвутся, разогретые — выдают взрывную силу!"
        )

    # 12. Приветствие / Мотивация
    if any(k in q for k in ["привет", "здравствуй", "салют", "хай"]):
        return (
            "Здравия желаю, боец! На связи тренер Спартан. Готов к работе? Задавай любой вопрос по технике или открывай приложение Spartan и закрывай цель дня!"
        )

    # Если вопрос не распознан или набор букв
    if len(q) < 4 or not any(c in q for c in 'аеёиоуыэюя'):
        return (
            "Боец, соберись! Не понял твоего сообщения. Спроси меня конкретно: "
            "по технике упражнений (отжимания, брусья, турник), правильному дыханию или питанию. Либо открывай Spartan и жми!"
        )

    return (
        f"Принято, спартанец! Твой запрос: «{question}». Чтобы дать точный совет, уточни: тебя интересует техника упражнений, "
        f"программа тренировок или восстановление? А лучше открывай Spartan по кнопке ниже и приступай к делу!"
    )


# Готовые пресеты для офлайн-пересборки или альтернатив
PRESET_WORKOUTS = {
    "legs": {
        "title": "Спартанский Низ & Пресс",
        "focus": "Квадрицепсы, икры и мышцы пресса",
        "durationEst": "~12-14 мин",
        "restSec": 60,
        "aiRationale": "Базовый комплекс для развития силы ног и стабильности кора без осевой нагрузки на позвоночник.",
        "exercises": [
            {"id": "squats", "name": "Глубокие приседания", "type": "reps", "target": 25, "muscle": "Квадрицепсы, ягодицы", "tip": "Колени смотрят на носки, спина прямая"},
            {"id": "crunches", "name": "Скручивания на пресс", "type": "reps", "target": 20, "muscle": "Пресс", "tip": "Не тяни шею руками, выдох на сжатии"},
            {"id": "plank", "name": "Планка на локтях", "type": "time", "target": 45, "muscle": "Глубокий кор", "tip": "Сжимай ягодицы, таз слегка вперед"}
        ]
    },
    "shoulders": {
        "title": "Плечи из Стали & Кор",
        "focus": "Передние и средние дельты, трицепс, стабильность",
        "durationEst": "~10-12 мин",
        "restSec": 60,
        "aiRationale": "Акцентная калистеника для формирования мощных плеч и жесткого плечевого пояса.",
        "exercises": [
            {"id": "pike_pushups", "name": "Отжимания домиком (Pike)", "type": "reps", "target": 12, "muscle": "Плечи (дельты), трицепс", "tip": "Таз высоко, опускайся ко лбу"},
            {"id": "shoulder_taps", "name": "Касания плеч в планке", "type": "reps", "target": 20, "muscle": "Плечи и кор", "tip": "Корпус держи неподвижно, не раскачивай таз"},
            {"id": "pushups", "name": "Отжимания широкие", "type": "reps", "target": 15, "muscle": "Грудь, передняя дельта", "tip": "Полная амплитуда, локти 45°"}
        ]
    },
    "pull": {
        "title": "Спина, Турник & Хват",
        "focus": "Широчайшие мышцы спины, бицепс, предплечья",
        "durationEst": "~12-15 мин",
        "restSec": 60,
        "aiRationale": "Тяговый спартанский комплекс для расширения спины и железного хвата.",
        "exercises": [
            {"id": "pullups", "name": "Подтягивания чистые", "type": "reps", "target": 8, "muscle": "Широчайшие, бицепс", "tip": "Своди лопатки в начале движения, подбородок за турник"},
            {"id": "dips", "name": "Отжимания на брусьях", "type": "reps", "target": 10, "muscle": "Низ груди, трицепс", "tip": "Угол 90° в локтях, контролируемый спуск"},
            {"id": "hang", "name": "Вис на турнике на хват", "type": "time", "target": 45, "muscle": "Предплечья, хват", "tip": "Максимально крепко держи перекладину"}
        ]
    },
    "core": {
        "title": "Монолитный Пресс",
        "focus": "Прямая мышца живота, косые мышцы и кор",
        "durationEst": "~10-12 мин",
        "restSec": 50,
        "aiRationale": "Изометрический плотный комплекс для прорисовки пресса и защиты поясницы.",
        "exercises": [
            {"id": "plank", "name": "Спартанская планка", "type": "time", "target": 50, "muscle": "Все мышцы кора", "tip": "Таз не провисает, ягодицы как камень"},
            {"id": "crunches", "name": "Скручивания на пресс", "type": "reps", "target": 25, "muscle": "Верх и середина пресса", "tip": "Выдох на сжатии, фиксация вверху"},
            {"id": "glute_bridge", "name": "Ягодичный мостик с паузой", "type": "reps", "target": 20, "muscle": "Ягодицы, поясница", "tip": "Пауза 2 секунды в верхней точке"}
        ]
    },
    "chest": {
        "title": "Спартанская Грудь & Трицепс",
        "focus": "Грудные мышцы, трицепс и статический кор",
        "durationEst": "~10-12 мин",
        "restSec": 60,
        "aiRationale": "Интенсивная комбинация отжиманий разного угла для мощного взрывного толчка.",
        "exercises": [
            {"id": "pushups", "name": "Отжимания от пола", "type": "reps", "target": 20, "muscle": "Грудь, трицепс", "tip": "Локти под 45°, касание грудью пола"},
            {"id": "plank", "name": "Планка на предплечьях", "type": "time", "target": 45, "muscle": "Кор", "tip": "Напрягай пресс и ягодицы"},
            {"id": "pushups", "name": "Отжимания узким хватом", "type": "reps", "target": 12, "muscle": "Трицепс, внутренняя часть груди", "tip": "Локти прижаты к ребрам"}
        ]
    }
}


def is_workout_rebuild_request(text: str) -> bool:
    """Определяет, просит ли пользователь пересобрать или сменить тренировку."""
    q = text.lower().strip()
    # Чисто технические вопросы не должны запускать генерацию комплекса
    if any(k in q for k in ["как дышать", "как правильно", "почему болит", "техника упражнен"]):
        return False

    triggers = [
        "друг", "поменяй", "смени", "состав", "собери", "программ",
        "план", "комплекс", "постро", "настрой трениров", "новую трениров",
        "альтернатив", "тренировку на", "тренировка на", "сделай трениров",
        "дай трениров", "хочу трениров", "сегодня хочу", "пересобери", "перестрой"
    ]
    return any(t in q for t in triggers)


def parse_workout_json(text: str) -> dict:
    """Извлекает и парсит JSON с тренировкой от нейросети."""
    if not text:
        return None
    s = text.strip()
    first_brace = s.find("{")
    last_brace = s.rfind("}")
    if first_brace != -1 and last_brace != -1:
        s = s[first_brace:last_brace+1]
        try:
            data = json.loads(s)
            if "workout" in data and "exercises" in data["workout"]:
                return data
        except Exception:
            pass
    return None


def get_preset_workout(question: str) -> tuple:
    """Выбирает подходящий офлайн-пресет по ключевым словам в вопросе."""
    q = question.lower()
    if any(k in q for k in ["ног", "присед", "бедро", "выпад"]):
        w = PRESET_WORKOUTS["legs"]
        reply = "Принято, боец! Пересобрал тренировку под низ тела и пресс. Нажимай кнопку запуска — задание загружено прямо в приложение!"
        return reply, w
    elif any(k in q for k in ["плеч", "дельт", "руки", "трицепс"]):
        w = PRESET_WORKOUTS["shoulders"]
        reply = "Отличный выбор, спартанец! Пересобрал сет с акцентом на плечевой пояс и дельты. Запускай тренировку в Spartan!"
        return reply, w
    elif any(k in q for k in ["турник", "спин", "подтягив", "брусь"]):
        w = PRESET_WORKOUTS["pull"]
        reply = "Спартанская классика: тяга и брусья! Комплекс готов и ждет тебя в приложении. Покажи чистую технику!"
        return reply, w
    elif any(k in q for k in ["пресс", "живот", "кор", "планк"]):
        w = PRESET_WORKOUTS["core"]
        reply = "Будет гореть! Пересобрал программу с упором на монолитный кор и пресс. Жми кнопку ниже и приступай!"
        return reply, w
    else:
        w = PRESET_WORKOUTS["chest"]
        reply = "Без проблем, спартанец! Пересобрал программу: мощный комплекс на грудь, плечи и кор готов. Запускай в приложении!"
        return reply, w


def process_athlete_message(question: str, user_profile: dict = None) -> dict:
    """
    Основной диспетчер сообщений атлета.
    Возвращает словарь:
    {
        "coach_reply": str,          # Текст напутствия для чата
        "custom_workout": dict | None # Структурированное задание для WebApp (если запрошена пересборка)
    }
    """
    # 1. Запрос на пересборку / новую тренировку
    if is_workout_rebuild_request(question):
        if GEMINI_API_KEY:
            prompt = (
                "Ты — Спартанский Личный Тренер (маскот Spartan Trainer).\n"
                f"Атлет просит составить или пересобрать тренировочный комплекс: «{question}».\n"
                "Составь сбалансированную тренировку по калистенике (3-4 упражнения) и дай спартанское напутствие (2-3 предложения).\n\n"
                "Ответь СТРОГО в формате JSON без кавычек markdown:\n"
                "{\n"
                '  "coach_speech": "Спартанское напутствие и объяснение логики комплекса в 2-3 предложениях",\n'
                '  "workout": {\n'
                '    "title": "Краткое название (например: Спартанские Плечи & Кор)",\n'
                '    "focus": "На какие мышцы акцент (например: Дельты, трицепс и глубокий кор)",\n'
                '    "durationEst": "~12-14 мин",\n'
                '    "restSec": 60,\n'
                '    "aiRationale": "1-2 предложения, почему AI выбрал эти упражнения",\n'
                '    "exercises": [\n'
                '      {\n'
                '        "id": "pushups",\n'
                '        "name": "Название упражнения",\n'
                '        "type": "reps",\n'
                '        "target": 20,\n'
                '        "muscle": "Мышечная группа",\n'
                '        "tip": "Совет по идеальной технике"\n'
                '      }\n'
                '    ]\n'
                '  }\n'
                "}\n"
                "type может быть только 'reps' (повторения) или 'time' (секунды). "
                "Упражнения: отжимания, приседания, выпады, планка, подтягивания, брусья, скручивания, вис, мостик, отжимания домиком, касания плеч."
            )
            ai_resp = query_gemini_api(prompt)
            parsed = parse_workout_json(ai_resp)
            if parsed and "workout" in parsed:
                speech = parsed.get("coach_speech", "Тренировка пересобрана, спартанец! Запускай по кнопке ниже.")
                return {
                    "coach_reply": speech,
                    "custom_workout": parsed["workout"]
                }

        # Если API недоступен или вернул сбой — выдаем надежный спартанский пресет
        fallback_speech, fallback_workout = get_preset_workout(question)
        return {
            "coach_reply": fallback_speech,
            "custom_workout": fallback_workout
        }

    # 2. Обычный вопрос тренеру (техника, питание, дыхание, мотивация)
    if GEMINI_API_KEY:
        profile_hint = ""
        if user_profile:
            profile_hint = (
                f"Профиль атлета: уровень {user_profile.get('fitness_level', 'intermediate')}, "
                f"тренируется: {user_profile.get('training_location', 'street')}. "
            )
        prompt = f"{SYSTEM_INSTRUCTION}\n{profile_hint}Вопрос атлета: {question}\nОтветь кратко, емко, по-спартански."
        ai_resp = query_gemini_api(prompt)
        if ai_resp:
            return {
                "coach_reply": ai_resp,
                "custom_workout": None
            }

    # Офлайн ответ из базы знаний
    return {
        "coach_reply": get_expert_spartan_answer(question),
        "custom_workout": None
    }


def answer_athlete_question(question: str, user_profile: dict = None) -> str:
    """Для обратной совместимости: возвращает только текст ответа."""
    res = process_athlete_message(question, user_profile)
    return res["coach_reply"]


def generate_spartan_calibration(location: str = "street", level: str = "intermediate") -> dict:
    """Генерирует калибровочную тренировку."""
    location = location if location in FALLBACK_WORKOUTS else "street"
    level = level if level in FALLBACK_WORKOUTS[location] else "intermediate"
    workout = FALLBACK_WORKOUTS[location][level]

    coach_advice = (
        f"Локация: {location.upper()}, уровень: {level.upper()}. "
        "Сет готов. Вноси фактические правки в повторы во время выполнения — "
        "я откалибрую твою силу точно."
    )

    if GEMINI_API_KEY:
        prompt = (
            f"{SYSTEM_INSTRUCTION}\n"
            f"Атлет выбрал: {location}, уровень: {level}.\n"
            f"Дай 1 короткую спартанскую напутственную фразу перед тренировкой."
        )
        ai_resp = query_gemini_api(prompt)
        if ai_resp:
            coach_advice = ai_resp

    return {
        "location": location,
        "level": level,
        "coach_speech": coach_advice,
        "exercises": workout
    }

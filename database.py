#!/usr/bin/env python3
"""
Spartan Trainer - Модуль базы данных SQLite (spartan.db)
Работает на стандартной библиотеке Python sqlite3 (без сторонних зависимостей).
"""

import sqlite3
import json
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "spartan.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени: row["first_name"]
    return conn


def init_db():
    """Инициализация таблиц базы данных при первом запуске."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            first_name TEXT,
            username TEXT,
            training_location TEXT DEFAULT 'street', -- 'home', 'gym', 'street'
            fitness_level TEXT DEFAULT 'intermediate', -- 'beginner', 'intermediate', 'advanced'
            active_track TEXT DEFAULT 'progression', -- 'maintenance', 'progression', 'spartan_beast'
            default_rest_sec INTEGER DEFAULT 60,
            theme TEXT DEFAULT 'dark',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)

        # Таблица истории тренировок
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS workout_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            location TEXT,
            track TEXT,
            duration_sec INTEGER,
            total_reps INTEGER,
            exercises_json TEXT,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        # Таблица напоминаний и расписания
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            days_of_week TEXT DEFAULT 'mon,wed,fri',
            time_of_day TEXT DEFAULT '19:00',
            is_enabled INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
        """)

        conn.commit()
    print(f"База данных SQLite успешно инициализирована: {DB_PATH}")


def upsert_user(telegram_id: int, first_name: str = "", username: str = "", **kwargs) -> dict:
    """Создает или обновляет пользователя по его telegram_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("SELECT id FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()

        if row:
            # Обновление
            fields = ["last_active = ?"]
            values = [now]
            for key in ["first_name", "username", "training_location", "fitness_level", "active_track", "default_rest_sec", "theme"]:
                if key in kwargs and kwargs[key] is not None:
                    fields.append(f"{key} = ?")
                    values.append(kwargs[key])
            if first_name:
                fields.append("first_name = ?")
                values.append(first_name)
            if username:
                fields.append("username = ?")
                values.append(username)

            values.append(telegram_id)
            cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE telegram_id = ?", values)
        else:
            # Вставка нового
            cursor.execute("""
            INSERT INTO users (telegram_id, first_name, username, training_location, fitness_level, active_track, default_rest_sec, theme, created_at, last_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                telegram_id,
                first_name,
                username,
                kwargs.get("training_location", "street"),
                kwargs.get("fitness_level", "intermediate"),
                kwargs.get("active_track", "progression"),
                kwargs.get("default_rest_sec", 60),
                kwargs.get("theme", "dark"),
                now,
                now
            ))

        conn.commit()
        return get_user(telegram_id)


def get_user(telegram_id: int) -> dict:
    """Получает профиль пользователя в виде словаря."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE telegram_id = ?", (telegram_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def log_workout(telegram_id: int, duration_sec: int, total_reps: int, exercises: list, location: str = "street", track: str = "progression"):
    """Сохраняет завершенную тренировку."""
    user = get_user(telegram_id)
    if not user:
        user = upsert_user(telegram_id)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO workout_logs (user_id, location, track, duration_sec, total_reps, exercises_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            user["id"],
            location,
            track,
            duration_sec,
            total_reps,
            json.dumps(exercises, ensure_ascii=False)
        ))
        conn.commit()


def get_user_workouts(telegram_id: int, limit: int = 20) -> list:
    """Возвращает историю тренировок пользователя."""
    user = get_user(telegram_id)
    if not user:
        return []

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT * FROM workout_logs WHERE user_id = ? ORDER BY date DESC LIMIT ?
        """, (user["id"], limit))
        return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    init_db()
    # Тестовая проверка записи
    test_user = upsert_user(12345678, first_name="Тестовый Атлет", training_location="home", fitness_level="intermediate")
    print("Создан тестовый пользователь:", test_user)
    log_workout(12345678, duration_sec=840, total_reps=95, exercises=[{"name": "Отжимания", "reps": 20}], location="home")
    history = get_user_workouts(12345678)
    print("История тренировок (записей):", len(history))

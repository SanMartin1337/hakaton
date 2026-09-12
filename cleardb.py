"""
Полная очистка ОБЕИХ баз без удаления файлов:
  - app.db (SQLite): очищает users, friend_requests, user_events
  - teamup_db.json: очищает до пустого списка []
Запуск: python clear_all.py
"""
import json
import os

from sqlalchemy import text, inspect

from app.database import engine
from app.services.teamup import DB_FILE

# порядок важен: сначала дочерние таблицы, потом users
TABLES_TO_CLEAR = ["friend_requests", "user_events", "users"]


def clear_sqlite():
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())

    with engine.connect() as conn:
        for table in TABLES_TO_CLEAR:
            if table in existing:
                conn.execute(text(f"DELETE FROM {table}"))
                print(f"  ✅ таблица '{table}' очищена")
            else:
                print(f"  ⚠️ таблицы '{table}' нет — пропускаю")

        # сброс счётчиков id, чтобы новые юзеры снова шли с 1
        if "sqlite_sequence" in existing:
            conn.execute(text("DELETE FROM sqlite_sequence"))
            print("  ✅ счётчики id сброшены")

        conn.commit()


def clear_teamup():
    # файл НЕ удаляем — просто перезаписываем пустым списком
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump([], f, indent=4, ensure_ascii=False)
    print(f"  ✅ {os.path.basename(DB_FILE)} очищен до пустого списка")


if __name__ == "__main__":
    print("🧹 Очищаю базы данных (файлы остаются на месте)...")
    print("\n[1/2] SQLite (app.db):")
    clear_sqlite()
    print("\n[2/2] TeamUp (teamup_db.json):")
    clear_teamup()
    print("\n✅ Готово! Обе базы пустые, файлы НЕ удалены.")
    print("Теперь регистрируй демо-аккаунты и/или запускай python seed_demo.py")
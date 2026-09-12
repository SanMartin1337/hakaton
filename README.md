<div align="center">

#  Campus Connect — УрФУ

**Единая цифровая платформа кампуса: события, знакомства, менторство и ИИ-подбор команды**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.0-D71F00?logo=sqlalchemy&logoColor=white)](https://www.sqlalchemy.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

##  О проекте

**Campus Connect** — веб-платформа для студентов УрФУ, которая закрывает сразу несколько задач:

-  единая лента студенческих событий и мероприятий;
-  система друзей и заявок;
-  менторская программа (студенты помогают студентам);
-  **TeamUp** — подбор команды и участников проектов на основе ИИ (GigaChat);
-  личный кабинет, избранное, профиль с навыками.

Проект сделан на **FastAPI + SQLAlchemy + Jinja2**, с JWT-авторизацией через cookie.

---

## 🎬 Демонстрация

### Авторизация и регистрация
![Login demo](docs/gifs/auth.gif)

### Лента событий и избранное
![Events demo](docs/gifs/events.gif)

### Друзья и заявки
![Friends demo](docs/gifs/friends.gif)

### Менторская программа
![Mentors demo](docs/gifs/mentors.gif)

### TeamUp — ИИ-подбор команды
![TeamUp demo](docs/gifs/teamup.gif)

---

## ⚙️ Технологии

| Категория | Стек |
|---|---|
| Backend | FastAPI, Uvicorn |
| БД / ORM | SQLAlchemy, Alembic |
| Авторизация | python-jose (JWT), passlib + bcrypt |
| Шаблоны | Jinja2 |
| ИИ | GigaChat, scikit-learn |
| Конфиг | pydantic-settings, python-dotenv |

---

## 🚀 Быстрый старт

```bash
# 1. Клонируем репозиторий
git clone https://github.com/SanMartin1337/hakaton.git
cd hakaton

# 2. Создаём виртуальное окружение
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 3. Устанавливаем зависимости
pip install -r requirements.txt

# 4. Настраиваем переменные окружения
cp .env.example .env           # заполни SECRET_KEY, ключи GigaChat и т.д.

# 5. Запускаем сервер
python main.py
# либо: uvicorn main:app --reload
```

Приложение будет доступно на `http://127.0.0.1:8000`.

---

## 📂 Структура проекта

```
hakaton/
├── app/
│   ├── api/v1/          # роуты: auth, chat, users
│   ├── models/           # User, FriendRequest, UserEvent
│   ├── services/         # teamup.py — интеграция с GigaChat
│   ├── templates/        # Jinja2-шаблоны
│   └── static/           # статика (css/js/images)
├── main.py               # точка входа FastAPI
├── requirements.txt
└── .env
```

---

##  Основные возможности

- [x] Регистрация и вход по email/паролю (JWT в httponly cookie)
- [x] Лента событий с добавлением в избранное
- [x] Система заявок в друзья / менторы
- [x] Личный кабинет с профилем и навыками
- [x] TeamUp: ИИ-подбор тиммейтов по текстовому описанию
- [ ] Уведомления в реальном времени
- [ ] Мобильная версия


<div align="center">

Сделано с ❤️ для студентов УрФУ

</div>

import os
import re
import json

import requests
import urllib3

from app.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# база TeamUp лежит в корне проекта (рядом с main.py)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_FILE = os.path.join(BASE_DIR, "teamup_db.json")
MODEL_NAME = "GigaChat"   # обычная модель — та же, что у AI-виджета

JSON_SYSTEM_PROMPT = (
    "Ты — строгий механизм извлечения данных для платформы «UrFU TeamUp».\n"
    "Проанализируйте текст, введенный пользователем, и определите тип его профиля.\n\n"
    "Важные правила:\n"
    "1. Отвечайте ТОЛЬКО «сырым» валидным JSON-объектом, точно соответствующим приведенной ниже схеме.\n"
    "2. НЕ пишите никакого текста в разговорном стиле до или после JSON.\n"
    "3. НЕ оборачивайте JSON в блоки кода Markdown, такие как ```json ... ```.\n\n"
    "Далее следует JSON-схема:\n"
    "{\n"
    '  "user_type": "student" or "project_leader",\n'
    '  "contact": "средство связи, если указано в тексте (Telegram @username, email или телефон), иначе пустая строка",\n'
    '  "extracted_data": {\n'
    '    "name_or_title": "Name of the student OR Title of the project",\n'
    '    "core_skills_or_needs": ["list", "of", "skills", "or", "technologies"],\n'
    '    "summary_description": "A clean 1-sentence summary of who they are or what they build"\n'
    "  }\n"
    "}"
)


# =====================================================
# Вызов GigaChat ТОЧНО так же, как это делает рабочий виджет (chat.py)
# =====================================================
def _get_token() -> str:
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': '12345678-1234-1234-1234-123456789012',
        'Authorization': f'Basic {settings.GIGACHAT_CREDENTIALS}',
    }
    payload = {'scope': settings.GIGACHAT_SCOPE}
    r = requests.post(url, headers=headers, data=payload, verify=False, timeout=15)
    r.raise_for_status()
    return r.json().get('access_token')


def _ask_giga(messages: list) -> str:
    if not settings.GIGACHAT_CREDENTIALS:
        raise RuntimeError("Не указан GIGACHAT_CREDENTIALS в .env")
    token = _get_token()
    r = requests.post(
        settings.GIGACHAT_API_URL,
        headers={
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}',
        },
        json={"model": MODEL_NAME, "messages": messages, "temperature": 0.4},
        verify=False,
        timeout=60,
    )
    r.raise_for_status()
    return r.json()['choices'][0]['message']['content']


# =====================================================
# Извлечение средства связи из свободного текста
# =====================================================
def extract_contact(text: str) -> str:
    if not text:
        return ""

    # email
    m = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
    if m:
        return m.group(0)

    # ссылка t.me/username или telegram.me/username
    m = re.search(r"(?:https?://)?(?:t\.me|telegram\.me)/([A-Za-z0-9_]{5,})", text)
    if m:
        return "@" + m.group(1)

    # @username (но НЕ часть email: перед @ не должно быть букв/точек/плюсов)
    m = re.search(r"(?<![A-Za-z0-9._%+-])@([A-Za-z0-9_]{5,32})", text)
    if m:
        return "@" + m.group(1)

    # телефон
    m = re.search(r"\+?\d[\d\s\-\(\)]{10,15}\d", text)
    if m:
        return m.group(0).strip()

    return ""


# =====================================================
# ФУНКЦИЯ 1: текст -> структурированный JSON-профиль
# =====================================================
def extract_profile_to_dict(user_input: str) -> dict:
    messages = [
        {"role": "system", "content": JSON_SYSTEM_PROMPT},
        {"role": "user", "content": user_input},
    ]
    raw_output = _ask_giga(messages).strip()

    if raw_output.startswith("```"):
        raw_output = raw_output.strip("`").replace("json", "", 1).strip()

    try:
        return json.loads(raw_output)
    except json.JSONDecodeError:
        return {"error": "Invalid JSON received from AI", "raw": raw_output}


# =====================================================
# ФУНКЦИЯ 2: сохранение профиля в JSON-базу
# (один аккаунт = один профиль: повторное сохранение обновляет запись)
# =====================================================
def save_profile_to_db(profile_data: dict, filename: str = DB_FILE) -> bool:
    if not profile_data or "error" in profile_data:
        return False

    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                database = json.load(f)
                if not isinstance(database, list):
                    database = [database]
        except (json.JSONDecodeError, ValueError):
            database = []
    else:
        database = []

    # заменяем старую запись ТОГО ЖЕ пользователя, чтобы не плодить дубликаты
    user_id = profile_data.get("user_id")
    if user_id is not None:
        database = [r for r in database if r.get("user_id") != user_id]

    database.append(profile_data)

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(database, f, indent=4, ensure_ascii=False)
    return True


def get_db_records(filename: str = DB_FILE) -> list:
    if not os.path.exists(filename):
        return []
    try:
        with open(filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, list) else [data]
    except (json.JSONDecodeError, ValueError):
        return []


# =====================================================
# ФУНКЦИЯ 3: двусторонний мэтчинг (тимлид <-> студенты)
# =====================================================
def query_matchmaker(search_context: str, look_for_type: str, filename: str = DB_FILE) -> str:
    look_for_type = str(look_for_type).strip().lower()

    records = get_db_records(filename)
    if not records:
        return "База данных пуста. Зарегистрируйте первых участников!"

    target_pool = [
        r for r in records
        if str(r.get("user_type", "")).strip().lower() == look_for_type
    ]

    if not target_pool:
        type_label = "разработчиков" if look_for_type == "student" else "открытых проектов"
        return f"В базе данных пока нет доступных {type_label}."

    pool_text = ""
    for idx, item in enumerate(target_pool):
        data = item["extracted_data"]
        contact = item.get("contact") or data.get("contact") or "не указан"
        pool_text += (
            f"- Вариант #{idx + 1}: {data['name_or_title']}. "
            f"Стек/Требования: {', '.join(data['core_skills_or_needs'])}. "
            f"Описание: {data['summary_description']}. "
            f"Контакт: {contact}\n"
        )

    if look_for_type == "student":
        role_desc = "Ты — ИИ-Рекрутер платформы UrFU TeamUp. Помоги Тимлиду найти разработчиков из базы данных."
        query_label = "Запрос Тимлида (какие навыки нужны проекту)"
    else:
        role_desc = "Ты — ИИ-Ментор платформы UrFU TeamUp. Помоги одиночному Студенту найти подходящую команду."
        query_label = "Профиль и навыки Студента"

    hr_prompt = (
        f"{role_desc}\n"
        f"Наша текущая локальная база данных:\n{pool_text}\n\n"
        f'Входящий {query_label}: """{search_context}"""\n\n'
        "ЗАДАЧА: Выбери топ-1 или топ-2 лучших совпадения из предоставленной базы данных. "
        "Для каждого выбранного совпадения напиши короткое, убедительное предложение-обоснование "
        "(почему это идеальный мэтч). "
        "ОБЯЗАТЕЛЬНО для каждого совпадения добавь отдельную строку: "
        "«📞 Средство связи: <значение из поля Контакт базы>». "
        "Отвечай вежливо, профессионально, на русском языке."
    )

    reply = _ask_giga([{"role": "user", "content": hr_prompt}])

    # =====================================================
    # Надёжно дописываем контакты СЕРВЕРОМ (не надеемся на нейросеть)
    # =====================================================
    contact_lines = []
    for item in target_pool:
        data = item.get("extracted_data", {})
        name = (data.get("name_or_title") or "").strip()
        contact = item.get("contact") or data.get("contact") or ""
        if not name or not contact:
            continue

        # упомянул ли ИИ этого кандидата в ответе (по имени или первому слову)
        first_word = name.split()[0].lower() if name.split() else ""
        if name.lower() in reply.lower() or (first_word and first_word in reply.lower()):
            contact_lines.append(f"📞 {name}: {contact}")

    if contact_lines:
        reply += "\n\nКонтакты кандидатов:\n" + "\n".join(contact_lines)

    return reply
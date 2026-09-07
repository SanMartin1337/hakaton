import os
import json

import requests
import urllib3

from app.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_FILE = os.path.join(BASE_DIR, "teamup_db.json")
MODEL_NAME = "GigaChat"

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
# ФУНКЦИЯ 3: мэтчинг (тимлид <-> студенты)
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
        pool_text += (
            f"- Вариант #{idx + 1}: {data['name_or_title']}. "
            f"Стек/Требования: {', '.join(data['core_skills_or_needs'])}. "
            f"Описание: {data['summary_description']}\n"
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
        "(почему это идеальный мэтч). Отвечай вежливо, профессионально, на русском языке."
    )

    return _ask_giga([{"role": "user", "content": hr_prompt}])
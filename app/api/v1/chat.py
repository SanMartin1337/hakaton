import requests
import urllib3
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from app.database import get_db
from app.models.user import User
from app.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    question: str

# =====================================================
# Функция аутентификации (скопирована из main.py)
# =====================================================
def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
    except JWTError:
        return None
    return db.query(User).filter(User.email == email).first()

# =====================================================
# GigaChat API
# =====================================================
SYSTEM_PROMPT = """Ты — умный и дружелюбный AI-помощник для студентов Уральского федерального университета (УрФУ) в системе Campus Connect.
Твоя задача — помогать студентам ориентироваться в университете, отвечать на вопросы про учебу, институты, кампусы (включая Новокольцовский), студенческую жизнь, общежития и мероприятия.

Правила ответа:
1. Отвечай структурированно: используй списки, эмодзи и абзацы, чтобы текст легко читался.
2. Если ты не уверен в точных деталях (номера кабинетов, точные суммы, актуальные расписания на сегодня), честно скажи об этом и посоветуй обратиться в деканат или на официальный сайт urfu.ru. НИКОГДА не выдумывай факты, телефоны или имена преподавателей.
3. Отвечай по-русски.
4. Будь кратким, но информативным. Помогай студенту решать его проблемы и навигироваться по сайту.
"""

def get_gigachat_token(credentials: str) -> str:
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': '12345678-1234-1234-1234-123456789012',
        'Authorization': f'Basic {credentials}'
    }
    payload = {'scope': settings.GIGACHAT_SCOPE}
    response = requests.post(url, headers=headers, data=payload, verify=False, timeout=15)
    response.raise_for_status()
    return response.json().get('access_token')

def ask_gigachat_api(question: str, token: str) -> str:
    url = settings.GIGACHAT_API_URL
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        "temperature": 0.7
    }
    response = requests.post(url, headers=headers, json=payload, verify=False, timeout=30)
    response.raise_for_status()
    return response.json()['choices'][0]['message']['content']

# =====================================================
# Эндпоинт чата
# =====================================================
@router.post("/ask")
def ask_gigachat(
    req: ChatRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    # Аутентификация вручную (без циклического импорта)
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return {"reply": "⚠️ Вы не авторизованы. Пожалуйста, войдите в систему."}

    print(f"📨 Получен вопрос от {current_user.email}: {req.question}")

    if not settings.GIGACHAT_CREDENTIALS:
        return {"reply": "Ошибка конфигурации: не указан GIGACHAT_CREDENTIALS в файле .env."}

    try:
        token = get_gigachat_token(settings.GIGACHAT_CREDENTIALS)
        print(f"✅ Токен получен: {token[:20]}...")

        reply = ask_gigachat_api(req.question, token)
        print(f"🤖 Ответ GigaChat: {reply[:100]}...")

        return {"reply": reply}

    except requests.exceptions.HTTPError as e:
        error_body = e.response.text if e.response else "нет тела ответа"
        print(f"🚨 HTTP Ошибка: {e} | Тело: {error_body}")
        return {"reply": f"⚠️ Ошибка API Сбера: {error_body}"}
    except Exception as e:
        print(f"🚨 Неизвестная ошибка: {type(e).__name__}: {e}")
        return {"reply": f"⚠️ Ошибка: {type(e).__name__}: {str(e)}"}
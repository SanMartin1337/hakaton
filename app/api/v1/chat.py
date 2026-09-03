from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.config import settings

router = APIRouter(prefix="/chat", tags=["chat"])
security = HTTPBearer()

def get_current_user(token: HTTPAuthorizationCredentials = Depends(security), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token.credentials, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise credentials_exception
    return user

@router.post("/ask")
async def ask_gigachat(
    question: str,
    current_user: User = Depends(get_current_user)
):
    # ВРЕМЕННАЯ ЗАГЛУШКА
    fake_reply = f"""
📚 Вопрос: {question}

🏛️ Институт: {current_user.institute}
📚 Группа: {current_user.group_number}

Ответ (заглушка): 
Это пример ответа от AI-помощника. 
В реальности здесь будет ответ от GigaChat с информацией об УРФУ.

Полезные контакты:
• Сайт: https://urfu.ru
• Email: info@urfu.ru
• Приемная комиссия: +7 (343) 375-41-10
"""
    return {"reply": fake_reply}
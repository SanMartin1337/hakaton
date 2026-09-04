from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi.responses import RedirectResponse

from app.database import engine, Base, get_db
from app.models import user
from app.api.v1 import auth, chat
from app.api.v1 import users
from app.config import settings

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Campus Connect — УрФУ")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Статика и шаблоны
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# API роуты
app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")
app.include_router(users.router, prefix="/api/v1")


# =========================================
# Функция для получения пользователя из куки
# =========================================
def get_current_user_from_cookie(request: Request, db: Session = Depends(get_db)):
    # Пытаемся взять токен из куки
    token = request.cookies.get("access_token")
    if not token:
        # Если нет куки — пробуем из заголовка (для API)
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

    user_db = db.query(user.User).filter(user.User.email == email).first()
    return user_db


# =========================================
# Страницы
# =========================================

@app.get("/")
async def index(request: Request):
    current_user = get_current_user_from_cookie(request, next(get_db()))
    if current_user:
        return RedirectResponse(url="/dashboard")
    return templates.TemplateResponse("index.html", {"request": request, "user": None})


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None})


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "user": None})


@app.get("/dashboard")
async def dashboard(request: Request):
    current_user = get_current_user_from_cookie(request, next(get_db()))
    if not current_user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user
    })


@app.get("/profile")
async def profile(request: Request):
    current_user = get_current_user_from_cookie(request, next(get_db()))
    if not current_user:
        return RedirectResponse(url="/login")
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user
    })


# =========================================
# Выход (удаляем куку)
# =========================================
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/")
    response.delete_cookie("access_token")
    return response


from app.models.user import User
from fastapi.responses import RedirectResponse


@app.get("/people")
async def people_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    people = db.query(User).filter(User.id != user.id).all()

    return templates.TemplateResponse("people.html", {
        "request": request,
        "user": user,
        "people": people
    })



@app.get("/projects")
async def projects_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user_from_cookie(request, db)
    if not user:
        return RedirectResponse(url="/login", status_code=303)

    return templates.TemplateResponse("projects.html", {"request": request, "user": user})


# =========================================
# Запуск
# =========================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
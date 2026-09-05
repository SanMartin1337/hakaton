from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from passlib.context import CryptContext

from app.database import engine, Base, get_db
from app.models import user
from app.api.v1 import auth, chat, users
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

# Утилиты
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(hours=24))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


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
    return db.query(user.User).filter(user.User.email == email).first()


# =========================================
# Главная страница (всегда доступна)
# =========================================
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "user": None})


# =========================================
# Авторизация
# =========================================
@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None})


@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user_db = db.query(user.User).filter(user.User.email == email).first()

    if not user_db or not verify_password(password, user_db.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "user": None, "error": "Неверный email или пароль"}
        )

    access_token = create_access_token(data={"sub": user_db.email})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    return response


# =========================================
# Регистрация
# =========================================
@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "user": None})


@app.post("/register")
async def register_submit(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    institute: str = Form(...),
    group: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    db: Session = Depends(get_db)
):
    if password != confirm_password:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "user": None, "error": "Пароли не совпадают"}
        )

    if db.query(user.User).filter(user.User.email == email).first():
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "user": None, "error": "Пользователь с таким email уже существует"}
        )

    new_user = user.User(
        full_name=full_name,
        email=email,
        institute=institute,
        group=group,
        hashed_password=hash_password(password)
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    access_token = create_access_token(data={"sub": new_user.email})
    response = RedirectResponse(url="/dashboard", status_code=303)
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        max_age=86400,
        samesite="lax"
    )
    return response


# =========================================
# Выход
# =========================================
@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie("access_token")
    return response


# =========================================
# Защищённые страницы
# =========================================
@app.get("/dashboard")
async def dashboard(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user
    })


@app.get("/profile")
async def profile(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("profile.html", {
        "request": request,
        "user": current_user
    })


@app.get("/people")
async def people_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    people = db.query(user.User).filter(user.User.id != current_user.id).all()

    return templates.TemplateResponse("people.html", {
        "request": request,
        "user": current_user,
        "people": people
    })


@app.get("/projects")
async def projects_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("projects.html", {
        "request": request,
        "user": current_user
    })


# =========================================
# Запуск
# =========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
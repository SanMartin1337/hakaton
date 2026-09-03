from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.models import user
from app.api.v1 import auth, chat

# Создаем таблицы
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Student Life URFU")

# Добавляем CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключаем статику и шаблоны
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

# Подключаем API роуты
app.include_router(auth.router, prefix="/api/v1")
app.include_router(chat.router, prefix="/api/v1")

# Страницы
@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "user": None})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "user": None})

@app.get("/login-form")
async def login_form_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "user": None})
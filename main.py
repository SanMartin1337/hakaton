from fastapi import FastAPI, Request, Depends, Form
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from fastapi.responses import RedirectResponse
from datetime import datetime, timedelta
from passlib.context import CryptContext
from app.models.user_event import UserEvent
from app.database import engine, Base, get_db
from app.models import user
from app.api.v1 import auth, chat, users
from app.config import settings
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from app.models.friend_request import FriendRequest
from app.models.user import User
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


# Словарь всех событий (ID -> данные) — для быстрого поиска
EVENTS_DB = {
    1: {"title": "Знакомство с Campus Connect", "category": "Студенческая жизнь", "date": "07.09.2026", "time": "18:00",
        "place": "Главный холл кампуса"},
    2: {"title": "Открытая тренировка по баскетболу", "category": "Спорт", "date": "08.09.2026", "time": "19:00",
        "place": "Спортивный комплекс УрФУ"},
    3: {"title": "Вечер настольных игр", "category": "Сообщества", "date": "09.09.2026", "time": "18:30",
        "place": "Студенческий центр"},
    4: {"title": "Frontend за один вечер", "category": "IT", "date": "10.09.2026", "time": "18:00",
        "place": "Технопарк УрФУ"},
    5: {"title": "Welcome-встреча первокурсников ИРИТ-РТФ", "category": "Образование", "date": "11.09.2026",
        "time": "17:30", "place": "Учебный корпус ИРИТ-РТФ"},
    6: {"title": "Campus Startup Meetup", "category": "Стартапы", "date": "12.09.2026", "time": "17:00",
        "place": "Коворкинг УрФУ"},
    7: {"title": "Фотопрогулка по кампусу", "category": "Медиа", "date": "13.09.2026", "time": "16:00",
        "place": "Главная площадь кампуса"},
    8: {"title": "Открытая встреча «Волонтеры Урала»", "category": "Волонтерство", "date": "14.09.2026",
        "time": "18:00", "place": "Студенческий центр"},
    9: {"title": "Квиз «Знаешь ли ты УрФУ?»", "category": "Развлечения", "date": "15.09.2026", "time": "18:30",
        "place": "Коворкинг УрФУ"},
    10: {"title": "Киберспортивный вечер", "category": "Киберспорт", "date": "16.09.2026", "time": "18:00",
         "place": "Киберспортивная зона УрФУ"},
    11: {"title": "Как попасть на стажировку без опыта", "category": "Карьера", "date": "17.09.2026", "time": "18:00",
         "place": "Коворкинг УрФУ"},
    12: {"title": "Научный speed dating", "category": "Наука", "date": "18.09.2026", "time": "17:30",
         "place": "Научная библиотека УрФУ"},
    13: {"title": "Хакатон Campus Data", "category": "IT", "date": "19.09.2026", "time": "10:00",
         "place": "Технопарк УрФУ"},
    14: {"title": "Открытый день Design Hub", "category": "Дизайн", "date": "20.09.2026", "time": "17:00",
         "place": "Коворкинг УрФУ"},
    15: {"title": "Как устроена БРС", "category": "Образование", "date": "21.09.2026", "time": "18:00",
         "place": "Лекционный зал УрФУ"},
    16: {"title": "Экскурсия по лабораториям УрФУ", "category": "Наука", "date": "22.09.2026", "time": "16:00",
         "place": "Научно-лабораторный корпус"},
    17: {"title": "Открытый микрофон Campus Stage", "category": "Культура", "date": "23.09.2026", "time": "19:00",
         "place": "Актовый зал УрФУ"},
    18: {"title": "Турнир по настольному теннису", "category": "Спорт", "date": "24.09.2026", "time": "18:00",
         "place": "Спортивный зал УрФУ"},
    19: {"title": "Встреча клуба иностранных языков", "category": "Сообщества", "date": "25.09.2026", "time": "18:30",
         "place": "Коворкинг УрФУ"},
    20: {"title": "День карьеры IT", "category": "Карьера", "date": "26.09.2026", "time": "12:00",
         "place": "Технопарк УрФУ"},
    21: {"title": "Добровольческий день", "category": "Волонтерство", "date": "27.09.2026", "time": "12:00",
         "place": "Студенческий центр"},
    22: {"title": "Введение в Git и GitVerse", "category": "IT", "date": "28.09.2026", "time": "18:00",
         "place": "Компьютерный класс"},
    23: {"title": "Как собрать команду для проекта", "category": "Проекты", "date": "29.09.2026", "time": "18:00",
         "place": "Коворкинг УрФУ"},
    24: {"title": "Вечер студенческих организаций", "category": "Сообщества", "date": "30.09.2026", "time": "18:00",
         "place": "Главный холл УрФУ"},
    25: {"title": "AI для учебы: без магии", "category": "AI", "date": "02.10.2026", "time": "18:00",
         "place": "Технопарк УрФУ"},
    26: {"title": "Дебют первокурсников: отборочный этап", "category": "Культура", "date": "03.10.2026",
         "time": "17:00", "place": "Актовый зал института"},
    27: {"title": "Турнир по волейболу", "category": "Спорт", "date": "04.10.2026", "time": "12:00",
         "place": "СКИВС УрФУ"},
    28: {"title": "Лекция «Как работает стартап»", "category": "Стартапы", "date": "05.10.2026", "time": "18:30",
         "place": "Коворкинг УрФУ"},
    29: {"title": "НаукаФест: открытые лаборатории", "category": "Наука", "date": "06.10.2026", "time": "15:00",
         "place": "Лабораторные корпуса УрФУ"},
    30: {"title": "НаукаФест: научпоп-лекторий", "category": "Наука", "date": "07.10.2026", "time": "18:00",
         "place": "Большой лекционный зал"},
    31: {"title": "Финансовая грамотность студента", "category": "Образование", "date": "08.10.2026", "time": "18:00",
         "place": "Коворкинг УрФУ"},
    32: {"title": "Турнир 3x3 по баскетболу", "category": "Спорт", "date": "10.10.2026", "time": "11:00",
         "place": "Спортивный комплекс УрФУ"},
    33: {"title": "Как сделать сильное портфолио", "category": "Карьера", "date": "11.10.2026", "time": "17:00",
         "place": "Коворкинг УрФУ"},
    34: {"title": "День открытых проектов", "category": "Проекты", "date": "12.10.2026", "time": "18:00",
         "place": "Точка кипения УрФУ"},
    35: {"title": "Мастер-класс по публичным выступлениям", "category": "Навыки", "date": "13.10.2026", "time": "18:30",
         "place": "Актовый зал УрФУ"},
    36: {"title": "Медиа-день УрФУ", "category": "Медиа", "date": "14.10.2026", "time": "17:00",
         "place": "Медиа-студия"},
    37: {"title": "Подготовка волонтеров к Хороводу УрФУ", "category": "Волонтерство", "date": "15.10.2026",
         "time": "18:00", "place": "Главный учебный корпус"},
    38: {"title": "Встреча Buddy System UrFU", "category": "Международное", "date": "16.10.2026", "time": "18:00",
         "place": "Международный центр"},
    39: {"title": "Demo Day студенческих проектов", "category": "Проекты", "date": "17.10.2026", "time": "16:00",
         "place": "Большой лекционный зал"},
    40: {"title": "Хоровод УрФУ", "category": "Традиции", "date": "19.10.2026", "time": "17:00",
         "place": "Площадь перед ГУК"},
    41: {"title": "Вечер истории УрФУ", "category": "Образование", "date": "20.10.2026", "time": "18:00",
         "place": "Главный учебный корпус"},
    42: {"title": "Хакатон «Умный кампус»", "category": "IT", "date": "23.10.2026", "time": "10:00",
         "place": "Технопарк УрФУ"},
    43: {"title": "Осенний кубок КВН УрФУ", "category": "Культура", "date": "24.10.2026", "time": "18:00",
         "place": "Актовый зал УрФУ"},
    44: {"title": "Время карьеры: день работодателей", "category": "Карьера", "date": "27.10.2026", "time": "12:00",
         "place": "Главный учебный корпус"},
    45: {"title": "Время карьеры: быстрые собеседования", "category": "Карьера", "date": "28.10.2026", "time": "15:00",
         "place": "Коворкинг УрФУ"},
    46: {"title": "Киберспортивный кубок УрФУ", "category": "Киберспорт", "date": "31.10.2026", "time": "12:00",
         "place": "Киберспортивная зона"},
    47: {"title": "Школа студенческого актива", "category": "Сообщества", "date": "03.11.2026", "time": "17:00",
         "place": "Точка кипения УрФУ"},
    48: {"title": "Как получить грант на студенческий проект", "category": "Проекты", "date": "05.11.2026",
         "time": "18:00", "place": "Коворкинг УрФУ"},
    49: {"title": "Студенческая конференция молодых исследователей", "category": "Наука", "date": "07.11.2026",
         "time": "10:00", "place": "Научно-лабораторный корпус"},
    50: {"title": "Мастер-класс по Python", "category": "IT", "date": "09.11.2026", "time": "18:00",
         "place": "Компьютерный класс"},
    51: {"title": "День донорства", "category": "Волонтерство", "date": "11.11.2026", "time": "09:00",
         "place": "Площадка УрФУ"},
    52: {"title": "Международный вечер культур", "category": "Международное", "date": "13.11.2026", "time": "18:00",
         "place": "Студенческий центр"},
    53: {"title": "Фестиваль студенческих медиа", "category": "Медиа", "date": "15.11.2026", "time": "16:00",
         "place": "Медиа-студия УрФУ"},
    54: {"title": "Инженерный кейс-чемпионат", "category": "Инженерия", "date": "17.11.2026", "time": "10:00",
         "place": "Инженерный корпус"},
    55: {"title": "Campus Product Meetup", "category": "IT", "date": "19.11.2026", "time": "18:00",
         "place": "Точка кипения УрФУ"},
    56: {"title": "Студенческий турнир по шахматам", "category": "Спорт", "date": "21.11.2026", "time": "12:00",
         "place": "Студенческий центр"},
    57: {"title": "День проектных команд", "category": "Проекты", "date": "23.11.2026", "time": "17:00",
         "place": "Коворкинг УрФУ"},
    58: {"title": "Лекция «Как не выгореть в университете»", "category": "Образование", "date": "25.11.2026",
         "time": "18:00", "place": "Лекционный зал"},
    59: {"title": "Музыкальный квартирник УрФУ", "category": "Культура", "date": "27.11.2026", "time": "19:00",
         "place": "Творческое пространство УрФУ"},
    60: {"title": "Hack Night", "category": "IT", "date": "28.11.2026", "time": "18:00", "place": "Технопарк УрФУ"},
    61: {"title": "Ярмарка студенческих инициатив", "category": "Сообщества", "date": "30.11.2026", "time": "16:00",
         "place": "Главный учебный корпус"},
    62: {"title": "Зимний турнир по баскетболу", "category": "Спорт", "date": "03.12.2026", "time": "17:00",
         "place": "Спортивный комплекс УрФУ"},
    63: {"title": "Питч-сессия студенческих стартапов", "category": "Стартапы", "date": "05.12.2026", "time": "16:00",
         "place": "Точка кипения УрФУ"},
    64: {"title": "Как подготовиться к первой сессии", "category": "Образование", "date": "07.12.2026", "time": "18:00",
         "place": "Лекционный зал УрФУ"},
    65: {"title": "Зимний благотворительный сбор", "category": "Волонтерство", "date": "09.12.2026", "time": "12:00",
         "place": "Студенческий центр"},
    66: {"title": "Новогодний студенческий фестиваль", "category": "Культура", "date": "12.12.2026", "time": "18:00",
         "place": "Актовый зал УрФУ"},
    67: {"title": "Финальный Demo Day семестра", "category": "Проекты", "date": "15.12.2026", "time": "16:00",
         "place": "Большой лекционный зал"},
    68: {"title": "Открытая встреча «Итоги семестра»", "category": "Сообщества", "date": "18.12.2026", "time": "18:00",
         "place": "Коворкинг УрФУ"},
}


# API: добавить/убрать событие из избранного
@app.post("/api/v1/events/favorite")
async def toggle_favorite(
        request: Request,
        db: Session = Depends(get_db)
):
    body = await request.json()
    event_id = body.get("event_id")

    if not event_id or event_id not in EVENTS_DB:
        raise HTTPException(status_code=400, detail="Неверный ID события")

    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    # Проверяем, есть ли уже в избранном
    existing = db.query(UserEvent).filter(
        UserEvent.user_id == current_user.id,
        UserEvent.event_id == event_id
    ).first()

    if existing:
        # Удаляем из избранного
        db.delete(existing)
        db.commit()
        return {"status": "removed", "event_id": event_id}
    else:
        # Добавляем в избранное
        new_fav = UserEvent(user_id=current_user.id, event_id=event_id)
        db.add(new_fav)
        db.commit()
        return {"status": "added", "event_id": event_id}


# API: получить список избранных событий пользователя
@app.get("/api/v1/events/favorites")
async def get_favorites(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    favorites = db.query(UserEvent).filter(UserEvent.user_id == current_user.id).all()
    result = []
    for fav in favorites:
        event_data = EVENTS_DB.get(fav.event_id)
        if event_data:
            result.append({"id": fav.event_id, **event_data})

    return result


@app.post("/api/v1/friends/request")
async def send_friend_request(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    body = await request.json()
    receiver_id = body.get("receiver_id")

    if receiver_id == current_user.id:
        return {"error": "Нельзя добавить себя в друзья"}

    # Проверяем ВСЕ возможные варианты существующих заявок
    existing = db.query(FriendRequest).filter(
        ((FriendRequest.sender_id == current_user.id) & (FriendRequest.receiver_id == receiver_id)) |
        ((FriendRequest.sender_id == receiver_id) & (FriendRequest.receiver_id == current_user.id))
    ).first()

    if existing:
        if existing.status == "pending":
            return {"status": "already_pending"}
        elif existing.status == "accepted":
            return {"status": "already_friends"}
        elif existing.status == "declined":
            # Если была отклонена, создаем новую заявку
            existing.status = "pending"
            db.commit()
            return {"status": "sent"}

    new_request = FriendRequest(sender_id=current_user.id, receiver_id=receiver_id, status="pending")
    db.add(new_request)
    db.commit()

    return {"status": "sent"}

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

    favorites = db.query(UserEvent).filter(UserEvent.user_id == current_user.id).all()
    favorite_events = []
    for fav in favorites:
        event_data = EVENTS_DB.get(fav.event_id)
        if event_data:
            favorite_events.append({"id": fav.event_id, **event_data})

    # ===== Мои менторы =====
    mentor_requests = db.query(FriendRequest).filter(
        FriendRequest.sender_id == current_user.id,
        FriendRequest.request_type == "mentorship"
    ).all()

    my_mentors = []
    for req in mentor_requests:
        mentor = db.query(user.User).filter(user.User.id == req.receiver_id).first()
        if mentor:
            my_mentors.append({
                "id": mentor.id,
                "full_name": mentor.full_name,
                "institute": mentor.institute,
                "mentor_skills": mentor.mentor_skills,
                "status": req.status  # "pending" / "accepted" / "declined"
            })

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": current_user,
        "favorite_events": favorite_events,
        "my_mentors": my_mentors
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


@app.get("/events")
async def events_page(request: Request, db: Session = Depends(get_db)):
    print("\n" + "=" * 50)
    print("=== ЗАПРОС НА /events ===")
    print("Все куки:", request.cookies)

    current_user = get_current_user_from_cookie(request, db)
    print("Результат get_current_user_from_cookie:", current_user)
    print("=" * 50 + "\n")

    if not current_user:
        print("❌ АВТОРИЗАЦИЯ НЕ ПРОЙДЕНА -> редирект на /login")
        return RedirectResponse(url="/login", status_code=303)

    print("✅ АВТОРИЗАЦИЯ УСПЕШНА -> отдаем events.html")
    return templates.TemplateResponse("events.html", {
        "request": request,
        "user": current_user
    })


# =========================================
# СИСТЕМА ДРУЗЕЙ (API + Страница)
# =========================================

@app.get("/friends")
async def friends_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    # 1. Получаем входящие заявки (pending)
    requests_db = db.query(FriendRequest).filter(
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).all()

    # 2. Для каждой заявки находим отправителя и создаем кортеж (req, sender)
    incoming_data = []
    for req in requests_db:
        sender = db.query(user.User).filter(user.User.id == req.sender_id).first()
        if sender:
            incoming_data.append((req, sender))

    # 3. Получаем список друзей (accepted)
    friends = db.query(user.User).join(
        FriendRequest,
        ((FriendRequest.sender_id == current_user.id) | (FriendRequest.receiver_id == current_user.id)) &
        (FriendRequest.status == "accepted")
    ).filter(user.User.id != current_user.id).all()

    # Отладка (можешь оставить или убрать)
    print(f"\n=== DEBUG /friends ===")
    print(f"User: {current_user.full_name}")
    print(f"Incoming: {len(incoming_data)}")
    for req, sender in incoming_data:
        print(f"  -> От: {sender.full_name} (ID заявки: {req.id})")
    print(f"===================\n")

    return templates.TemplateResponse("friends.html", {
        "request": request,
        "user": current_user,
        "incoming_data": incoming_data,  # <-- Передаем под новым именем
        "friends": friends
    })

@app.post("/api/v1/friends/request")
async def send_friend_request(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    body = await request.json()
    receiver_id = body.get("receiver_id")
    request_type = body.get("request_type", "friend")

    if receiver_id == current_user.id:
        return {"error": "Нельзя отправить заявку самому себе"}

    existing = db.query(FriendRequest).filter(
        ((FriendRequest.sender_id == current_user.id) & (FriendRequest.receiver_id == receiver_id)) |
        ((FriendRequest.sender_id == receiver_id) & (FriendRequest.receiver_id == current_user.id)),
        FriendRequest.request_type == request_type
    ).first()

    if existing:
        if existing.status == "pending":
            return {"status": "already_pending"}
        elif existing.status == "accepted":
            return {"status": "already_connected"}
        elif existing.status == "declined":
            existing.status = "pending"
            db.commit()
            return {"status": "sent"}

    new_request = FriendRequest(
        sender_id=current_user.id,
        receiver_id=receiver_id,
        status="pending",
        request_type=request_type
    )
    db.add(new_request)
    db.commit()

    return {"status": "sent"}

@app.post("/api/v1/friends/respond")
async def respond_to_friend_request(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    body = await request.json()
    request_id = body.get("request_id")
    action = body.get("action")  # "accept" или "decline"

    req = db.query(FriendRequest).filter(
        FriendRequest.id == request_id,
        FriendRequest.receiver_id == current_user.id,
        FriendRequest.status == "pending"
    ).first()

    if not req:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    req.status = "accepted" if action == "accept" else "declined"
    db.commit()

    return {"status": "updated"}

@app.get("/mentors")
async def mentors_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)

    mentors = db.query(user.User).filter(
        user.User.is_mentor == True,
        user.User.id != current_user.id
    ).all()

    return templates.TemplateResponse("mentors.html", {
        "request": request,
        "user": current_user,
        "mentors": mentors
    })


@app.post("/api/v1/profile/mentor")
async def toggle_mentor(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        raise HTTPException(status_code=401, detail="Не авторизован")

    body = await request.json()
    current_user.is_mentor = body.get("is_mentor", not current_user.is_mentor)
    current_user.mentor_bio = body.get("mentor_bio", current_user.mentor_bio)
    current_user.mentor_skills = body.get("mentor_skills", current_user.mentor_skills)
    db.commit()

    return {"status": "ok", "is_mentor": current_user.is_mentor}

@app.get("/about")
async def about_page(request: Request, db: Session = Depends(get_db)):
    current_user = get_current_user_from_cookie(request, db)
    if not current_user:
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("about_urfu.html", {
        "request": request,
        "user": current_user
    })
# =========================================
# Запуск
# =========================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
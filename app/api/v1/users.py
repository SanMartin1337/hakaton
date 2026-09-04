from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserResponse
from app.api.v1.auth import get_current_user

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/", response_model=list[UserResponse])
def get_users(
        search: str = Query(None, min_length=1, description="Поиск по ФИО или группе"),
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)  # только для авторизованных
):
    query = db.query(User)

    if search:
        # Ищем по полному имени или группе (без учёта регистра)
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                User.full_name.ilike(search_term),
                User.group_number.ilike(search_term)
            )
        )


    users = query.all()
    return users
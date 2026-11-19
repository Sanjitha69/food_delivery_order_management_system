from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.exceptions import AppException
from app.models import User, Role
from app.core.security import hash_password, verify_password, create_access_token
from app.core.security import require_role
from app.schemas.admin import AccountCreate
from app.schemas.auth import RegisterRequest, TokenResponse
from app.core.limiter import limiter

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == str(data.email)).first():
        raise AppException(409, "EMAIL_EXISTS", "Email is already registered")
    user = User(email=str(data.email), password_hash=hash_password(data.password),
                full_name=data.full_name, phone=data.phone, role=Role.CUSTOMER)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(request: Request, form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not user.is_active or not verify_password(form.password, user.password_hash):
        raise AppException(401, "INVALID_CREDENTIALS", "Invalid email or password")
    return {"access_token": create_access_token(user), "token_type": "bearer"}


@router.post("/users", status_code=201)
def create_managed_account(data: AccountCreate, db: Session = Depends(get_db),
                           admin: User = Depends(require_role(Role.ADMIN))):
    if data.role not in {Role.RESTAURANT_OWNER, Role.DELIVERY_AGENT}:
        raise AppException(422, "INVALID_ROLE", "Only restaurant owner and delivery agent accounts can be created")
    if db.query(User).filter(User.email == str(data.email)).first():
        raise AppException(409, "EMAIL_EXISTS", "Email is already registered")
    user = User(email=str(data.email), password_hash=hash_password(data.password),
                full_name=data.full_name, phone=data.phone, role=data.role)
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "full_name": user.full_name,
            "phone": user.phone, "role": user.role.value}

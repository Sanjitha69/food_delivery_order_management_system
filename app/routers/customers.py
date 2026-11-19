from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import require_role
from app.models import User, Role
from app.schemas.customer import (
    AddressCreate,
    AddressOut,
    AddressUpdate,
    CustomerProfileOut,
    ProfileUpdate,
)
from app.services.customer_service import (
    create_address,
    list_addresses,
    update_address,
    update_profile,
)

router = APIRouter(tags=["Customer"], dependencies=[Depends(require_role(Role.CUSTOMER))])

@router.get("/addresses", response_model=list[AddressOut])
def addresses(db: Session = Depends(get_db), user: User = Depends(require_role(Role.CUSTOMER))):
    return list_addresses(db, user)

@router.post("/addresses", response_model=AddressOut, status_code=201)
def add_address(data: AddressCreate, db: Session = Depends(get_db),
                user: User = Depends(require_role(Role.CUSTOMER))):
    return create_address(db, user, data)


@router.patch("/addresses/{address_id}", response_model=AddressOut)
def edit_address(address_id: int, data: AddressUpdate, db: Session = Depends(get_db),
                 user: User = Depends(require_role(Role.CUSTOMER))):
    return update_address(db, user, address_id, data)

@router.get("/customers/me", response_model=CustomerProfileOut)
def profile(user: User = Depends(require_role(Role.CUSTOMER))):
    return user

@router.put("/customers/me", response_model=CustomerProfileOut)
def update_profile_route(data: ProfileUpdate, db: Session = Depends(get_db),
                        user: User = Depends(require_role(Role.CUSTOMER))):
    return update_profile(db, user, data)

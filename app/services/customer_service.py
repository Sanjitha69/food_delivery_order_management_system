from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models import Address, User
from app.exceptions import AppException


def list_addresses(db: Session, user: User):
    return db.scalars(select(Address).where(Address.user_id == user.id).order_by(Address.is_default.desc(), Address.id)).all()


def create_address(db: Session, user: User, data):
    if data.is_default:
        for address in db.scalars(select(Address).where(Address.user_id == user.id)):
            address.is_default = False
    address = Address(user_id=user.id, **data.model_dump())
    db.add(address)
    db.commit()
    db.refresh(address)
    return address


def update_address(db: Session, user: User, address_id: int, data):
    address = db.scalar(
        select(Address).where(Address.id == address_id, Address.user_id == user.id)
    )
    if not address:
        raise AppException(404, "ADDRESS_NOT_FOUND", "Delivery address not found")
    changes = data.model_dump(exclude_unset=True)
    if changes.get("is_default") is True:
        db.query(Address).filter(
            Address.user_id == user.id, Address.id != address.id
        ).update({Address.is_default: False}, synchronize_session=False)
    for key, value in changes.items():
        setattr(address, key, value)
    db.commit()
    db.refresh(address)
    return address


def update_profile(db: Session, user: User, data):
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(user, key, value)
    db.commit()
    db.refresh(user)
    return user

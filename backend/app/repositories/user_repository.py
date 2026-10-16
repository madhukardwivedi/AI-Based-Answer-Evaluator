from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


class UserRepository:
    def get_by_email(self, db: Session, email: str) -> User | None:
        return db.scalar(select(User).where(User.email == email.lower()))

    def get(self, db: Session, user_id: UUID) -> User | None:
        return db.get(User, user_id)

    def create(self, db: Session, *, name: str, email: str, password_hash: str) -> User:
        user = User(name=name, email=email.lower(), password_hash=password_hash)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

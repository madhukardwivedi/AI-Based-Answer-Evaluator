from sqlalchemy.orm import Session

from app.core.security import verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository


class AuthService:
    def __init__(self, users: UserRepository | None = None) -> None:
        self.users = users or UserRepository()

    def authenticate(self, db: Session, email: str, password: str) -> User | None:
        user = self.users.get_by_email(db, email)
        if user is None or not verify_password(password, user.password_hash):
            return None
        return user

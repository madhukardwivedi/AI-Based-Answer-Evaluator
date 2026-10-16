"""Create the first evaluator account without exposing a public registration endpoint."""
import getpass
import sys

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.repositories.user_repository import UserRepository


def main() -> None:
    name = input("Evaluator name: ").strip()
    email = input("Evaluator email: ").strip().lower()
    password = getpass.getpass("Password (minimum 8 characters): ")
    if not name or "@" not in email or len(password) < 8:
        sys.exit("A name, valid email, and password of at least 8 characters are required.")
    with SessionLocal() as db:
        repository = UserRepository()
        if repository.get_by_email(db, email):
            sys.exit("An evaluator with that email already exists.")
        repository.create(db, name=name, email=email, password_hash=hash_password(password))
    print("Evaluator created.")


if __name__ == "__main__":
    main()

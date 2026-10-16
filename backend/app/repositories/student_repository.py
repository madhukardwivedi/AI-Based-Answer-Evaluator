from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.student import Student


class StudentRepository:
    def list_for_exam(self, db: Session, exam_id: UUID) -> list[Student]:
        return list(db.scalars(select(Student).where(Student.exam_id == exam_id).order_by(Student.name, Student.roll_number)))

    def get(self, db: Session, student_id: UUID) -> Student | None:
        return db.get(Student, student_id)

    def existing_identifiers(self, db: Session, exam_id: UUID) -> tuple[set[str], set[str]]:
        rows = db.execute(
            select(Student.roll_number, Student.external_id).where(Student.exam_id == exam_id)
        ).all()
        return (
            {roll_number for roll_number, _ in rows if roll_number is not None},
            {external_id for _, external_id in rows if external_id is not None},
        )

    def save(self, db: Session, student: Student) -> Student:
        db.add(student)
        db.commit()
        db.refresh(student)
        return student

    def delete(self, db: Session, student: Student) -> None:
        db.delete(student)
        db.commit()

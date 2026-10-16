from io import BytesIO

from openpyxl import Workbook

from app.core.security import hash_password
from app.db.session import get_db
from app.models.user import User


def seed_user(client, email: str = "ada@example.com") -> None:
    generator = client.app.dependency_overrides[get_db]()
    db = next(generator)
    db.add(User(name="Evaluator", email=email, password_hash=hash_password("correct-horse")))
    db.commit()
    generator.close()


def login(client, email: str = "ada@example.com") -> None:
    assert client.post("/api/auth/login", json={"email": email, "password": "correct-horse"}).status_code == 200


def create_exam(client, name: str = "Roster exam") -> dict:
    response = client.post("/api/exams", json={"name": name, "subject": "Science", "class_name": "Grade 8", "total_marks": "20"})
    assert response.status_code == 201
    return response.json()


def upload_csv(client, exam_id: str, content: bytes, filename: str = "students.csv"):
    return client.post(f"/api/exams/{exam_id}/students/import", files={"file": (filename, content, "text/csv")})


def test_csv_import_normalizes_headers_whitespace_and_ignores_blank_rows(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client)
    response = upload_csv(client, exam["id"], b" Name , Roll No , External ID \n Rahul Sharma , 101 , STU-001 \n\nPriya Verma,102,STU-002\n")
    assert response.status_code == 200, response.text
    assert response.json() == {"total_rows": 2, "imported_count": 2, "skipped_count": 0, "errors": []}
    students = client.get(f"/api/exams/{exam['id']}/students").json()
    assert [(item["name"], item["roll_number"], item["external_id"]) for item in students] == [
        ("Priya Verma", "102", "STU-002"), ("Rahul Sharma", "101", "STU-001")
    ]


def test_xlsx_import_and_partial_success_duplicate_handling(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client)
    assert client.post(f"/api/exams/{exam['id']}/students", json={"name": "Existing", "roll_number": "101", "external_id": "OLD"}).status_code == 201
    workbook = Workbook(); sheet = workbook.active
    sheet.append(["NAME", "roll_number", "external_id"])
    sheet.append(["New student", "102", "STU-002"])
    sheet.append(["Existing roll", "101", "STU-003"])
    sheet.append(["Existing external", "103", "OLD"])
    sheet.append(["", "104", "STU-004"])
    sheet.append(["Repeated in file", "102", "STU-005"])
    output = BytesIO(); workbook.save(output)
    response = client.post(
        f"/api/exams/{exam['id']}/students/import",
        files={"file": ("students.xlsx", output.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_rows"] == 5
    assert body["imported_count"] == 1
    assert body["skipped_count"] == 4
    assert {(issue["row"], issue["field"]) for issue in body["errors"]} == {(3, "roll_number"), (4, "external_id"), (5, "name"), (6, "roll_number")}


def test_import_rejects_invalid_files_and_requires_name_header(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client)
    assert upload_csv(client, exam["id"], b"roll_number\n101\n").status_code == 422
    assert upload_csv(client, exam["id"], b'name,roll_number\n"unclosed,101\n').status_code == 422
    assert upload_csv(client, exam["id"], b"name\n", "empty.txt").status_code == 422
    assert upload_csv(client, exam["id"], b"not an xlsx", "broken.xlsx").status_code == 422
    empty = upload_csv(client, exam["id"], b"name\n", "empty.csv")
    assert empty.status_code == 200
    assert empty.json()["imported_count"] == 0


def test_import_requires_authentication_and_exam_ownership(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client)
    client.post("/api/auth/logout")
    assert upload_csv(client, exam["id"], b"name\nUnauthenticated\n").status_code == 401
    login(client)
    seed_user(client, "other@example.com")
    login(client, "other@example.com")
    assert upload_csv(client, exam["id"], b"name\nWrong owner\n").status_code == 404


def test_manual_student_creation_remains_available_after_import(client) -> None:
    seed_user(client); login(client)
    exam = create_exam(client)
    assert upload_csv(client, exam["id"], b"name\nImported student\n").json()["imported_count"] == 1
    manual = client.post(f"/api/exams/{exam['id']}/students", json={"name": "Manual student", "roll_number": "M-1"})
    assert manual.status_code == 201

from app.services.auth_service import AuthService


def test_generate_temporary_password_length_and_charset() -> None:
    password = AuthService._generate_temporary_password(12)
    assert len(password) == 12
    assert password.isalnum()

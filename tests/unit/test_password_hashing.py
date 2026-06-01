from app.core.security import get_password_hash, verify_password


def test_password_hash_roundtrip() -> None:
    hashed = get_password_hash("password123")
    assert hashed.startswith("$2")
    assert verify_password("password123", hashed)
    assert not verify_password("wrong", hashed)

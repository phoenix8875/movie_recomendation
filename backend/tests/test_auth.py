"""
Unit tests for password hashing (app/auth.py).
Pure functions — no database, no network — so they run fast and green in CI.
"""

from app.auth import hash_password, verify_password


def test_hash_is_not_plaintext():
    # the stored hash must never equal the raw password
    hashed = hash_password("supersecret123")
    assert hashed != "supersecret123"
    assert len(hashed) > 20


def test_correct_password_verifies():
    hashed = hash_password("supersecret123")
    assert verify_password("supersecret123", hashed) is True


def test_wrong_password_fails():
    hashed = hash_password("supersecret123")
    assert verify_password("wrongpassword", hashed) is False


def test_same_password_different_hashes():
    # bcrypt salts each hash, so two hashes of the same password differ
    assert hash_password("samepass") != hash_password("samepass")

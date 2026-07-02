"""
Unit tests for Pydantic schema validation (app/schemas.py).
No database — just checks the request models enforce their rules.
"""

import pytest
from pydantic import ValidationError

from app.schemas import UserSignup, RecommendRequest


def test_signup_rejects_short_password():
    # schema requires password >= 8 chars
    with pytest.raises(ValidationError):
        UserSignup(email="a@b.com", password="short")


def test_signup_accepts_valid_input():
    user = UserSignup(email="a@b.com", password="longenough123")
    assert user.email == "a@b.com"


def test_signup_rejects_bad_email():
    with pytest.raises(ValidationError):
        UserSignup(email="not-an-email", password="longenough123")


def test_recommend_request_defaults():
    # empty request should default to empty lists and top_n = 10
    req = RecommendRequest()
    assert req.movie_titles == []
    assert req.genres == []
    assert req.top_n == 10

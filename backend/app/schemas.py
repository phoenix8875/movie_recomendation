from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator


# ---------- Auth ----------

class UserSignup(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    email: EmailStr
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ---------- Movies ----------

class MovieOut(BaseModel):
    id: int
    title: str
    year: int | None = None
    genres: str | None = None
    poster_url: str | None = None

    class Config:
        from_attributes = True


class RecommendRequest(BaseModel):
    movie_titles: list[str] = []
    genres: list[str] = []
    top_n: int = 10


# ---------- Watchlist ----------

class WatchlistAdd(BaseModel):
    movie_id: int


class WatchlistItemOut(BaseModel):
    id: int
    movie: MovieOut
    added_at: datetime

    class Config:
        from_attributes = True

import os

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://movieuser:moviepass@localhost:5432/moviedb",
)

# In production, set this via environment variable / secret — never hardcode.
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "60"))

# TMDB API key, used to fetch poster images at startup. If left blank,
# posters are simply skipped — nothing else in the app depends on this.
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")

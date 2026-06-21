"""
Fetches poster images from TMDB for movies that don't have one cached yet.

Runs once at startup (see main.py). Cheap on restarts because it only
queries TMDB for movies where poster_url is still NULL — once a poster is
found and saved, that movie is never queried again.

If TMDB_API_KEY is not set (or still the placeholder value), this skips
poster fetching entirely — the app still works fine without posters, it
just shows a placeholder box in the UI instead of an image.
"""

import sys
import requests
from sqlalchemy.orm import Session

from app.config import TMDB_API_KEY
from app.models import Movie

TMDB_SEARCH_URL = "https://api.themoviedb.org/3/search/movie"
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"  # decent size for cards

PLACEHOLDER_VALUES = {"", "changeme", "paste_your_tmdb_api_key_here"}

# (connect_timeout, read_timeout) in seconds. Without this, a network that
# accepts the connection but never responds can hang forever — requests
# only times out if you tell it to.
REQUEST_TIMEOUT = (5, 10)


def _looks_like_placeholder(key: str) -> bool:
    return key.strip().lower() in PLACEHOLDER_VALUES


def fetch_poster_url(title: str, year: int | None) -> str | None:
    """Look up a single movie on TMDB and return its poster URL, or None
    if not found / request failed / timed out.
    """
    params = {"api_key": TMDB_API_KEY, "query": title}
    if year:
        params["year"] = year

    try:
        response = requests.get(TMDB_SEARCH_URL, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        print(f"  TMDB lookup failed for '{title}': {e}", file=sys.stderr)
        return None

    results = data.get("results") or []
    if not results:
        return None

    poster_path = results[0].get("poster_path")
    if not poster_path:
        return None

    return f"{TMDB_IMAGE_BASE}{poster_path}"


def backfill_missing_posters(db: Session):
    """Fetch and save poster URLs for any movie that doesn't have one yet."""
    if not TMDB_API_KEY or _looks_like_placeholder(TMDB_API_KEY):
        print("TMDB_API_KEY not set (or still a placeholder) — skipping poster fetch.")
        return

    movies_without_posters = db.query(Movie).filter(Movie.poster_url.is_(None)).all()
    if not movies_without_posters:
        print("All movies already have posters cached — skipping fetch.")
        return

    total = len(movies_without_posters)
    print(f"Fetching posters for {total} movies from TMDB...")

    fetched_count = 0
    for i, movie in enumerate(movies_without_posters, start=1):
        poster_url = fetch_poster_url(movie.title, movie.year)
        if poster_url:
            movie.poster_url = poster_url
            fetched_count += 1
        if i % 20 == 0 or i == total:
            print(f"  ...{i}/{total} processed ({fetched_count} found so far)")

    db.commit()
    print(f"Done. Fetched {fetched_count}/{total} posters from TMDB.")

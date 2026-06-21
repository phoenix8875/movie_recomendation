from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Movie
from app.schemas import MovieOut, RecommendRequest
from app.recommender import recommender

router = APIRouter(prefix="/movies", tags=["movies"])


@router.get("", response_model=list[MovieOut])
def list_movies(
    search: str | None = Query(default=None, description="Search by title"),
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Movie)
    if search:
        query = query.filter(Movie.title.ilike(f"%{search}%"))
    return query.order_by(Movie.title).limit(limit).all()


@router.get("/genres", response_model=list[str])
def list_genres(db: Session = Depends(get_db)):
    rows = db.query(Movie.genres).all()
    genre_set: set[str] = set()
    for (genres_str,) in rows:
        if genres_str:
            genre_set.update(genres_str.split())
    return sorted(genre_set)


@router.post("/recommend", response_model=list[MovieOut])
def recommend(payload: RecommendRequest, db: Session = Depends(get_db)):
    # Resolve titles -> movie ids
    seed_ids: list[int] = []
    if payload.movie_titles:
        matched = (
            db.query(Movie).filter(Movie.title.in_(payload.movie_titles)).all()
        )
        seed_ids = [m.id for m in matched]

    ranked = recommender.recommend(
        seed_movie_ids=seed_ids,
        seed_genres=payload.genres,
        top_n=payload.top_n,
    )

    if not ranked:
        return []

    result_ids = [mid for mid, _ in ranked]
    movies = db.query(Movie).filter(Movie.id.in_(result_ids)).all()
    movies_by_id = {m.id: m for m in movies}
    # preserve ranking order
    return [movies_by_id[mid] for mid in result_ids if mid in movies_by_id]

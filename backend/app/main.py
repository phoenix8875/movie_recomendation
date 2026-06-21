from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, SessionLocal, Base
from app.seed import seed_movies_if_empty
from app.posters import backfill_missing_posters
from app.recommender import recommender
from app.routers import auth_router, movies_router, watchlist_router

# import models so SQLAlchemy registers them on Base before create_all
from app import models  # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables, seed data, fetch posters, build the recommender index
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_movies_if_empty(db)
        backfill_missing_posters(db)
        recommender.build(db)
    finally:
        db.close()

    yield
    # (no shutdown cleanup needed)


app = FastAPI(title="Movie Recommender API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # fine for local learning project; restrict in real deployments
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(movies_router.router)
app.include_router(watchlist_router.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}

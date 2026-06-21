import csv
import os

from sqlalchemy.orm import Session

from app.models import Movie

SEED_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "movies_seed.csv")


def seed_movies_if_empty(db: Session):
    existing_count = db.query(Movie).count()
    if existing_count > 0:
        return

    with open(SEED_CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        movies = [
            Movie(
                title=row["title"],
                year=int(row["year"]) if row["year"] else None,
                genres=row["genres"],
                overview=row["overview"],
            )
            for row in reader
        ]

    db.bulk_save_objects(movies)
    db.commit()
    print(f"Seeded {len(movies)} movies into the database.")
